Dưới đây là toàn bộ nội dung đã được chuẩn hóa và định dạng lại chuẩn **Markdown**:

---

# Buổi 18 - Vibe Coding: AI Compliance Checker & AI Audit Checklist Generator

## 1. Mục tiêu
- **Hoàn thiện hệ thống AI Compliance & Audit** với 2 luồng cốt lõi:
  - **UC3 - AI Compliance Checker**: So sánh chéo các văn bản nội bộ Agribank & văn bản pháp luật / đối chiếu quy định (domain, scope), phát hiện xung đột/mâu thuẫn, gán mức độ rủi ro (Severity: `HIGH`, `MEDIUM`, `LOW`) & gán trạng thái `NEEDS_HUMAN_REVIEW`.
  - **UC4 - AI Audit Checklist Generator**: Tự động sinh danh mục Checklist kiểm toán bám sát Domain & Unit, trích dẫn rõ điều/khoản/văn bản gốc kèm đường link/citation trực tiếp.
- **Tích hợp RBAC & Audit Trail**: Phân quyền người dùng chi tiết, ghi nhật ký kiểm toán không thể chỉnh sửa và không lộ API key / secret.
- **Tối ưu hóa giao diện**: Tích hợp toàn diện trên ứng dụng Streamlit (`app.py`).

---

## 2. Các Use Case chính

### UC3 - AI Compliance Checker (Kiểm tra tuân thủ & So sánh chéo)
- Lấy tập văn bản nội bộ Agribank làm cơ sở đối chiếu.
- Truy xuất các cặp văn bản liên quan (Hybrid Search kết hợp Metadata Filtering theo Domain / Nghiệp vụ).
- So sánh chéo (Cross-Comparison) bằng LLM:
  - Chỉ ra điểm mâu thuẫn, xung đột giữa 2 văn bản.
  - Phân loại xung đột: Hạn mức/ngưỡng, quy trình thực hiện, thẩm quyền phê duyệt, thời hạn / hiệu lực, khác.
  - Đánh giá mức độ rủi ro: `HIGH`, `MEDIUM`, `LOW`.
  - `review_status`: Mặc định `NEEDS_HUMAN_REVIEW` nếu có phát hiện xung đột.
- Xuất báo cáo dạng Markdown & CSV (`outputs/compliance_conflicts.csv`, `outputs/compliance_conflict_report.md`).

### UC4 - AI Audit Checklist Generator (Tạo Checklist kiểm toán)
- Nhận đầu vào: `Domain` (Nghiệp vụ) và `Unit` (Đơn vị / Phòng ban được kiểm toán).
- Truy xuất các quy định nội bộ và văn bản pháp luật liên quan tới Domain & Unit.
- AI sinh danh mục checklist kiểm toán:
  - Câu hỏi kiểm toán (`audit_question`).
  - Rủi ro tiềm ẩn nếu vi phạm (`risk_description`).
  - Mức độ rủi ro (`risk_level`: `HIGH` / `MEDIUM` / `LOW`).
  - Citation / Trích dẫn điều khoản gốc bắt buộc (`source_citation`).
  - Gợi ý hành động khắc phục / kiến nghị (`recommendation`).
- Xuất kết quả checklist ra file CSV & Markdown (`outputs/audit_checklist_results.csv`, `outputs/audit_checklist_report.md`).

---

## 3. Cấu trúc Project đề xuất

```text
buoi_17/ (hoặc buoi_18/)
├── data/
│   ├── agribank_internal_policies.csv
│   └── chunks_combined_secure.csv
├── scripts/
│   ├── compliance_checker.py       # UC3: AI Compliance Checker Engine
│   ├── audit_checklist_gen.py      # UC4: AI Audit Checklist Generator Engine
│   ├── audit_logger.py             # Hệ thống ghi log audit trail
│   ├── security_tests_b18.py       # Test bảo mật & guardrails Buổi 18
│   └── final_validation_b18.py     # Script kiểm tra & nghiệm thu toàn diện
├── outputs/
│   ├── compliance_conflicts.csv
│   ├── compliance_conflict_report.md
│   ├── audit_checklist_results.csv
│   ├── audit_checklist_report.md
│   ├── security_test_b18_report.md
│   └── final_validation_b18_report.md
├── app.py                          # Web UI Streamlit tích hợp UC3 & UC4
└── .env
```

