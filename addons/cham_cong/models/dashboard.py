from odoo import models, fields, api
from datetime import date, timedelta
import pytz

class ChamCongDashboard(models.AbstractModel):
    _name = 'cham_cong.dashboard'
    _description = 'Cham Cong Dashboard Data Provider'

    @api.model
    def get_dashboard_data(self):
        """ Fetch and compute stats for the Attendance Dashboard """
        today = date.today()
        first_day_of_month = today.replace(day=1)
        
        # 1. KPI: Total Check-ins Today
        total_nv = self.env['nhan_vien'].search_count([])
        checkins_today = self.env['cham_cong'].search_count([
            ('ngay', '=', today)
        ])
        
        # 2. KPI: Lates / Early leaves this month
        lates_this_month = self.env['cham_cong'].search_count([
            ('ngay', '>=', first_day_of_month),
            ('trang_thai', 'in', ['muon', 've_som', 'muon_ve_som'])
        ])
        lates_today = self.env['cham_cong'].search_count([
            ('ngay', '=', today),
            ('trang_thai', 'in', ['muon', 've_som', 'muon_ve_som'])
        ])
        
        # 3. KPI: Pending Requests (Đơn từ chờ duyệt)
        pending_requests = self.env['don_tu'].search_count([
            ('trang_thai', '=', 'cho_duyet')
        ])
        
        # --- CHARTS DATA ---
        
        # Chart 1: Attendance over the last 7 days
        last_7_days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
        bar_labels = [d.strftime('%d/%m') for d in last_7_days]
        bar_on_time = []
        bar_late = []
        bar_absent = []
        
        for d in last_7_days:
            # Count on time or purely checked in
            on_time = self.env['cham_cong'].search_count([
                ('ngay', '=', d),
                ('trang_thai', 'not in', ['muon', 've_som', 'muon_ve_som', 'vang_mat'])
            ])
            # Count late/early
            late = self.env['cham_cong'].search_count([
                ('ngay', '=', d),
                ('trang_thai', 'in', ['muon', 've_som', 'muon_ve_som'])
            ])
            # Absent (either explicitly marked or total - checked in)
            total_checked = on_time + late
            absent = max(0, total_nv - total_checked)
            
            bar_on_time.append(on_time)
            bar_late.append(late)
            bar_absent.append(absent)

        # Chart 2: Leave Requests Distribution (cho_duyet, da_duyet, tu_choi)
        leave_cho_duyet = pending_requests
        leave_da_duyet = self.env['don_tu'].search_count([('trang_thai', '=', 'da_duyet')])
        leave_tu_choi = self.env['don_tu'].search_count([('trang_thai', '=', 'tu_choi')])
        
        return {
            'kpi': {
                'total_employees': total_nv,
                'checkins_today': checkins_today,
                'lates_this_month': lates_this_month,
                'lates_today': lates_today,
                'pending_requests': pending_requests,
            },
            'charts': {
                'bar': {
                    'labels': bar_labels,
                    'on_time': bar_on_time,
                    'late': bar_late,
                    'absent': bar_absent,
                },
                'doughnut': {
                    'labels': ['Chờ duyệt', 'Đã duyệt', 'Từ chối'],
                    'data': [leave_cho_duyet, leave_da_duyet, leave_tu_choi],
                }
            }
        }
