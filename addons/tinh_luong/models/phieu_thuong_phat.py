# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PhieuThuongPhat(models.Model):
    _name = 'thuong.phat.phieu'
    _description = 'Phiếu Thưởng Phạt'
    _rec_name = 'so_phieu'
    _order = 'ngay_lap desc'

    so_phieu = fields.Char(string='Số Phiếu', required=True, copy=False, readonly=True, default='Mới')
    loai_id = fields.Many2one('thuong.phat.loai', string='Loại Quyết Định', required=True)
    tinh_chat = fields.Selection(related='loai_id.tinh_chat', string='Tính chất', store=True)
    
    nhan_vien_ids = fields.Many2many('nhan_vien', string='Danh sách Nhân viên', required=True)
    ngay_lap = fields.Date(string='Ngày lập phiếu', default=fields.Date.context_today)
    ngay_ap_dung = fields.Date(string='Tháng tính lương (áp dụng)', default=fields.Date.context_today, help="Sẽ quyết định phiếu này được tính vào bảng lương của tháng nào")
    
    so_tien = fields.Float(string='Số tiền (VND)/Người', required=True)
    tong_tien = fields.Float(string='Tổng tiền', compute='_compute_tong_tien', store=True)

    ly_do = fields.Text(string='Lý do chi tiết')
    
    state = fields.Selection([
        ('nhap', 'Mới nhập'),
        ('cho_duyet', 'Chờ duyệt'),
        ('da_duyet', 'Đã duyệt'),
        ('tu_choi', 'Từ chối')
    ], string='Trạng thái', default='nhap', tracking=True)

    nguoi_duyet_id = fields.Many2one('res.users', string='Người duyệt', readonly=True)
    ngay_duyet = fields.Datetime(string='Ngày duyệt', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('so_phieu', 'Mới') == 'Mới':
            # Có thể dùng sequence, tạm thời auto generate bằng datetime/mã định danh
            vals['so_phieu'] = self.env['ir.sequence'].next_by_code('thuong.phat.phieu') or 'TP'
        return super(PhieuThuongPhat, self).create(vals)

    @api.onchange('loai_id')
    def _onchange_loai_id(self):
        if self.loai_id and self.loai_id.so_tien_mac_dinh > 0:
            self.so_tien = self.loai_id.so_tien_mac_dinh

    @api.depends('nhan_vien_ids', 'so_tien')
    def _compute_tong_tien(self):
        for rec in self:
            rec.tong_tien = len(rec.nhan_vien_ids) * rec.so_tien

    def action_gui_duyet(self):
        self.state = 'cho_duyet'

    def action_duyet(self):
        if self.so_tien <= 0:
            raise ValidationError("Số tiền phải lớn hơn 0!")
        if not self.nhan_vien_ids:
            raise ValidationError("Phải chọn ít nhất 1 nhân viên!")
        
        self.state = 'da_duyet'
        self.nguoi_duyet_id = self.env.user.id
        self.ngay_duyet = fields.Datetime.now()

    def action_tu_choi(self):
        self.state = 'tu_choi'

    def action_huy(self):
        self.state = 'nhap'
        self.nguoi_duyet_id = False
        self.ngay_duyet = False
