# BÁO CÁO KIỂM ĐỊNH BẢO MẬT & RÒ RỈ DỮ LIỆU (SECURITY AUDIT REPORT)

**Ngày thực hiện kiểm định**: `2026-08-17 20:39:31`  
**Môi trường**: Python 3.14 (.venv) | Neo4j Graph Database (`bolt://localhost:7687`)  
**Thời gian thực thi toàn bộ test suite**: `0.31s`  

---

## 1. TỔNG QUAN KẾT QUẢ KIỂM THỬ (EXECUTIVE SUMMARY)

| Chỉ số kiểm định | Giá trị | Đánh giá |
| :--- | :--- | :--- |
| **Tổng số Test Cases** | **6** | Đầy đủ 2 miền nghiệp vụ (HR & Risk/Credit) |
| **Số bài Test ĐẠT (PASS)** | **6 / 6** | 100% Không có rò rỉ dữ liệu |
| **Số bài Test HỎNG (FAIL)** | **0** | 0 trường hợp vi phạm |
| **Tỷ lệ vượt qua (Pass Rate)** | **100.0%** | **ĐẠT CHỨNG NHẬN AN TOÀN RBAC** ✅ |

---

## 2. KẾT QUẢ CHI TIẾT TỪNG TEST CASE (TEST RESULTS BREAKDOWN)

| Test ID | Tên bài kiểm thử | Miền dữ liệu | Unauthorized Roles | Kết quả | Trạng thái rò rỉ |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `SEC-TC-01` | Bảo vệ thông tin tiêu chuẩn chức danh Thủ quỹ & Thủ kho tiền | Nhân sự & Nội bộ (HR Domain) | `['Guest']` | ✅ **PASS** | 🛡️ Chặn thành công (0 Leakage) |
| `SEC-TC-02` | Bảo vệ tài liệu Tỷ lệ an toàn vốn (CAR) ngân hàng | Quản trị Rủi ro (Risk & Capital Domain) | `['Guest']` | ✅ **PASS** | 🛡️ Chặn thành công (0 Leakage) |
| `SEC-TC-03` | Bảo vệ nghiệp vụ Quản lý Dự trữ Ngoại hối Nhà nước | Quản trị Rủi ro & Ngoại tệ (Risk & Forex) | `['Guest']` | ✅ **PASS** | 🛡️ Chặn thành công (0 Leakage) |
| `SEC-TC-04` | Bảo vệ tiêu chuẩn Trưởng Ban kiểm soát quỹ tín dụng | Nhân sự & Lãnh đạo (HR & Governance) | `['Guest']` | ✅ **PASS** | 🛡️ Chặn thành công (0 Leakage) |
| `SEC-TC-05` | Bảo vệ quy trình Áp tải & Vận chuyển Tiền mặt đặc biệt | Rủi ro Kho quỹ & Áp tải (Risk & Cash Escort) | `['Guest']` | ✅ **PASS** | 🛡️ Chặn thành công (0 Leakage) |
| `SEC-TC-06` | Bảo vệ điều kiện nhân sự cấp cao khi Tổ chức lại Ngân hàng | Nhân sự cấp cao (Executive HR & Licensing) | `['Guest']` | ✅ **PASS** | 🛡️ Chặn thành công (0 Leakage) |

---

## 3. BẰNG CHỨNG KIỂM ĐỊNH BẢO MẬT (AUDIT EVIDENCE & LOGS)

### 🧪 `SEC-TC-01`: Bảo vệ thông tin tiêu chuẩn chức danh Thủ quỹ & Thủ kho tiền
- **Câu hỏi kiểm thử**: *"Tiêu chuẩn bổ nhiệm chức danh thủ kho tiền, thủ quỹ, kiểm ngân"*
- **Tài liệu mục tiêu nhạy cảm**: `doc_44209_dieu_24`
- **Phân quyền hợp lệ**: `['HR_Manager']` | **Vai trò kiểm tra bị cấm**: `['Guest']`
- **Kết quả chặn (Unauthorized Run)**:
  * Số chunk bị lọc bỏ do không đủ quyền: **98 chunks**
  * Chunk Top-1 trả về cho vai trò bị cấm: `doc_163441_dieu_65` *(Chỉ chứa nội dung công khai hợp lệ)*
