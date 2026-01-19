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
    'depends': ['base', 'nhan_su'],
    'data': [
        'security/ir.model.access.csv',
        'views/cham_cong.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
