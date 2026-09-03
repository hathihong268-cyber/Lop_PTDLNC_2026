# BÁO CÁO TÁI SỬ DỤNG RBAC VÀ KIỂM THỬ SECURERETRIEVER (BUỔI 14 -> BUỔI 17)

## 1. Phân tích Dữ liệu Phân quyền (`allowed_roles`) trong Corpus

Dữ liệu được kiểm tra từ file: `../buoi_14/data/processed/chunks_secure.csv` (Tổng cộng 720 chunks).

### 1.1. Tính Ổn định Parse và Các Vai trò Tồn tại (Unique Roles)

* **Parse JSON stability:** **PASS** (100% 720/720 dòng chứa JSON array hợp lệ, 0 lỗi parse).
* **Danh sách tất cả 5 vai trò (Unique Roles) trong hệ thống:**
  1. `Admin` (Quản trị viên toàn quyền)
  2. `HR_Manager` (Cán bộ nhân sự)
  3. `Risk_Officer` (Cán bộ quản trị rủi ro & tín dụng)
  4. `Employee` (Nhân viên chính thức)
  5. `Guest` (Khách vãng lai / Đối tác ngoài)

### 1.2. Thống kê Phân bổ Chunks theo Vai trò

| Vai trò (Role) | Số Chunks được quyền xem | Tỷ lệ % trên tổng 720 Chunks | Ghi chú |
| :--- | :---: | :---: | :--- |
| **`Admin`** | 720 | 100.0% | Xem toàn bộ tài liệu |
| **`Risk_Officer`** | 563 | 78.2% | Quy định nghiệp vụ, vận chuyển tiền, tín dụng & công khai |
| **`Employee`** | 563 | 78.2% | Nội quy, quy trình nghiệp vụ & công khai |
| **`HR_Manager`** | 418 | 58.1% | Tiêu chuẩn nhân sự, lương thưởng, quy chế nội bộ & công khai |
| **`Guest`** | 261 | 36.2% | Chỉ truy cập tài liệu công khai chung |

### 1.3. Phân loại Mức độ Hạn chế Quyên Truy cập (Access Restriction Levels)

* **Restricted Chunks (<= 2 vai trò, e.g. `["Admin", "HR_Manager"]`):** **157 chunks** (21.8%). Bao gồm các văn bản nhạy cảm về tiêu chuẩn nhân sự, điều kiện bổ nhiệm thủ kho, thủ quỹ.
* **Standard Internal Chunks (3 vai trò, e.g. `["Admin", "Risk_Officer", "Employee"]`):** **302 chunks** (41.9%). Bao gồm các quy trình vận chuyển tiền, quản lý an toàn kho quỹ.
* **Public Chunks (Tất cả 5 vai trò bao gồm `Guest`):** **261 chunks** (36.2%). Văn bản công khai.

---

## 2. Kiểm thử Lọc Quyên Thực tế với `SecureRetriever`

* **File module kiểm thử:** `buoi_14/src/secure_retriever.py`
* **Query thử nghiệm:** *"Tiêu chuẩn bổ nhiệm chức danh thủ kho tiền, thủ quỹ và quy định giao nhận tiền mặt"*
* **Phương pháp tìm kiếm:** Hybrid Search (BM25 + Dense RRF Fusion)

### Kết quả Kiểm thử theo 5 Kịch bản Vai trò

| Kịch bản Vai trò | Input Role truyền vào | Roles sau chuẩn hóa | Số Chunk trả về (`top_k=5`) | Số Chunk bị lọc bỏ (`filtered_out`) | Trạng thái bảo mật |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **1. Admin** | `["Admin"]` | `['Admin']` | 5 | **0** | Đầy đủ 100% ngữ cảnh (kể cả nhạy cảm HR) |
| **2. HR** | `["HR_Manager"]` | `['HR_Manager']` | 5 | **66** | Nhận chunk nhạy cảm HR (`doc_44209_dieu_24`), loại bỏ chunk cấm khác |
| **3. Risk_Manager** | `["Risk_Officer"]` | `['Risk_Officer']` | 5 | **5** | Lọc bỏ hoàn toàn chunk nhạy cảm HR (`doc_44209_dieu_24`) |
| **4. Staff** | `["Employee"]` | `['Employee']` | 5 | **5** | Lọc bỏ hoàn toàn chunk nhạy cảm HR, chỉ trả về chunk nghiệp vụ |
| **5. Guest** | `["Guest"]` | `['Guest']` | 5 | **202** | Lọc bỏ 202 chunks nội bộ, chỉ trả về văn bản công khai |
| **6. Unknown Role** | `["Hacker_Role"]` | `['Guest']` | 5 | **202** | Cảnh báo vai trò không hợp lệ, tự động hạ quyền về `Guest` (Default Deny) |

---

## 3. Đánh giá Cơ chế Bảo mật & Khả năng Tái sử dụng

1. **Lọc trước retrieval/context (Pre-filtering):**
   * Trong BM25 & Dense Search: Quá trình tính điểm kiểm tra quyền xem ngay lập tức qua `check_access_permission`. Chunk cấm không bao giờ lọt vào danh sách ứng viên (Candidate pool).
   * Trong Hybrid Fusion & Neural Reranker: Không tính RRF hay Cross-Encoder score cho chunk bị cấm.
   * -> **Cơ chế lọc trước retrieval: ĐẠT (PASS)**.

2. **Xử lý vai trò không xác định (Unknown Role Handling):**
   * Hàm `validate_roles` tự động phát hiện vai trò lạ, phát cảnh báo và gán danh sách mặc định `['Guest']`.
   * -> **Cơ chế Default Deny / Least Privilege: ĐẠT (PASS)**.

3. **Tái sử dụng nguyên trạng:**
   * Dữ liệu `chunks_secure.csv` và code `SecureRetriever` từ Buổi 14 hoàn toàn đáp ứng đầy đủ yêu cầu RBAC của Buổi 17 mà không cần sửa đổi dữ liệu hay viết lại retriever.

---

## 4. Kết luận

```text
RBAC REUSED: YES
FILTER BEFORE RETRIEVAL: PASS
UNKNOWN ROLE DEFAULT DENY: PASS
```
