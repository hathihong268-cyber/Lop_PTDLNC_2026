# BÁO CÁO KẾT QUẢ AI COMPLIANCE CHECKER ENGINE (UC3)
**Hệ thống So sánh Chéo & Phát hiện Xung đột Quy định Agribank**

---

## 1. Tổng quan Đợt Kiểm tra (Inspection Summary)
- **Ngày thực hiện**: 2026-08-24 21:36:06
- **Số cặp văn bản được kiểm tra**: 3 cặp
- **Số mâu thuẫn / chênh lệch phát hiện**: 3 mâu thuẫn
- **Cơ chế Bảo mật & Kiểm soát**: Tự động gán `review_status = "NEEDS_HUMAN_REVIEW"` cho toàn bộ phát hiện.

---

## 2. Bảng Thống kê Xung đột (Conflict Matrix)

| Conflict ID | Domain | Văn bản A | Văn bản B | Loại Xung đột | Severity | Guardrail Status |
|---|---|---|---|---|---|---|
| `CFL-8418E3` | An toàn kho quỹ & Tiền mặt | `100/QĐ-NHNO-AT` | `01/2014/TT-NHNN` | `Quy trình thực hiện` | 🔴 HIGH | `NEEDS_HUMAN_REVIEW` |
| `CFL-358555` | CAR & Quản lý rủi ro | `250/QĐ-NHNO-QLRR` | `41/2016/TT-NHNN` | `Hạn mức/ngưỡng` | 🟢 LOW | `NEEDS_HUMAN_REVIEW` |
| `CFL-28BA9B` | Hoạt động Tín dụng & Ủy quyền | `315/QC-NHNO-TD` | `43/2024/TT-NHNN` | `Hạn mức/ngưỡng` | 🔴 HIGH | `NEEDS_HUMAN_REVIEW` |

---

## 3. Chi tiết Phân tích Xung đột (Detailed Conflict Findings)


### 1. Conflict ID: `CFL-8418E3` - Domain: **An toàn kho quỹ & Tiền mặt**
- **Văn bản A (Nội bộ)**: `100/QĐ-NHNO-AT` - [100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT | Điều 12 | doc_agr_kq01_02]
- **Văn bản B (Đối chiếu)**: `01/2014/TT-NHNN` - [01/2014/TT-NHNN - Thông tư số 01/2014/TT-NHNN | Điều 50 | doc_44209_dieu_50]
- **Phân loại Xung đột**: `Quy trình thực hiện`
- **Mức độ Rủi ro (Severity)**: 🔴 HIGH
- **Trạng thái Duyệt (Guardrail)**: `NEEDS_HUMAN_REVIEW`
- **Mô tả Mâu thuẫn / Chênh lệch**:
  > Văn bản A quy định vận chuyển tiền mặt trên 500 triệu đồng phải sử dụng xe bọc thép và 02 bảo vệ. Tuy nhiên, Văn bản B của NHNN quy định vận chuyển tiền từ 1 tỷ đồng trở lên phải có xe công an hoặc bảo vệ chuyên nghiệp hộ tống. Mâu thuẫn phát sinh khi quy định nội bộ của Agribank có thể không đáp ứng đầy đủ yêu cầu về hình thức hộ tống bên ngoài (xe công an/bảo vệ chuyên nghiệp) theo quy định của NHNN cho các giao dịch trên 1 tỷ đồng, dù có yêu cầu nghiêm ngặt hơn về phương tiện và ngưỡng ban đầu.

---

