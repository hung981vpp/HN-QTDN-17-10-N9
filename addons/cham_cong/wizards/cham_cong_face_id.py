# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import base64
import logging

_logger = logging.getLogger(__name__)

class ChamCongFaceID(models.TransientModel):
    _name = 'cham_cong.face_id.wizard'
    _description = 'Check-in/Out bằng Face ID'

    image = fields.Binary('Ảnh khuôn mặt lấy từ Camera', required=True)
    
    def action_checkin_faceid(self):
        self.ensure_one()
        if not self.image:
            raise ValidationError("Vui lòng chụp ảnh khuôn mặt!")
            
        try:
            import face_recognition
            import numpy as np
            import cv2
        except ImportError as e:
            raise ValidationError(f"Lỗi Import thư viện: {str(e)}. Hệ thống chưa cài đặt đủ thư viện (face_recognition, opencv). Báo Admin!")
            
        # 1. Decode base64 image from user upload/webcam
        try:
            img_data = base64.b64decode(self.image)
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                raise ValueError("Không thể đọc định dạng ảnh.")
                
            # face_recognition takes RGB images
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            face_encodings = face_recognition.face_encodings(rgb_img)
            
            if not face_encodings:
                raise ValidationError("Không tìm thấy khuôn mặt nào trong ảnh. Vui lòng nhìn thẳng vào camera, đảm bảo đủ sáng và thử lại!")
            if len(face_encodings) > 1:
                raise ValidationError("Có quá nhiều khuôn mặt. Vui lòng chỉ chụp một mình bạn!")
                
            current_face_encoding = face_encodings[0]
        except ValidationError:
            raise
        except Exception as e:
            _logger.error(f'Face Decode Error: {str(e)}')
            raise ValidationError(f"Xử lý ảnh lỗi: {str(e)}")
            
        # 2. Match against all employees with image
        nhan_viens = self.env['nhan_vien'].search([('anh', '!=', False)])
        matched_nhan_vien = None
        min_distance = 1.0
        threshold = 0.50 # Tolerance: The lower, the stricter
        
        for nv in nhan_viens:
            try:
                nv_img_data = base64.b64decode(nv.anh)
                nv_nparr = np.frombuffer(nv_img_data, np.uint8)
                nv_img = cv2.imdecode(nv_nparr, cv2.IMREAD_COLOR)
                
                if nv_img is None:
                    continue # Skip invalid profiles
                    
                nv_rgb_img = cv2.cvtColor(nv_img, cv2.COLOR_BGR2RGB)
                nv_encodings = face_recognition.face_encodings(nv_rgb_img)
                
                if nv_encodings:
                    nv_encoding = nv_encodings[0]
                    # Calculate euclidean distance
                    distance = face_recognition.face_distance([nv_encoding], current_face_encoding)[0]
                    if distance < threshold and distance < min_distance:
                        min_distance = distance
                        matched_nhan_vien = nv
            except Exception as e:
                _logger.error(f"Error processing profile image for NV {nv.ho_va_ten}: {str(e)}")
                continue
                
        # 3. Handle Attendance logic
        if matched_nhan_vien:
            today = fields.Date.today()
            cham_cong = self.env['cham_cong'].search([
                ('id_nhan_vien', '=', matched_nhan_vien.id),
                ('ngay', '=', today)
            ], limit=1)
            
            # Using Telegram check-in logic to handle actual checkin mechanism
            if not cham_cong or not cham_cong.gio_vao:
                # Chưa check-in
                result = self.env['cham_cong'].zalo_checkin(matched_nhan_vien.id, "FaceID_Web")
                msg = f"Xin chào {matched_nhan_vien.ho_va_ten}! {result.get('message', 'Check-in thành công.')}"
            else:
                if not cham_cong.gio_ra:
                    # Đã check-in -> Gọi check-out
                    result = self.env['cham_cong'].zalo_checkout(matched_nhan_vien.id, "FaceID_Web")
                    msg = f"Tạm biệt {matched_nhan_vien.ho_va_ten}. {result.get('message', 'Check-out thành công.')}"
                else:
                    msg = f"Chào {matched_nhan_vien.ho_va_ten}, bạn đã hoàn tất cả check-in và check-out đủ cho hôm nay rồi!"
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Face ID Thành công',
                    'message': msg,
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise ValidationError(f"Không thể nhận diện! Không tìm thấy nhân viên nào trùng khớp với khuôn mặt này (Độ lệch {min_distance:.2f} >= {threshold}). Vui lòng cập nhật Ảnh chân dung chuẩn trong Hồ sơ và thử lại!")
