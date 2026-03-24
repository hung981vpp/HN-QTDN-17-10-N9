# -*- coding: utf-8 -*-
{
    'name': 'Chấm Công',
    'version': '1.0',
    'category': 'Human Resources/Attendance',
    'summary': 'Quản lý chấm công nhân viên',
    'description': """
Quản Lý Chấm Công
=================
Module quản lý chấm công nhân viên bao gồm:
* Check-in/Check-out
* Tính giờ làm việc tự động
* Tính giờ OT
* Quản lý trạng thái (đúng giờ, đến muộn, về sớm)
* Xin phép đến muộn/về sớm
    """,
    'author': 'Your Company',
    'website': 'http://www.yourcompany.com',
    'depends': ['base', 'nhan_su', 'mail'],
    'data': [
        'views/cham_cong.xml',
        'views/dot_dang_ky_views.xml',
        'views/dang_ky_ca_lam_views.xml',
        'views/don_tu_views.xml',
        'views/dashboard_views.xml',
        'views/menu.xml',
        'security/ir.model.access.csv',
        'views/cham_cong_face_id_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cham_cong/static/src/css/dashboard.css',
            'cham_cong/static/src/js/dashboard.js',
        ],
        'web.assets_qweb': [
            'cham_cong/static/src/xml/dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
