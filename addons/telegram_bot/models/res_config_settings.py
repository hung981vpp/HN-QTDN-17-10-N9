# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Telegram Bot Settings
    telegram_bot_token = fields.Char(
        string='Telegram Bot Token',
        config_parameter='telegram_bot.bot_token',
        help='Token từ @BotFather trên Telegram'
    )
    telegram_bot_active = fields.Boolean(
        string='Kích hoạt Telegram Bot',
        config_parameter='telegram_bot.is_active'
    )
    telegram_enable_gps = fields.Boolean(
        string='Kiểm tra GPS',
        config_parameter='telegram_bot.enable_gps',
        default=False
    )
    telegram_company_lat = fields.Float(
        string='Vĩ độ công ty',
        config_parameter='telegram_bot.company_latitude',
        digits=(10, 7)
    )
    telegram_company_lng = fields.Float(
        string='Kinh độ công ty',
        config_parameter='telegram_bot.company_longitude',
        digits=(10, 7)
    )
    telegram_gps_radius = fields.Float(
        string='Bán kính GPS (m)',
        config_parameter='telegram_bot.gps_radius',
        default=100.0
    )

    def test_telegram_connection(self):
        """Test kết nối Telegram Bot"""
        config = self.env['telegram.bot.config'].get_config()
        if self.telegram_bot_token:
            config.bot_token = self.telegram_bot_token
        config.is_active = self.telegram_bot_active
        config.enable_gps_check = self.telegram_enable_gps
        config.company_latitude = self.telegram_company_lat
        config.company_longitude = self.telegram_company_lng
        config.gps_radius = self.telegram_gps_radius
        return config.test_connection()
