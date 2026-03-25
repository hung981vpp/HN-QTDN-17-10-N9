# 🏢 Hệ thống Quản lý Nhân sự - Chấm công - Tính lương
<h2 align="center">
    <a href="https://dainam.edu.vn/vi/khoa-cong-nghe-thong-tin">
    🎓 Faculty of Information Technology (DaiNam University)
    </a>
</h2>
<div align="center">
    <p align="center">
        <img src="docs/logo/aiotlab_logo.png" alt="AIoTLab Logo" width="170"/>
        <img src="docs/logo/fitdnu_logo.png" alt="AIoTLab Logo" width="180"/>
        <img src="docs/logo/dnu_logo.png" alt="DaiNam University Logo" width="200"/>
    </p>

[![AIoTLab](https://img.shields.io/badge/AIoTLab-green?style=for-the-badge)](https://www.facebook.com/DNUAIoTLab)
[![Faculty of Information Technology](https://img.shields.io/badge/Faculty%20of%20Information%20Technology-blue?style=for-the-badge)](https://dainam.edu.vn/vi/khoa-cong-nghe-thong-tin)
[![DaiNam University](https://img.shields.io/badge/DaiNam%20University-orange?style=for-the-badge)](https://dainam.edu.vn)

</div>

> **Bài tập lớn học phần Hội nhập & Quản trị phần mềm Doanh nghiệp**  
> Nhóm 9 — Lớp CNTT 17-10 — Khoa Công nghệ Thông tin — Đại học Đại Nam

---

## 📖 Giới thiệu

Dự án xây dựng hệ thống **ERP quản lý nguồn nhân lực** trên nền tảng mã nguồn mở **Odoo**, bao gồm 3 module nghiệp vụ cốt lõi được tích hợp chặt chẽ với nhau:

| Module | Mô tả |
|---|---|
| 👤 `nhan_su` | Quản lý hồ sơ nhân viên, phòng ban, chức vụ |
| 🕐 `cham_cong` | Ghi nhận và theo dõi thời gian làm việc |
| 💰 `tinh_luong` | Tính toán và quản lý bảng lương hàng tháng |

---

## 🧩 Các Module Chính

### 👤 Module Nhân Sự (`nhan_su`)

Quản lý toàn bộ thông tin nhân viên trong doanh nghiệp:

- Lưu trữ hồ sơ nhân viên: họ tên, ngày sinh, CCCD, địa chỉ, liên hệ
- Quản lý phòng ban và chức vụ
- Theo dõi hợp đồng lao động và loại hợp đồng
- Phân quyền theo vai trò người dùng (HR Manager, Employee)

---

### 🕐 Module Chấm Công (`cham_cong`)

Theo dõi và quản lý thời gian làm việc của nhân viên:

- Ghi nhận giờ vào / giờ ra theo từng ngày
- Theo dõi đi trễ, về sớm, làm thêm giờ (OT)
- Quản lý nghỉ phép, nghỉ lễ
- Tổng hợp bảng chấm công theo tháng, phòng ban
- Tích hợp dữ liệu với module Tính lương

---

### 💰 Module Tính Lương (`tinh_luong`)

Tự động tính toán và quản lý lương nhân viên:

- Cấu hình các khoản lương, phụ cấp và khấu trừ
- Tính lương tự động dựa trên dữ liệu chấm công
- Hỗ trợ các loại: lương cố định, lương theo ngày công
- Tính bảo hiểm xã hội, bảo hiểm y tế, thuế TNCN
- Xuất bảng lương chi tiết theo nhân viên / phòng ban

---

## 🔧 Công Nghệ Sử Dụng

| Thành phần | Công nghệ |
|---|---|
| Nền tảng ERP | Odoo 17 |
| Ngôn ngữ backend | Python 3.10 |
| Ngôn ngữ frontend | JavaScript, XML |
| Cơ sở dữ liệu | PostgreSQL |
| Hệ điều hành | Ubuntu |
| Container | Docker |

---

## ⚙️ Hướng Dẫn Cài Đặt

### 1. Clone repository

```bash
git clone https://github.com/hung981vpp/HN-QTDN-17-10-N9.git
cd HN-QTDN-17-10-N9
```

### 2. Cài đặt thư viện hệ thống

```bash
sudo apt-get install libxml2-dev libxslt-dev libldap2-dev libsasl2-dev \
  libssl-dev python3.10-distutils python3.10-dev build-essential \
  libffi-dev zlib1g-dev python3.10-venv libpq-dev
```

### 3. Khởi tạo môi trường ảo Python

```bash
python3.10 -m venv ./venv
source venv/bin/activate
pip3 install -r requirements.txt
```

### 4. Khởi động database (Docker)

```bash
sudo docker-compose up -d
```

### 5. Cấu hình Odoo

Tạo file `odoo.conf` với nội dung:

```ini
[options]
addons_path = addons
db_host = localhost
db_password = odoo
db_user = odoo
db_port = 5431
xmlrpc_port = 8069
```

### 6. Chạy hệ thống

```bash
python3 odoo-bin.py -c odoo.conf -u all
```

Truy cập hệ thống tại: [http://localhost:8069](http://localhost:8069)

---

## 📁 Cấu Trúc Module

```
module_name/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── model_name.py
├── views/
│   ├── model_views.xml
│   └── menu_views.xml
├── security/
│   └── ir.model.access.csv
├── data/
└── static/
    └── src/
        ├── css/
        ├── js/
        └── img/
```

---

## 👥 Thành Viên Nhóm 9

| STT | Họ và Tên | Mã sinh viên | Vai trò |
|---|---|---|---|
| 1 | Đàm Vĩnh Hưng | 1771020333 | Trưởng nhóm |
| 2 | Vương Thị Ngọc Ánh | 1771020066 | Thành viên |
| 3 | Phạm Thị Yến Anh | 1771020060 | Thành viên |

---

## 📝 License

© 2024 AIoTLab, Khoa Công nghệ Thông tin, Đại học Đại Nam. All rights reserved.