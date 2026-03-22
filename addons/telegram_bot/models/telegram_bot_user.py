# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class TelegramBotUser(models.Model):
    """Liên kết Telegram Chat ID với Nhân viên"""
    _name = 'telegram.bot.user'
    _description = 'Telegram Bot User'
    _rec_name = 'display_name_full'

    telegram_chat_id = fields.Char(
        string='Telegram Chat ID', required=True, index=True,
        help='Chat ID từ Telegram (số nguyên âm với group, dương với private chat)'
    )
    display_name_full = fields.Char(
        string='Tên hiển thị',
        compute='_compute_display_name_full', store=True
    )

    id_nhan_vien = fields.Many2one('nhan_vien', string='Nhân viên', required=True, ondelete='cascade')
    is_verified = fields.Boolean(string='Đã xác thực', default=False)

    linked_date = fields.Datetime(string='Ngày liên kết', default=fields.Datetime.now)
    last_interaction = fields.Datetime(string='Tương tác cuối')

    _sql_constraints = [
        ('unique_telegram_chat', 'UNIQUE(telegram_chat_id)',
         'Telegram Chat ID này đã được liên kết với nhân viên khác!')
    ]

    @api.depends('id_nhan_vien', 'telegram_chat_id')
    def _compute_display_name_full(self):
        for record in self:
            if record.id_nhan_vien:
                record.display_name_full = f'{record.id_nhan_vien.ho_va_ten} ({record.telegram_chat_id})'
            else:
                record.display_name_full = record.telegram_chat_id or 'Unknown'

    def send_message(self, text):
        """Gửi tin nhắn đến user này qua Telegram"""
        self.ensure_one()

        config = self.env['telegram.bot.config'].get_config()
        if not config.is_active or not config.bot_token:
            _logger.warning('Telegram Bot chưa được cấu hình hoặc chưa kích hoạt')
            return False

        try:
            from ..services.telegram_api import TelegramBotAPI

            api = TelegramBotAPI(config.bot_token)
            result = api.send_message(self.telegram_chat_id, text)

            if result and result.get('ok'):
                _logger.info(f'Telegram message sent to chat_id {self.telegram_chat_id}')
                return True
            else:
                _logger.error(f'Failed to send Telegram message to {self.telegram_chat_id}: {result}')
                return False

        except Exception as e:
            _logger.error(f'Error sending Telegram message: {str(e)}')
            return False