### 2. Conflict ID: `CFL-358555` - Domain: **CAR & Quản lý rủi ro**
- **Văn bản A (Nội bộ)**: `250/QĐ-NHNO-QLRR` - [250/QĐ-NHNO-QLRR - Quy định nội bộ số 250/QĐ-NHNO-QLRR | Điều 5 | doc_agr_rr02_01]
- **Văn bản B (Đối chiếu)**: `41/2016/TT-NHNN` - [41/2016/TT-NHNN - Thông tư số 41/2016/TT-NHNN | Điều 3 | doc_117310_dieu_3]
- **Phân loại Xung đột**: `Hạn mức/ngưỡng`
- **Mức độ Rủi ro (Severity)**: 🟢 LOW
- **Trạng thái Duyệt (Guardrail)**: `NEEDS_HUMAN_REVIEW`
- **Mô tả Mâu thuẫn / Chênh lệch**:
  > Văn bản A (Quy định nội bộ Agribank) yêu cầu duy trì tỷ lệ an toàn vốn (CAR) nội bộ tối thiểu 9.0% và kích hoạt kế hoạch khôi phục vốn khi CAR giảm xuống dưới 8.5%. Trong khi đó, Văn bản B (Thông tư 41/2016/TT-NHNN) quy định tỷ lệ an toàn vốn tối thiểu là 8%. Agribank đã thiết lập ngưỡng CAR nội bộ cao hơn mức tối thiểu theo quy định của Ngân hàng Nhà nước, tạo ra một vùng đệm an toàn lớn hơn. Đây là sự chênh lệch về hạn mức nhưng không gây mâu thuẫn vi phạm pháp luật, mà thể hiện sự thận trọng trong quản lý rủi ro của Agribank.

---

### 3. Conflict ID: `CFL-28BA9B` - Domain: **Hoạt động Tín dụng & Ủy quyền**
- **Văn bản A (Nội bộ)**: `315/QC-NHNO-TD` - [315/QC-NHNO-TD - Quy chế tín dụng nội bộ số 315/QC-NHNO-TD | Điều 8 | doc_agr_td03_01]
- **Văn bản B (Đối chiếu)**: `43/2024/TT-NHNN` - [43/2024/TT-NHNN - Thông tư số 43/2024/TT-NHNN | Điều 2 | doc_169221_dieu_2]
- **Phân loại Xung đột**: `Hạn mức/ngưỡng`
- **Mức độ Rủi ro (Severity)**: 🔴 HIGH
- **Trạng thái Duyệt (Guardrail)**: `NEEDS_HUMAN_REVIEW`
- **Mô tả Mâu thuẫn / Chênh lệch**:
  > Văn bản A quy định hạn mức phán quyết tín dụng cố định cho Giám đốc Chi nhánh Agribank loại I. Tuy nhiên, Văn bản B (Thông tư 43/2024/TT-NHNN) yêu cầu tổ chức tín dụng phải quy định hạn mức ủy quyền cho vay của Giám đốc chi nhánh phù hợp với năng lực quản trị rủi ro và tỷ lệ nợ xấu của từng chi nhánh. Điều này cho thấy sự chênh lệch trong nguyên tắc xác định hạn mức: Văn bản A áp dụng hạn mức chung theo loại chi nhánh, trong khi Văn bản B yêu cầu cá thể hóa dựa trên hồ sơ rủi ro cụ thể của từng đơn vị. Agribank cần rà soát để đảm bảo các hạn mức nội bộ được thiết lập linh hoạt và tuân thủ yêu cầu của NHNN.

---


## 4. Kết luận & Khuyến nghị Kiểm toán (Audit Recommendation)
1. Tất cả các mâu thuẫn nêu trên đều sử dụng **Citation thật** từ bộ dữ liệu Agribank và Thông tư NHNN.
2. Các điểm mâu thuẫn về ngưỡng vận chuyển tiền mặt (500 triệu vs 1 tỷ) và tỷ lệ an toàn vốn CAR (9% nội bộ vs 8% tối thiểu NHNN) phản ánh chính xác sự khác biệt giữa tiêu chuẩn nội bộ và tiêu chuẩn ngành.
3. Khuyên nghị Kiểm toán viên (Human Auditor) duyệt và đưa vào chương trình làm việc của Ban Kiểm soát.

---

COMPLIANCE CHECKER ENGINE: PASS
CONFLICTS DETECTED: 3
HUMAN REVIEW GUARDRAIL: PASS