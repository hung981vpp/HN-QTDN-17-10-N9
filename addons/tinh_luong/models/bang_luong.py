# -*- coding: utf-8 -*-
from odoo import models, fields, api

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

    @api.depends('luong_co_ban', 'ty_le_bhxh', 'ty_le_bhyt', 'ty_le_bhtn')
    def _compute_bao_hiem(self):
        """Tính tổng bảo hiểm cá nhân phải đóng"""
        for record in self:
            bhxh = record.luong_co_ban * (record.ty_le_bhxh / 100)
            bhyt = record.luong_co_ban * (record.ty_le_bhyt / 100)
            bhtn = record.luong_co_ban * (record.ty_le_bhtn / 100)
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
    
    @api.depends('thuong_chuyen_can', 'thuong_ot', 'thuong_hieu_suat', 'thuong_le_tet', 'thuong_khac')
    def _compute_tong_thuong(self):
        """Tổng thưởng = Thưởng tự động + Thưởng thủ công"""
        for record in self:
            total = (record.thuong_chuyen_can + record.thuong_ot + 
                    record.thuong_hieu_suat + record.thuong_le_tet + record.thuong_khac)
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
    
    @api.depends('phat_khong_chuyen_can', 'phat_den_muon', 'phat_ve_som', 'phat_thu_cong')
    def _compute_tong_phat(self):
        """Tổng phạt = Phạt không chuyên cần + Phạt đến muộn + Phạt về sớm + Phạt thủ công"""
        for record in self:
            record.tong_phat = (record.phat_khong_chuyen_can + record.phat_den_muon + 
                               record.phat_ve_som + record.phat_thu_cong)

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
