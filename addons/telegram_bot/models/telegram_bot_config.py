# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

# Bot Token mặc định (được set trong cấu hình)
DEFAULT_TOKEN = '8626565906:AAGYCeNn4PZT15CPx5Dacd57HBNH_Uy6tEQ'


class TelegramBotConfig(models.Model):
    """Cấu hình Telegram Bot"""
    _name = 'telegram.bot.config'
    _description = 'Cấu hình Telegram Bot'

    name = fields.Char(string='Tên cấu hình', default='Telegram Bot Configuration', required=True)
    bot_token = fields.Char(
        string='Bot Token', required=True,
        default=DEFAULT_TOKEN,
        help='Token từ @BotFather trên Telegram'
    )
    bot_name = fields.Char(string='Tên Bot', readonly=True)
    bot_username = fields.Char(string='Username Bot', readonly=True)
    is_active = fields.Boolean(string='Kích hoạt', default=True)

    # GPS Settings
    enable_gps_check = fields.Boolean(string='Kiểm tra vị trí GPS', default=False,
                                      help='Telegram không hỗ trợ share location tự động, nên thường tắt')
    company_latitude = fields.Float(string='Vĩ độ công ty', digits=(10, 7))
    company_longitude = fields.Float(string='Kinh độ công ty', digits=(10, 7))
    gps_radius = fields.Float(string='Bán kính cho phép (m)', default=100.0)

    # Polling Settings
    last_update_id = fields.Integer(string='Last Update ID', default=0)
    last_poll_time = fields.Datetime(string='Lần poll cuối', readonly=True)
    last_error = fields.Text(string='Lỗi cuối cùng', readonly=True)

    _sql_constraints = [
        ('unique_config', 'UNIQUE(id)', 'Chỉ được tạo một cấu hình Telegram Bot!')
    ]

    @api.model
    def get_config(self):
        """Lấy cấu hình Telegram Bot (singleton)"""
        config = self.search([], limit=1)
        if not config:
            config = self.create({
                'name': 'Telegram Bot Configuration',
                'bot_token': DEFAULT_TOKEN,
                'is_active': True,
            })
        return config

    @api.model
    def action_view_config(self):
        """Mở form cấu hình Telegram Bot (luôn mở record cũ, không tạo mới)"""
        config = self.get_config()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cấu hình Telegram Bot',
            'res_model': 'telegram.bot.config',
            'view_mode': 'form',
            'res_id': config.id,
            'target': 'current',
            'flags': {'mode': 'edit'},
        }


    def test_connection(self):
        """Test kết nối với Telegram Bot API"""
        self.ensure_one()

        if not self.bot_token:
            raise UserError('Vui lòng nhập Bot Token!')

        try:
            from ..services.telegram_api import TelegramBotAPI

            api = TelegramBotAPI(self.bot_token)
            result = api.get_me()

            if result and result.get('ok'):
                bot_info = result.get('result', {})
                self.write({
                    'bot_name': bot_info.get('first_name', ''),
                    'bot_username': bot_info.get('username', ''),
                    'last_error': False,
                })

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Kết nối thành công! ✅',
                        'message': f'Bot: @{bot_info.get("username", "Unknown")} ({bot_info.get("first_name", "")})',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                error_msg = f'Không thể kết nối: {result}'
                self.last_error = error_msg
                raise UserError('Không thể kết nối với Telegram. Kiểm tra lại Bot Token.')

        except UserError:
            raise
        except Exception as e:
            error_msg = f'Lỗi kết nối: {str(e)}'
            self.last_error = error_msg
            _logger.error(error_msg)
            raise UserError(error_msg)

    def poll_updates(self):
        """Poll updates từ Telegram (được gọi bởi cron job)"""
        if not self:
            self = self.search([], limit=1)
            if not self:
                _logger.warning('No Telegram Bot Config found. Skipping poll.')
                return

        self.ensure_one()

        if not self.is_active or not self.bot_token:
            _logger.info('Telegram Bot: Not active or no token configured')
            return

        try:
            from ..services.telegram_api import TelegramBotAPI

            api = TelegramBotAPI(self.bot_token)

            # Telegram trả về list updates (offset = last_update_id + 1)
            offset = self.last_update_id + 1 if self.last_update_id else None
            response = api.get_updates(offset=offset, timeout=5)

            if not response or not response.get('ok'):
                _logger.warning(f'Telegram polling failed: {response}')
                return

            updates = response.get('result', [])
            if not updates:
                _logger.debug('No new Telegram updates')
                self.last_poll_time = fields.Datetime.now()
                return

            _logger.info(f'Received {len(updates)} Telegram updates')

            for update in updates:
                update_id = update.get('update_id', 0)
                try:
                    self._handle_update(update, api)
                except Exception as e:
                    _logger.error(f'Error handling update {update_id}: {str(e)}', exc_info=True)

                # Cập nhật last_update_id sau mỗi update
                if update_id > self.last_update_id:
                    self.last_update_id = update_id

            self.last_poll_time = fields.Datetime.now()
            self.last_error = False

        except Exception as e:
            error_msg = f'Telegram polling error: {str(e)}'
            _logger.error(error_msg)
            self.last_error = error_msg

    def _handle_update(self, update, api):
        """Xử lý một update từ Telegram"""
        # Telegram update có thể là message, edited_message, callback_query, v.v.
        message = update.get('message') or update.get('edited_message')
        if not message:
            return

        chat = message.get('chat', {})
        chat_id = str(chat.get('id', ''))
        text = (message.get('text') or '').strip()

        if not chat_id or not text:
            return

        _logger.info(f'Telegram message from {chat_id}: {text}')

        # Tìm user đã liên kết
        telegram_user = self.env['telegram.bot.user'].search([
            ('telegram_chat_id', '=', chat_id)
        ], limit=1)

        command = text.lower().lstrip('/')

        # Xử lý lệnh link (không cần liên kết trước)
        if command.startswith('link ') or command.startswith('link\n'):
            self._handle_link_command(chat_id, text, api)
            return

        # Xử lý lệnh start
        if command == 'start':
            api.send_message(chat_id, self._get_message('welcome'))
            return

        # Các lệnh khác cần liên kết trước
        if not telegram_user or not telegram_user.is_verified:
            api.send_message(chat_id, self._get_message('not_linked'))
            return

        # Cập nhật last interaction
        telegram_user.last_interaction = fields.Datetime.now()

        # Xử lý commands
        if command in ['checkin', 'vao', 'vào']:
            self._handle_checkin(telegram_user, message, api)
        elif command in ['checkout', 'ra']:
            self._handle_checkout(telegram_user, message, api)
        elif command in ['status', 'xem']:
            self._handle_status(telegram_user, api)
        elif command in ['help', 'huongdan', 'hướng dẫn']:
            api.send_message(chat_id, self._get_message('help'))
        else:
            api.send_message(chat_id, '❓ Lệnh không hợp lệ. Gửi /help để xem hướng dẫn.')

    def _handle_link_command(self, chat_id, text, api):
        """Xử lý lệnh link tài khoản: 'link 0123456789'"""
        parts = text.strip().split(maxsplit=1)
        if len(parts) < 2:
            api.send_message(chat_id,
                '❌ Sai cú pháp.\n\nGửi: <code>link &lt;số điện thoại&gt;</code>\nVí dụ: <code>link 0123456789</code>')
            return

        phone = parts[1].strip()

        nhan_vien = self.env['nhan_vien'].search([
            ('so_dien_thoai', '=', phone)
        ], limit=1)

        if not nhan_vien:
            api.send_message(chat_id,
                f'❌ Không tìm thấy nhân viên với SĐT: <b>{phone}</b>\n\nVui lòng kiểm tra lại.')
            return

        existing = self.env['telegram.bot.user'].search([
            ('telegram_chat_id', '=', str(chat_id))
        ], limit=1)

        if existing:
            if existing.id_nhan_vien.id == nhan_vien.id:
                api.send_message(chat_id,
                    f'✅ Bạn đã liên kết với nhân viên: <b>{nhan_vien.ho_va_ten}</b>')
            else:
                existing.write({
                    'id_nhan_vien': nhan_vien.id,
                    'is_verified': True,
                    'linked_date': fields.Datetime.now(),
                })
                api.send_message(chat_id,
                    self._get_message('link_success').format(ten=nhan_vien.ho_va_ten))
        else:
            self.env['telegram.bot.user'].create({
                'telegram_chat_id': str(chat_id),
                'id_nhan_vien': nhan_vien.id,
                'is_verified': True,
                'linked_date': fields.Datetime.now(),
            })
            api.send_message(chat_id,
                self._get_message('link_success').format(ten=nhan_vien.ho_va_ten))

    def _handle_checkin(self, telegram_user, message, api):
        """Xử lý lệnh check-in"""
        # GPS check (nếu bật và user gửi location)
        if self.enable_gps_check:
            location = message.get('location')
            if not location:
                api.send_message(telegram_user.telegram_chat_id,
                    '📍 Vui lòng gửi <b>vị trí hiện tại</b> của bạn trước khi check-in.\n\n'
                    'Cách gửi: nhấn 📎 → Location → Send My Current Location\n'
                    'Sau đó gửi lại lệnh /checkin')
                return

            lat = location.get('latitude')
            lng = location.get('longitude')

            if not self._check_location(lat, lng):
                api.send_message(telegram_user.telegram_chat_id,
                    f'❌ Bạn đang ở ngoài phạm vi công ty (>{self.gps_radius}m).\n'
                    'Vui lòng check-in tại văn phòng.')
                return

        result = self.env['cham_cong'].zalo_checkin(
            telegram_user.id_nhan_vien.id,
            message.get('message_id')
        )
        api.send_message(telegram_user.telegram_chat_id, result['message'])

    def _handle_checkout(self, telegram_user, message, api):
        """Xử lý lệnh check-out"""
        if self.enable_gps_check:
            location = message.get('location')
            if not location:
                api.send_message(telegram_user.telegram_chat_id,
                    '📍 Vui lòng gửi vị trí để check-out: nhấn 📎 → Location')
                return

            lat = location.get('latitude')
            lng = location.get('longitude')

            if not self._check_location(lat, lng):
                api.send_message(telegram_user.telegram_chat_id,
                    '❌ Bạn đang ở ngoài phạm vi công ty. Vui lòng check-out tại văn phòng.')
                return

        result = self.env['cham_cong'].zalo_checkout(
            telegram_user.id_nhan_vien.id,
            message.get('message_id')
        )
        api.send_message(telegram_user.telegram_chat_id, result['message'])

    def _handle_status(self, telegram_user, api):
        """Xử lý lệnh xem trạng thái"""
        result = self.env['cham_cong'].zalo_get_status(telegram_user.id_nhan_vien.id)
        api.send_message(telegram_user.telegram_chat_id, result['message'])

    def _check_location(self, lat, lng):
        """Kiểm tra vị trí có trong bán kính cho phép không"""
        if not self.company_latitude or not self.company_longitude:
            _logger.warning('Company location not configured, skipping GPS check')
            return True

        from math import radians, cos, sin, asin, sqrt
        lon1, lat1, lon2, lat2 = map(radians, [
            self.company_longitude, self.company_latitude, lng, lat
        ])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        distance = c * 6371000  # mét

        _logger.info(f'GPS Check: Distance = {distance:.2f}m, Allowed = {self.gps_radius}m')
        return distance <= self.gps_radius

    def _get_message(self, key):
        """Lấy message template"""
        messages = {
            'welcome': (
                '👋 Chào mừng bạn đến với <b>Bot Chấm Công</b>!\n\n'
                'Gửi <code>link &lt;số điện thoại&gt;</code> để liên kết tài khoản.\n'
                'Ví dụ: <code>link 0123456789</code>'
            ),
            'help': (
                '📖 <b>HƯỚNG DẪN SỬ DỤNG BOT CHẤM CÔNG</b>\n\n'
                '✅ Chấm công:\n'
                '• /checkin hoặc <code>vao</code> → Check-in\n'
                '• /checkout hoặc <code>ra</code> → Check-out\n'
                '• /status hoặc <code>xem</code> → Xem trạng thái\n\n'
                '🔗 Liên kết tài khoản:\n'
                '• <code>link &lt;số điện thoại&gt;</code>\n'
                '• Ví dụ: <code>link 0123456789</code>\n\n'
                '❓ Trợ giúp:\n'
                '• /help → Xem hướng dẫn này'
            ),
            'not_linked': (
                '⚠️ Bạn chưa liên kết tài khoản.\n\n'
                'Gửi: <code>link &lt;số điện thoại&gt;</code>\n'
                'Ví dụ: <code>link 0123456789</code>'
            ),
            'link_success': (
                '🔗 Liên kết thành công với nhân viên: <b>{ten}</b>\n\n'
                'Bạn có thể bắt đầu chấm công:\n'
                '• /checkin → Check-in\n'
                '• /checkout → Check-out\n'
                '• /status → Xem trạng thái'
            ),
        }
        return messages.get(key, '')

    @api.model
    def handle_message_from_daemon(self, chat_id, text, message=None):
        """
        Được gọi từ polling daemon bên ngoài qua JSON-RPC.
        Xử lý ngay lập tức thay vì đợi cron 1 phút.

        Args:
            chat_id (str): Telegram chat ID
            text (str): Nội dung tin nhắn
            message (str): JSON string của toàn bộ message object
        """
        import json as _json

        config = self.get_config()
        if not config.is_active:
            return False

        try:
            from ..services.telegram_api import TelegramBotAPI
            api = TelegramBotAPI(config.bot_token)

            # Rebuild message dict từ JSON string nếu có
            msg_dict = {}
            if message:
                try:
                    msg_dict = _json.loads(message)
                except Exception:
                    msg_dict = {'chat': {'id': chat_id}, 'text': text}
            else:
                msg_dict = {'chat': {'id': chat_id}, 'text': text}

            update = {'message': msg_dict}
            config._handle_update(update, api)

            # Cập nhật thời gian poll
            config.last_poll_time = fields.Datetime.now()
            return True

        except Exception as e:
            _logger.error(f'handle_message_from_daemon error: {str(e)}', exc_info=True)
            return False
