# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, time
import logging
import pytz

_logger = logging.getLogger(__name__)

class ChamCong(models.Model):
    _name = 'cham_cong'
    _description = 'Chấm công'
    _order = 'ngay desc'

    ma_cham_cong = fields.Char(string='Mã chấm công', required=True, copy=False, readonly=True, default='New')
    id_nhan_vien = fields.Many2one('nhan_vien', string='Nhân viên', required=True)
    ngay = fields.Date(string='Ngày', required=True, default=fields.Date.today)
    gio_vao = fields.Datetime(string='Giờ vào (Check-in)')
    gio_ra = fields.Datetime(string='Giờ ra (Check-out)')
    gio_nghi = fields.Float(string='Giờ nghỉ (giờ)', default=1.5)  # Nghỉ trưa 1.5 giờ
    tong_so_gio_lam = fields.Float(string='Tổng số giờ làm', compute='_compute_tong_gio_lam', store=True)
    gio_ot = fields.Float(string='Giờ OT', compute='_compute_gio_ot', store=True)
    trang_thai = fields.Selection([
        ('dung_gio', 'Đúng giờ'),
        ('den_muon', 'Đến muộn'),
        ('ve_som', 'Về sớm'),
        ('lam_them', 'Làm thêm giờ'),
        ('nghi', 'Nghỉ')
    ], string='Trạng thái', compute='_compute_trang_thai', store=True)
    co_xin_phep = fields.Boolean(string='Có xin phép', default=False, help='Đánh dấu nếu nhân viên đã xin phép đến muộn/về sớm')
    ghi_chu = fields.Text(string='Ghi chú')

    @api.model
    def create(self, vals):
        if vals.get('ma_cham_cong', 'New') == 'New':
            # Thử lấy từ sequence trước
            ma_moi = self.env['ir.sequence'].next_by_code('cham_cong.sequence')
            
            # Nếu sequence không hoạt động hoặc bị trùng, tự tạo mã mới
            if not ma_moi or ma_moi == 'New':
                # Tìm số lớn nhất hiện có
                self.env.cr.execute("""
                    SELECT ma_cham_cong FROM cham_cong 
                    WHERE ma_cham_cong ~ '^CC[0-9]+$' 
                    ORDER BY CAST(SUBSTRING(ma_cham_cong FROM 3) AS INTEGER) DESC 
                    LIMIT 1
                """)
                result = self.env.cr.fetchone()
                if result:
                    # Lấy số từ mã cũ và tăng lên 1
                    so_cu = int(result[0][2:])  # Bỏ 'CC' ở đầu
                    ma_moi = f'CC{so_cu + 1:05d}'
                else:
                    ma_moi = 'CC00001'
            
            vals['ma_cham_cong'] = ma_moi
        return super(ChamCong, self).create(vals)

    @api.depends('gio_vao', 'gio_ra', 'gio_nghi')
    def _compute_tong_gio_lam(self):
        for record in self:
            if record.gio_vao and record.gio_ra:
                delta = record.gio_ra - record.gio_vao
                tong_gio = delta.total_seconds() / 3600
                # Tổng giờ làm = Giờ ra - Giờ vào - Giờ nghỉ
                record.tong_so_gio_lam = max(0, tong_gio - record.gio_nghi)
            else:
                record.tong_so_gio_lam = 0

    @api.depends('tong_so_gio_lam')
    def _compute_gio_ot(self):
        """Tính giờ OT tự động nếu làm quá 8 giờ/ngày"""
        GIO_LAM_CHUAN = 8.0  # 8 giờ/ngày
        
        for record in self:
            if record.tong_so_gio_lam > GIO_LAM_CHUAN:
                record.gio_ot = record.tong_so_gio_lam - GIO_LAM_CHUAN
            else:
                record.gio_ot = 0

    @api.depends('gio_vao', 'gio_ra', 'tong_so_gio_lam', 'gio_nghi')
    def _compute_trang_thai(self):
        # Giờ hành chính
        GIO_VAO_SANG = time(8, 0)      # 08:00
        GIO_RA_CHIEU = time(17, 30)    # 17:30
        GIO_LAM_CHUAN = 8.0            # 8 giờ/ngày
        SAI_SO = 0.1                   # Sai số 6 phút (0.1 giờ)
        
        for record in self:
            if not record.gio_vao and not record.gio_ra:
                record.trang_thai = 'nghi'
                continue
            
            if not record.gio_vao or not record.gio_ra:
                record.trang_thai = 'nghi'
                continue
            
            # Chuyển đổi từ UTC sang giờ địa phương (Vietnam UTC+7)
            tz = pytz.timezone('Asia/Ho_Chi_Minh')
            gio_vao_local = pytz.utc.localize(record.gio_vao.replace(tzinfo=None)).astimezone(tz)
            gio_ra_local = pytz.utc.localize(record.gio_ra.replace(tzinfo=None)).astimezone(tz)
            
            gio_vao_time = gio_vao_local.time()
            gio_ra_time = gio_ra_local.time()
            
            # Debug logging
            _logger.info(f"=== DEBUG CHAM CONG ===")
            _logger.info(f"Gio vao UTC: {record.gio_vao} -> Local: {gio_vao_local} -> time: {gio_vao_time}")
            _logger.info(f"Gio ra UTC: {record.gio_ra} -> Local: {gio_ra_local} -> time: {gio_ra_time}")
            _logger.info(f"GIO_VAO_SANG: {GIO_VAO_SANG}")
            
            # Kiểm tra đến muộn (vào sau 08:00)
            den_muon = gio_vao_time > GIO_VAO_SANG
            
            # Kiểm tra về sớm (ra trước 17:30)
            ve_som = gio_ra_time < GIO_RA_CHIEU
            
            # Kiểm tra làm thêm giờ (làm > 8 giờ, với sai số nhỏ)
            lam_them = record.tong_so_gio_lam > (GIO_LAM_CHUAN + SAI_SO)
            
            # Kiểm tra làm đủ giờ (từ 7.9 đến 8.1 giờ coi như đủ)
            lam_du = abs(record.tong_so_gio_lam - GIO_LAM_CHUAN) <= SAI_SO
            
            _logger.info(f"den_muon: {den_muon} (gio_vao_time > GIO_VAO_SANG)")
            _logger.info(f"ve_som: {ve_som}")
            _logger.info(f"lam_them: {lam_them}")
            _logger.info(f"Tong gio lam: {record.tong_so_gio_lam}")
            
            # Logic ưu tiên: Đến muộn được ưu tiên cao nhất
            if den_muon:
                record.trang_thai = 'den_muon'
                _logger.info(f"Trang thai: DEN MUON")
            elif lam_them:
                record.trang_thai = 'lam_them'
                _logger.info(f"Trang thai: LAM THEM")
            elif ve_som:
                # Chỉ coi là về sớm nếu làm thiếu giờ
                record.trang_thai = 've_som'
                _logger.info(f"Trang thai: VE SOM")
            else:
                record.trang_thai = 'dung_gio'
                _logger.info(f"Trang thai: DUNG GIO")