---

## 4. Cấu hình môi trường (`.env`)

```ini
SOURCE_SECURE_CSV=data/agribank_internal_policies.csv
SOURCE_NORMALIZED_CSV=data/chunks_combined_secure.csv

GEMINI_API_KEY=your_gemini_api_key_here
LLM_API_KEY=your_gemini_api_key_here
LLM_MODEL=gemini-2.5-flash
APP_ENV=training
```

---

## 5. Các bước thực hiện & Chuỗi Prompt Vibe Coding

### PROMPT SETUP – Kiểm tra môi trường & Dữ liệu Buổi 18

```plaintext
Kiểm tra toàn bộ môi trường và dữ liệu cho Buổi 18.

Dữ liệu đầu vào chính:
1. data/agribank_internal_policies.csv
2. data/chunks_combined_secure.csv

Kiểm tra:
- Python và virtual environment.
- File data/agribank_internal_policies.csv: kiểm tra 14 cột metadata (so_ky_hieu, article, title, allowed_roles,...).
- Đọc file chunks_combined_secure.csv và xác nhận số văn bản pháp lý / nội bộ.
- Đảm bảo các thư mục scripts/, outputs/ đã sẵn sàng.
- File .env đã có GEMINI_API_KEY / LLM_API_KEY hợp lệ chưa.

Báo kết quả:
- ENVIRONMENT READY: YES / NO
- INTERNAL DATA READY: YES / NO
- COMBINED DATA READY: YES / NO
```

---

### PROMPT 1 – Cataloging & Chuẩn bị dữ liệu cho UC3 & UC4

```plaintext
Thực hiện Cataloging dữ liệu cho Buổi 18.

Dùng 2 tệp:
- data/agribank_internal_policies.csv
- data/chunks_combined_secure.csv

Yêu cầu:
1. Thống kê tất cả các văn bản nội bộ Agribank (Title, số ký hiệu, loại văn bản, cơ quan ban hành, ngày ban hành, scope,...).
2. Phân loại các văn bản theo Domain/Nhiệm vụ (ví dụ: An toàn kho quỹ, CAR & Quản lý rủi ro, Tín dụng, Ngoại tệ, Bảo mật CNTT & AI, Thẩm quyền phê duyệt, Mua sắm nội bộ,...).
3. Kiểm tra tính đầy đủ của 14 trường metadata (`article`, `citation`, và `allowed_roles`).

Tạo file báo cáo:
- outputs/b18_data_catalog.md

Cuối file báo:
DATA CATALOGING: PASS / FAIL
DOMAINS DETECTED: [số lượng domain]
READY FOR UC3 & UC4: YES / NO
```

---

### PROMPT 2 – Xây dựng Engine UC3: AI Compliance Checker