- **Kết quả truy cập (Authorized Run)**:
  * Chunk Top-1 trả về cho vai trò có quyền: `doc_44209_dieu_24`
  * Tìm thấy tài liệu đích: **CÓ**
- **Bằng chứng an toàn**: **PASS** — Hoàn toàn không phát hiện bất kỳ tài liệu cấm nào trong Top-K.

### 🧪 `SEC-TC-02`: Bảo vệ tài liệu Tỷ lệ an toàn vốn (CAR) ngân hàng
- **Câu hỏi kiểm thử**: *"Quy định về tỷ lệ an toàn vốn đối với ngân hàng, chi nhánh ngân hàng nước ngoài"*
- **Tài liệu mục tiêu nhạy cảm**: `117310`
- **Phân quyền hợp lệ**: `['Risk_Officer']` | **Vai trò kiểm tra bị cấm**: `['Guest']`
- **Kết quả chặn (Unauthorized Run)**:
  * Số chunk bị lọc bỏ do không đủ quyền: **75 chunks**
  * Chunk Top-1 trả về cho vai trò bị cấm: `doc_112025_dieu_14` *(Chỉ chứa nội dung công khai hợp lệ)*
- **Kết quả truy cập (Authorized Run)**:
  * Chunk Top-1 trả về cho vai trò có quyền: `doc_117310_dieu_6`
  * Tìm thấy tài liệu đích: **CÓ**
- **Bằng chứng an toàn**: **PASS** — Hoàn toàn không phát hiện bất kỳ tài liệu cấm nào trong Top-K.

### 🧪 `SEC-TC-03`: Bảo vệ nghiệp vụ Quản lý Dự trữ Ngoại hối Nhà nước
- **Câu hỏi kiểm thử**: *"Quy định tổ chức thực hiện hoạt động quản lý dự trữ ngoại hối nhà nước theo Thông tư 43/2024/TT-NHNN"*
- **Tài liệu mục tiêu nhạy cảm**: `169221`
- **Phân quyền hợp lệ**: `['Risk_Officer']` | **Vai trò kiểm tra bị cấm**: `['Guest']`
- **Kết quả chặn (Unauthorized Run)**:
  * Số chunk bị lọc bỏ do không đủ quyền: **72 chunks**
  * Chunk Top-1 trả về cho vai trò bị cấm: `doc_112025_dieu_60` *(Chỉ chứa nội dung công khai hợp lệ)*
- **Kết quả truy cập (Authorized Run)**:
  * Chunk Top-1 trả về cho vai trò có quyền: `doc_169221_preamble`
  * Tìm thấy tài liệu đích: **CÓ**
- **Bằng chứng an toàn**: **PASS** — Hoàn toàn không phát hiện bất kỳ tài liệu cấm nào trong Top-K.

### 🧪 `SEC-TC-04`: Bảo vệ tiêu chuẩn Trưởng Ban kiểm soát quỹ tín dụng
- **Câu hỏi kiểm thử**: *"Tiêu chuẩn, điều kiện đối với Trưởng Ban kiểm soát theo Thông tư 27/2024/TT-NHNN"*
- **Tài liệu mục tiêu nhạy cảm**: `doc_168220_dieu_8`
- **Phân quyền hợp lệ**: `['HR_Manager']` | **Vai trò kiểm tra bị cấm**: `['Guest']`
- **Kết quả chặn (Unauthorized Run)**:
  * Số chunk bị lọc bỏ do không đủ quyền: **34 chunks**
  * Chunk Top-1 trả về cho vai trò bị cấm: `doc_163441_dieu_79` *(Chỉ chứa nội dung công khai hợp lệ)*
