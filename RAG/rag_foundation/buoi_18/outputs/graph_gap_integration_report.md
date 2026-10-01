# BÁO CÁO ĐÁNH GIÁ VÀ TÍCH HỢP KNOWLEDGE GRAPH CHO COMPLIANCE GAP CHECKER (BUỔI 17)

## 1. Mục tiêu Khảo sát

Khảo sát toàn bộ schema và danh sách quan hệ thực tế (Relationships & Nodes) trong cơ sở dữ liệu **Neo4j Knowledge Graph** để đánh giá tính khả thi của việc sử dụng Graph Candidate Expansion cho bài toán **Compliance Gap Analysis** (So sánh Yêu cầu Quản lý Nhà nước với Quy định Nội bộ).

---

## 2. Kết quả Thực tế Truy vấn từ Neo4j Knowledge Graph

* **Tổng số Nodes:** **968 nodes** (gồm 720 `DieuKhoan`, 15 `VanBan`, 94 `Document`, 85 `DoiTuongApDung`, 14 `NguoiKy`, 14 `LinhVuc`, 12 `RuiRo`, 10 `KiemSoat`, 12 `SuKienRuiRo`, 5 `CoQuan`).
* **Tổng số Cạnh (Edges / Relationships):** 1,675 relationships.

### Thống kê chi tiết các Relationship Types thực tế:

| Nhóm quan hệ | Relationship Type | Số lượng cạnh | Vai trò & Đánh giá mức độ hữu ích đối với Gap Matching |
| :--- | :--- | :---: | :--- |
| **Cấu trúc Nội bộ** | `CONTAINS` | 720 | **Cấu trúc thuần túy:** Nối `VanBan` chứa `DieuKhoan`. Không giúp nối sang văn bản khác. |
| **Cấu trúc Nội bộ** | `NEXT` | 705 | **Cấu trúc thuần túy:** Nối thứ tự tuần tự giữa các `DieuKhoan` trong cùng 1 văn bản. |
| **Liên kết Pháp lý** | `SUA_DOI_BO_SUNG` | 64 | **Nối văn bản bên ngoài:** Nối các Thông tư/Nghị định bên ngoài với nhau (e.g. TT 43/2024 sửa đổi TT 01/2014). Không nối sang quy định nội bộ. |
| **Liên kết Pháp lý** | `THAM_CHIEU` | 46 | **Nối văn bản bên ngoài:** Trích dẫn tham chiếu giữa các văn bản Nhà nước. |
| **Pháp lý khác** | `THAY_THE_BOI`, `CAN_CU`, `THAY_THE`, `HOP_NHAT` | 14 | **Nối văn bản bên ngoài:** Quan hệ thay thế/căn cứ giữa các văn bản Nhà nước. |
| **Thuộc tính & Metadata** | `AP_DUNG_CHO`, `THUOC_LINH_VUC`, `BAN_HANH_BOI`, `KY_BOI` | 234 | **Thuộc tính:** Phân loại cơ quan ban hành, người ký, lĩnh vực. Không trực tiếp khớp gap. |
| **Taxonomy Rủi ro/Kiểm soát** | `OBSERVED_AS`, `MITIGATES` | 22 | **Phân loại Rủi ro:** Nối điều khoản với loại rủi ro/kiểm soát (mô phỏng). |

---

## 3. Đánh giá Tính giá trị đối với Compliance Gap Matching

1. **Thiếu cạnh kết nối 2 tầng (Cross-layer edges):**
   * Do dữ liệu hiện tại chứa 100% văn bản Quản lý Nhà nước (`EXTERNAL_REQUIREMENT`) và chưa có node Quy định Nội bộ (`INTERNAL_POLICY`), trong Graph **không tồn tại bất kỳ cạnh nào nối giữa Yêu cầu NHNN và Quy định Nội bộ Ngân hàng**.
   * Tuân thủ quy tắc: **Tuyệt đối không tự ý tạo cạnh (edge) giả hoặc gán liên kết thủ công**.

2. **Hạn chế của quan hệ cấu trúc (`CONTAINS`, `NEXT`):**
   * Các quan hệ `CONTAINS` và `NEXT` chỉ có tác dụng duyệt chuyển qua lại giữa các điều khoản kế tiếp trong cùng một văn bản (Structural Expansion), không tạo ra giá trị tìm kiếm điều khoản đối ứng giữa 2 tổ chức.

3. **Quyết định Tích hợp (Integration Decision):**
   * Không sử dụng Graph Expansion làm phương pháp mở rộng ứng viên chính cho Gap Matching nhằm tránh nhiễu thông tin.
   * Giữ nguyên phương pháp **Hybrid Search (BM25 + Dense Embeddings) + Cross-Encoder Reranker** để tìm kiếm ứng viên liên quan.
   * Ghi nhận chính thức: `GRAPH NOT USED FOR GAP MATCHING`.

---

## 4. Kết luận Trạng thái (Final Status)

```text
GRAPH USED: NO
GRAPH NOT USED FOR GAP MATCHING: PASS
REASON: Graph currently lacks cross-layer edges connecting External Requirements to Internal Policies (0 internal policy nodes present). Existing edges are strictly structural (CONTAINS, NEXT) or external-to-external legal amendments.
```
