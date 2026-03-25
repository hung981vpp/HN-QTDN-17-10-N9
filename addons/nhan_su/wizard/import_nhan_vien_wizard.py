from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
import logging

_logger = logging.getLogger(__name__)

try:
    import openpyxl
except ImportError:
    openpyxl = None
from datetime import datetime

class ImportNhanVienWizard(models.TransientModel):
    _name = 'import.nhan.vien.wizard'
    _description = 'Wizard Nhập dữ liệu Nhân viên từ Excel'

    file_upload = fields.Binary(string='File Excel')
    file_name = fields.Char(string='Tên File')
    
    def action_download_template(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/nhan_su/static/src/files/template_nhan_vien.xlsx',
            'target': 'new',
        }

    def action_import(self):
        if not openpyxl:
            raise UserError('Thư viện openpyxl chưa được cài đặt trên server.')
            
        if not self.file_upload:
            raise UserError('Vui lòng chọn file Excel để tải lên!')

        # Decode base64 
        try:
            file_data = base64.b64decode(self.file_upload)
            file_stream = io.BytesIO(file_data)
            wb = openpyxl.load_workbook(file_stream, data_only=True)
            ws = wb.active
        except Exception as e:
            raise UserError(f"File không đúng định dạng Excel (.xlsx). Lỗi: {str(e)}")

        nhan_vien_obj = self.env['nhan_vien']
        don_vi_obj = self.env['don_vi']
        chuc_vu_obj = self.env['chuc_vu']
        
        count_success = 0
        errors = []
        
        # Mapping loai_hop_dong
        hd_map = {
            'Thử việc': 'thu_viec',
            'Có thời hạn': 'co_thoi_han',
            'Không thời hạn': 'khong_thoi_han'
        }

        # Bắt đầu đọc từ dòng số 2 (bỏ qua Header)
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not any(row):  # Bỏ qua dòng trống
                continue
                
            try:
                ma_dinh_danh = str(row[0]).strip() if row[0] else ''
                ho_dem = str(row[1]).strip() if row[1] else ''
                ten = str(row[2]).strip() if row[2] else ''
                
                if not ho_dem or not ten:
                    errors.append(f"Dòng {row_idx}: Thiếu Họ đệm hoặc Tên.")
                    continue
                    
                if not ma_dinh_danh:
                    chu_cai_dau = ''.join([tu[0][0] for tu in ho_dem.lower().split()]) if ho_dem else ''
                    ma_dinh_danh = ten.lower() + chu_cai_dau
                
                sdt = str(row[3]).strip() if row[3] else ''
                email = str(row[4]).strip() if row[4] else ''
                que_quan = str(row[5]).strip() if row[5] else ''
                
                # Parse Ngày sinh
                ngay_sinh = False
                if row[6]:
                    if isinstance(row[6], datetime):
                        ngay_sinh = row[6].date()
                    else:
                        try:
                            # Parse DD/MM/YYYY text
                            ngay_sinh = datetime.strptime(str(row[6]).strip(), "%d/%m/%Y").date()
                        except:
                            pass
                            
                loai_hd_text = str(row[7]).strip() if row[7] else 'Thử việc'
                loai_hd = hd_map.get(loai_hd_text, 'thu_viec')
                
                # Relational fields
                phong_ban_name = str(row[8]).strip() if row[8] else ''
                chuc_vu_name = str(row[9]).strip() if row[9] else ''
                
                phong_ban_id = False
                if phong_ban_name:
                    don_vi = don_vi_obj.search([('name', '=ilike', phong_ban_name)], limit=1)
                    if not don_vi:
                        don_vi = don_vi_obj.create({'name': phong_ban_name})
                    phong_ban_id = don_vi.id
                    
                chuc_vu_id = False
                if chuc_vu_name:
                    chuc_vu = chuc_vu_obj.search([('name', '=ilike', chuc_vu_name)], limit=1)
                    if not chuc_vu:
                        chuc_vu = chuc_vu_obj.create({'name': chuc_vu_name})
                    chuc_vu_id = chuc_vu.id
                    
                luong_cb = 5000000
                if row[10]:
                    try:
                        luong_cb = float(row[10])
                    except:
                        pass
                
                # Check tồn tại
                nv = nhan_vien_obj.search([('ma_dinh_danh', '=', ma_dinh_danh)], limit=1)
                
                vals = {
                    'ho_ten_dem': ho_dem,
                    'ten': ten,
                    'so_dien_thoai': sdt,
                    'email': email,
                    'que_quan': que_quan,
                    'ngay_sinh': ngay_sinh,
                    'loai_hop_dong': loai_hd,
                    'phong_ban_hien_tai_id': phong_ban_id,
                    'chuc_vu_hien_tai_id': chuc_vu_id,
                    'luong_co_ban': luong_cb
                }
                
                if nv:
                    nv.write(vals)
                else:
                    vals['ma_dinh_danh'] = ma_dinh_danh
                    nhan_vien_obj.create(vals)
                    
                count_success += 1
                
            except Exception as e:
                errors.append(f"Dòng {row_idx}: Lỗi hệ thống - {str(e)}")

        if errors:
            err_msg = "\n".join(errors)
            raise UserError(f'Thành công: {count_success} Nhân viên.\n\nNhưng có lỗi tại các dòng sau:\n{err_msg}')
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '✅ Import thành công!',
                'message': f'Đã cập nhật/tạo mới {count_success} hồ sơ nhân viên trong hệ thống.',
                'type': 'success',
                'sticky': False,
            }
        }