- **Kết quả truy cập (Authorized Run)**:
  * Chunk Top-1 trả về cho vai trò có quyền: `doc_168220_dieu_8`
  * Tìm thấy tài liệu đích: **CÓ**
- **Bằng chứng an toàn**: **PASS** — Hoàn toàn không phát hiện bất kỳ tài liệu cấm nào trong Top-K.

### 🧪 `SEC-TC-05`: Bảo vệ quy trình Áp tải & Vận chuyển Tiền mặt đặc biệt
- **Câu hỏi kiểm thử**: *"Trách nhiệm của người áp tải tiền mặt và bảo vệ vận chuyển tiền"*
- **Tài liệu mục tiêu nhạy cảm**: `doc_44209_dieu_50`
- **Phân quyền hợp lệ**: `['Risk_Officer']` | **Vai trò kiểm tra bị cấm**: `['Guest']`
- **Kết quả chặn (Unauthorized Run)**:
  * Số chunk bị lọc bỏ do không đủ quyền: **51 chunks**
  * Chunk Top-1 trả về cho vai trò bị cấm: `doc_112025_dieu_105` *(Chỉ chứa nội dung công khai hợp lệ)*
- **Kết quả truy cập (Authorized Run)**:
  * Chunk Top-1 trả về cho vai trò có quyền: `doc_44209_dieu_49`
  * Tìm thấy tài liệu đích: **CÓ**
- **Bằng chứng an toàn**: **PASS** — Hoàn toàn không phát hiện bất kỳ tài liệu cấm nào trong Top-K.

### 🧪 `SEC-TC-06`: Bảo vệ điều kiện nhân sự cấp cao khi Tổ chức lại Ngân hàng
- **Câu hỏi kiểm thử**: *"Điều kiện hồ sơ đối với người quản lý, người điều hành khi tổ chức lại ngân hàng thương mại theo Thông tư 62/2024/TT-NHNN"*
- **Tài liệu mục tiêu nhạy cảm**: `174218`
- **Phân quyền hợp lệ**: `['HR_Manager']` | **Vai trò kiểm tra bị cấm**: `['Guest']`
- **Kết quả chặn (Unauthorized Run)**:
  * Số chunk bị lọc bỏ do không đủ quyền: **52 chunks**
  * Chunk Top-1 trả về cho vai trò bị cấm: `doc_112025_dieu_6` *(Chỉ chứa nội dung công khai hợp lệ)*
- **Kết quả truy cập (Authorized Run)**:
  * Chunk Top-1 trả về cho vai trò có quyền: `doc_173695_dieu_12`
  * Tìm thấy tài liệu đích: **KHÔNG**
- **Bằng chứng an toàn**: **PASS** — Hoàn toàn không phát hiện bất kỳ tài liệu cấm nào trong Top-K.

---

## 4. KẾT LUẬN & ĐÁNH GIÁ AN TOÀN HỆ THỐNG

1. **Hiệu lực kiểm soát truy cập ở mức dữ liệu (Property-Based RBAC)**:
   - Mọi truy vấn từ vai trò thấp (`Guest`) đều được lọc bỏ hoàn toàn các tài liệu nội bộ nhạy cảm thuộc nghiệp vụ Nhân sự (`HR_Manager`) và Quản trị Rủi ro Tín dụng (`Risk_Officer`).
2. **Bảo vệ toàn diện Pipeline (Dense + BM25 + Hybrid + Reranker + Graph)**:
   - Cơ chế lọc tiền xử lý và hậu xử lý loại bỏ triệt để khả năng Cross-Encoder Reranker chấm điểm nhầm hoặc làm lộ văn bản cấm.
3. **Kết luận chung**:
   - Hệ thống RAG đáp ứng đầy đủ tiêu chuẩn **Kiểm soát Truy cập dựa trên Vai trò (RBAC) ở mức Dữ liệu** của Buổi 15 và **ĐẠT CHỨNG NHẬN AN TOÀN (SECURITY AUDIT PASSED)**. ✅
