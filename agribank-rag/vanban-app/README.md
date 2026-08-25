# Ứng Dụng Quản Lý Danh Mục Văn Bản Nội Bộ — Agribank VanBan

Ứng dụng web quản lý danh mục văn bản, thông tư, quy chế nội bộ phục vụ công tác Kiểm toán Nội bộ (KTNB) và chuẩn bị dữ liệu cho hệ thống tra cứu tài liệu **Agribank RAG**.

---

## 🎯 Chức năng chính (Theo SPEC_van_ban.md)

1. **Quản lý danh mục văn bản (CRUD)**:
   - Thêm văn bản mới (Số hiệu, Tiêu đề, Ngày ban hành, Trạng thái hiệu lực).
   - Chỉnh sửa thông tin văn bản qua Modal trực quan.
   - Xóa văn bản khỏi danh mục với xác nhận an toàn.
   - Đổi nhanh trạng thái hiệu lực (*Còn hiệu lực* $\leftrightarrow$ *Hết hiệu lực*).

2. **Tìm kiếm & Bộ lọc nâng cao**:
   - **Tìm kiếm thời gian thực (Real-time Search)**: Hỗ trợ tìm kiếm theo một phần số hiệu hoặc một phần tiêu đề tiếng Việt có dấu.
   - **Bộ lọc trạng thái (Filter Tabs)**: Lọc tức thì theo *Tất cả*, *Còn hiệu lực*, *Hết hiệu lực*.

3. **Giao diện & Dữ liệu**:
   - Giao diện tiếng Việt chuẩn nhận diện thương hiệu Agribank (Emerald & Burgundy).
   - Lưu trữ dữ liệu an toàn trong bộ nhớ tạm thời (In-Memory Data Store).
   - Xử lý triệt để các trường hợp biên: chống trùng số hiệu, kiểm tra định dạng ngày, chống XSS.

---

## 🚀 Hướng dẫn chạy ứng dụng

### Bước 1: Mở terminal tại thư mục `agribank-rag/vanban-app`
```powershell
cd "d:\Lop PTDLNC 2026\agribank-rag\vanban-app"
```

### Bước 2: Kích hoạt môi trường ảo Python & Khởi chạy ứng dụng
```powershell
# Chạy file backend app.py (Port 5001):
& "d:/Lop PTDLNC 2026/.venv/Scripts/python.exe" app.py
```

### Bước 3: Truy cập trên trình duyệt
Mở trình duyệt web và truy cập địa chỉ:  
👉 **http://127.0.0.1:5001**

---

## 📂 Cấu trúc thư mục

```text
vanban-app/
├── app.py                  # Backend Flask REST API, validation & In-Memory Store
├── templates/
│   └── index.html          # Giao diện quản lý danh mục dạng bảng chuyên nghiệp
├── static/
│   ├── css/
│   │   └── style.css       # Stylesheet responsive, bảng tra cứu, badge hiệu lực
│   └── js/
│       └── app.js          # Logic tìm kiếm debounce, lọc trạng thái, CRUD & modal
└── README.md               # Tài liệu hướng dẫn sử dụng
```
