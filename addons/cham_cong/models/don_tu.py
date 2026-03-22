# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class DonTu(models.Model):
    _name = 'don_tu'
    _description = 'Đơn từ xin phép'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'ma_don'
    _order = 'ngay_lam_don desc'
    
    # Basic Info
    ma_don = fields.Char(string='Mã đơn', required=True, copy=False, readonly=True, default='New')
    nhan_vien_id = fields.Many2one('nhan_vien', string='Nhân viên', required=True)
    ngay_lam_don = fields.Date(string='Ngày làm đơn', required=True, default=fields.Date.today)
    ngay_ap_dung = fields.Date(string='Ngày áp dụng', required=True, help='Ngày có hiệu lực')
    ly_do = fields.Text(string='Lý do', required=True, help='Giải thích chi tiết')
    
    # Loại đơn
    loai_don = fields.Selection([
        ('nghi', '🏥 Đơn xin nghỉ'),
        ('di_muon', '⏰ Đơn xin đi muộn'),
        ('ve_som', '🏃 Đơn xin về sớm'),
    ], string='Loại đơn', required=True, default='nghi')
    
    # Thời gian (cho đơn đi muộn/về sớm)
    thoi_gian_xin = fields.Integer(string='Thời gian xin (phút)', help='Số phút xin đi muộn hoặc về sớm')
    
    # Trạng thái duyệt
    trang_thai = fields.Selection([
        ('cho_duyet', '⏳ Chờ duyệt'),
        ('da_duyet', '✅ Đã duyệt'),
        ('tu_choi', '❌ Từ chối'),
    ], string='Trạng thái', default='cho_duyet', required=True, tracking=True)
    
    # Người duyệt
    nguoi_duyet_id = fields.Many2one('res.users', string='Người duyệt', readonly=True)
    ngay_duyet = fields.Datetime(string='Ngày duyệt', readonly=True)
    ghi_chu_duyet = fields.Text(string='Ghi chú duyệt', help='Lý do từ chối hoặc ghi chú khi duyệt')
    
    # Display fields
    ten_nhan_vien = fields.Char(related='nhan_vien_id.ho_va_ten', string='Tên nhân viên', readonly=True)
    
    # Relationships
    cham_cong_id = fields.Many2one('cham_cong', string='Chấm công liên quan', 
                                    compute='_compute_cham_cong_id', store=True)
    trang_thai_cham_cong = fields.Selection([
        ('dung_gio', 'Đúng giờ'),
        ('den_muon', 'Đến muộn'),
        ('ve_som', 'Về sớm'),
        ('lam_them', 'Làm thêm giờ'),
        ('nghi', 'Nghỉ')
    ], string='Trạng thái chấm công', related='cham_cong_id.trang_thai', readonly=True)
    
    _sql_constraints = [
        ('unique_don', 'UNIQUE(nhan_vien_id, ngay_ap_dung, loai_don)', 
         'Nhân viên đã có đơn cùng loại cho ngày này rồi!')
    ]
    
    @api.model
    def create(self, vals):
        if vals.get('ma_don', 'New') == 'New':
            # Tạo mã đơn: DT + YYYYMMDD + sequence
            ngay = vals.get('ngay_lam_don', fields.Date.today())
            if isinstance(ngay, str):
                ngay_str = ngay.replace('-', '')
            else:
                ngay_str = ngay.strftime('%Y%m%d')
            
            # Đếm số đơn trong ngày
            count = self.search_count([('ngay_lam_don', '=', ngay)]) + 1
            vals['ma_don'] = f'DT{ngay_str}{count:03d}'
        return super(DonTu, self).create(vals)
    
    @api.constrains('thoi_gian_xin', 'loai_don')
    def _check_thoi_gian_xin(self):
        """Kiểm tra thời gian xin cho đơn đi muộn/về sớm"""
        for record in self:
            if record.loai_don in ['di_muon', 've_som']:
                if not record.thoi_gian_xin or record.thoi_gian_xin <= 0:
                    raise ValidationError('Đơn xin đi muộn/về sớm phải có thời gian xin (phút) > 0!')
                if record.thoi_gian_xin > 480:  # 8 giờ
                    raise ValidationError('Thời gian xin không được quá 480 phút (8 giờ)!')
    
    @api.constrains('ngay_ap_dung', 'ngay_lam_don')
    def _check_ngay_ap_dung(self):
        """Kiểm tra ngày áp dụng phải >= ngày làm đơn"""
        for record in self:
            if record.ngay_ap_dung < record.ngay_lam_don:
                raise ValidationError('Ngày áp dụng không được nhỏ hơn ngày làm đơn!')
    
    @api.depends('nhan_vien_id', 'ngay_ap_dung')
    def _compute_cham_cong_id(self):
        """Tìm bản ghi chấm công liên quan"""
        for record in self:
            if record.nhan_vien_id and record.ngay_ap_dung:
                cham_cong = self.env['cham_cong'].search([
                    ('id_nhan_vien', '=', record.nhan_vien_id.id),
                    ('ngay', '=', record.ngay_ap_dung)
                ], limit=1)
                record.cham_cong_id = cham_cong.id if cham_cong else False
            else:
                record.cham_cong_id = False
    
    def action_duyet(self):
        """Duyệt đơn"""
        self.ensure_one()
        if self.trang_thai != 'cho_duyet':
            raise ValidationError('Chỉ có thể duyệt đơn đang chờ duyệt!')
        
        self.write({
            'trang_thai': 'da_duyet',
            'nguoi_duyet_id': self.env.user.id,
            'ngay_duyet': fields.Datetime.now(),
        })
        
        # Tự động cập nhật chấm công nếu có
        if self.cham_cong_id:
            self.cham_cong_id.write({'co_xin_phep': True})
        else:
            # Nếu chưa có bản ghi chấm công, tìm lại
            cham_cong = self.env['cham_cong'].search([
                ('id_nhan_vien', '=', self.nhan_vien_id.id),
                ('ngay', '=', self.ngay_ap_dung)
            ], limit=1)
            if cham_cong:
                cham_cong.write({'co_xin_phep': True})
                self.cham_cong_id = cham_cong.id
        
        # Gửi thông báo Zalo
        try:
            self.env['zalo.notification.service'].notify_don_tu_duyet(self.id)
        except Exception as e:
            _logger.warning(f'Không thể gửi thông báo Zalo: {str(e)}')
        
    def action_tu_choi(self):
        """Từ chối đơn"""
        self.ensure_one()
        if self.trang_thai != 'cho_duyet':
            raise ValidationError('Chỉ có thể từ chối đơn đang chờ duyệt!')
        
        self.write({
            'trang_thai': 'tu_choi',
            'nguoi_duyet_id': self.env.user.id,
            'ngay_duyet': fields.Datetime.now(),
        })
        
        # Xóa đánh dấu xin phép nếu có
        if self.cham_cong_id:
            self.cham_cong_id.write({'co_xin_phep': False})
        
        # Gửi thông báo Zalo
        try:
            self.env['zalo.notification.service'].notify_don_tu_tu_choi(self.id)
        except Exception as e:
            _logger.warning(f'Không thể gửi thông báo Zalo: {str(e)}')
    
    def action_reset_to_draft(self):
        """Đưa về chờ duyệt"""
        self.ensure_one()
        self.write({
            'trang_thai': 'cho_duyet',
            'nguoi_duyet_id': False,
            'ngay_duyet': False,
            'ghi_chu_duyet': False,
        })
