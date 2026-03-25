# -*- coding: utf-8 -*-
{
    'name': 'Tính Lương',
    'version': '1.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Quản lý bảng lương nhân viên',
    'description': """
Quản Lý Tính Lương
==================
Module quản lý tính lương nhân viên bao gồm:
* Tính lương tự động từ dữ liệu chấm công
* Tính OT, thưởng, phạt
* Quản lý bảo hiểm
* Tính lương thực nhận
* Báo cáo lương
    """,
    'author': 'Your Company',
    'website': 'http://www.yourcompany.com',
    'depends': ['base', 'nhan_su', 'cham_cong'],  # Phụ thuộc vào cham_cong
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_thuong_phat.xml',
        'data/ir_sequence.xml',
        'data/ir_cron.xml',
        'data/email_template_bang_luong.xml',
        'views/loai_thuong_phat_views.xml',
        'views/phieu_thuong_phat_views.xml',
        'views/report_bang_luong.xml',
        'views/bang_luong.xml',
        'views/dashboard_views.xml',
        'views/nhan_vien_inherit.xml',
        'views/menu.xml',
        'wizard/import_bang_luong_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'web/static/lib/Chart/Chart.js',
            'tinh_luong/static/src/css/dashboard.css',
            'tinh_luong/static/src/js/dashboard.js',
        ],
        'web.assets_qweb': [
            'tinh_luong/static/src/xml/dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
