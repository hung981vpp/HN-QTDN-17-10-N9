from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io

try:
    import openpyxl
except ImportError:
    openpyxl = None

class ImportBangLuongWizard(models.TransientModel):
    _name = 'import.bang.luong.wizard'
    _description = 'Wizard Nhập Bảng Lương từ Excel'

    file_upload = fields.Binary(string='File Excel')
    file_name = fields.Char(string='Tên File')
    
    def action_download_template(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/tinh_luong/static/src/files/template_tinh_luong.xlsx',
            'target': 'new',
        }

    def action_import(self):
        if not openpyxl:
            raise UserError('Thư viện openpyxl chưa được cài đặt.')
        if not self.file_upload:
            raise UserError('Vui lòng chọn file Excel!')

        try:
            file_data = base64.b64decode(self.file_upload)
            file_stream = io.BytesIO(file_data)
            wb = openpyxl.load_workbook(file_stream, data_only=True)
            ws = wb.active
        except Exception as e:
            raise UserError(f"File không đúng định dạng. Lỗi: {str(e)}")

        bang_luong_obj = self.env['bang_luong']
        nhan_vien_obj = self.env['nhan_vien']
        
        count_success = 0
        errors = []
        
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not any(row): continue
                
            try:
                ma_dinh_danh = str(row[0]).strip() if row[0] else ''
                thang_val = int(row[1]) if row[1] else False
                nam_val = int(row[2]) if row[2] else 2026
                
                if not ma_dinh_danh or not thang_val:
                    errors.append(f"Dòng {row_idx}: Thiếu Mã Định Danh hoặc Tháng.")
                    continue
                
                nv = nhan_vien_obj.search([('ma_dinh_danh', '=', ma_dinh_danh)], limit=1)
                if not nv:
                    errors.append(f"Dòng {row_idx}: Không tìm thấy nhân viên mã '{ma_dinh_danh}'.")
                    continue
                
                thuong_hs = float(row[3]) if row[3] else 0.0
                thuong_lt = float(row[4]) if row[4] else 0.0
                thuong_kh = float(row[5]) if row[5] else 0.0
                phat_tc = float(row[6]) if row[6] else 0.0
                ghi_chu = str(row[7]).strip() if row[7] else ''
                
                bl = bang_luong_obj.search([
                    ('id_nhan_vien', '=', nv.id),
                    ('thang', '=', str(thang_val)),
                    ('nam', '=', nam_val)
                ], limit=1)
                
                vals = {
                    'thuong_hieu_suat': thuong_hs,
                    'thuong_le_tet': thuong_lt,
                    'thuong_khac': thuong_kh,
                    'phat_thu_cong': phat_tc,
                }
                if ghi_chu: vals['ghi_chu'] = ghi_chu

                if bl:
                    bl.write(vals)
                else:
                    vals['id_nhan_vien'] = nv.id
                    vals['thang'] = str(thang_val)
                    vals['nam'] = nam_val
                    bang_luong_obj.create(vals)
                    
                count_success += 1
            except Exception as e:
                errors.append(f"Dòng {row_idx}: Lỗi hệ thống - {str(e)}")

        if errors:
            err_msg = "\n".join(errors)
            raise UserError(f'Thành công: {count_success} lượt điều chỉnh.\n\nLỗi:\n{err_msg}')
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '✅ Import thành công!',
                'message': f'Đã cập nhật/tạo mới {count_success} bảng lương.',
                'type': 'success',
            }
        }
