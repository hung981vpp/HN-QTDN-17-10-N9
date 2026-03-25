from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
from datetime import datetime, time
import pytz

try:
    import openpyxl
except ImportError:
    openpyxl = None

class ImportChamCongWizard(models.TransientModel):
    _name = 'import.cham.cong.wizard'
    _description = 'Wizard Nhập dữ liệu Chấm Công từ Excel'

    file_upload = fields.Binary(string='File Excel')
    file_name = fields.Char(string='Tên File')
    
    def action_download_template(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/cham_cong/static/src/files/template_cham_cong.xlsx',
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
            raise UserError(f"File không đúng định dạng Excel (.xlsx). Lỗi: {str(e)}")

        cham_cong_obj = self.env['cham_cong']
        nhan_vien_obj = self.env['nhan_vien']
        
        count_success = 0
        errors = []
        tz = pytz.timezone('Asia/Ho_Chi_Minh')
        
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not any(row): continue
                
            try:
                ma_dinh_danh = str(row[0]).strip() if row[0] else ''
                ngay_str = str(row[2]).strip() if row[2] else ''
                
                if not ma_dinh_danh or not ngay_str:
                    errors.append(f"Dòng {row_idx}: Thiếu Mã Định Danh hoặc Ngày.")
                    continue
                    
                # Parse date
                ngay_lam = False
                if isinstance(row[2], datetime):
                    ngay_lam = row[2].date()
                else:
                    try:
                        ngay_lam = datetime.strptime(ngay_str.split(' ')[0], "%d/%m/%Y").date()
                    except:
                        errors.append(f"Dòng {row_idx}: Ngày phải định dạng DD/MM/YYYY.")
                        continue
                
                nv = nhan_vien_obj.search([('ma_dinh_danh', '=', ma_dinh_danh)], limit=1)
                if not nv:
                    errors.append(f"Dòng {row_idx}: Không tìm thấy nhân viên mã '{ma_dinh_danh}'.")
                    continue
                
                ghi_chu = str(row[5]).strip() if row[5] else ''
                
                def parse_time_to_utc(val):
                    if not val: return False
                    h, m = 0, 0
                    if isinstance(val, time):
                        h, m = val.hour, val.minute
                    elif isinstance(val, str) and ':' in val:
                        try:
                            parts = val.split(':')
                            h, m = int(parts[0]), int(parts[1])
                        except:
                            return False
                    else:
                        return False
                        
                    local_dt = datetime.combine(ngay_lam, time(h, m))
                    local_dt = tz.localize(local_dt)
                    utc_dt = local_dt.astimezone(pytz.utc).replace(tzinfo=None)
                    return utc_dt
                
                gio_vao_utc = parse_time_to_utc(row[3])
                gio_ra_utc = parse_time_to_utc(row[4])
                
                # Check existing
                cc = cham_cong_obj.search([('id_nhan_vien', '=', nv.id), ('ngay', '=', ngay_lam)], limit=1)
                
                vals = {}
                if gio_vao_utc: vals['gio_vao'] = gio_vao_utc
                if gio_ra_utc: vals['gio_ra'] = gio_ra_utc
                if ghi_chu: vals['ghi_chu'] = ghi_chu
                
                if cc:
                    if vals: cc.write(vals)
                else:
                    # Tự động sinh ID chấm công nếu record mới
                    vals['id_nhan_vien'] = nv.id
                    vals['ngay'] = ngay_lam
                    vals['nguon_checkin'] = 'device'
                    cham_cong_obj.create(vals)
                    
                count_success += 1
            except Exception as e:
                errors.append(f"Dòng {row_idx}: Lỗi hệ thống - {str(e)}")

        if errors:
            err_msg = "\n".join(errors)
            raise UserError(f'Thành công: {count_success} lượt chấm công.\n\nLỗi:\n{err_msg}')
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '✅ Import thành công!',
                'message': f'Đã cập nhật/tạo mới {count_success} lượt chấm công.',
                'type': 'success',
            }
        }
