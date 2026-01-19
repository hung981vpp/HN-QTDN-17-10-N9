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
        'views/bang_luong.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
