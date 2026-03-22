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
    
    # Relationships
    don_tu_ids = fields.One2many('don_tu', 'cham_cong_id', string='Đơn từ liên quan')
    dang_ky_ca_id = fields.Many2one('dang_ky_ca_lam_theo_ngay', string='Ca làm đã đăng ký', 
                                     compute='_compute_dang_ky_ca', store=True)
    
    # Computed fields for relationships
    co_don_duyet = fields.Boolean(string='Có đơn đã duyệt', compute='_compute_co_don_duyet', store=True)
    ca_lam_dang_ky = fields.Selection([
        ('sang', 'Sáng'),
        ('chieu', 'Chiều'),
        ('ca_ngay', 'Cả Ngày'),
    ], string='Ca làm đăng ký', related='dang_ky_ca_id.ca_lam', readonly=True)
    
    # Zalo Bot Integration
    nguon_checkin = fields.Selection([
        ('manual', 'Thủ công'),
        ('device', 'Thiết bị'),
        ('zalo', 'Zalo Bot'),
        ('web', 'Web')
    ], string='Nguồn check-in', default='manual')
    zalo_message_id = fields.Char(string='Zalo Message ID', help='ID tin nhắn Zalo để tránh duplicate')

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
    
    @api.depends('don_tu_ids', 'don_tu_ids.trang_thai')
    def _compute_co_don_duyet(self):
        """Kiểm tra xem có đơn từ đã duyệt cho ngày này không"""
        for record in self:
            don_duyet = record.don_tu_ids.filtered(lambda d: d.trang_thai == 'da_duyet')
            record.co_don_duyet = bool(don_duyet)
            # Tự động cập nhật co_xin_phep nếu có đơn đã duyệt
            if don_duyet:
                record.co_xin_phep = True
    
    @api.depends('id_nhan_vien', 'ngay')
    def _compute_dang_ky_ca(self):
        """Tìm ca làm đã đăng ký cho ngày này"""
        for record in self:
            if record.id_nhan_vien and record.ngay:
                dang_ky = self.env['dang_ky_ca_lam_theo_ngay'].search([
                    ('nhan_vien_id', '=', record.id_nhan_vien.id),
                    ('ngay_lam', '=', record.ngay)
                ], limit=1)
                record.dang_ky_ca_id = dang_ky.id if dang_ky else False
            else:
                record.dang_ky_ca_id = False
    
    # Zalo Bot Integration Methods
    @api.model
    def zalo_checkin(self, nhan_vien_id, zalo_message_id):
        """
        Check-in từ Zalo Bot
        
        Args:
            nhan_vien_id (int): ID nhân viên
            zalo_message_id (str): ID tin nhắn Zalo
            
        Returns:
            dict: {'success': bool, 'message': str}
        """
        # Kiểm tra đã check-in hôm nay chưa
        today = fields.Date.today()
        existing = self.search([
            ('id_nhan_vien', '=', nhan_vien_id),
            ('ngay', '=', today),
            ('gio_vao', '!=', False)
        ], limit=1)
        
        if existing:
            # Convert UTC to Vietnam timezone
            tz = pytz.timezone('Asia/Ho_Chi_Minh')
            gio_vao_local = pytz.utc.localize(existing.gio_vao.replace(tzinfo=None)).astimezone(tz)
            gio_vao_str = gio_vao_local.strftime('%H:%M')
            return {
                'success': False,
                'message': f'⚠️ Bạn đã check-in lúc {gio_vao_str}.'
            }
        
        # Tạo record mới
        try:
            record = self.create({
                'id_nhan_vien': nhan_vien_id,
                'ngay': today,
                'gio_vao': fields.Datetime.now(),
                'nguon_checkin': 'zalo',
                'zalo_message_id': zalo_message_id
            })
            
            # Convert UTC to Vietnam timezone
            tz = pytz.timezone('Asia/Ho_Chi_Minh')
            gio_vao_local = pytz.utc.localize(record.gio_vao.replace(tzinfo=None)).astimezone(tz)
            gio_vao_str = gio_vao_local.strftime('%H:%M')
            
            # Gửi cảnh báo nếu đi muộn
            if record.trang_thai == 'den_muon' and not record.co_xin_phep:
                try:
                    self.env['zalo.notification.service'].notify_di_muon(record.id)
                except Exception as e:
                    _logger.warning(f'Không thể gửi cảnh báo đi muộn: {str(e)}')
            
            return {
                'success': True,
                'message': f'✅ Check-in thành công lúc {gio_vao_str}.\n\nChúc bạn làm việc hiệu quả! 💪'
            }
        except Exception as e:
            _logger.error(f'Zalo checkin error: {str(e)}')
            return {
                'success': False,
                'message': f'❌ Lỗi check-in: {str(e)}'
            }
    
    @api.model
    def zalo_checkout(self, nhan_vien_id, zalo_message_id):
        """
        Check-out từ Zalo Bot
        
        Args:
            nhan_vien_id (int): ID nhân viên
            zalo_message_id (str): ID tin nhắn Zalo
            
        Returns:
            dict: {'success': bool, 'message': str}
        """
        today = fields.Date.today()
        record = self.search([
            ('id_nhan_vien', '=', nhan_vien_id),
            ('ngay', '=', today),
            ('gio_vao', '!=', False),
            ('gio_ra', '=', False)
        ], limit=1)
        
        if not record:
            return {
                'success': False,
                'message': '⚠️ Bạn chưa check-in hôm nay hoặc đã check-out rồi.'
            }
        
        try:
            record.write({
                'gio_ra': fields.Datetime.now(),
                'zalo_message_id': zalo_message_id
            })
            
            # Convert UTC to Vietnam timezone
            tz = pytz.timezone('Asia/Ho_Chi_Minh')
            gio_ra_local = pytz.utc.localize(record.gio_ra.replace(tzinfo=None)).astimezone(tz)
            gio_ra_str = gio_ra_local.strftime('%H:%M')
            tong_gio = record.tong_so_gio_lam
            gio_ot = record.gio_ot
            
            msg = f'✅ Check-out thành công lúc {gio_ra_str}.\n\n'
            msg += f'📊 Tổng giờ làm: {tong_gio:.1f} giờ'
            
            if gio_ot > 0:
                msg += f'\n⏰ Giờ OT: {gio_ot:.1f} giờ'
            
            msg += '\n\nHẹn gặp lại! 👋'
            
            return {
                'success': True,
                'message': msg
            }
        except Exception as e:
            _logger.error(f'Zalo checkout error: {str(e)}')
            return {
                'success': False,
                'message': f'❌ Lỗi check-out: {str(e)}'
            }
    
    @api.model
    def zalo_get_status(self, nhan_vien_id):
        """
        Xem trạng thái chấm công hôm nay
        
        Args:
            nhan_vien_id (int): ID nhân viên
            
        Returns:
            dict: {'success': bool, 'message': str}
        """
        today = fields.Date.today()
        record = self.search([
            ('id_nhan_vien', '=', nhan_vien_id),
            ('ngay', '=', today)
        ], limit=1)
        
        if not record or not record.gio_vao:
            return {
                'success': True,
                'message': f'📊 Trạng thái hôm nay ({today.strftime("%d/%m/%Y")}):'
                          f'\n\n❌ Chưa check-in'
                          f'\n\nGửi "checkin" để bắt đầu làm việc.'
            }
        
        # Convert UTC to Vietnam timezone
        tz = pytz.timezone('Asia/Ho_Chi_Minh')
        gio_vao_local = pytz.utc.localize(record.gio_vao.replace(tzinfo=None)).astimezone(tz)
        gio_vao = gio_vao_local.strftime('%H:%M')
        
        if record.gio_ra:
            gio_ra_local = pytz.utc.localize(record.gio_ra.replace(tzinfo=None)).astimezone(tz)
            gio_ra = gio_ra_local.strftime('%H:%M')
        else:
            gio_ra = '---'
        
        msg = f'📊 Trạng thái hôm nay ({today.strftime("%d/%m/%Y")}):'
        msg += f'\n\n✅ Check-in: {gio_vao}'
        msg += f'\n📤 Check-out: {gio_ra}'
        
        if record.gio_ra:
            tong_gio = record.tong_so_gio_lam
            msg += f'\n⏱️ Tổng giờ làm: {tong_gio:.1f} giờ'
            
            if record.gio_ot > 0:
                msg += f'\n⏰ Giờ OT: {record.gio_ot:.1f} giờ'
            
            trang_thai_dict = dict(record._fields['trang_thai'].selection)
            msg += f'\n📌 Trạng thái: {trang_thai_dict.get(record.trang_thai, "N/A")}'
        else:
            # Tính giờ làm hiện tại
            from datetime import datetime
            now = datetime.now()
            gio_vao_dt = record.gio_vao.replace(tzinfo=None)
            delta = now - gio_vao_dt
            gio_hien_tai = max(0, delta.total_seconds() / 3600 - record.gio_nghi)
            msg += f'\n⏱️ Đang làm: {gio_hien_tai:.1f} giờ'
        
        return {
            'success': True,
            'message': msg
        }