```plaintext
Xây dựng Core Engine cho UC3 - AI Compliance Checker.

Tạo file:
scripts/compliance_checker.py

Chức năng chính:
1. Cho phép chọn hoặc tự động quét các cặp văn bản nội bộ Agribank cùng domain (hoặc giữa quy định nội bộ vs Thông tư/Nghị định).
2. Thực hiện so sánh chéo (cross-comparison) bằng cách truy xuất các điều/khoản liên quan qua BM25/Hybrid search.
3. Gửi Evidence Package gồm điều khoản A và điều khoản B sang LLM để phân tích:
   - Có mâu thuẫn/chồng chéo/xung đột không?
   - Loại xung đột: Hạn mức/ngưỡng, quy trình thực hiện, thẩm quyền phê duyệt, hoặc thời hạn hiệu lực.
   - Trích dẫn cụ thể: Citation A (so_ky_hieu_A + article_A) vs Citation B (so_ky_hieu_B + article_B).
   - Đánh giá Severity: HIGH (nếu vi phạm pháp luật/rủi ro tài chính lớn), MEDIUM (rủi ro vận hành), LOW (chồng chéo thủ tục).
   - review_status = "NEEDS_HUMAN_REVIEW".
4. Nếu không phát hiện mâu thuẫn rõ ràng, trả về classification = "KHONG_XUNG_DOT" hoặc "CHUA_DU_BANG_CHUNG".

Đảm bảo:
- Bắt buộc dùng Citation thật từ dataset, không tự bịa điều khoản.
- Tích hợp AuditLogger để ghi lại mọi vết kiểm tra.

Chạy test thử nghiệm với 3 cặp quy định (Kho quỹ, CAR, Tín dụng).

Xuất kết quả ra:
- outputs/compliance_conflicts.csv
- outputs/compliance_conflict_report.md

Cuối report:
COMPLIANCE CHECKER ENGINE: PASS / FAIL
CONFLICTS DETECTED: [Số lượng]
HUMAN REVIEW GUARDRAIL: PASS
```

#### Schema Output UC3 (`compliance_conflicts.csv`):
```csv
conflict_id,domain,doc_a_id,doc_a_citation,doc_a_text,doc_b_id,doc_b_citation,doc_b_text,conflict_type,severity,description,review_status,timestamp,request_id
```

---

### PROMPT 3 – Xây dựng Engine UC4: AI Audit Checklist Generator

```plaintext
Xây dựng Core Engine cho UC4 - AI Audit Checklist Generator.

Tạo file:
scripts/audit_checklist_gen.py

Chức năng chính:
1. Đầu vào:
   - domain: Miền kiểm toán ("An toàn kho quỹ & Vận chuyển tiền", "Phân quyền tín dụng", "Bảo mật CNTT & AI", "Quản lý CAR", v.v.)
   - unit: Đơn vị được kiểm toán ("Chi nhánh loại 1", "Phòng giao dịch", "Khối CNTT", "Phòng Kế toán", v.v.)
   - user_role: Vai trò người dùng (lọc RBAC).
2. Quy trình xử lý:
   - Truy xuất các đoạn quy định nội bộ và văn bản NHNN liên quan đến domain và unit trong phạm vi RBAC.
   - LLM phân tích và sinh danh mục các mục kiểm tra, rủi ro tương ứng, và câu hỏi kiểm tra (Checklist items).
   - Gán mức độ rủi ro (risk_level: HIGH / MEDIUM / LOW) cho từng mục kiểm tra.
   - Đóng gói link/citation trực tiếp tới Điều/Khoản văn bản gốc.

Output Schema cho từng mục checklist:
- item_id: Mã mục kiểm tra (ví dụ: CHK_KHO_01)
- domain: Miền nghiệp vụ
- unit_scope: Phạm vi áp dụng
- audit_question: Câu hỏi kiểm toán (Ví dụ: "Chi nhánh có bố trí ô tô bọc thép chuyên dùng để vận chuyển tiền không?")
- risk_description: Rủi ro tiềm ẩn (Ví dụ: "Thất thoát tiền mặt, rủi ro an ninh trên đường vận chuyển")
- risk_level: HIGH / MEDIUM / LOW
- source_citation: Citation văn bản gốc kèm Điều/Khoản
- recommendation: Gợi ý hành động kiểm toán
- review_status: "NEEDS_HUMAN_REVIEW"

3. Tích hợp AuditLogger để ghi lại thao tác tạo checklist.

Chạy thử nghiệm tạo checklist cho 2 domain: "An toàn kho quỹ" và "Bảo mật CNTT & AI".

Xuất kết quả ra:
- outputs/audit_checklist_results.csv
- outputs/audit_checklist_report.md

Cuối report:
CHECKLIST GENERATOR ENGINE: PASS / FAIL
CHECKLIST ITEMS GENERATED: [Số lượng]
CITATIONS ATTACHED: YES
```

