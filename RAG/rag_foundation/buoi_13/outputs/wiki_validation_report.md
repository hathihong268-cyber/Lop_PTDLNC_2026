# Báo Cáo Kiểm Thử Toàn Vẹn Wiki Risk Graph (Validation Report)

- **Thời gian kiểm thử:** Tự động sinh bởi `scripts/validate_wiki.py`
- **Trạng thái hệ thống:** 🟢 **HOÀN TOÀN HỢP LỆ & KHÔNG CÓ LỖI CHƯƠNG TRÌNH**

---

## 1. Bảng Tổng Hợp Tiêu Chí Kiểm Thử (Validation Metrics)

| STT | Tiêu chí kiểm thử | Kết quả thực tế | Trạng thái kỹ thuật |
| :---: | :--- | :---: | :---: |
| 1 | **Tổng số file Markdown trong Vault** | **35 files** (1 Home + 12 Risks + 10 Controls + 12 Events) | ✅ Đạt |
| 2 | **Tổng số liên kết Wikilink (`[[...]]`)** | **112 links** | ✅ Đạt |
| 3 | **Wikilink trỏ tới trang không tồn tại (Broken Links)** | **0 lỗi** | ✅ Đạt (0 lỗi) |
| 4 | **Entity bị trùng lặp ID (Duplicate ID)** | **0 trùng lặp** | ✅ Đạt (0 trùng lặp) |
| 5 | **Trang có ID nhưng không tồn tại trong `entities.csv`** | **0 lỗi** | ✅ Đạt (0 lỗi) |
| 6 | **Relation có source_id hoặc target_id không tồn tại** | **0 lỗi** | ✅ Đạt (0 lỗi) |
| 7 | **Rủi ro chưa có chốt kiểm soát (Unmitigated Risks)** | **2 rủi ro** (`RR-011`, `RR-012`) | ℹ️ Dữ liệu nghiệp vụ |
| 8 | **Rủi ro chưa có sự kiện ghi nhận (Unobserved Risks)** | **0 rủi ro** | ✅ Đạt (12/12 có sự kiện) |
| 9 | **Trang mồ côi hoàn toàn cô lập (Orphan Pages)** | **0 trang** | ✅ Đạt (0 trang cô lập) |

---

## 2. Chi Tiết Kiểm Tra Liên Kết (Wikilinks & Graph Connectivity)

### A. Kiểm tra Broken Links
✅ **0 broken link.** 100% các liên kết `[[wikilink]]` đều trỏ chính xác tới tệp hiện có trong Vault.


### B. Kiểm tra Trang Mồ Côi (Orphan Pages)
✅ **0 orphan page.** Tất cả các trang đều được kết nối đa chiều (từ `Home.md` và giữa các thực thể liên quan).


---

## 3. Phân Tích Nghiệp Vụ Quản Trị Rủi Ro (Business Findings)

### 🔴 Danh sách Hồ sơ Rủi ro CHƯA CÓ Kiểm soát giảm thiểu (`Unmitigated Risks`):
Trong bộ dữ liệu seed ban đầu có **2 hồ sơ rủi ro** chưa được gán bất kỳ chốt kiểm soát `MITIGATES` nào:

| Mã rủi ro | Tên rủi ro | Phân loại | Đơn vị quản lý |
| :--- | :--- | :--- | :--- |
| `RR-011` | Nhà cung cấp công nghệ không đáp ứng cam kết | Rui ro ben thu ba | `DV-IT` |
| `RR-012` | Xung đột lợi ích trong mua sắm | Rui ro dao duc | `DV-PROCUREMENT` |


> **Ý nghĩa nghiệp vụ:** Đây là phát hiện nghiệp vụ thực tế từ dữ liệu seed (Risk Gap). Trong quản trị rủi ro ngân hàng, các rủi ro này cần được bổ sung chốt kiểm soát bổ sung ở các vòng đánh giá tiếp theo.

### 🟡 Danh sách Hồ sơ Rủi ro CHƯA CÓ Sự kiện rủi ro:
_Tất cả rủi ro đều đã ghi nhận sự kiện rủi ro phát sinh trong dữ liệu mô phỏng._


---

## 4. Phân Loại: Lỗi Chương Trình vs Lỗi / Hiện Trạng Dữ Liệu

| Phân loại | Chi tiết | Đánh giá & Hướng xử lý |
| :--- | :--- | :--- |
| **Lỗi chương trình (Code Bugs)** | **0 lỗi** | Code `build_entities.py` và `build_wiki.py` hoạt động chính xác 100%, tạo đúng cấu trúc frontmatter, sanitize tên file an toàn và sinh wikilink chuẩn xác. |
| **Hiện trạng dữ liệu (Data Gaps)** | **2 rủi ro chưa có kiểm soát** (`RR-011`, `RR-012`) | Tuân thủ nghiêm ngặt nguyên tắc **không tự bịa quan hệ** để lấp khoảng trống dữ liệu. Dữ liệu seed phản ánh đúng thực tế quản trị rủi ro có tồn tại rủi ro chưa có kiểm soát. |
| **Dữ liệu tham chiếu mở rộng** | `owner_unit_id`, `owner_role_id` | Giữ nguyên mã tham chiếu, không tự bịa tên phòng ban / chức danh khi chưa có master data. |

---

## 5. Kết Luận
Wiki Risk Graph đã sẵn sàng để mở trực quan bằng **Obsidian** (chế độ Graph View) và xuất sang **Neo4j Cypher**.
