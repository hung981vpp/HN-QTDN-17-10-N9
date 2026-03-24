from odoo import models, fields, api
from datetime import date
from dateutil.relativedelta import relativedelta

class TinhLuongDashboard(models.AbstractModel):
    _name = 'tinh_luong.dashboard'
    _description = 'Dashboard Data Provider for Payroll'

    @api.model
    def get_dashboard_data(self):
        """ Fetch and compute stats for the Payroll Dashboard """
        today = date.today()
        current_month = str(today.month)
        current_year = today.year

        # 1. KPIs for current month
        domain_current = [('thang', '=', current_month), ('nam', '=', current_year)]
        bang_luongs_hien_tai = self.env['bang_luong'].search(domain_current)
        
        payslips_count = len(bang_luongs_hien_tai)
        total_salary = sum(bang_luongs_hien_tai.mapped('luong_thuc_nhan'))
        total_bonus = sum(bang_luongs_hien_tai.mapped('tong_thuong'))
        total_penalty = sum(bang_luongs_hien_tai.mapped('tong_phat'))

        # 2. Charts Data
        
        # Chart 1: Salary Trend over last 6 months
        trend_labels = []
        trend_salary = []
        
        for i in range(5, -1, -1):
            m_date = today - relativedelta(months=i)
            m_str = str(m_date.month)
            y_int = m_date.year
            trend_labels.append(f"T{m_str}/{y_int}")
            
            records = self.env['bang_luong'].search([('thang', '=', m_str), ('nam', '=', y_int)])
            trend_salary.append(sum(records.mapped('luong_thuc_nhan')))

        # Chart 2: Status Distribution (Current Month)
        status_chua_duyet = len(bang_luongs_hien_tai.filtered(lambda r: r.trang_thai == 'chua_duyet'))
        status_da_duyet = len(bang_luongs_hien_tai.filtered(lambda r: r.trang_thai == 'da_duyet'))
        status_da_thanh_toan = len(bang_luongs_hien_tai.filtered(lambda r: r.trang_thai == 'da_thanh_toan'))

        # 3. Recent Records
        recent_records = self.env['bang_luong'].search([], order='nam desc, thang desc, id desc', limit=15)
        history = []
        trang_thai_map = dict(self.env['bang_luong']._fields['trang_thai'].selection)
        
        for rec in recent_records:
            history.append({
                'id': rec.id,
                'ma_bang_luong': rec.ma_bang_luong,
                'nhan_vien': rec.id_nhan_vien.ho_va_ten or '',
                'ky_luong': f"T{rec.thang}/{rec.nam}",
                'tong_luong': rec.luong_thuc_nhan,
                'trang_thai': trang_thai_map.get(rec.trang_thai, rec.trang_thai or ''),
                'trang_thai_key': rec.trang_thai or '',
            })
            
        return {
            'kpi': {
                'payslips_count': payslips_count,
                'total_salary': total_salary,
                'total_bonus': total_bonus,
                'total_penalty': total_penalty,
            },
            'charts': {
                'trend': {
                    'labels': trend_labels,
                    'salary': trend_salary,
                },
                'doughnut_status': {
                    'labels': ['Chưa duyệt', 'Đã duyệt', 'Đã thanh toán'],
                    'data': [status_chua_duyet, status_da_duyet, status_da_thanh_toan],
                }
            },
            'history': history,
        }
