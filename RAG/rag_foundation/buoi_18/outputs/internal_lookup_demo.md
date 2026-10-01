# BÁO CÁO MÔ PHỎNG USE CASE 1: AI TRA CỨU QUY ĐỊNH NỘI BỘ (BUỔI 17)

## 1. Kiến trúc Giải pháp Use Case 1

System [`buoi_17/scripts/internal_lookup.py`](file:///c:/Users/admins/Desktop/05_m%E1%BA%ABu/Rag_thuchanh/RAG/rag_foundation/buoi_17/scripts/internal_lookup.py) tích hợp quy trình khép kín:
```text
User Question + User Role
→ RBAC Pre-filtering (SecureRetriever Adapter)
→ Context Sạch (Chỉ chứa Chunks được phép xem)
→ Gemini LLM Prompting (Strict Context Only + Mandatory Citations)
→ Response + Citations + Request ID
→ Automatic Audit Trail Logging (audit_log.jsonl)
```

---

## 2. Kết quả Thử nghiệm Thực tế (3 Kịch bản Câu hỏi)

### 🔴 Kịch bản 1: Cán bộ Nhân sự tra cứu Quy định Nhân sự (ALLOWED)
* **Request ID:** `req-93bd11bb`
* **Người dùng demo:** `usr_hr_manager_01`
* **Quyền xem (Access Scope):** `['HR_Manager']`
* **Câu hỏi:** *"Tiêu chuẩn bổ nhiệm chức danh thủ kho tiền, thủ quỹ và kiểm ngân trong ngành Ngân hàng được quy định thế nào?"*
* **Tài liệu/Chunk trích xuất (sau RBAC):**
  * Document IDs: `['163441', '44209']`
  * Chunk IDs: `['doc_44209_dieu_24', 'doc_44209_dieu_39', 'doc_163441_dieu_1_3']`
* **Danh sách Trích dẫn (Citations):**
  ```text
  [
  "[01/2014/TT-NHNN | Điều 24 | doc_44209_dieu_24]",
  "[01/2014/TT-NHNN | Điều 39 | doc_44209_dieu_39]",
  "[46/2023/NĐ-CP | Điều 1 | doc_163441_dieu_1_3]"
]
  ```
* **Câu trả lời từ AI (LLM Answer):**
  > Tiêu chuẩn bổ nhiệm chức danh thủ kho tiền, thủ quỹ và kiểm ngân trong ngành Ngân hàng được quy định như sau:

1.  **Đối với Sở Giao dịch, Ngân hàng Nhà nước chi nhánh, kho tiền Trung ương**: Thủ kho tiền, thủ quỹ, kiểm ngân phải đủ tiêu chuẩn chức danh theo quy định của Nhà nước và được quản lý theo Quy chế cán bộ, công chức, viên chức Ngân hàng Nhà nước. Thủ kho tiền Trung ương do Thống đốc Ngân hàng Nhà nước quyết định. Thủ kho tiền Sở Giao dịch, Ngân hàng Nhà nước chi nhánh do Giám đốc quyết định [01/2014/TT-NHNN | Điều 24 | doc_44209_dieu_24].
2.  **Đối với tổ chức tín dụng, chi nhánh ngân hàng nước ngoài**: Căn cứ tiêu chuẩn chức danh thủ kho tiền, thủ quỹ, kiểm ngân của Ngân hàng Nhà nước và các quy định khác của pháp luật để quy định tiêu chuẩn chức danh thủ kho tiền, thủ quỹ, kiểm ngân trong hệ thống của mình [01/2014/TT-NHNN | Điều 24 | doc_44209_dieu_24].

---

### 🟡 Kịch bản 2: Khách vãng lai tra cứu Văn bản Nhân sự Nhạy cảm (DENIED / INSUFFICIENT SCOPE)
* **Request ID:** `req-052e42d5`
* **Người dùng demo:** `usr_guest_99`
* **Quyền xem (Access Scope):** `['Guest']`
* **Câu hỏi:** *"Tiêu chuẩn chức danh thủ kho tiền, thủ quỹ và các quy định bổ nhiệm nhân sự nhạy cảm"*
* **Số Chunks bị lọc bỏ bởi RBAC:** `179` chunks
* **Tài liệu nhạy cảm HR `doc_44209_dieu_24`:** **KHÔNG xuất hiện trong Context** (RBAC đã chặn).
* **Câu trả lời từ AI (LLM Answer):**
  > **Không tìm thấy đủ thông tin trong phạm vi tài liệu được phép truy cập.**
* **Đánh giá bảo mật:** LLM phản hồi đúng thông điệp mẫu khi không đủ thông tin trong phạm vi quyền, tuyệt đối không bịa đặt hay rò rỉ kiến thức bên ngoài.

---

### 🟢 Kịch bản 3: Nhân viên tra cứu Quy định Nghiệp vụ Giao nhận Tiền mặt (STANDARD ALLOWED)
* **Request ID:** `req-5b239ec1`
* **Người dùng demo:** `usr_employee_05`
* **Quyền xem (Access Scope):** `['Employee']`
* **Câu hỏi:** *"Quy định việc giao nhận, bảo quản, vận chuyển tiền mặt và tài sản quý trong ngành Ngân hàng"*
* **Tài liệu/Chunk trích xuất (sau RBAC):**
  * Document IDs: `['44209']`
  * Chunk IDs: `['doc_44209_dieu_1', 'doc_44209_preamble', 'doc_44209_dieu_50']`
* **Danh sách Trích dẫn (Citations):**
  ```text
  [
  "[01/2014/TT-NHNN | Điều 1 | doc_44209_dieu_1]",
  "[01/2014/TT-NHNN | Căn cứ ban hành | doc_44209_preamble]",
  "[01/2014/TT-NHNN | Điều 50 | doc_44209_dieu_50]"
]
  ```
* **Câu trả lời từ AI (LLM Answer):**
  > Thông tư 01/2014/TT-NHNN quy định việc giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá trong ngành Ngân hàng [01/2014/TT-NHNN | Điều 1 | doc_44209_dieu_1].

Cụ thể về phương tiện vận chuyển:
*   Vận chuyển tiền mặt, tài sản quý, giấy tờ có giá phải sử dụng xe chuyên dùng và các phương tiện kỹ thuật cần thiết [01/2014/TT-NHNN | Điều 50 | doc_44209_dieu_50].
*   Trong hệ thống Ngân hàng Nhà nước, việc vận chuyển tiền mặt, tài sản quý, giấy tờ có giá phải có xe hộ tống. Trường hợp cần thuê phương tiện khác như máy bay, tàu hỏa, tàu biển để vận chuyển, Thống đốc Ngân hàng Nhà nước sẽ quyết định [01/2014/TT-NHNN | Điều 50 | doc_44209_dieu_50].
*   Đối với tổ chức tín dụng, chi nhánh ngân hàng nước ngoài sử dụng phương tiện khác để vận chuyển tiền mặt, tài sản quý, giấy tờ có giá, phải quy định bằng văn bản và hướng dẫn quy trình vận chuyển, bảo vệ, các biện pháp đảm bảo an toàn tài sản [01/2014/TT-NHNN | Điều 50 | doc_44209_dieu_50].
*   Sở Giao dịch, Ngân hàng Nhà nước chi nhánh có nhu cầu giao, nhận trực tiếp tiền mặt, tài sản quý, giấy tờ có giá của Ngân hàng Nhà nước tại kho tiền Trung ương và có khả năng tự bố trí xe chuyên dùng, phải được sự chấp thuận của Cục trưởng Cục Phát hành và Kho quỹ [01/2014/TT-NHNN | Điều 50 | doc_44209_dieu_50].

---

## 3. Tổng hợp Bảng Kết quả Đánh giá

| Tiêu chí | Kịch bản 1 (HR) | Kịch bản 2 (Guest) | Kịch bản 3 (Employee) | Đánh giá chung |
| :--- | :---: | :---: | :---: | :---: |
| **RBAC Pre-filtering** | PASS | PASS (Chặn 100% chunk cấm) | PASS | **PASS** |
| **Bảo tồn Citation & Metadata** | PASS (Đầy đủ 3 citations) | N/A (Không có quyền) | PASS (Đầy đủ 3 citations) | **PASS** |
| **Nhật ký Audit Trail (JSONL)** | Logged (`req_id: req-93bd11bb`) | Logged (`req_id: req-052e42d5`) | Logged (`req_id: req-5b239ec1`) | **PASS** |
| **Ràng buộc LLM Strict Context** | PASS | PASS ("Không tìm thấy đủ thông tin trong phạm vi tài liệu được phép truy cập.") | PASS | **PASS** |

---

## 4. Kết luận Trạng thái (Final Status)

```text
CITATION: PASS
RBAC: PASS
AUDIT: PASS
```
