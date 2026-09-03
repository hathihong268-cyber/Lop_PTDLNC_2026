# BÁO CÁO KIỂM TRA DỮ LIỆU VÀ MÔI TRƯỜNG DỰ ÁN — BUỔI 14

**Ngày thực hiện**: 15/08/2026  
**Chủ đề**: *Hybrid Search + Reranking + Mini Knowledge Graph*  
**Thư mục làm việc**: `Rag_thuchanh/RAG/rag_foundation/buoi_14`  

---

## 1. Cấu Trúc Thư Mục & File Hiện Có Trong `buoi_14/`

| Loại File | Danh Sách / Trạng Thái | Ghi Chú |
|---|---|---|
| **Python (`.py`)** | *Chưa có* | Chưa tạo file mã nguồn nào |
| **Markdown (`.md`)** | `buoi_14.md` | Tài liệu đặc tả yêu cầu và kịch bản thực hành |
| **Dữ liệu (`.csv`)** | *Chưa có* | Toàn bộ dữ liệu trung gian sẽ tạo trong `buoi_14/` |
| **Cấu hình (`.json`, `.env`)** | *Chưa có* | Chưa khởi tạo cấu hình môi trường |
| **Requirements (`requirements.txt`)** | *Chưa có* | Sẽ định nghĩa dependency tối thiểu theo yêu cầu |
| **Môi trường ảo (`.venv/`)** | Đã có | `buoi_14/.venv` sẵn sàng |

---

## 2. Thẩm Định Chi Tiết 3 File Dữ Liệu Nguồn (`kb+hops/`)

> [!IMPORTANT]
> Toàn bộ 3 file nguồn trong `../buoi_10/graph_rag_labs/kb+hops/` được **đọc trực tiếp ở chế độ CHỈ ĐỌC (Read-Only)**. Không copy, move, sửa đổi hay ghi đè.

### 2.1. `metadata.csv`
- **Đường dẫn**: `.../graph_rag_labs/kb+hops/metadata.csv`
- **Dung lượng**: 5,982 bytes
- **Encoding**: `UTF-8`
- **Tổng số dòng**: **15 dòng** (tương ứng 15 văn bản quy định / pháp quy)
- **Số cột**: 17 cột
- **Danh sách cột**:
  `id`, `title`, `so_ky_hieu`, `ngay_ban_hanh`, `loai_van_ban`, `ngay_co_hieu_luc`, `ngay_het_hieu_luc`, `nguon_thu_thap`, `ngay_dang_cong_bao`, `nganh`, `linh_vuc`, `co_quan_ban_hanh`, `chuc_danh`, `nguoi_ky`, `pham_vi`, `thong_tin_ap_dung`, `tinh_trang_hieu_luc`
- **Kiểm tra trùng lặp (Duplicates)**: 0 dòng trùng
- **Thống kê giá trị Null / Rỗng**:
  - `thong_tin_ap_dung`: 15/15 null (100.0%)
  - `ngay_het_hieu_luc`: 14/15 null (93.3%)
  - `ngay_dang_cong_bao`: 11/15 null (73.3%)
  - `nguon_thu_thap`: 5/15 null (33.3%)
  - `nganh`: 3/15 null (20.0%)
  - `linh_vuc`: 2/15 null (13.3%)
  - `ngay_co_hieu_luc`: 1/15 null (6.7%)
  - Các cột còn lại: 0% null (đầy đủ 15/15)
- **Khóa chính có thể sử dụng (Primary Key)**: `id` (15 giá trị duy nhất, gồm cả định dạng số nguyên và UUID) hoặc `so_ky_hieu`.
- **Trường text phù hợp Retrieval**: `title` (tiêu đề đầy đủ của văn bản).
- **Metadata phù hợp Citation**: `id`, `so_ky_hieu`, `title`, `loai_van_ban`, `ngay_ban_hanh`, `co_quan_ban_hanh`, `tinh_trang_hieu_luc`.

---

