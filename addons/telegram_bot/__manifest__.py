# -*- coding: utf-8 -*-
{
    'name': 'Telegram Bot Integration',
    'version': '1.0',
    'category': 'Human Resources/Attendance',
    'summary': 'Tích hợp Telegram Bot cho chấm công và thông báo',
    'description': """
Telegram Bot Integration
========================
Module tích hợp Telegram Bot để nhân viên chấm công và nhận thông báo qua Telegram:
* Check-in/Check-out qua Telegram Bot
* Liên kết tài khoản Telegram với nhân viên (số điện thoại)
* Kiểm tra vị trí GPS khi chấm công
* Polling mechanism để nhận tin nhắn
* Bot commands: checkin, checkout, status, link, help
* Thông báo duyệt/từ chối đăng ký ca làm
    """,
    'author': 'Your Company',
    'website': 'http://www.yourcompany.com',
    'depends': ['base', 'nhan_su', 'cham_cong'],
    'external_dependencies': {
        'python': ['requests'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/telegram_bot_config_views.xml',
        'views/telegram_bot_user_views.xml',
        'views/menu.xml',
        'data/ir_cron.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
