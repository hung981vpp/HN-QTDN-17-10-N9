# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime
from calendar import monthrange
import logging

_logger = logging.getLogger(__name__)


class DotDangKy(models.Model):
    _name = 'dot_dang_ky'
    _description = 'Đợt đăng ký ca làm'
    _rec_name = 'ten_dot'
    _order = 'nam_dang_ky desc, thang_dang_ky desc'
    
    # Basic Info
    ma_dot = fields.Char(string='Mã đợt', required=True, copy=False, readonly=True, default='New')
    active = fields.Boolean(string='Active', default=True)
    ten_dot = fields.Char(string='Tên đợt', compute='_compute_ten_dot', store=True)
    
    # Time Period
    nam_dang_ky = fields.Integer(string='Năm đăng ký', required=True, default=lambda self: datetime.now().year)
    thang_dang_ky = fields.Selection([
        ('1', 'Tháng 1'),
        ('2', 'Tháng 2'),
        ('3', 'Tháng 3'),
        ('4', 'Tháng 4'),
        ('5', 'Tháng 5'),
        ('6', 'Tháng 6'),
        ('7', 'Tháng 7'),
        ('8', 'Tháng 8'),
        ('9', 'Tháng 9'),
        ('10', 'Tháng 10'),
        ('11', 'Tháng 11'),
        ('12', 'Tháng 12'),
    ], string='Tháng đăng ký', required=True, default=str(datetime.now().month))
    
    ngay_bat_dau = fields.Date(string='Ngày bắt đầu', compute='_compute_ngay_bat_dau_ket_thuc', store=True)
    ngay_ket_thuc = fields.Date(string='Ngày kết thúc', compute='_compute_ngay_bat_dau_ket_thuc', store=True)
    
    # Registration Settings
    nhan_vien_ids = fields.Many2many('nhan_vien', string='Nhân viên được đăng ký', help='Danh sách nhân viên được phép đăng ký ca làm')
    han_dang_ky = fields.Date(string='Hạn đăng ký', help='Deadline để nhân viên đăng ký ca làm')
    
    # Status
    trang_thai_dang_ky = fields.Selection([
        ('dang_mo', 'Đang mở'),
        ('het_han', 'Đã hết hạn'),
        ('da_dong', 'Đã đóng'),
    ], string='Trạng thái đăng ký', default='dang_mo', required=True)
    
    trang_thai_ap_dung = fields.Selection([
        ('chua_ap_dung', 'Chưa áp dụng'),
        ('dang_ap_dung', 'Đang áp dụng'),
        ('ngung_ap_dung', 'Ngừng áp dụng'),
    ], string='Trạng thái áp dụng', default='chua_ap_dung', required=True)
    
    # Relations
    dang_ky_ca_ids = fields.One2many('dang_ky_ca_lam_theo_ngay', 'dot_dang_ky_id', string='Đăng ký ca làm')
    
    # Statistics
    so_luong_nhan_vien = fields.Integer(string='Số lượng nhân viên', compute='_compute_so_luong_nhan_vien')
    so_luong_dang_ky = fields.Integer(string='Số lượng đăng ký', compute='_compute_so_luong_dang_ky')
    so_ngay_cham_cong = fields.Integer(string='Số ngày chấm công', compute='_compute_so_ngay_cham_cong', 
                                        help='Tổng số ngày đã chấm công trong đợt')
    ty_le_cham_cong = fields.Float(string='Tỷ lệ chấm công (%)', compute='_compute_ty_le_cham_cong',
                                    help='Tỷ lệ % chấm công so với đăng ký')
    
    _sql_constraints = [
        ('unique_dot', 'UNIQUE(nam_dang_ky, thang_dang_ky)', 'Đã tồn tại đợt đăng ký cho tháng này!')
    ]
    
    @api.model
    def create(self, vals):
        if vals.get('ma_dot', 'New') == 'New':
            # Tạo mã đợt: DDK + YYYYMM
            nam = vals.get('nam_dang_ky', datetime.now().year)
            thang = vals.get('thang_dang_ky', str(datetime.now().month))
            vals['ma_dot'] = f'DDK{nam}{int(thang):02d}'
        return super(DotDangKy, self).create(vals)
    
    @api.depends('thang_dang_ky', 'nam_dang_ky')
    def _compute_ten_dot(self):
        for record in self:
            if record.thang_dang_ky and record.nam_dang_ky:
                record.ten_dot = f'Tháng {record.thang_dang_ky}/{record.nam_dang_ky}'
            else:
                record.ten_dot = 'Chưa xác định'
    
    @api.depends('thang_dang_ky', 'nam_dang_ky')
    def _compute_ngay_bat_dau_ket_thuc(self):
        for record in self:
            if record.thang_dang_ky and record.nam_dang_ky:
                thang = int(record.thang_dang_ky)
                nam = record.nam_dang_ky
                
                # Ngày đầu tháng
                record.ngay_bat_dau = datetime(nam, thang, 1).date()
                
                # Ngày cuối tháng
                _, ngay_cuoi = monthrange(nam, thang)
                record.ngay_ket_thuc = datetime(nam, thang, ngay_cuoi).date()
            else:
                record.ngay_bat_dau = False
                record.ngay_ket_thuc = False
    
    @api.depends('nhan_vien_ids')
    def _compute_so_luong_nhan_vien(self):
        for record in self:
            record.so_luong_nhan_vien = len(record.nhan_vien_ids)
    
    @api.depends('dang_ky_ca_ids')
    def _compute_so_luong_dang_ky(self):
        for record in self:
            record.so_luong_dang_ky = len(record.dang_ky_ca_ids)
    
    @api.depends('ngay_bat_dau', 'ngay_ket_thuc', 'nhan_vien_ids')
    def _compute_so_ngay_cham_cong(self):
        """Tính tổng số ngày chấm công trong đợt"""
        for record in self:
            if record.ngay_bat_dau and record.ngay_ket_thuc and record.nhan_vien_ids:
                cham_cong_count = self.env['cham_cong'].search_count([
                    ('id_nhan_vien', 'in', record.nhan_vien_ids.ids),
                    ('ngay', '>=', record.ngay_bat_dau),
                    ('ngay', '<=', record.ngay_ket_thuc)
                ])
                record.so_ngay_cham_cong = cham_cong_count
            else:
                record.so_ngay_cham_cong = 0
    
    @api.depends('so_ngay_cham_cong', 'so_luong_dang_ky')
    def _compute_ty_le_cham_cong(self):
        """Tính tỷ lệ % chấm công so với đăng ký"""
        for record in self:
            if record.so_luong_dang_ky > 0:
                record.ty_le_cham_cong = (record.so_ngay_cham_cong / record.so_luong_dang_ky) * 100
            else:
                record.ty_le_cham_cong = 0.0
    
    def action_dong_dang_ky(self):
        """Đóng đăng ký"""
        self.ensure_one()
        self.trang_thai_dang_ky = 'da_dong'
    
    def action_mo_dang_ky(self):
        """Mở lại đăng ký"""
        self.ensure_one()
        self.trang_thai_dang_ky = 'dang_mo'
    
    def action_ap_dung(self):
        """Áp dụng đợt đăng ký"""
        self.ensure_one()
        self.trang_thai_ap_dung = 'dang_ap_dung'
    
    def action_ngung_ap_dung(self):
        """Ngừng áp dụng"""
        self.ensure_one()
        self.trang_thai_ap_dung = 'ngung_ap_dung'
