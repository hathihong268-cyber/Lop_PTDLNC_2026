# BÁO CÁO PHÂN LOẠI VĂN BẢN VÀ KIỂM TRA DỮ LIỆU ĐẦU VÀO CHO COMPLIANCE GAP CHECKER (BUỔI 17)

## 1. Mục tiêu và Phạm vi Khảo sát

Khảo sát và kiểm tra toàn bộ 15 văn bản hiện có trong file dữ liệu gốc [`../buoi_14/data/processed/chunks_secure.csv`](file:///c:/Users/admins/Desktop/05_m%E1%BA%ABu/Rag_thuchanh/RAG/rag_foundation/buoi_14/data/processed/chunks_secure.csv) (Tổng 720 chunks) để đánh giá khả năng thực hiện **Compliance Gap Analysis** (So sánh Quy định Nội bộ ngân hàng với Yêu cầu Quản lý Nhà nước / Thông tư NHNN).

---

## 2. Danh mục Phân loại Chi tiết 15 Văn bản (Document Catalog)

| STT | Document ID | Số ký hiệu | Loại văn bản | Cơ quan ban hành | Tên văn bản (Title) | Phân loại (Classification) | Bằng chứng thực tế (Evidence) |
| :---: | :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| 1 | `112025` | 73/2016/NĐ-CP | Nghị định | Chính phủ | Nghị định số 73/2016/NĐ-CP Quy định chi tiết thi hành Luật kinh doanh bảo hiểm... | **EXTERNAL_REQUIREMENT** | Nghị định do Chính phủ ban hành (QPPL bên ngoài). |
| 2 | `112924` | 105/2016/TT-BTC | Thông tư | Bộ Tài chính | Thông tư số 105/2016/TT-BTC Hướng dẫn hoạt động đầu tư gián tiếp ra nước ngoài... | **EXTERNAL_REQUIREMENT** | Thông tư do Bộ Tài chính ban hành (QPPL bên ngoài). |
| 3 | `117310` | 41/2016/TT-NHNN | Thông tư | Ngân hàng Nhà nước | Thông tư số 41/2016/TT-NHNN Quy định tỷ lệ an toàn vốn đối với ngân hàng... | **EXTERNAL_REQUIREMENT** | Thông tư do NHNN ban hành (QPPL quản lý nhà nước). |
| 4 | `163441` | 46/2023/NĐ-CP | Nghị định | Chính phủ | Nghị định số 46/2023/NĐ-CP Quy định chi tiết thi hành một số điều của Luật KDBH | **EXTERNAL_REQUIREMENT** | Nghị định do Chính phủ ban hành (QPPL bên ngoài). |
| 5 | `166269` | 17/2023/QH15 | Luật | Quốc hội | Luật Hợp tác xã số 17/2023/QH15 | **EXTERNAL_REQUIREMENT** | Luật do Quốc hội ban hành (QPPL bên ngoài). |
| 6 | `168220` | 27/2024/TT-NHNN | Thông tư | Ngân hàng Nhà nước | Thông tư số 27/2024/TT-NHNN Quy định về việc ngân hàng hợp tác xã... | **EXTERNAL_REQUIREMENT** | Thông tư do NHNN ban hành (QPPL quản lý nhà nước). |
| 7 | `169221` | 43/2024/TT-NHNN | Thông tư | Ngân hàng Nhà nước | Thông tư số 43/2024/TT-NHNN sửa đổi, bổ sung một số điều của Thông tư 01/2014/TT-NHNN | **EXTERNAL_REQUIREMENT** | Thông tư do NHNN ban hành (QPPL quản lý nhà nước). |
| 8 | `173695` | 56/2024/TT-NHNN | Thông tư | Ngân hàng Nhà nước | Thông tư số 56/2024/TT-NHNN Quy định hồ sơ, thủ tục cấp Giấy phép lần đầu... | **EXTERNAL_REQUIREMENT** | Thông tư do NHNN ban hành (QPPL quản lý nhà nước). |
| 9 | `174218` | 62/2024/TT-NHNN | Thông tư | Ngân hàng Nhà nước | Thông tư số 62/2024/TT-NHNN Quy định điều kiện, hồ sơ, thủ tục chấp thuận... | **EXTERNAL_REQUIREMENT** | Thông tư do NHNN ban hành (QPPL quản lý nhà nước). |
| 10 | `177271` | 01/2025/TT-NHNN | Thông tư | Ngân hàng Nhà nước | Thông tư số 01/2025/TT-NHNN Quy định về cấp Giấy phép lần đầu, cấp đổi Giấy phép... | **EXTERNAL_REQUIREMENT** | Thông tư do NHNN ban hành (QPPL quản lý nhà nước). |
| 11 | `185630` | 63/2025/TT-NHNN | Thông tư | Ngân hàng Nhà nước | Thông tư số 63/2025/TT-NHNN Sửa đổi, bổ sung một số điều của một số Thông tư... | **EXTERNAL_REQUIREMENT** | Thông tư do NHNN ban hành (QPPL quản lý nhà nước). |
| 12 | `25692` | 46/2010/QH12 | Luật | Quốc hội | Luật Ngân hàng Nhà nước Việt Nam | **EXTERNAL_REQUIREMENT** | Luật do Quốc hội ban hành (QPPL bên ngoài). |
| 13 | `44209` | 01/2014/TT-NHNN | Thông tư | Ngân hàng Nhà nước | Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt... | **EXTERNAL_REQUIREMENT** | Thông tư do NHNN ban hành (QPPL quản lý nhà nước). |
| 14 | `6e689cd0-6f81-11f1-94d6-fd5d6d5ff793` | 52/VBHN-NHNN | Văn bản hợp nhất | Ngân hàng Nhà nước | Quy định hồ sơ, thủ tục cấp Giấy phép lần đầu của ngân hàng thương mại... | **EXTERNAL_REQUIREMENT** | Văn bản hợp nhất do NHNN ban hành (QPPL bên ngoài). |
| 15 | `95652` | 135/2015/NĐ-CP | Nghị định | Chính phủ | Nghị định số 135/2015/NĐ-CP Quy định về đầu tư gián tiếp ra nước ngoài | **EXTERNAL_REQUIREMENT** | Nghị định do Chính phủ ban hành (QPPL bên ngoài). |

---

## 3. Tổng hợp và Đánh giá Tính đầy đủ của Dữ liệu

* **Tổng số văn bản (Total Documents):** **15 văn bản**
* **Văn bản Yêu cầu Bên ngoài (EXTERNAL_REQUIREMENT):** **15 văn bản** (100%)
* **Văn bản Quy định Nội bộ (INTERNAL_POLICY):** **0 văn bản** (0%)

> ⚠️ **ĐÁNH GIÁ NGUYÊN TẮC THỰC TẾ (REAL EVIDENCE PRINCIPLE):**
> * Toàn bộ 15 văn bản trong tập dữ liệu hiện tại đều là **Văn bản Quy phạm Pháp luật Quản lý Nhà nước** do Quốc hội, Chính phủ, Bộ Tài chính hoặc Ngân hàng Nhà nước Việt Nam ban hành.
> * Trong tập dữ liệu **KHÔNG TỒN TẠI** bất kỳ văn bản quy định nội bộ nào của Ngân hàng (như Quy chế nội bộ Agribank, Quyết định HĐTV).
> * Tuân thủ nghiêm ngặt nguyên tắc: **Tuyệt đối không tự ý gắn nhãn hoặc ép một Thông tư/Nghị định thành "quy định nội bộ" chỉ để chạy demo giả tạo**.
> * Do thiếu dữ liệu đối chiếu 2 phía (Internal vs External), hệ thống **không thể thực hiện bài toán Compliance Gap Analysis một cách hợp lệ trên tập dữ liệu này**.

---

## 4. Kết luận Trạng thái (Final Status)

```text
COMPLIANCE GAP DATA: INSUFFICIENT
DATA GAP: INTERNAL POLICY NOT FOUND
```
