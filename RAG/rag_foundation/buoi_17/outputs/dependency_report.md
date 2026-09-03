# BÁO CÁO ĐÁNH GIÁ DỮ LIỆU NGUỒN VÀ SECURE RETRIEVER (BUỔI 14 -> BUỔI 17)

## 1. Tổng quan Dữ liệu Nguồn Buổi 14

* **File dữ liệu đầu vào chính:** `../buoi_14/data/processed/chunks_secure.csv`
* **File dữ liệu đối chiếu:** `../buoi_14/data/processed/chunks_normalized.csv`

### 1.1. Thống kê chi tiết Dữ liệu

| Tiêu chí | `chunks_secure.csv` | `chunks_normalized.csv` | Khớp / Khác biệt |
| :--- | :--- | :--- | :--- |
| **Số lượng dòng (Chunks)** | 720 | 720 | Khớp 100% (720 dòng) |
| **Số lượng cột** | 14 | 13 | Khác biệt 1 cột (`allowed_roles`) |
| **Nội dung 13 cột chung** | Trùng khớp 100% | Trùng khớp 100% | Nội dung dữ liệu hoàn toàn giống nhau |

### 1.2. Danh sách Cột và Kiểm tra Trường Dữ liệu

* **Danh sách cột trong `chunks_secure.csv` (14 cột):**
  1. `chunk_id` (Ví dụ: `doc_44209_dieu_1`)
  2. `document_id` (Ví dụ: `44209`)
  3. `title` (Tên quy định / văn bản)
  4. `so_ky_hieu` (Số ký hiệu văn bản, e.g. `01/2014/TT-NHNN`)
  5. `document_type` (Tương ứng loại văn bản, e.g. `Thông tư`, `Quyết định`)
  6. `chapter` (Chương)
  7. `section` (Mục)
  8. `article` (Điều)
  9. `clause` (Khoản)
  10. `text` (Nội dung chi tiết chunk)
  11. `source_file` (File nguồn)
  12. `effective_date` (Tương ứng ngày ban hành / hiệu lực, e.g. `20/02/2014`)
  13. `status` (Trạng thái hiệu lực)
  14. `allowed_roles` (Danh sách vai trò được xem dưới dạng JSON string, e.g. `["Admin", "Risk_Officer", "Employee"]`)

* **Ghi chú về các trường bổ sung:**
  * **`citation`**: Không phải cột tĩnh lưu trong CSV mà được tự động tính và format bởi hàm `format_citation(row)` trong `src/citation.py` khi trả về kết quả retrieval.
  * **`co_quan_ban_hanh`**: Không tách thành cột riêng trong schema CSV; thông tin cơ quan ban hành nằm trong `title`, `so_ky_hieu` hoặc nội dung `text`.

### 1.3. Xác nhận So sánh Dữ liệu
$$\text{chunks\_secure.csv} = \text{chunks\_normalized.csv} + \text{allowed\_roles}$$
Không có bất kỳ sự khác biệt nào về dữ liệu văn bản, chunking hay ID giữa hai file.

---

## 2. Phân tích Code `SecureRetriever` (Buổi 14)

* **Vị trí File / Module:** `buoi_14/src/secure_retriever.py`
* **Class chính:** `SecureRetriever`
* **Hàm Unified API chính:** `secure_retrieve(query, user_roles, method='hybrid_rerank', top_k=5, candidate_k=20, include_graph_hints=True)`

### 2.1. Tham số và Cấu trúc Input/Output

* **Input Roles:** `user_roles: List[str]` (ví dụ: `["Guest"]`, `["HR_Manager"]`, `["Risk_Officer"]`, `["Admin"]`). Được kiểm tra & chuẩn hóa qua `validate_roles(user_roles)`.
* **Output structure:**
  ```python
  {
      "query": str,
      "user_roles": List[str],
      "method": str,
      "top_k": int,
      "results_count": int,
      "filtered_out_count": int,
      "elapsed_ms": float,
      "results": List[Dict[str, Any]],  # Chứa chunk_id, document_id, text, score, citation, allowed_roles, matched_roles
      "graph_hints": Optional[Dict[str, Any]]
  }
  ```

### 2.2. Cơ chế Lọc Quyền (RBAC Filtering Timing)

* **Filter Timing:** Lọc quyền được thực hiện **TRƯỚC** khi đưa ngữ cảnh vào Reranking/Context cho LLM.
  1. **BM25 & Dense Search:** Sử dụng *Early Filtering / Pre-filtering* thông qua hàm `check_access_permission`. Các chunk không có quyền xem bị bỏ qua ngay trong vòng lặp thu thập candidate.
  2. **Hybrid Fusion & Reranking:** Chỉ tính RRF score và chỉ truyền ứng viên hợp lệ (đã lọc quyền) sang Cross-Encoder Reranker (`BAAI/bge-reranker-base`).
  3. **Knowledge Graph Hints:** Sử dụng mệnh đề Cypher trực tiếp `WHERE any(role IN node.allowed_roles WHERE role IN $user_roles)`.

### 2.3. Bảo toàn Metadata (`chunk_id`, `document_id`, `citation`)

* **CÓ.** Mọi kết quả trả về trong danh sách `results` đều giữ nguyên vẹn:
  * `chunk_id`: Định danh duy nhất của chunk
  * `document_id`: Mã văn bản nguồn
  * `citation`: Chuỗi trích dẫn đầy đủ được định dạng chuẩn mực
  * `allowed_roles` & `matched_roles`: Kiểm toán vai trò khớp

---

## 3. Kết luận và Kế hoạch Tái sử dụng (Reuse Plan)

```text
SOURCE DATA: PASS
RBAC DATA AVAILABLE: YES
SECURE RETRIEVER REUSABLE: YES
REUSE PLAN:
1. Thêm đường dẫn `buoi_14` vào `sys.path` tại các script thực thi của `buoi_17`.
2. Import trực tiếp hàm `secure_retrieve` từ module `src.secure_retriever`.
3. Sử dụng `chunks_secure.csv` làm nguồn dữ liệu corpus chính thông qua biến môi trường `SOURCE_SECURE_CSV`.
4. Truyền vai trò người dùng (`user_roles`) từ hệ thống RBAC của Buổi 17 vào `secure_retrieve` để truy xuất context đã bảo mật trước khi tổng hợp câu trả lời và ghi Audit Trail.
```
