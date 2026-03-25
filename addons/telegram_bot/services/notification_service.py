# -*- coding: utf-8 -*-
"""
Telegram Notification Service
Service để gửi thông báo tự động qua Telegram Bot
"""
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class TelegramNotificationService(models.AbstractModel):
    """Service để gửi notifications qua Telegram Bot"""
    _name = 'telegram.notification.service'
    _description = 'Telegram Notification Service'

    # Message Templates
    TEMPLATES = {
        'don_tu_duyet': '''✅ <b>Đơn từ đã được duyệt</b>

📋 Loại đơn: {loai_don}
📅 Ngày áp dụng: {ngay_ap_dung}
👤 Người duyệt: {nguoi_duyet}
🕐 Thời gian: {ngay_duyet}

{ghi_chu}''',

        'don_tu_tu_choi': '''❌ <b>Đơn từ đã bị từ chối</b>

📋 Loại đơn: {loai_don}
📅 Ngày áp dụng: {ngay_ap_dung}
👤 Người từ chối: {nguoi_duyet}
🕐 Thời gian: {ngay_duyet}

💬 Lý do: {ghi_chu}

Bạn có thể nộp đơn mới nếu cần.''',

        'di_muon_warning': '''⚠️ <b>Cảnh báo đi muộn</b>

🕐 Giờ check-in: {gio_vao}
📅 Ngày: {ngay}
⏰ Trạng thái: Đến muộn

💡 Bạn có thể nộp đơn xin đi muộn để tránh bị phạt.''',

        'chua_checkout': '''🔔 <b>Nhắc nhở check-out</b>

Bạn đã check-in lúc {gio_vao} nhưng chưa check-out.
📅 Ngày: {ngay}

Gửi /checkout để check-out ngay.''',

        'dang_ky_duyet': '''✅ <b>Đăng ký ca làm đã được duyệt</b>

📅 Ngày: {ngay_lam}
⏰ Ca làm: {ca_lam}
👤 Người duyệt: {nguoi_duyet}

Chúc bạn làm việc tốt! 💪''',

        'dang_ky_tu_choi': '''❌ <b>Đăng ký ca làm đã bị từ chối</b>

📅 Ngày: {ngay_lam}
⏰ Ca làm: {ca_lam}
👤 Người từ chối: {nguoi_duyet}

💬 Lý do: {ghi_chu}''',

        'thuong_phat_duyet': '''🔔 <b>Quyết định {tinh_chat} đã được duyệt</b>

📋 Loại: {loai}
💰 Số tiền: {so_tien} VND
📅 Ngày áp dụng: {ngay_ap_dung}
👤 Người ký: {nguoi_duyet}

{ghi_chu}''',

        'thuong_phat_tu_choi': '''❌ <b>Quyết định {tinh_chat} bị từ chối</b>

📋 Loại: {loai}
📅 Ngày áp dụng: {ngay_ap_dung}
👤 Người duyệt: {nguoi_duyet}

💬 Lý do: {ghi_chu}''',
    }

    def _get_telegram_user(self, nhan_vien_id):
        """Lấy Telegram user từ nhân viên"""
        return self.env['telegram.bot.user'].search([
            ('id_nhan_vien', '=', nhan_vien_id)
        ], limit=1)

    def _send_notification(self, nhan_vien_id, message):
        """Gửi notification đến nhân viên qua Telegram"""
        telegram_user = self._get_telegram_user(nhan_vien_id)

        if not telegram_user:
            _logger.warning(f'Nhân viên {nhan_vien_id} chưa liên kết Telegram account')
            return False

        try:
            result = telegram_user.send_message(message)
            if result:
                _logger.info(f'Telegram notification sent to employee {nhan_vien_id}')
            return result
        except Exception as e:
            _logger.error(f'Error sending Telegram notification: {str(e)}')
            return False

    @api.model
    def notify_don_tu_duyet(self, don_tu_id):
        """Gửi thông báo khi đơn từ được duyệt"""
        don_tu = self.env['don_tu'].browse(don_tu_id)
        if not don_tu.exists():
            return False

        loai_don_dict = dict(don_tu._fields['loai_don'].selection)
        loai_don = loai_don_dict.get(don_tu.loai_don, don_tu.loai_don)

        message = self.TEMPLATES['don_tu_duyet'].format(
            loai_don=loai_don,
            ngay_ap_dung=don_tu.ngay_ap_dung.strftime('%d/%m/%Y'),
            nguoi_duyet=don_tu.nguoi_duyet_id.name or 'N/A',
            ngay_duyet=don_tu.ngay_duyet.strftime('%d/%m/%Y %H:%M') if don_tu.ngay_duyet else 'N/A',
            ghi_chu=f'\n💬 Ghi chú: {don_tu.ghi_chu_duyet}' if don_tu.ghi_chu_duyet else ''
        )
        return self._send_notification(don_tu.nhan_vien_id.id, message)

    @api.model
    def notify_don_tu_tu_choi(self, don_tu_id):
        """Gửi thông báo khi đơn từ bị từ chối"""
        don_tu = self.env['don_tu'].browse(don_tu_id)
        if not don_tu.exists():
            return False

        loai_don_dict = dict(don_tu._fields['loai_don'].selection)
        loai_don = loai_don_dict.get(don_tu.loai_don, don_tu.loai_don)

        message = self.TEMPLATES['don_tu_tu_choi'].format(
            loai_don=loai_don,
            ngay_ap_dung=don_tu.ngay_ap_dung.strftime('%d/%m/%Y'),
            nguoi_duyet=don_tu.nguoi_duyet_id.name or 'N/A',
            ngay_duyet=don_tu.ngay_duyet.strftime('%d/%m/%Y %H:%M') if don_tu.ngay_duyet else 'N/A',
            ghi_chu=don_tu.ghi_chu_duyet or 'Không có lý do cụ thể'
        )
        return self._send_notification(don_tu.nhan_vien_id.id, message)

    @api.model
    def notify_di_muon(self, cham_cong_id):
        """Gửi cảnh báo khi nhân viên đi muộn"""
        cham_cong = self.env['cham_cong'].browse(cham_cong_id)
        if not cham_cong.exists():
            return False

        if cham_cong.trang_thai != 'den_muon' or cham_cong.co_xin_phep:
            return False

        import pytz
        tz = pytz.timezone('Asia/Ho_Chi_Minh')
        gio_vao_local = pytz.utc.localize(cham_cong.gio_vao.replace(tzinfo=None)).astimezone(tz)

        message = self.TEMPLATES['di_muon_warning'].format(
            gio_vao=gio_vao_local.strftime('%H:%M'),
            ngay=cham_cong.ngay.strftime('%d/%m/%Y')
        )
        return self._send_notification(cham_cong.id_nhan_vien.id, message)

    @api.model
    def notify_chua_checkout(self, cham_cong_id):
        """Gửi nhắc nhở khi nhân viên chưa check-out"""
        cham_cong = self.env['cham_cong'].browse(cham_cong_id)
        if not cham_cong.exists():
            return False

        if not cham_cong.gio_vao or cham_cong.gio_ra:
            return False

        import pytz
        tz = pytz.timezone('Asia/Ho_Chi_Minh')
        gio_vao_local = pytz.utc.localize(cham_cong.gio_vao.replace(tzinfo=None)).astimezone(tz)

        message = self.TEMPLATES['chua_checkout'].format(
            gio_vao=gio_vao_local.strftime('%H:%M'),
            ngay=cham_cong.ngay.strftime('%d/%m/%Y')
        )
        return self._send_notification(cham_cong.id_nhan_vien.id, message)

    @api.model
    def notify_dang_ky_duyet(self, dang_ky_id):
        """Gửi thông báo khi đăng ký ca làm được duyệt"""
        dang_ky = self.env['dang_ky_ca_lam_theo_ngay'].browse(dang_ky_id)
        if not dang_ky.exists():
            return False

        ca_lam_dict = dict(dang_ky._fields['ca_lam'].selection)
        ca_lam = ca_lam_dict.get(dang_ky.ca_lam, dang_ky.ca_lam or 'N/A')

        message = self.TEMPLATES['dang_ky_duyet'].format(
            ngay_lam=dang_ky.ngay_lam.strftime('%d/%m/%Y') if dang_ky.ngay_lam else 'N/A',
            ca_lam=ca_lam,
            nguoi_duyet=dang_ky.nguoi_duyet_id.name or 'N/A',
        )
        return self._send_notification(dang_ky.nhan_vien_id.id, message)

        return self._send_notification(dang_ky.nhan_vien_id.id, message)

    @api.model
    def notify_thuong_phat_duyet(self, phieu_id):
        """Gửi thông báo khi phiếu thưởng phạt được duyệt"""
        phieu = self.env['thuong.phat.phieu'].browse(phieu_id)
        if not phieu.exists():
            return False

        tinh_chat = 'Thưởng' if phieu.tinh_chat == 'thuong' else 'Phạt'
        message = self.TEMPLATES['thuong_phat_duyet'].format(
            tinh_chat=tinh_chat,
            loai=phieu.loai_id.ten_loai,
            so_tien='{:,.0f}'.format(phieu.so_tien),
            ngay_ap_dung=phieu.ngay_ap_dung.strftime('%m/%Y'),
            nguoi_duyet=phieu.nguoi_duyet_id.name or 'N/A',
            ghi_chu=f'\n💬 Lý do: {phieu.ly_do}' if phieu.ly_do else ''
        )
        
        results = []
        for emp in phieu.nhan_vien_ids:
            results.append(self._send_notification(emp.id, message))
        return all(results)

    @api.model
    def notify_thuong_phat_tu_choi(self, phieu_id):
        """Gửi thông báo khi phiếu thưởng phạt bị từ chối"""
        phieu = self.env['thuong.phat.phieu'].browse(phieu_id)
        if not phieu.exists():
            return False

        tinh_chat = 'Thưởng' if phieu.tinh_chat == 'thuong' else 'Phạt'
        message = self.TEMPLATES['thuong_phat_tu_choi'].format(
            tinh_chat=tinh_chat,
            loai=phieu.loai_id.ten_loai,
            ngay_ap_dung=phieu.ngay_ap_dung.strftime('%m/%Y'),
            nguoi_duyet=phieu.nguoi_duyet_id.name or 'N/A',
            ghi_chu=phieu.ly_do or 'Không có lý do cụ thể'
        )
        
        results = []
        for emp in phieu.nhan_vien_ids:
            results.append(self._send_notification(emp.id, message))
        return all(results)
