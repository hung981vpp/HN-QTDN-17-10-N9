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
        location = message.get('location')
        photos = message.get('photo', [])

        if not chat_id or (not text and not location and not photos):
            return

        _logger.info(f'Telegram message from {chat_id}: text="{text}", location={bool(location)}, photo={bool(photos)}')

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
        
        # Xử lý gửi ảnh (Face ID Check-in)
        if photos:
            api.send_chat_action(chat_id, 'typing')
            self._handle_faceid_photo(telegram_user, photos, api)
            return

        # Tự động suy luận từ Location
        if location and not text:
            today = fields.Date.today()
            cham_cong = self.env['cham_cong'].search([
                ('id_nhan_vien', '=', telegram_user.id_nhan_vien.id),
                ('ngay', '=', today)
            ], limit=1)
            if cham_cong and cham_cong.gio_vao and not cham_cong.gio_ra:
                command = 'checkout'
            else:
                command = 'checkin'

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
            # Truy vấn AI (Natural Language Query)
            api.send_chat_action(chat_id, 'typing')
            self._handle_ai_chat(telegram_user, text, api)

    def _handle_ai_chat(self, telegram_user, query, api):
        """Xử lý câu hỏi tự nhiên bằng Local AI (Ollama) có Context Database"""
        import requests
        
        chat_id = telegram_user.telegram_chat_id
        msg_resp = api.send_message(chat_id, '⏳ <i>Đang thu thập dữ liệu chuyên cần & lương Odoo...</i>')
        msg_id = msg_resp['result'].get('message_id') if msg_resp and msg_resp.get('ok') else None
        
        try:
            today = fields.Date.today()
            nv = telegram_user.id_nhan_vien
            
            def format_time(f):
                if not f: return "Chưa có"
                try:
                    from datetime import timedelta
                    if hasattr(f, 'strftime'):
                        return (f + timedelta(hours=7)).strftime('%H:%M')
                    else:
                        from datetime import datetime
                        dt = datetime.strptime(str(f), "%Y-%m-%d %H:%M:%S")
                        return (dt + timedelta(hours=7)).strftime('%H:%M')
                except Exception:
                    try:
                        h = int(f)
                        m = int(round((f - h) * 60))
                        return f"{h:02d}:{m:02d}"
                    except:
                        return str(f)
            
            # Context chấm công hôm nay
            cham_cong_hom_nay = self.env['cham_cong'].search([
                ('id_nhan_vien', '=', nv.id),
                ('ngay', '=', today)
            ], limit=1)
            
            hom_nay_text = f"Hôm nay ({today}) CHƯA CHECK-IN."
            if cham_cong_hom_nay:
                if cham_cong_hom_nay.gio_vao and not cham_cong_hom_nay.gio_ra:
                    hom_nay_text = f"Hôm nay ({today}) ĐÃ CHECK-IN lúc {format_time(cham_cong_hom_nay.gio_vao)}, chưa check-out."
                elif cham_cong_hom_nay.gio_vao and cham_cong_hom_nay.gio_ra:
                    hom_nay_text = f"Hôm nay ({today}) ĐÃ CHECK-IN lúc {format_time(cham_cong_hom_nay.gio_vao)} và ĐÃ CHECK-OUT lúc {format_time(cham_cong_hom_nay.gio_ra)}."
            
            # Context chấm công tháng này
            cham_congs = self.env['cham_cong'].search([
                ('id_nhan_vien', '=', nv.id),
                ('ngay', '>=', today.replace(day=1))
            ])
            tong_lam = sum(cham_congs.mapped('tong_so_gio_lam'))
            tong_ot = sum(cham_congs.mapped('gio_ot'))
            so_ngay_tre = len(cham_congs.filtered(lambda c: c.trang_thai in ['vao_tre', 'di_tre_ve_som']))
            
            # Context bảng lương gần nhất
            bang_luong = self.env['bang_luong'].search([('id_nhan_vien', '=', nv.id)], order='id desc', limit=1)
            luong_info = "Nhân viên chưa có bảng lương nào."
            if bang_luong:
                luong_info = f"Kỳ lương mới nhất (Tháng {bang_luong.thang}/{bang_luong.nam}): Lương gốc {bang_luong.luong_co_ban:,.0f}đ. " \
                             f"Thưởng {bang_luong.tong_thuong:,.0f}đ. Phạt (đi trễ, nghỉ): {bang_luong.tong_phat:,.0f}đ. " \
                             f"Thực lĩnh mang về: {bang_luong.luong_thuc_nhan:,.0f}đ."
            
            phong_ban = nv.phong_ban_hien_tai_id.display_name if nv.phong_ban_hien_tai_id else "Chưa có"
            chuc_vu = nv.chuc_vu_hien_tai_id.display_name if nv.chuc_vu_hien_tai_id else "Chưa có"
            hd_map = {'thu_viec': 'Thử việc', 'co_thoi_han': 'Có thời hạn', 'khong_thoi_han': 'Không thời hạn'}
            loai_hd = hd_map.get(nv.loai_hop_dong, "Chưa rõ")
            
            # Super Brain System Prompt
            context = f"Bạn là Giám đốc Nhân sự (HR Manager) ảo của công ty QTDN (Quản Trị Doanh Nghiệp). Tên bạn là 'HR Bot'. " \
                      f"Bạn đang nói chuyện trực tiếp với nhân viên công ty qua hệ thống nội bộ.\n\n" \
                      f"=== HỒ SƠ NHÂN VIÊN ===\n" \
                      f"- Tên: {nv.ho_va_ten} ({nv.tuoi} tuổi). Phòng: {phong_ban}. Chức vụ: {chuc_vu}. Hợp đồng: {loai_hd}\n\n" \
                      f"=== DỮ LIỆU ĐIỂM DANH ({today.strftime('%m/%Y')}) ===\n" \
                      f"- Tính riêng {hom_nay_text}\n" \
                      f"- Lũy kế tháng này: Đi làm {tong_lam:.1f}h, Tăng ca {tong_ot:.1f}h, Trễ/Sớm {so_ngay_tre} lần.\n\n" \
                      f"=== BẢNG LƯƠNG GẦN NHẤT ===\n" \
                      f"- {luong_info}\n\n" \
                      f"=== CHỈ TÍNH CÁCH (PERSONA) ===\n" \
                      f"1. Bạn cực kỳ THÔNG MINH, SẮC BÉN, giải thích cặn kẽ logic tài chính.\n" \
                      f"2. Ví dụ: Nếu nhân viên thắc mắc 'Tại sao lương bị âm?', hãy dùng tư duy IQ cao để suy luận rằng: 'Tiền phạt hoặc tiền đóng bảo hiểm cao hơn mức lương cơ sở (có thể do đi làm 0 ngày)'.\n" \
                      f"3. Xưng hô: 'Tôi' (đại diện HR) và xưng tên nhân viên.\n" \
                      f"4. Kỷ luật thép: KHÔNG BỊA ĐẶT DỮ LIỆU. Chỉ trả lời dựa trên con số ở trên. Trả lời NGẮN GỌN dưới 4 câu."
                      
            payload = {
                "model": "qwen2:1.5b",
                "messages": [
                    {"role": "system", "content": context},
                    {"role": "user", "content": query}
                ],
                "stream": False
            }
            
            if msg_id:
                api.edit_message_text(chat_id, msg_id, '🧠 <i>AI đang đọc suy luận nội dung (Qwen2-Local)...</i>')
                
            # Gửi tới Local Ollama (qua API 11434)
            resp = requests.post('http://localhost:11434/api/chat', json=payload, timeout=60)
            if resp.status_code == 200:
                answer = resp.json().get('message', {}).get('content', '')
                if msg_id:
                    api.edit_message_text(chat_id, msg_id, f"🤖 <b>AI QTDN Trả Lời:</b>\n\n{answer}")
                else:
                    api.send_message(chat_id, f"🤖 <b>AI QTDN Trả Lời:</b>\n\n{answer}")
            else:
                err = "🤖 Cố vấn AI nội bộ hiện đang bận hoặc quá tải, vui lòng thử lại sau."
                if msg_id:
                    api.edit_message_text(chat_id, msg_id, err)
                else:
                    api.send_message(chat_id, err)
                    
        except Exception as e:
            err = f"🤖 Lỗi AI nội bộ Odoo (Ollama service not running or crashed): {str(e)}"
            if msg_id:
                api.edit_message_text(chat_id, msg_id, err)
            else:
                api.send_message(chat_id, err)

    def _handle_faceid_photo(self, telegram_user, photos, api):
        """Xử lý nhận diện khuôn mặt qua ảnh Telegram kèm hiệu ứng loading"""
        chat_id = telegram_user.telegram_chat_id
        
        # 1. Bắt đầu quá trình
        msg_resp = api.send_message(chat_id, '⏳ <b>[10%]</b> Đang khởi tạo bộ phân tích...')
        msg_id = None
        if msg_resp and msg_resp.get('ok'):
            msg_id = msg_resp['result'].get('message_id')
            
        def update_progress(text):
            if msg_id:
                api.edit_message_text(chat_id, msg_id, text)
            else:
                api.send_message(chat_id, text)

        try:
            import face_recognition
            import numpy as np
            import cv2
            import base64
            import time
        except ImportError as e:
            update_progress(f'❌ Hệ thống chưa cài đặt đủ thư viện ({str(e)}). Vui lòng liên hệ Admin.')
            return

        time.sleep(0.5)
        update_progress('⏳ <b>[30%]</b> Đang tải ảnh độ phân giải cao từ hệ thống...')
        
        # Lấy file_id lớn nhất (độ phân giải cao nhất)
        file_id = photos[-1]['file_id']
        file_info = api.get_file(file_id)
        if not file_info or not file_info.get('ok'):
            update_progress('❌ Không thể lấy thông tin ảnh từ Telegram.')
            return
            
        file_path = file_info['result'].get('file_path')
        img_bytes = api.download_file(file_path)
        if not img_bytes:
            update_progress('❌ Lỗi tải ảnh từ hệ thống lưu trữ.')
            return
            
        try:
            time.sleep(0.6)
            update_progress('⏳ <b>[50%]</b> Đang trích xuất đặc điểm khuôn mặt...')
            
            # 1. Decode ảnh từ Telegram
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                update_progress('❌ Không thể đọc định dạng ảnh.')
                return
                
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            face_encodings = face_recognition.face_encodings(rgb_img)
            
            if not face_encodings:
                update_progress('❌ Không tìm thấy khuôn mặt nào trong ảnh. Hãy nhìn thẳng và đủ sáng!')
                return
            if len(face_encodings) > 1:
                update_progress('❌ Có quá nhiều khuôn mặt. Hãy chụp một mình bạn!')
                return
                
            current_face_encoding = face_encodings[0]
            
            time.sleep(0.6)
            update_progress('⏳ <b>[75%]</b> Đang đối chiếu với kho dữ liệu nhân sự...')
            
            # 2. Decode ảnh hồ sơ của nhân viên
            nv = telegram_user.id_nhan_vien
            if not nv.anh:
                update_progress('❌ Tài khoản của bạn chưa cập nhật Ảnh chân dung. Vui lòng liên hệ HR!')
                return
                
            nv_img_data = base64.b64decode(nv.anh)
            nv_nparr = np.frombuffer(nv_img_data, np.uint8)
            nv_img = cv2.imdecode(nv_nparr, cv2.IMREAD_COLOR)
            
            if nv_img is None:
                update_progress('❌ Ảnh chân dung trong Hồ sơ bị lỗi định dạng. Cần cập nhật lại.')
                return
                
            nv_rgb_img = cv2.cvtColor(nv_img, cv2.COLOR_BGR2RGB)
            nv_encodings = face_recognition.face_encodings(nv_rgb_img)
            
            if not nv_encodings:
                update_progress('❌ Không thể trích xuất khuôn mặt từ Ảnh hồ sơ của bạn. Cần cập nhật ảnh RÕ MẶT.')
                return
                
            time.sleep(0.6)
            update_progress('⏳ <b>[95%]</b> Đang tính toán độ lệch đồng dạng sinh trắc học...')
            
            # 3. So sánh
            distance = face_recognition.face_distance([nv_encodings[0]], current_face_encoding)[0]
            threshold = 0.50
            if distance >= threshold:
                update_progress(f'❌ <b>[100%]</b> Khuôn mặt trong ảnh không khớp với hồ sơ (Độ lệch {distance:.2f} >= {threshold}).')
                return
                
            time.sleep(0.6)
            # 4. Thành công -> Checkin/Checkout
            today = fields.Date.today()
            cham_cong = self.env['cham_cong'].search([
                ('id_nhan_vien', '=', nv.id),
                ('ngay', '=', today)
            ], limit=1)
            
            if not cham_cong or not cham_cong.gio_vao:
                result = self.env['cham_cong'].zalo_checkin(nv.id, "FaceID_Telegram")
                msg = f"✅ <b>[100%] TRỰC THUỘC TÀI KHOẢN HỢP LỆ</b>\n📸 Nhận diện thành công ({100 - distance*100:.1f}%)\n\n" + result['message']
            else:
                if not cham_cong.gio_ra:
                    result = self.env['cham_cong'].zalo_checkout(nv.id, "FaceID_Telegram")
                    msg = f"✅ <b>[100%] TRỰC THUỘC TÀI KHOẢN HỢP LỆ</b>\n📸 Nhận diện thành công ({100 - distance*100:.1f}%)\n\n" + result['message']
                else:
                    msg = f"✅ <b>[100%] TRỰC THUỘC TÀI KHOẢN HỢP LỆ</b>\n📸 Chào {nv.ho_va_ten}, bạn đã hoàn tất cả check-in và check-out đủ cho hôm nay rồi!"
            
            update_progress(msg)

        except Exception as e:
            _logger.error(f'Face Decode Error Telegram: {str(e)}')
            update_progress(f'❌ Xử lý ảnh lỗi: {str(e)}')


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
                    '📍 Vui lòng gửi <b>vị trí hiện tại (Location)</b> thay thế cho tin nhắn /checkin.\n\n'
                    'Cách gửi trên điện thoại: Nhấn nút 📎 đính kèm → Chọn Location/Vị trí → Chọn Send My Current Location\n'
                    'Hệ thống sẽ tự nhận diện thời gian và vị trí để tự check-in!')
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
                    '📍 Vui lòng gửi <b>vị trí hiện tại (Location)</b> thay thế cho tin nhắn /checkout.\n\n'
                    'Hệ thống sẽ tự nhận diện điểm danh ra về khi nhận được vị trí.')
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

    @api.model
    def cron_send_daily_report(self):
        """Cron job gửi báo cáo chuyên cần cuối ngày cho tất cả nhân sự đã liên kết Telegram"""
        import datetime
        
        today = fields.Date.today()
        users = self.env['telegram.bot.user'].search([('is_verified', '=', True)])
        
        if not users:
            return
            
        config = self.get_config()
        if not config.bot_token or not config.is_active:
            return
            
        from ..services.telegram_api import TelegramBotAPI
        api = TelegramBotAPI(config.bot_token)
        
        for user in users:
            cham_cong = self.env['cham_cong'].search([
                ('id_nhan_vien', '=', user.id_nhan_vien.id),
                ('ngay', '=', today)
            ], limit=1)
            
            msg = f"🌅 <b>Báo cáo điểm danh ngày {today.strftime('%d/%m/%Y')}</b>\n\n"
            msg += f"👤 Nhân viên: <b>{user.id_nhan_vien.ho_va_ten}</b>\n"
            
            if not cham_cong:
                msg += "\n❌ Bạn KHÔNG có dữ liệu chấm công ngày hôm nay (Vắng mặt)."
            else:
                import pytz
                tz = pytz.timezone('Asia/Ho_Chi_Minh')
                
                gio_vao = '---'
                if cham_cong.gio_vao:
                    gio_vao = pytz.utc.localize(cham_cong.gio_vao.replace(tzinfo=None)).astimezone(tz).strftime('%H:%M')
                    
                gio_ra = '---'
                if cham_cong.gio_ra:
                    gio_ra = pytz.utc.localize(cham_cong.gio_ra.replace(tzinfo=None)).astimezone(tz).strftime('%H:%M')
                
                msg += f"\n✅ Giờ vào: {gio_vao}"
                msg += f"\n📤 Giờ ra: {gio_ra}"
                msg += f"\n⏱️ Tổng làm: {cham_cong.tong_so_gio_lam:.1f}h"
                
                if cham_cong.gio_ot > 0:
                    msg += f"\n⏰ OT: {cham_cong.gio_ot:.1f}h"
                    
                trang_thai_dict = dict(cham_cong._fields['trang_thai'].selection)
                msg += f"\n📌 Trạng thái: <b>{trang_thai_dict.get(cham_cong.trang_thai, 'N/A')}</b>"
                
            msg += "\n\n<i>Chúc bạn một buổi tối vui vẻ!</i> 🌙"
            
            try:
                api.send_message(user.telegram_chat_id, msg)
                _logger.info(f"Đã gửi báo cáo Telegram cuối ngày cho {user.id_nhan_vien.ho_va_ten}")
            except Exception as e:
                _logger.error(f"Cannot send daily report to {user.id_nhan_vien.ho_va_ten}: {e}")