---

### PROMPT 4 – Xây dựng Giao diện Streamlit UI cho UC3 & UC4

```plaintext
Cập nhật/Xây dựng giao diện Streamlit trong file:
app.py

Yêu cầu giao diện:
1. Sidebar:
   - Chọn User ID & User Role (Admin, Risk Manager, KiemToanVien, Staff).
   - Trạng thái kết nối dữ liệu (Internal Policies & External Legal Docs).
   - Nút Reset Session / Clean Audit Log.

2. Tab 1 - UC3 - AI Compliance Checker (Kiểm tra xung đột quy định):
   - Chọn bộ lọc Domain hoặc Quét toàn bộ văn bản.
   - Nút "Phát hiện xung đột & Mâu thuẫn".
   - Hiển thị danh sách phát hiện dưới dạng Card / Bảng đẹp mắt:
     + 2 cột đối chiếu: Văn bản A (Trích dẫn, Nội dung) vs Văn bản B (Trích dẫn, Nội dung).
     + Phân tích & Giải thích chi tiết từ AI.
     + Tag phân loại mâu thuẫn & Tag Severity (HIGH - Đỏ, MEDIUM - Vàng, LOW - Xanh).
     + Nút gắn nhãn / Phê duyệt của Kiểm toán viên (`review_status`).
   - Tải về kết quả (CSV / Markdown).

3. Tab 2 - UC4 - AI Audit Checklist Generator (Tạo Checklist kiểm toán):
   - Chọn Phạm vi kiểm toán (Domain dropdown + Unit dropdown).
   - Nút "Tạo bản nháp Checklist kiểm toán".
   - Bảng danh mục Checklist kiểm toán trực quan:
     + Mã mục, Câu hỏi kiểm toán, Rủi ro tiềm ẩn, Mức rủi ro.
     + Cột Văn bản gốc / Citation có thể xem chi tiết / trích dẫn gốc.
   - Tải xuống Checklist (CSV / JSON).

4. Tab 3 - Audit Log & System Trail:
   - Hiển thị bảng toàn bộ log hệ thống: tra cứu, quét xung đột, sinh checklist.
   - Lọc theo Role và Action.

5. Banner & Warning:
   - Đặt banner khuyến cáo: "Demo sản phẩm AI Kiểm toán - Kết quả gợi ý cần kiểm toán viên xác minh trước khi ban hành."

Chạy ứng dụng:
streamlit run app.py
```

---

### PROMPT 5 – Security & Guardrail Testing cho Buổi 18

```plaintext
Đóng vai Security & Compliance Tester để kiểm thử ứng dụng Buổi 18.

Tạo file:
scripts/security_tests_b18.py

Thực hiện 7 bài test:
1. RBAC Test: Role 'Staff' không truy cập được quy định bảo mật riêng của 'Risk Manager' hay 'Admin'.
2. Citation Integrity: Mọi conflict (UC3) và checklist item (UC4) bắt buộc phải có Citation hợp lệ (không rỗng).
3. Hallucination Check: Kiểm tra AI có tự bịa ra điều khoản/thông tin không tồn tại trong dataset không.
4. Human Review Guardrail: Mọi kết quả xuất ra đều có review_status = "NEEDS_HUMAN_REVIEW".
5. Audit Log Privacy: Audit log không lưu API key / secret, mã hóa thông tin nhạy cảm.
6. Unknown Domain Test: Nhập Domain không có trong dữ liệu -> Hệ thống thông báo rõ ràng "Chưa có dữ liệu quy định", không tự bịa.
7. File Export Verification: Kiểm tra file CSV xuất ra có đúng schema và mở được không.

Xuất báo cáo:
- outputs/security_test_b18_report.md

Cuối file báo:
SECURITY & GUARDRAIL TESTS: PASS / FAIL
```

