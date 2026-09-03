# BÁO CÁO KẾT QUẢ AI AUDIT CHECKLIST GENERATOR ENGINE (UC4)
**Hệ thống Sinh Danh mục Kiểm toán Tự động theo Domain & Đơn vị Agribank [Provider: OLLAMA]**

---

## 1. Tổng quan Đợt Sinh Checklist (Summary)
- **Ngày thực hiện**: 2026-08-26 22:41:53
- **Tổng số mục Checklist đã sinh**: 4 mục
- **Các Domain được kiểm tra**: An toàn kho quỹ & Vận chuyển tiền, Bảo mật CNTT & AI
- **Ràng buộc Trích dẫn (Citation Guardrail)**: Gắn kèm 100% Citation thật
- **Trạng thái Duyệt**: Mặc định `NEEDS_HUMAN_REVIEW` cho 100% mục checklist.

---

## 2. Bảng Tổng hợp Danh mục Kiểm toán (Audit Checklist Summary)

| Mã mục (Item ID) | Domain | Phạm vi (Unit) | Câu hỏi Kiểm toán chính | Mức độ Rủi ro | Citation văn bản gốc | Guardrail Status |
|---|---|---|---|---|---|---|
| `CHK_KHO_01` | An toàn kho quỹ & Vận chuyển tiền | `Chi nhánh loại 1` | Chi nhánh có trang bị đầy đủ xe bọc thép chuyên dùng và came... | 🔴 HIGH | `[100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT | Điều 12 | doc_agr_kq01_02]` | `NEEDS_HUMAN_REVIEW` |
| `CHK_KHO_02` | An toàn kho quỹ & Vận chuyển tiền | `Chi nhánh loại 1` | Ban Quản lý kho tiền có thực hiện đúng quy trình kiểm đếm và... | 🟡 MEDIUM | `[100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT | Điều 25 | doc_agr_kq01_03]` | `NEEDS_HUMAN_REVIEW` |
| `CHK_IT_01` | Bảo mật CNTT & AI | `Khối CNTT` | Các ứng dụng AI và hệ thống RAG tra cứu quy định có thực hiệ... | 🔴 HIGH | `[600/QC-NHNO-CNTT - Quy chế bảo mật CNTT số 600/QC-NHNO-CNTT | Điều 9 | doc_agr_it07_01]` | `NEEDS_HUMAN_REVIEW` |
| `CHK_IT_02` | Bảo mật CNTT & AI | `Khối CNTT` | Nhật ký hệ thống (Audit Log) có ghi nhận đầy đủ timestamp, u... | 🟡 MEDIUM | `[600/QC-NHNO-CNTT - Quy chế bảo mật CNTT số 600/QC-NHNO-CNTT | Điều 16 | doc_agr_it07_02]` | `NEEDS_HUMAN_REVIEW` |

---

## 3. Chi tiết Nội dung Checklist Kiểm toán (Detailed Checklist Items)

### Domain: **An toàn kho quỹ & Vận chuyển tiền** (2 mục kiểm tra)

#### Mã mục: `CHK_KHO_01` - Phạm vi: `Chi nhánh loại 1`
- **Câu hỏi Kiểm toán**: **Chi nhánh có trang bị đầy đủ xe bọc thép chuyên dùng và camera giám sát khi vận chuyển tiền mặt không?**
- **Rủi ro Tiềm ẩn**: Thất thoát tài sản quý, rủi ro an toàn tính mạng cán bộ vận chuyển và vi phạm quy định an toàn kho quỹ.
- **Mức độ Rủi ro**: 🔴 HIGH
- **Trích dẫn Văn bản gốc (Citation)**: `[100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT | Điều 12 | doc_agr_kq01_02]`
- **Gợi ý Hành động Kiểm toán**: Kiểm tra nhật ký điều xe bọc thép và đối chiếu chứng từ kiểm đếm niêm phong trước khi xuất kho.
- **Trạng thái Duyệt (Guardrail)**: `NEEDS_HUMAN_REVIEW`