### 2.2. `content.csv`
- **Đường dẫn**: `.../graph_rag_labs/kb+hops/content.csv`
- **Dung lượng**: 3,064,989 bytes (~3 MB)
- **Encoding**: `UTF-8`
- **Tổng số dòng**: **15 dòng** (khớp 1-1 với 15 văn bản trong `metadata.csv`)
- **Số cột**: 2 cột
- **Danh sách cột**: `id`, `content_html`
- **Kiểm tra trùng lặp (Duplicates)**: 0 dòng trùng
- **Thống kê giá trị Null**: 0/15 (0% null, toàn bộ 15 văn bản đều có nội dung HTML)
- **Khóa chính**: `id` (khớp với `metadata.csv.id`)
- **Trường text phù hợp Retrieval**: `content_html` chứa toàn văn định dạng HTML. Cần bóc tách thẻ HTML (`html parser` / `BeautifulSoup`), trích xuất văn bản thuần và chia nhỏ thành các Điều/Khoản (chunking) để phục vụ **BM25**, **Dense Embedding** và **Reranking**.
- **Metadata phù hợp Citation**: `id` kết hợp với thông tin Điều/Khoản sau khi trích xuất.

---

### 2.3. `relationships.csv`
- **Đường dẫn**: `.../graph_rag_labs/kb+hops/relationships.csv`
- **Dung lượng**: 387 bytes
- **Encoding**: `UTF-8`
- **Tổng số dòng**: **8 dòng** (8 mối quan hệ pháp lý thực tế)
- **Số cột**: 4 cột
- **Danh sách cột**: `doc_id`, `other_doc_id`, `relationship`, `relationship_type`
- **Kiểm tra trùng lặp**: 0 dòng trùng
- **Thống kê giá trị Null**: 0/8 (0% null)
- **Khóa liên kết (Foreign Keys)**: `doc_id` và `other_doc_id` trỏ về `id` của `metadata.csv` / `content.csv`.
- **Tập quan hệ thực tế trong dữ liệu**:
  1. `SUA_DOI_BO_SUNG` (Sửa đổi, bổ sung): 1 quan hệ (`169221` -> `44209`)
  2. `CAN_CU` (Căn cứ): 4 quan hệ (`112924` -> `95652`, `174218` -> `25692`, `168220` -> `166269`, `117310` -> `25692`)
  3. `VAN_BAN_BO_SUNG` (Văn bản bổ sung): 1 quan hệ (`177271` -> `185630`)
  4. `THAY_THE` (Thay thế): 1 quan hệ (`163441` -> `112025`)
  5. `HOP_NHAT` (Hợp nhất): 1 quan hệ (`6e689cd0-6f81-11f1-94d6-fd5d6d5ff793` -> `173695`)
- **Nguyên tắc Knowledge Graph**: Chỉ nạp đúng 5 loại quan hệ có thực này vào Neo4j, không tự bịa thêm quan hệ.

---

## 3. Rà Soát Mã Nguồn & Nguy Cơ Phá Hủy Dữ Liệu

- **Mã nguồn trong `buoi_14/`**: Hiện chưa có file code (`.py`) nào.
- **Rà soát từ khóa nguy hiểm**:
  - `os.remove`: Không có trong code
  - `shutil.rmtree`: Không có trong code
  - `open(..., "w")`: Không có trong code
  - `DELETE` / `DROP` / `DETACH DELETE`: Không có script nào thực thi câu lệnh xóa cơ sở dữ liệu.
- **Đánh giá rủi ro**: **AN TOÀN TUYỆT ĐỐI**.

---

## 4. Kiểm Tra Môi Trường Thực Thi

- **Python Binary**: `Python 3.14.6 (tags/v3.14.6:c63aec6, Jun 10 2026)`
- **Môi trường ảo**: `buoi_14/.venv` hoạt động bình thường.
- **Kiểm tra `import pandas`**: `ModuleNotFoundError: No module named 'pandas'` (Chưa cài đặt - đúng theo quy trình chưa cài hàng loạt).

---

## 5. Kết Luận
Môi trường và dữ liệu nguồn đã được thẩm định đầy đủ và sẵn sàng để tiến hành các bước tiếp theo.
