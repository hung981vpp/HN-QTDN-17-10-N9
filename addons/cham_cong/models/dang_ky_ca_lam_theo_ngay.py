# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class DangKyCaLamTheoNgay(models.Model):
    _name = 'dang_ky_ca_lam_theo_ngay'
    _description = "Đăng ký ca làm theo ngày"
    _rec_name = 'ma_dot_ngay'
    _order = 'dot_dang_ky_id desc, ngay_lam asc'
    
    ma_dot_ngay = fields.Char("Mã đợt ngày", required=True, copy=False, readonly=True, default='New')
    dot_dang_ky_id = fields.Many2one('dot_dang_ky', string="Đợt đăng ký", required=True, ondelete='cascade')
    nhan_vien_id = fields.Many2one('nhan_vien', string="Nhân viên", required=True)
    ngay_lam = fields.Date(string="Ngày làm", required=True)

    ca_lam = fields.Selection([
        ("", ""),
        ("sang", "Sáng"),
        ("chieu", "Chiều"),
        ("ca_ngay", "Cả Ngày"),
        ("cong_tac", "Đi Công Tác (Cả Ngày)"),
    ], string="Ca làm", default="")
    
    # Approval Status
    trang_thai = fields.Selection([
        ('nhap', 'Nháp'),
        ('cho_duyet', 'Chờ duyệt'),
        ('da_duyet', 'Đã duyệt'),
        ('tu_choi', 'Từ chối')
    ], string='Trạng thái', default='nhap', required=True, tracking=True)
    
    ly_do_tu_choi = fields.Text(string='Lý do từ chối')
    nguoi_duyet_id = fields.Many2one('res.users', string='Người duyệt', readonly=True)
    ngay_duyet = fields.Datetime(string='Ngày duyệt', readonly=True)
    
    # Display fields
    ten_nhan_vien = fields.Char(related='nhan_vien_id.ho_va_ten', string='Tên nhân viên', readonly=True)
    ten_dot = fields.Char(related='dot_dang_ky_id.ten_dot', string='Tên đợt', readonly=True)
    
    # Relationships
    cham_cong_ids = fields.One2many('cham_cong', 'dang_ky_ca_id', string='Chấm công')
    da_cham_cong = fields.Boolean(string='Đã chấm công', compute='_compute_da_cham_cong', store=True)
    trang_thai_cham_cong = fields.Selection([
        ('dung_gio', 'Đúng giờ'),
        ('den_muon', 'Đến muộn'),
        ('ve_som', 'Về sớm'),
        ('lam_them', 'Làm thêm giờ'),
        ('nghi', 'Nghỉ'),
        ('chua_cham', 'Chưa chấm')
    ], string='Trạng thái chấm công', compute='_compute_trang_thai_cham_cong', store=True)
    
    _sql_constraints = [
        ('unique_dang_ky', 'UNIQUE(dot_dang_ky_id, nhan_vien_id, ngay_lam)', 
         'Nhân viên đã đăng ký ca làm cho ngày này rồi!')
    ]
    
    @api.model
    def create(self, vals):
        if vals.get('ma_dot_ngay', 'New') == 'New':
            # Tạo mã: DKTN + sequence
            sequence = self.env['ir.sequence'].next_by_code('dang_ky_ca_lam_theo_ngay.sequence')
            if not sequence:
                # Fallback nếu sequence chưa tạo
                count = self.search_count([]) + 1
                sequence = f'{count:05d}'
            vals['ma_dot_ngay'] = f'DKTN{sequence}'
        return super(DangKyCaLamTheoNgay, self).create(vals)
    
    @api.constrains('ngay_lam', 'dot_dang_ky_id')
    def _check_ngay_lam(self):
        for record in self:
            if record.ngay_lam and record.dot_dang_ky_id:
                if record.ngay_lam < record.dot_dang_ky_id.ngay_bat_dau or record.ngay_lam > record.dot_dang_ky_id.ngay_ket_thuc:
                    raise ValidationError(
                        f'Ngày làm phải nằm trong khoảng thời gian của đợt đăng ký '
                        f'(từ {record.dot_dang_ky_id.ngay_bat_dau} đến {record.dot_dang_ky_id.ngay_ket_thuc})'
                    )
    
    @api.constrains('nhan_vien_id', 'dot_dang_ky_id')
    def _check_nhan_vien_in_dot_dang_ky(self):
        for record in self:
            if record.nhan_vien_id not in record.dot_dang_ky_id.nhan_vien_ids:
                raise ValidationError(
                    f'Nhân viên {record.nhan_vien_id.ho_va_ten} không thuộc đợt đăng ký này!'
                )
    
    @api.constrains('dot_dang_ky_id')
    def _check_trang_thai_dang_ky(self):
        """Kiểm tra đợt đăng ký còn mở không"""
        for record in self:
            if record.dot_dang_ky_id.trang_thai_dang_ky == 'da_dong':
                raise ValidationError('Đợt đăng ký đã đóng, không thể đăng ký ca làm!')
            if record.dot_dang_ky_id.trang_thai_dang_ky == 'het_han':
                raise ValidationError('Đợt đăng ký đã hết hạn!')
    
    @api.depends('cham_cong_ids')
    def _compute_da_cham_cong(self):
        """Kiểm tra xem đã chấm công chưa"""
        for record in self:
            record.da_cham_cong = bool(record.cham_cong_ids)
    
    @api.depends('cham_cong_ids', 'cham_cong_ids.trang_thai')
    def _compute_trang_thai_cham_cong(self):
        """Lấy trạng thái chấm công mới nhất"""
        for record in self:
            if record.cham_cong_ids:
                # Lấy bản ghi chấm công mới nhất
                cham_cong_moi_nhat = record.cham_cong_ids.sorted(key=lambda r: r.create_date, reverse=True)[0]
                record.trang_thai_cham_cong = cham_cong_moi_nhat.trang_thai
            else:
                record.trang_thai_cham_cong = 'chua_cham'
    
    def action_gui_duyet(self):
        """Gửi yêu cầu duyệt"""
        self.ensure_one()
        if self.trang_thai != 'nhap':
            raise ValidationError('Chỉ có thể gửi duyệt phiếu ở trạng thái nháp!')
        self.write({'trang_thai': 'cho_duyet'})
    
    def action_duyet(self):
        """Duyệt đăng ký"""
        self.ensure_one()
        if self.trang_thai != 'cho_duyet':
            raise ValidationError('Chỉ có thể duyệt phiếu đang chờ duyệt!')
            
        self.write({
            'trang_thai': 'da_duyet',
            'nguoi_duyet_id': self.env.user.id,
            'ngay_duyet': fields.Datetime.now()
        })
        
        # Gửi thông báo Telegram
        try:
            self.env['telegram.notification.service'].notify_dang_ky_duyet(self.id)
        except Exception as e:
            _logger.exception(f'Không thể gửi thông báo Telegram: {str(e)}')
            
    def action_tu_choi(self):
        self.ensure_one()
        if self.trang_thai != 'cho_duyet':
            raise ValidationError('Chỉ có thể từ chối phiếu đang chờ duyệt!')
            
        self.write({
            'trang_thai': 'tu_choi',
            'nguoi_duyet_id': self.env.user.id,
            'ngay_duyet': fields.Datetime.now()
        })
        
        # Gửi thông báo Telegram
        try:
            self.env['telegram.notification.service'].notify_dang_ky_tu_choi(self.id, self.ly_do_tu_choi)
        except Exception as e:
            _logger.warning(f'Không thể gửi thông báo Telegram: {str(e)}')
            
    def action_reset(self):
        self.ensure_one()
        self.write({
            'trang_thai': 'nhap',
            'nguoi_duyet_id': False,
            'ngay_duyet': False,
            'ly_do_tu_choi': False
        })
