from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

class BangLuong(models.Model):
    _name = 'bang_luong'
    _description = 'Bảng lương'
    _order = 'nam desc, thang desc'

    ma_bang_luong = fields.Char(string='Mã bảng lương', required=True, copy=False, readonly=True, default='New')
    id_nhan_vien = fields.Many2one('nhan_vien', string='Nhân viên', required=True)
    thang = fields.Selection([
        ('1', 'Tháng 1'), ('2', 'Tháng 2'), ('3', 'Tháng 3'),
        ('4', 'Tháng 4'), ('5', 'Tháng 5'), ('6', 'Tháng 6'),
        ('7', 'Tháng 7'), ('8', 'Tháng 8'), ('9', 'Tháng 9'),
        ('10', 'Tháng 10'), ('11', 'Tháng 11'), ('12', 'Tháng 12')
    ], string='Tháng', required=True)
    nam = fields.Integer(string='Năm', required=True, default=2026)
    
    # Thông tin công và giờ làm
    so_cong = fields.Float(string='Số công', compute='_compute_so_cong', store=True)
    tong_gio_lam = fields.Float(string='Tổng giờ làm (giờ)', compute='_compute_gio_lam', store=True)
    tong_gio_ot = fields.Float(string='Tổng giờ OT (giờ)', compute='_compute_gio_lam', store=True)
    
    # Lương cơ bản và phụ cấp
    luong_co_ban = fields.Float(string='Lương cơ bản/tháng', compute='_compute_luong_co_ban', store=True, readonly=False)
    luong_theo_gio = fields.Float(string='Lương theo giờ', compute='_compute_luong_theo_gio', store=True)
    tien_luong_chinh = fields.Float(string='Tiền lương chính', compute='_compute_tien_luong', store=True)
    
    # Lương OT
    he_so_ot = fields.Float(string='Hệ số OT', default=1.5)
    tien_ot = fields.Float(string='Tiền OT', compute='_compute_tien_ot', store=True)
    
    
    # Trợ cấp
    tro_cap = fields.Float(string='Trợ cấp', default=0)
    
    # Thưởng tự động
    thuong_chuyen_can = fields.Float(string='Thưởng chuyên cần', compute='_compute_thuong_tu_dong', store=True, help='Đi làm đủ công, không muộn')
    thuong_ot = fields.Float(string='Thưởng OT', compute='_compute_thuong_tu_dong', store=True, help='Làm OT nhiều')
    
    # Thưởng thủ công
    thuong_hieu_suat = fields.Float(string='Thưởng hiệu suất', default=0)
    thuong_le_tet = fields.Float(string='Thưởng lễ tết', default=0)
    thuong_khac = fields.Float(string='Thưởng khác', default=0)
    
    # Tổng thưởng
    tong_thuong = fields.Float(string='Tổng thưởng', compute='_compute_tong_thuong', store=True)
    
    # Backward compatibility: thuong = tong_thuong
    thuong = fields.Float(string='Thưởng (tổng)', compute='_compute_tong_thuong', store=True, help='Tổng thưởng (tự động + thủ công)')
    
    # Phạt thủ công
    phat_thu_cong = fields.Float(string='Phạt (thủ công)', default=0)
    
    # Phạt tự động
    phat_khong_chuyen_can = fields.Float(string='Phạt không chuyên cần', compute='_compute_phat_tu_dong', store=True, help='Đi làm thiếu hoặc hay muộn')
    phat_den_muon = fields.Float(string='Phạt đến muộn', compute='_compute_phat_tu_dong', store=True)
    phat_ve_som = fields.Float(string='Phạt về sớm', compute='_compute_phat_tu_dong', store=True)
    tong_phat = fields.Float(string='Tổng phạt', compute='_compute_tong_phat', store=True)

    # Thưởng phạt từ phiếu
    thuong_phat_ids = fields.Many2many('thuong.phat.phieu', compute='_compute_thuong_phat')
    thuong_tu_phieu = fields.Float(string='Thưởng từ phiếu', compute='_compute_tien_thuong_phat', store=True)
    phat_tu_phieu = fields.Float(string='Phạt từ phiếu', compute='_compute_tien_thuong_phat', store=True)
    
    # Bảo hiểm
    ty_le_bhxh = fields.Float(string='Tỷ lệ BHXH (%)', default=8.0)
    ty_le_bhyt = fields.Float(string='Tỷ lệ BHYT (%)', default=1.5)
    ty_le_bhtn = fields.Float(string='Tỷ lệ BHTN (%)', default=1.0)
    tong_bao_hiem = fields.Float(string='Tổng BH cá nhân', compute='_compute_bao_hiem', store=True)
    
    # Tổng lương
    tong_luong = fields.Float(string='Tổng lương', compute='_compute_tong_luong', store=True)
    luong_thuc_nhan = fields.Float(string='Lương thực nhận', compute='_compute_luong_thuc_nhan', store=True)
    
    trang_thai = fields.Selection([
        ('chua_duyet', 'Chưa duyệt'),
        ('da_duyet', 'Đã duyệt'),
        ('da_thanh_toan', 'Đã thanh toán')
    ], string='Trạng thái', default='chua_duyet')
    
    ghi_chu = fields.Text(string='Ghi chú')
    
    # Quan hệ với chấm công
    cham_cong_ids = fields.One2many('cham_cong', compute='_compute_cham_cong')

    @api.model
    def create(self, vals):
        if vals.get('ma_bang_luong', 'New') == 'New':
            vals['ma_bang_luong'] = self.env['ir.sequence'].next_by_code('bang_luong.sequence') or 'New'
        return super(BangLuong, self).create(vals)

    def action_send_email(self):
        """Gửi email phiếu lương cho nhân viên (kèm PDF đính kèm)"""
        self.ensure_one()
        
        # Kiểm tra nhân viên có email không
        nv_email = self.id_nhan_vien.email
        if not nv_email:
            raise UserError(f'Nhân viên {self.id_nhan_vien.ho_va_ten} chưa có email. Vui lòng cập nhật email trước.')
        
        # Kiểm tra mail server
        mail_server = self.env['ir.mail_server'].search([], limit=1)
        if not mail_server:
            raise UserError(
                'Chưa cấu hình Outgoing Mail Server!\n\n'
                'Vào: Settings → Technical → Outgoing Mail Servers → Create'
            )
        
        # Tìm email template
        template = self.env.ref('tinh_luong.email_template_bang_luong', raise_if_not_found=False)
        if not template:
            raise UserError('Không tìm thấy Email Template!')
        
        # Gắn PDF report vào template
        report = self.env.ref('tinh_luong.action_report_bang_luong', raise_if_not_found=False)
        if report:
            template.report_template = report.id
        
        # Force set email_from từ mail server
        sender_email = mail_server.smtp_user or 'no-reply@company.com'
        
        # Gửi email với email_values override (bypass template rendering issues)
        template.send_mail(self.id, force_send=True, email_values={
            'email_from': sender_email,
            'email_to': nv_email,
        })
        
        # Thông báo thành công
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '✅ Đã gửi email!',
                'message': f'Phiếu lương T{self.thang}/{self.nam} đã gửi đến {nv_email}',
                'type': 'success',
                'sticky': False,
            }
        }


    def _compute_cham_cong(self):
        """Lấy dữ liệu chấm công theo tháng/năm"""
        for record in self:
            if record.id_nhan_vien and record.thang and record.nam:
                # Tìm tất cả bản ghi chấm công của nhân viên trong tháng
                domain = [
                    ('id_nhan_vien', '=', record.id_nhan_vien.id),
                    ('ngay', '>=', f'{record.nam}-{record.thang.zfill(2)}-01'),
                    ('ngay', '<=', f'{record.nam}-{record.thang.zfill(2)}-31'),
                ]
                record.cham_cong_ids = self.env['cham_cong'].search(domain)
            else:
                record.cham_cong_ids = False

    @api.depends('id_nhan_vien', 'thang', 'nam')
    def _compute_so_cong(self):
        """Tính số công = số ngày làm việc thực tế"""
        for record in self:
            if record.cham_cong_ids:
                # Đếm số ngày có giờ vào hoặc giờ ra (không nghỉ)
                so_ngay_lam = len([cc for cc in record.cham_cong_ids if cc.gio_vao or cc.gio_ra])
                record.so_cong = so_ngay_lam
            else:
                record.so_cong = 0

    @api.depends('id_nhan_vien', 'thang', 'nam')
    def _compute_gio_lam(self):
        """Tính tổng giờ làm và giờ OT từ chấm công"""
        for record in self:
            if record.cham_cong_ids:
                record.tong_gio_lam = sum(record.cham_cong_ids.mapped('tong_so_gio_lam'))
                record.tong_gio_ot = sum(record.cham_cong_ids.mapped('gio_ot'))
            else:
                record.tong_gio_lam = 0
                record.tong_gio_ot = 0

    @api.depends('id_nhan_vien')
    def _compute_luong_co_ban(self):
        """Lấy lương cơ bản từ thông tin nhân viên"""
        for record in self:
            if record.id_nhan_vien and record.id_nhan_vien.luong_co_ban:
                record.luong_co_ban = record.id_nhan_vien.luong_co_ban
            else:
                record.luong_co_ban = 5000000  # Mặc định nếu nhân viên chưa có lương

    @api.depends('luong_co_ban')
    def _compute_luong_theo_gio(self):
        """Tính lương theo giờ = Lương cơ bản / 176 giờ (8h x 22 ngày)"""
        for record in self:
            record.luong_theo_gio = record.luong_co_ban / 176

    @api.depends('luong_co_ban', 'so_cong')
    def _compute_tien_luong(self):
        """Tính tiền lương chính = (Số công / 28) x Lương cơ bản"""
        SO_NGAY_LAM_CHUAN = 28  # Số ngày làm việc chuẩn/tháng
        for record in self:
            if record.so_cong > 0:
                record.tien_luong_chinh = (record.so_cong / SO_NGAY_LAM_CHUAN) * record.luong_co_ban
            else:
                record.tien_luong_chinh = 0


    @api.depends('luong_theo_gio', 'tong_gio_ot', 'he_so_ot')
    def _compute_tien_ot(self):
        """Tính tiền OT = Lương theo giờ x Giờ OT x Hệ số OT"""
        for record in self:
            record.tien_ot = record.luong_theo_gio * record.tong_gio_ot * record.he_so_ot

    @api.depends('id_nhan_vien', 'thang', 'nam')
    def _compute_thuong_phat(self):
        """Tìm các phiếu thưởng/phạt đã duyệt trong tháng"""
        for record in self:
            if record.id_nhan_vien and record.thang and record.nam:
                month_str = record.thang.zfill(2)
                domain = [
                    ('nhan_vien_ids', 'in', record.id_nhan_vien.id),
                    ('state', '=', 'da_duyet'),
                    ('ngay_ap_dung', '>=', f'{record.nam}-{month_str}-01'),
                    ('ngay_ap_dung', '<=', f'{record.nam}-{month_str}-31')
                ]
                record.thuong_phat_ids = self.env['thuong.phat.phieu'].search(domain)
            else:
                record.thuong_phat_ids = False

    @api.depends('thuong_phat_ids')
    def _compute_tien_thuong_phat(self):
        for record in self:
            thuong = 0.0
            phat = 0.0
            for phieu in record.thuong_phat_ids:
                if phieu.tinh_chat == 'thuong':
                    thuong += phieu.so_tien
                else:
                    phat += phieu.so_tien
            record.thuong_tu_phieu = thuong
            record.phat_tu_phieu = phat

    @api.depends('id_nhan_vien.luong_dong_bao_hiem', 'ty_le_bhxh', 'ty_le_bhyt', 'ty_le_bhtn')
    def _compute_bao_hiem(self):
        """Tính tổng bảo hiểm cá nhân phải đóng dựa trên lương đóng bảo hiểm (tuân thủ luật)"""
        for record in self:
            luong_bh = record.id_nhan_vien.luong_dong_bao_hiem if record.id_nhan_vien else 0
            bhxh = luong_bh * (record.ty_le_bhxh / 100)
            bhyt = luong_bh * (record.ty_le_bhyt / 100)
            bhtn = luong_bh * (record.ty_le_bhtn / 100)
            record.tong_bao_hiem = bhxh + bhyt + bhtn


    @api.depends('id_nhan_vien', 'thang', 'nam', 'so_cong', 'tong_gio_ot')
    def _compute_thuong_tu_dong(self):
        """Tính thưởng tự động dựa trên hiệu suất làm việc"""
        SO_CONG_CHUAN = 26  # Số ngày làm việc chuẩn/tháng
        THUONG_CHUYEN_CAN = 500000  # 500k nếu đi làm đủ và không muộn
        THUONG_OT_MOI_GIO = 50000  # 50k/giờ OT nếu làm nhiều
        GIO_OT_TOI_THIEU = 20  # Tối thiểu 20 giờ OT mới được thưởng
        
        for record in self:
            # Thưởng chuyên cần: Đi làm đủ công VÀ không đến muộn lần nào
            if record.cham_cong_ids and record.so_cong >= SO_CONG_CHUAN:
                # Kiểm tra có đến muộn không (không tính xin phép)
                so_lan_muon = len([cc for cc in record.cham_cong_ids 
                                   if cc.trang_thai == 'den_muon' and not cc.co_xin_phep])
                if so_lan_muon == 0:
                    record.thuong_chuyen_can = THUONG_CHUYEN_CAN
                else:
                    record.thuong_chuyen_can = 0
            else:
                record.thuong_chuyen_can = 0
            
            # Thưởng OT: Làm OT nhiều (>= 20 giờ)
            if record.tong_gio_ot >= GIO_OT_TOI_THIEU:
                record.thuong_ot = record.tong_gio_ot * THUONG_OT_MOI_GIO
            else:
                record.thuong_ot = 0
    
    @api.depends('thuong_chuyen_can', 'thuong_ot', 'thuong_hieu_suat', 'thuong_le_tet', 'thuong_khac', 'thuong_tu_phieu')
    def _compute_tong_thuong(self):
        """Tổng thưởng = Thưởng tự động + Thưởng thủ công + Thưởng từ phiếu"""
        for record in self:
            total = (record.thuong_chuyen_can + record.thuong_ot + 
                    record.thuong_hieu_suat + record.thuong_le_tet + record.thuong_khac + record.thuong_tu_phieu)
            record.tong_thuong = total
            record.thuong = total  # Backward compatibility

    @api.depends('id_nhan_vien', 'thang', 'nam', 'so_cong')
    def _compute_phat_tu_dong(self):
        """Tính phạt tự động dựa trên trạng thái chấm công"""
        MUC_PHAT_DEN_MUON = 50000  # 50k/lần
        MUC_PHAT_VE_SOM = 30000    # 30k/lần
        MUC_PHAT_KHONG_CHUYEN_CAN = 300000  # 300k nếu đi làm thiếu hoặc hay muộn
        SO_CONG_TOI_THIEU = 26  # Tối thiểu 26 ngày
        SO_LAN_MUON_TOI_DA = 3  # Tối đa 3 lần muộn
        
        for record in self:
            if record.cham_cong_ids:
                # Đếm số lần đến muộn (KHÔNG có xin phép)
                so_lan_den_muon = len([cc for cc in record.cham_cong_ids 
                                       if cc.trang_thai == 'den_muon' and not cc.co_xin_phep])
                record.phat_den_muon = so_lan_den_muon * MUC_PHAT_DEN_MUON
                
                # Đếm số lần về sớm (KHÔNG có xin phép)
                so_lan_ve_som = len([cc for cc in record.cham_cong_ids 
                                     if cc.trang_thai == 've_som' and not cc.co_xin_phep])
                record.phat_ve_som = so_lan_ve_som * MUC_PHAT_VE_SOM
                
                # Phạt không chuyên cần: Đi làm thiếu HOẶC hay đến muộn
                if record.so_cong < SO_CONG_TOI_THIEU or so_lan_den_muon > SO_LAN_MUON_TOI_DA:
                    record.phat_khong_chuyen_can = MUC_PHAT_KHONG_CHUYEN_CAN
                else:
                    record.phat_khong_chuyen_can = 0
            else:
                record.phat_den_muon = 0
                record.phat_ve_som = 0
                record.phat_khong_chuyen_can = 0
    
    @api.depends('phat_khong_chuyen_can', 'phat_den_muon', 'phat_ve_som', 'phat_thu_cong', 'phat_tu_phieu')
    def _compute_tong_phat(self):
        """Tổng phạt = Phạt không chuyên cần + Phạt đến muộn + Phạt về sớm + Phạt thủ công + Phạt từ phiếu"""
        for record in self:
            record.tong_phat = (record.phat_khong_chuyen_can + record.phat_den_muon + 
                                record.phat_ve_som + record.phat_thu_cong + record.phat_tu_phieu)

    @api.depends('tien_luong_chinh', 'tien_ot', 'tro_cap', 'tong_thuong')
    def _compute_tong_luong(self):
        """Tổng lương = Lương chính + OT + Trợ cấp + Tổng thưởng"""
        for record in self:
            record.tong_luong = record.tien_luong_chinh + record.tien_ot + record.tro_cap + record.tong_thuong

    @api.depends('tong_luong', 'tong_phat', 'tong_bao_hiem')
    def _compute_luong_thuc_nhan(self):
        """Lương thực nhận = Tổng lương - Tổng phạt - Bảo hiểm"""
        for record in self:
            record.luong_thuc_nhan = record.tong_luong - record.tong_phat - record.tong_bao_hiem

    @api.model
    def cron_tu_dong_tinh_luong(self):
        """Hàm chạy tự động (Cron job) vào ngày 15 hàng tháng để sinh bảng lương mới"""
        import datetime
        from dateutil.relativedelta import relativedelta

        today = datetime.date.today()
        # Tính lương cho tháng trước (hoặc tháng hiện tại tùy rule, nhưng thường là tháng trước)
        # Sẽ sinh bảng lương tháng trước nếu chạy ngày 15, hoặc tháng hiện tại
        target_month_date = today - relativedelta(months=1)
        thang_tinh = str(target_month_date.month)
        nam_tinh = target_month_date.year

        nhan_viens = self.env['nhan_vien'].search([('trang_thai_hop_dong', '=', 'dang_hieu_luc')])
        so_luong_tao = 0
        for nv in nhan_viens:
            # Kiểm tra xem đã tính lương cho tháng này chưa
            bang_luong_cu = self.search([
                ('id_nhan_vien', '=', nv.id),
                ('thang', '=', thang_tinh),
                ('nam', '=', nam_tinh)
            ])
            if not bang_luong_cu:
                self.create({
                    'id_nhan_vien': nv.id,
                    'thang': thang_tinh,
                    'nam': nam_tinh,
                })
                so_luong_tao += 1
                
        # Ghi log lịch sử cron job
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info(f"Đã tự động tạo xong {so_luong_tao} phiếu lương T{thang_tinh}/{nam_tinh}")

    def action_send_email(self):
        """Gửi email PDF Bảng lương cho nhân viên"""
        self.ensure_one()
        if not self.id_nhan_vien.email:
            raise ValidationError(f"Nhân viên {self.id_nhan_vien.ho_va_ten} chưa có địa chỉ Email được thiết lập trong Hồ sơ!")
            
        template = self.env.ref('tinh_luong.email_template_bang_luong', raise_if_not_found=False)
        if not template:
            raise ValidationError("Không tìm thấy mẫu Email 'tinh_luong.email_template_bang_luong'!")
            
        # Gắn report PDF vào email template tự động
        report = self.env.ref('tinh_luong.action_report_bang_luong', raise_if_not_found=False)
        if report:
            template.report_template = report
            template.report_name = f"Payslip_{self.id_nhan_vien.ma_dinh_danh}_T{self.thang}_{self.nam}"
            
        template.send_mail(self.id, force_send=True)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': f'Đã gửi Email Bảng lương thành công cho {self.id_nhan_vien.ho_va_ten}',
                'type': 'success',
                'sticky': False,
            }
        }

    # ─────────── APPROVAL WORKFLOW ───────────

    def action_duyet(self):
        """Duyệt phiếu lương → Đã duyệt"""
        for rec in self:
            if rec.trang_thai != 'chua_duyet':
                raise UserError('Chỉ có thể duyệt phiếu lương đang ở trạng thái "Chưa duyệt"!')
            rec.trang_thai = 'da_duyet'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '✅ Đã duyệt!',
                'message': f'Phiếu lương {self.ma_bang_luong} đã được duyệt thành công.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_tu_choi(self):
        """Từ chối / Hủy duyệt → quay về Chưa duyệt"""
        for rec in self:
            if rec.trang_thai == 'da_thanh_toan':
                raise UserError('Không thể hủy duyệt phiếu đã thanh toán!')
            rec.trang_thai = 'chua_duyet'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '↩️ Đã hủy duyệt',
                'message': f'Phiếu lương {self.ma_bang_luong} đã được đặt lại về Chưa duyệt.',
                'type': 'warning',
                'sticky': False,
            }
        }

    def action_thanh_toan(self):
        """Xác nhận đã thanh toán"""
        for rec in self:
            if rec.trang_thai != 'da_duyet':
                raise UserError('Chỉ có thể xác nhận thanh toán cho phiếu đã duyệt!')
            rec.trang_thai = 'da_thanh_toan'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '💰 Đã thanh toán!',
                'message': f'Phiếu lương {self.ma_bang_luong} đã được xác nhận thanh toán.',
                'type': 'success',
                'sticky': False,
            }
        }

    # ─────────── TELEGRAM NOTIFICATION ───────────

    def action_send_telegram(self):
        """Gửi thông báo phiếu lương qua Telegram cho nhân viên"""
        self.ensure_one()

        nhan_vien = self.id_nhan_vien
        # Tìm liên kết Telegram của nhân viên
        telegram_user = self.env['telegram.bot.user'].search(
            [('id_nhan_vien', '=', nhan_vien.id), ('is_verified', '=', True)], limit=1
        )
        if not telegram_user:
            raise UserError(
                f'Nhân viên {nhan_vien.ho_va_ten} chưa liên kết hoặc chưa xác thực tài khoản Telegram.\n'
                'Yêu cầu nhân viên gửi lệnh /link cho Bot Telegram để liên kết.'
            )

        # Định dạng số tiền VNĐ
        def fmt(num):
            return f"{int(num):,}".replace(',', '.') + ' ₫'

        trang_thai_str = dict(self.fields_get(['trang_thai'])['trang_thai']['selection']).get(self.trang_thai, '')

        message = (
            f"📋 <b>THÔNG BÁO PHIẾU LƯƠNG</b>\n"
            f"────────────────────\n"
            f"👤 Nhân viên: <b>{nhan_vien.ho_va_ten}</b>\n"
            f"📅 Kỳ lương: <b>T{self.thang}/{self.nam}</b>\n"
            f"─────── Chi tiết ───────\n"
            f"⏱ Tổng giờ làm: {self.tong_gio_lam:.1f}h\n"
            f"🕐 Giờ OT: {self.tong_gio_ot:.1f}h\n"
            f"💰 Lương chính: {fmt(self.tien_luong_chinh)}\n"
            f"🎁 Tổng thưởng: {fmt(self.tong_thuong)}\n"
            f"⚠️  Tổng phạt: {fmt(self.tong_phat)}\n"
            f"🛡 Bảo hiểm: {fmt(self.tong_bao_hiem)}\n"
            f"────────────────────\n"
            f"✅ <b>Lương thực nhận: {fmt(self.luong_thuc_nhan)}</b>\n"
            f"📌 Trạng thái: {trang_thai_str}\n"
            f"────────────────────\n"
            f"<i>Vui lòng liên hệ phòng Nhân sự nếu có thắc mắc.</i>"
        )

        success = telegram_user.send_message(message)

        if success:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '✅ Đã gửi Telegram!',
                    'message': f'Thông báo phiếu lương đã gửi đến {nhan_vien.ho_va_ten} qua Telegram.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise UserError(
                f'Không thể gửi tin nhắn Telegram đến {nhan_vien.ho_va_ten}.\n'
                'Kiểm tra lại cấu hình Bot Telegram trong Settings.'
            )

