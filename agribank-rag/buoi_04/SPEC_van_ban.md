# SPEC — Ứng dụng quản lý văn bản nội bộ (agribank-vanban)
 
## Mục tiêu
Web app quản lý danh mục văn bản nội bộ cho nhóm KTNB.
 
## Chức năng bắt buộc
- Thêm văn bản mới (số hiệu, tiêu đề, ngày ban hành, trạng thái hiệu lực)
- Sửa thông tin văn bản
- Xóa văn bản
- Tìm kiếm theo số hiệu / tiêu đề
- Lọc theo trạng thái hiệu lực (còn hiệu lực / hết hiệu lực)
 
## Dữ liệu
- Lưu tạm trong bộ nhớ
- Mỗi văn bản gồm: so_hieu, tieu_de, ngay_ban_hanh, con_hieu_luc
 
## Ràng buộc
- Giao diện tiếng Việt, giữ đúng dấu
- Code gọn, dễ đọc, có chú thích
- Không hardcode dữ liệu nhạy cảm
