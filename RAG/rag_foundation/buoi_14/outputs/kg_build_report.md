# BÁO CÁO XÂY DỰNG MINI KNOWLEDGE GRAPH — BUỔI 14
**Trạng thái CSDL**: Hoàn tất nạp dữ liệu vào Neo4j  
**Database**: `neo4j`  
**Phạm vi (lab_session)**: `"buoi_14"`  

---

## 1. Thống Kê Tổng Quan Nodes Theo Label

| Label | Số Lượng Node | Mô Tả Nghiệp Vụ |
|---|:---:|---|
| **`:DieuKhoan`** | **720** | Điều khoản / Khối nội dung phân cấp |
| **`:VanBan`** | **15** | Văn bản quy phạm pháp luật / chính sách |

---

## 2. Thống Kê Quan Hệ (Relationships) Theo Type

| Loại Quan Hệ (Type) | Số Lượng | Nguồn Dữ Liệu | Ý Nghĩa Nghiệp Vụ |
|---|:---:|---|---|
| **`[:CONTAINS]`** | **720** | `chunks_normalized.csv` | Cấu trúc phân cấp văn bản |
| **`[:NEXT]`** | **705** | `chunks_normalized.csv` | Thứ tự tuần tự giữa các điều khoản |
| **`[:CAN_CU]`** | **4** | `relationships.csv` | Văn bản căn cứ pháp lý |
| **`[:THAY_THE]`** | **1** | `relationships.csv` | Văn bản thay thế |
| **`[:SUA_DOI_BO_SUNG]`** | **1** | `relationships.csv` | Văn bản sửa đổi, bổ sung |
| **`[:HOP_NHAT]`** | **1** | `relationships.csv` | Văn bản hợp nhất |
| **`[:VAN_BAN_BO_SUNG]`** | **1** | `relationships.csv` | Văn bản bổ sung |

---

## 3. Kiểm Tra Node Mồ Côi (Orphan Nodes Analysis)

- **Tổng số Node mồ côi (không có bất kỳ liên kết nào)**: **0**
- **Đánh giá tính liên thông đồ thị**: **100% các Node (`:VanBan` và `:DieuKhoan`) đều được kết nối chặt chẽ** qua các cạnh `[:CONTAINS]` và `[:NEXT]`.

---

## 4. Các Truy Vấn Khám Phá Mẫu (Demo Cypher)
Xem chi tiết và thực thi tại file [demo_queries.cypher](file:///c:/Users/admins/Desktop/05_m%E1%BA%ABu/Rag_thuchanh/RAG/rag_foundation/buoi_14/cypher/demo_queries.cypher).
