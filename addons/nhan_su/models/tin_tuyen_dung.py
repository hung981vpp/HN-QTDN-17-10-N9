from odoo import models, fields

class TinTuyenDung(models.Model):
    _name = 'tin_tuyen_dung'
    _description = 'Bảng chứa thông tin tin tuyển dụng'
    _rec_name = 'tieu_de'
    _order = 'ma_tin desc'
    
    ma_tin = fields.Char("Mã tin", required=True)
    tieu_de = fields.Char("Tiêu đề", required=True)
    vi_tri = fields.Char("Vị trí", required=True)
    mo_ta = fields.Text("Mô tả công việc")
    muc_luong = fields.Float("Mức lương")
    thong_tin_cong_ty = fields.Text("Thông tin công ty")
    han_dang_ky = fields.Date("Hạn đăng ký")
    so_luong = fields.Integer("Số lượng tuyển")
