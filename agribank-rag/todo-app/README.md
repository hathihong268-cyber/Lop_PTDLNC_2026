# Ứng Dụng Quản Lý Công Việc KTNB — Agribank To-Do

Ứng dụng web quản lý công việc nội bộ dành cho nhóm Kiểm toán Nội bộ (KTNB), được xây dựng theo kiến trúc full-stack với Flask và Vanilla JS/CSS.

---

## 🎯 Chức năng chính
- ✅ **Thêm công việc mới**: Tên công việc, Người phụ trách.
- ✏️ **Chỉnh sửa công việc**: Cập nhật tên, người phụ trách, hoặc trạng thái.
- 🗑️ **Xóa công việc**: Xóa công việc với hộp thoại xác nhận an toàn.
- 🔄 **Đánh dấu hoàn thành / đang làm**: Chuyển đổi trạng thái nhanh với checkbox hoặc toggle API.
- 🔍 **Bộ lọc & Tìm kiếm**: Lọc theo trạng thái (*Tất cả / Đang làm / Đã xong*) và tìm kiếm theo từ khóa.
- 💾 **Lưu trữ in-memory**: Quản lý dữ liệu trong bộ nhớ tạm thời theo đúng đặc tả `SPEC.md`.

---

## 🚀 Hướng dẫn chạy ứng dụng

### Bước 1: Mở terminal tại thư mục `agribank-rag/todo-app`
```powershell
cd "d:\Lop PTDLNC 2026\agribank-rag\todo-app"
```

### Bước 2: Kích hoạt môi trường ảo Python & Khởi chạy ứng dụng
```powershell
# Kích hoạt venv (nếu chưa kích hoạt):
..\..\.venv\Scripts\Activate.ps1

# Chạy ứng dụng Flask:
python app.py
```

### Bước 3: Truy cập trên trình duyệt
Mở trình duyệt web và truy cập địa chỉ:  
👉 **http://127.0.0.1:5000**

---

## 📂 Cấu trúc thư mục

```text
todo-app/
├── app.py                  # Backend Flask REST API & In-Memory Store
├── templates/
│   └── index.html          # Giao diện tiếng Việt chuẩn nhận diện Agribank
├── static/
│   ├── css/
│   │   └── style.css       # Stylesheet responsive, hiện đại
│   └── js/
│       └── app.js          # Xử lý logic API, render danh sách, modal & filter
└── README.md               # Hướng dẫn sử dụng
```