---
#### Mã mục: `CHK_KHO_02` - Phạm vi: `Chi nhánh loại 1`
- **Câu hỏi Kiểm toán**: **Ban Quản lý kho tiền có thực hiện đúng quy trình kiểm đếm và niêm phong tiền nghi giả theo quy định không?**
- **Rủi ro Tiềm ẩn**: Rủi ro lọt lưới tiền giả vào hệ thống lưu thông và lây lan rủi ro pháp lý.
- **Mức độ Rủi ro**: 🟡 MEDIUM
- **Trích dẫn Văn bản gốc (Citation)**: `[100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT | Điều 25 | doc_agr_kq01_03]`
- **Gợi ý Hành động Kiểm toán**: Phỏng vấn Thủ kho, Kiểm ngân và kiểm tra biên bản niêm phong tiền nghi giả tại kho tiền.
- **Trạng thái Duyệt (Guardrail)**: `NEEDS_HUMAN_REVIEW`

---
### Domain: **Bảo mật CNTT & AI** (2 mục kiểm tra)

#### Mã mục: `CHK_IT_01` - Phạm vi: `Khối CNTT`
- **Câu hỏi Kiểm toán**: **Các ứng dụng AI và hệ thống RAG tra cứu quy định có thực hiện mã hóa dữ liệu nhạy cảm AES-128/Fernet at-rest không?**
- **Rủi ro Tiềm ẩn**: Rủi ro rò rỉ dữ liệu tài chính nội bộ, vi phạm tiêu chuẩn bảo mật Cấp độ 3 An toàn thông tin.
- **Mức độ Rủi ro**: 🔴 HIGH
- **Trích dẫn Văn bản gốc (Citation)**: `[600/QC-NHNO-CNTT - Quy chế bảo mật CNTT số 600/QC-NHNO-CNTT | Điều 9 | doc_agr_it07_01]`
- **Gợi ý Hành động Kiểm toán**: Soi chiếu cấu hình kỹ thuật của hệ thống RAG và kiểm tra chứng chỉ mã hóa dữ liệu cơ sở dữ liệu.
- **Trạng thái Duyệt (Guardrail)**: `NEEDS_HUMAN_REVIEW`

---
#### Mã mục: `CHK_IT_02` - Phạm vi: `Khối CNTT`
- **Câu hỏi Kiểm toán**: **Nhật ký hệ thống (Audit Log) có ghi nhận đầy đủ timestamp, user_id, user_role và lưu trữ tối thiểu 12 tháng không?**
- **Rủi ro Tiềm ẩn**: Không thể truy vết sự cố an ninh mạng hoặc truy cập trái phép khi xảy ra vi phạm bảo mật.
- **Mức độ Rủi ro**: 🟡 MEDIUM
- **Trích dẫn Văn bản gốc (Citation)**: `[600/QC-NHNO-CNTT - Quy chế bảo mật CNTT số 600/QC-NHNO-CNTT | Điều 16 | doc_agr_it07_02]`
- **Gợi ý Hành động Kiểm toán**: Trích xuất mẫu file audit_log.jsonl và xác minh thời hạn lưu trữ log trên server.
- **Trạng thái Duyệt (Guardrail)**: `NEEDS_HUMAN_REVIEW`

---


## 4. Kết luận & Hướng dẫn Sử dụng cho Đoàn Kiểm toán
1. Toàn bộ câu hỏi kiểm toán và rủi ro được tổng hợp từ dữ liệu quy định nội bộ Agribank và Thông tư NHNN.
2. Kiểm toán viên sử dụng danh mục này làm căn cứ lập kế hoạch kiểm toán thực địa tại Chi nhánh loại 1 và Khối CNTT.
3. Mọi điều chỉnh danh mục cần sự phê duyệt của Trưởng đoàn Kiểm toán (`NEEDS_HUMAN_REVIEW`).

---

CHECKLIST GENERATOR ENGINE: PASS
LLM PROVIDER: OLLAMA
CHECKLIST ITEMS GENERATED: 4
CITATIONS ATTACHED: YES