---

### PROMPT 6 – Audit Toàn bộ Project & Final Validation

```plaintext
Audit toàn bộ project Buổi 18 và tạo báo cáo nghiệm thu cuối cùng.

Tạo file:
output/final_validation_b18_report.md

Kiểm tra và xác nhận các tiêu chí:
1. Source Data Integrity: Giữ nguyên file gốc, đọc read-only.
2. UC3 AI Compliance Checker: So sánh chéo quy định nội bộ vs văn bản gốc, phát hiện mâu thuẫn kèm điều/khoản và Severity.
3. UC4 AI Audit Checklist Generator: Sinh checklist kiểm toán bám sát Domain & Unit, trích dẫn chuẩn xác văn bản gốc.
4. Citation & Linking: Trích dẫn đầy đủ số ký hiệu, điều, khoản.
5. RBAC & Governance: Lọc quyền trước retrieval/context, không để lộ dữ liệu cấm.
6. Streamlit Web Interface: Giao diện trực quan, hoạt động mượt mà cho cả 2 use case.
7. Audit Log: Ghi nhận log đầy đủ vào audit_log.json / DB.
8. Human Review Guardrail: Mọi finding đều yêu cầu Human Review.

Đánh giá tổng thể ở cuối file:
- UC3 COMPLIANCE CHECKER: PASS / FAIL
- UC4 AUDIT CHECKLIST GEN: PASS / FAIL
- CITATION INTEGRITY: PASS / FAIL
- RBAC & GOVERNANCE: PASS / FAIL
- STREAMLIT DEMO: PASS / FAIL
- AUDIT TRAIL: PASS / FAIL
- SYSTEM READY FOR DEMO: YES / NO
```

---

## 6. Trình tự Demo cuối buổi

1. **Trình bày UC3 (AI Compliance Checker)**:
   - Chọn miền "An toàn kho quỹ & Vận chuyển tiền" hoặc "Quản lý CAR".
   - Bấm nút kiểm tra tuân thủ $\rightarrow$ AI chỉ ra điểm mâu thuẫn giữa `Quyết định 100/QĐ-NHNO-AT` và `Thông tư 01/2014/TT-NHNN` về phương tiện bọc thép chuyên dùng (`Severity: HIGH`).
2. **Trình bày UC4 (AI Audit Checklist Generator)**:
   - Nhập Domain: "Bảo mật CNTT & AI", Unit: "Khối CNTT".
   - AI lập bảng checklist gồm các mục kiểm tra mã hóa AES-128 và lưu trữ RAG AI, thời gian lưu audit logs, quy trình phê duyệt $\rightarrow$ Trích dẫn trực tiếp `Quy chế 600/QĐ-NHNO-CNTT` & `Điều 9, 16`.
3. **Trình bày Audit Log & Guardrail**:
   - Mở tab Audit Log xem toàn bộ các truy vấn vừa thực hiện.
   - Nhấn mạnh nhãn `NEEDS_HUMAN_REVIEW` khẳng định AI đóng vai trò trợ lý trợ lực cho Kiểm toán viên, không thay thế quyết định con người.

---

## 7. Những điều Agent tuyệt đối không được làm

- ❌ **Không sửa đổi tệp dữ liệu nguồn** trong `data/`.
- ❌ **Không hardcode API key / secret** vào code hay file log/report.
- ❌ **Không để AI tự bịa văn bản / trích dẫn** nếu không có context chứng minh.
- ❌ **Không bỏ qua bước gắn nhãn `NEEDS_HUMAN_REVIEW`** cho các cảnh báo xung đột.
- ❌ **Không cho phép người dùng role thấp (Staff/Guest) truy xuất** các tài liệu nghiệp vụ mật mà chưa có thẩm quyền.