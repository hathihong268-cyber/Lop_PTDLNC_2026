# BÁO CÁO KIỂM THỬ BẢO MẬT & GUARDRAIL BUỔI 18
**Security, RBAC, Anti-Hallucination & Compliance Audit Test Report**

---

## 1. Tổng quan Kiểm thử (Test Execution Summary)
- **Ngày thực hiện**: 2026-08-24 21:24:18
- **Tổng số bài kiểm thử**: 7 bài test
- **Số bài test ĐẠT (PASS)**: 7/7
- **Kết luận Tổng thể**: PASSED

---

## 2. Kết quả Chi tiết 7 Bài Kiểm thử Security & Guardrail

| STT | Tên bài Kiểm thử (Test Case) | Trạng thái (Status) | Chi tiết Đánh giá (Evaluation Details) |
|---|---|---|---|
| 1 | **Test 1: RBAC Access Control** | 🟢 **PASS** | Role 'Staff' bị chặn 100% đối với 4 văn bản bảo mật (250/QĐ, 410/QĐ, 600/QC, 390/QĐ). |
| 2 | **Test 2: Citation Integrity** | 🟢 **PASS** | 100% trích dẫn trong UC3 (3 cặp) và UC4 (9 mục) đầy đủ, không rỗng. |
| 3 | **Test 3: Anti-Hallucination Guardrail** | 🟢 **PASS** | 100% số ký hiệu văn bản trong UC3 và UC4 khớp khớp hoàn toàn với Dataset gốc (0% hư cấu). |
| 4 | **Test 4: Human Review Guardrail** | 🟢 **PASS** | 100% kết quả xuất ra đều duy trì trạng thái 'NEEDS_HUMAN_REVIEW' (hoặc 'APPROVED_BY_AUDITOR'). |
| 5 | **Test 5: Audit Log Privacy & Security** | 🟢 **PASS** | Tệp audit_log.jsonl tuyệt đối không lộ API key, Secret hay Password. |
| 6 | **Test 6: Unknown Domain Handling** | 🟢 **PASS** | Nhập domain lạ 'Nghiệp vụ Hàng hải & Vận tải Tàu biển' -> Hệ thống xử lý an toàn, sử dụng trích dẫn có sẵn hoặc thông báo dữ liệu, không bịa luật Hàng hải. |
| 7 | **Test 7: File Export & Schema Verification** | 🟢 **PASS** | File UC3 CSV (14 cột) và UC4 CSV (11 cột) hợp lệ 100%, parse thành công. |

---

## 3. Chi tiết Phân tích An toàn & Guardrail (Safety Analysis)

1. **Phân quyền RBAC**: Đảm bảo phân tách ranh giới dữ liệu tuyệt đối giữa các vai trò `Staff` và `Risk_Manager`/`Admin`.
2. **Chống Hư cấu (Anti-Hallucination)**: 100% trích dẫn điều khoản đều được đối chiếu trực tiếp với bộ dữ liệu gốc `chunks_combined_secure.csv`.
3. **Cơ chế Kiểm soát Con người (Human-in-the-loop)**: Mọi mâu thuẫn quy định và mục checklist kiểm toán đều bắt buộc gán `review_status = "NEEDS_HUMAN_REVIEW"`.
4. **Bảo mật Nhật ký Kiểm toán (Audit Privacy)**: Không ghi nhận bất kỳ thông tin nhạy cảm (API key, secret) nào vào tệp `audit_log.jsonl`.

---

SECURITY & GUARDRAIL TESTS: PASS