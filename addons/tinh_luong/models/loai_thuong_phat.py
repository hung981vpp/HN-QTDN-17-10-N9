# -*- coding: utf-8 -*-
from odoo import models, fields

class LoaiThuongPhat(models.Model):
    _name = 'thuong.phat.loai'
    _description = 'Loại Thưởng Phạt'
    _rec_name = 'ten_loai'

    ten_loai = fields.Char(string='Tên Quyết Định/Loại', required=True)
    tinh_chat = fields.Selection([
        ('thuong', 'Thưởng (+)'),
        ('phat', 'Phạt (-)')
    ], string='Tính chất', required=True, default='thuong')
    
    so_tien_mac_dinh = fields.Float(string='Số tiền mặc định (VND)', default=0.0, help='Để 0 nếu tùy biến mỗi lần lập phiếu')
    ghi_chu = fields.Text(string='Ghi chú/Quy định')
    active = fields.Boolean(string='Hoạt động', default=True)
