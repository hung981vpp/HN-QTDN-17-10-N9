from odoo import models, fields, api
from datetime import date

from odoo.exceptions import ValidationError

class NhanVien(models.Model):
    _name = 'nhan_vien'
    _description = 'Bảng chứa thông tin nhân viên'
    _rec_name = 'ho_va_ten'
    _order = 'ten asc, tuoi desc'
    _sql_constraints = [
        ('ma_dinh_danh_unique', 'unique(ma_dinh_danh)', 'Mã định danh phải là duy nhất')
    ]
    
    # Thông tin cơ bản
    ma_dinh_danh = fields.Char("Mã định danh", required=True)
    ho_ten_dem = fields.Char("Họ tên đệm", required=True)
    ten = fields.Char("Tên", required=True)
    ho_va_ten = fields.Char("Họ và tên", compute="_compute_ho_va_ten", store=True)
    
    ngay_sinh = fields.Date("Ngày sinh")
    que_quan = fields.Char("Quê quán")
    email = fields.Char("Email")
    so_dien_thoai = fields.Char("Số điện thoại")
    lich_su_cong_tac_ids = fields.One2many(
        "lich_su_cong_tac", 
        inverse_name="nhan_vien_id", 
        string = "Danh sách lịch sử công tác")
    tuoi = fields.Integer("Tuổi", compute="_compute_tuoi", store=True)
    anh = fields.Binary("Ảnh")
    danh_sach_chung_chi_bang_cap_ids = fields.One2many(
        "danh_sach_chung_chi_bang_cap", 
        inverse_name="nhan_vien_id", 
        string = "Danh sách chứng chỉ bằng cấp")
    
    # Thông tin hợp đồng
    so_hop_dong = fields.Char("Số hợp đồng")
    ngay_ky_hop_dong = fields.Date("Ngày ký hợp đồng")
    ngay_bat_dau_lam_viec = fields.Date("Ngày bắt đầu làm việc")
    ngay_ket_thuc_hop_dong = fields.Date("Ngày kết thúc hợp đồng")
    
    # Vị trí công việc
    chuc_vu_hien_tai_id = fields.Many2one("chuc_vu", string="Chức vụ hiện tại")
    phong_ban_hien_tai_id = fields.Many2one("don_vi", string="Phòng ban hiện tại")
    
    # Hệ thống lương
    he_so_luong = fields.Float("Hệ số lương", default=1.0, help="Hệ số nhân với lương cơ bản")
    luong_co_ban = fields.Float("Lương cơ bản/tháng", default=5000000, help="Lương cơ bản hàng tháng của nhân viên")
    luong_theo_ngay = fields.Float("Lương theo ngày", compute="_compute_luong_theo_ngay", store=True, help="Lương theo ngày = (Lương cơ bản × Hệ số lương) / 26")
    luong_theo_gio = fields.Float("Lương theo giờ", compute="_compute_luong_theo_gio", store=True, help="Lương theo giờ = Lương theo ngày / 8")
    
    # Quản lý hợp đồng
    loai_hop_dong = fields.Selection([
        ('thu_viec', 'Thử việc'),
        ('co_thoi_han', 'Có thời hạn'),
        ('khong_thoi_han', 'Không thời hạn')
    ], string="Loại hợp đồng", default='thu_viec')
    thoi_han_hop_dong = fields.Integer("Thời hạn hợp đồng (tháng)", help="Thời hạn hợp đồng tính theo tháng")
    trang_thai_hop_dong = fields.Selection([
        ('dang_hieu_luc', 'Đang hiệu lực'),
        ('het_han', 'Hết hạn'),
        ('da_cham_dut', 'Đã chấm dứt')
    ], string="Trạng thái hợp đồng", compute="_compute_trang_thai_hop_dong", store=True)
    
    # Thông tin bảo hiểm
    ma_so_bhxh = fields.Char("Mã số BHXH")
    muc_tran_bhxh = fields.Float("Mức trần BHXH", default=46800000, help="Mức lương tối đa làm căn cứ đóng BHXH (20 × Lương cơ sở)")
    
    # Lương đóng bảo hiểm
    luong_dong_bao_hiem = fields.Float("Lương đóng bảo hiểm", compute="_compute_luong_dong_bao_hiem", store=True, help="= MIN(Lương cơ bản, Mức trần BHXH)")
    
    # Tỷ lệ đóng Người Lao Động (NLĐ)
    ty_le_dong_bhxh = fields.Float("Tỷ lệ BHXH (%)", default=8.0, help="Tỷ lệ BHXH người lao động đóng")
    ty_le_dong_bhyt = fields.Float("Tỷ lệ BHYT (%)", default=1.5, help="Tỷ lệ BHYT người lao động đóng")
    ty_le_dong_bhtn = fields.Float("Tỷ lệ BHTN (%)", default=1.0, help="Tỷ lệ BHTN người lao động đóng")
    
    # Số tiền Người Lao Động (NLĐ) phải đóng
    tien_dong_bhxh = fields.Float("Tiền BHXH", compute="_compute_tien_dong_bao_hiem", store=True, help="Số tiền BHXH người lao động phải đóng")
    tien_dong_bhyt = fields.Float("Tiền BHYT", compute="_compute_tien_dong_bao_hiem", store=True, help="Số tiền BHYT người lao động phải đóng")
    tien_dong_bhtn = fields.Float("Tiền BHTN", compute="_compute_tien_dong_bao_hiem", store=True, help="Số tiền BHTN người lao động phải đóng")
    tong_tien_bao_hiem = fields.Float("Tổng NLĐ đóng", compute="_compute_tien_dong_bao_hiem", store=True, help="Tổng số tiền bảo hiểm người lao động phải đóng (10.5%)")
    
    _sql_constrains = [
        ('ma_dinh_danh_unique', 'unique(ma_dinh_danh)', 'Mã định danh phải là duy nhất')
    ]

    @api.depends("ho_ten_dem", "ten")
    def _compute_ho_va_ten(self):
        for record in self:
            if record.ho_ten_dem and record.ten:
                record.ho_va_ten = record.ho_ten_dem + ' ' + record.ten
    
    @api.onchange("ten", "ho_ten_dem")
    def _default_ma_dinh_danh(self):
        for record in self:
            if record.ho_ten_dem and record.ten:
                chu_cai_dau = ''.join([tu[0][0] for tu in record.ho_ten_dem.lower().split()])
                record.ma_dinh_danh = record.ten.lower() + chu_cai_dau
    
    @api.depends("ngay_sinh")
    def _compute_tuoi(self):
        for record in self:
            if record.ngay_sinh:
                year_now = date.today().year
                record.tuoi = year_now - record.ngay_sinh.year

    @api.constrains('tuoi')
    def _check_tuoi(self):
        for record in self:
            if record.tuoi < 18:
                raise ValidationError("Tuổi không được bé hơn 18")
    
    # Computed methods cho hệ thống lương
    @api.depends("luong_co_ban", "he_so_luong")
    def _compute_luong_theo_ngay(self):
        """Tính lương theo ngày = (Lương cơ bản × Hệ số lương) / 26"""
        for record in self:
            if record.luong_co_ban and record.he_so_luong:
                record.luong_theo_ngay = (record.luong_co_ban * record.he_so_luong) / 26
            else:
                record.luong_theo_ngay = 0.0
    
    @api.depends("luong_theo_ngay")
    def _compute_luong_theo_gio(self):
        """Tính lương theo giờ = Lương theo ngày / 8"""
        for record in self:
            if record.luong_theo_ngay:
                record.luong_theo_gio = record.luong_theo_ngay / 8
            else:
                record.luong_theo_gio = 0.0
    
    @api.depends("ngay_ket_thuc_hop_dong")
    def _compute_trang_thai_hop_dong(self):
        """Tự động cập nhật trạng thái hợp đồng dựa trên ngày hết hạn"""
        for record in self:
            if not record.ngay_ket_thuc_hop_dong:
                # Nếu không có ngày kết thúc, có thể là hợp đồng không thời hạn
                if record.loai_hop_dong == 'khong_thoi_han':
                    record.trang_thai_hop_dong = 'dang_hieu_luc'
                else:
                    record.trang_thai_hop_dong = False
            else:
                today = date.today()
                if record.ngay_ket_thuc_hop_dong < today:
                    record.trang_thai_hop_dong = 'het_han'
                else:
                    record.trang_thai_hop_dong = 'dang_hieu_luc'
    
    @api.depends("luong_co_ban", "muc_tran_bhxh")
    def _compute_luong_dong_bao_hiem(self):
        """Tính lương đóng bảo hiểm = MIN(Lương cơ bản, Mức trần BHXH)"""
        for record in self:
            if record.luong_co_ban:
                # Công thức chuẩn: LƯƠNG_ĐÓNG_BH = MIN(LƯƠNG_CƠ_BẢN, TRẦN_LƯƠNG_ĐÓNG_BH)
                if record.muc_tran_bhxh and record.luong_co_ban > record.muc_tran_bhxh:
                    record.luong_dong_bao_hiem = record.muc_tran_bhxh
                else:
                    record.luong_dong_bao_hiem = record.luong_co_ban
            else:
                record.luong_dong_bao_hiem = 0.0
    
    @api.depends("luong_dong_bao_hiem", "ty_le_dong_bhxh", "ty_le_dong_bhyt", "ty_le_dong_bhtn")
    def _compute_tien_dong_bao_hiem(self):
        """Tính số tiền bảo hiểm người lao động phải đóng"""
        for record in self:
            if record.luong_dong_bao_hiem:
                # Số tiền Người Lao Động (NLĐ) đóng
                record.tien_dong_bhxh = record.luong_dong_bao_hiem * record.ty_le_dong_bhxh / 100
                record.tien_dong_bhyt = record.luong_dong_bao_hiem * record.ty_le_dong_bhyt / 100
                record.tien_dong_bhtn = record.luong_dong_bao_hiem * record.ty_le_dong_bhtn / 100
                record.tong_tien_bao_hiem = record.tien_dong_bhxh + record.tien_dong_bhyt + record.tien_dong_bhtn
            else:
                record.tien_dong_bhxh = 0.0
                record.tien_dong_bhyt = 0.0
                record.tien_dong_bhtn = 0.0
                record.tong_tien_bao_hiem = 0.0





