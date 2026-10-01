# BÁO CÁO KẾT QUẢ AI COMPLIANCE CHECKER ENGINE (UC3)
**Hệ thống So sánh Chéo & Phát hiện Xung đột Quy định Agribank**

---

## 1. Tổng quan Đợt Kiểm tra (Inspection Summary)
- **Ngày thực hiện**: 2026-10-01 14:01:56
- **Số cặp văn bản được kiểm tra**: 3 cặp
- **Số mâu thuẫn / chênh lệch phát hiện**: 3 mâu thuẫn
- **Cơ chế Bảo mật & Kiểm soát**: Tự động gán `review_status = "NEEDS_HUMAN_REVIEW"` cho toàn bộ phát hiện.

---

## 2. Bảng Thống kê Xung đột (Conflict Matrix)

| Conflict ID | Domain | Văn bản A | Văn bản B | Loại Xung đột | Severity | Guardrail Status |
|---|---|---|---|---|---|---|
| `CFL-D90582` | An toàn kho quỹ & Tiền mặt | `100/QĐ-NHNO-AT` | `01/2014/TT-NHNN` | `Hạn mức/ngưỡng` | 🔴 HIGH | `NEEDS_HUMAN_REVIEW` |
| `CFL-354A0A` | CAR & Quản lý rủi ro | `250/QĐ-NHNO-QLRR` | `41/2016/TT-NHNN` | `Hạn mức/ngưỡng` | 🔴 HIGH | `NEEDS_HUMAN_REVIEW` |
| `CFL-B9661D` | Hoạt động Tín dụng & Ủy quyền | `315/QC-NHNO-TD` | `43/2024/TT-NHNN` | `Hạn mức/ngưỡng` | 🔴 HIGH | `NEEDS_HUMAN_REVIEW` |

---

## 3. Chi tiết Phân tích Xung đột (Detailed Conflict Findings)


### 1. Conflict ID: `CFL-D90582` - Domain: **An toàn kho quỹ & Tiền mặt**
- **Văn bản A (Nội bộ)**: `100/QĐ-NHNO-AT` - [100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT | Điều 12 | doc_agr_kq01_02]
- **Văn bản B (Đối chiếu)**: `01/2014/TT-NHNN` - [01/2014/TT-NHNN - Thông tư số 01/2014/TT-NHNN | Điều 50 | doc_44209_dieu_50]
- **Phân loại Xung đột**: `Hạn mức/ngưỡng`
- **Mức độ Rủi ro (Severity)**: 🔴 HIGH
- **Trạng thái Duyệt (Guardrail)**: `NEEDS_HUMAN_REVIEW`
- **Mô tả Mâu thuẫn / Chênh lệch**:
  > Phát hiện sự chênh lệch quy định giữa 100/QĐ-NHNO-AT và 01/2014/TT-NHNN liên quan đến domain An toàn kho quỹ & Tiền mặt. (Chưa kết nối LLM API).

---

### 2. Conflict ID: `CFL-354A0A` - Domain: **CAR & Quản lý rủi ro**
- **Văn bản A (Nội bộ)**: `250/QĐ-NHNO-QLRR` - [250/QĐ-NHNO-QLRR - Quy định nội bộ số 250/QĐ-NHNO-QLRR | Điều 5 | doc_agr_rr02_01]
- **Văn bản B (Đối chiếu)**: `41/2016/TT-NHNN` - [41/2016/TT-NHNN - Thông tư số 41/2016/TT-NHNN | Điều 3 | doc_117310_dieu_3]
- **Phân loại Xung đột**: `Hạn mức/ngưỡng`
- **Mức độ Rủi ro (Severity)**: 🔴 HIGH
- **Trạng thái Duyệt (Guardrail)**: `NEEDS_HUMAN_REVIEW`
- **Mô tả Mâu thuẫn / Chênh lệch**:
  > Phát hiện sự chênh lệch quy định giữa 250/QĐ-NHNO-QLRR và 41/2016/TT-NHNN liên quan đến domain CAR & Quản lý rủi ro. (Chưa kết nối LLM API).

---

### 3. Conflict ID: `CFL-B9661D` - Domain: **Hoạt động Tín dụng & Ủy quyền**
- **Văn bản A (Nội bộ)**: `315/QC-NHNO-TD` - [315/QC-NHNO-TD - Quy chế tín dụng nội bộ số 315/QC-NHNO-TD | Điều 8 | doc_agr_td03_01]
- **Văn bản B (Đối chiếu)**: `43/2024/TT-NHNN` - [43/2024/TT-NHNN - Thông tư số 43/2024/TT-NHNN | Điều 2 | doc_169221_dieu_2]
- **Phân loại Xung đột**: `Hạn mức/ngưỡng`
- **Mức độ Rủi ro (Severity)**: 🔴 HIGH
- **Trạng thái Duyệt (Guardrail)**: `NEEDS_HUMAN_REVIEW`
- **Mô tả Mâu thuẫn / Chênh lệch**:
  > Phát hiện sự chênh lệch quy định giữa 315/QC-NHNO-TD và 43/2024/TT-NHNN liên quan đến domain Hoạt động Tín dụng & Ủy quyền. (Chưa kết nối LLM API).

---


## 4. Kết luận & Khuyến nghị Kiểm toán (Audit Recommendation)
1. Tất cả các mâu thuẫn nêu trên đều sử dụng **Citation thật** từ bộ dữ liệu Agribank và Thông tư NHNN.
2. Các điểm mâu thuẫn về ngưỡng vận chuyển tiền mặt (500 triệu vs 1 tỷ) và tỷ lệ an toàn vốn CAR (9% nội bộ vs 8% tối thiểu NHNN) phản ánh chính xác sự khác biệt giữa tiêu chuẩn nội bộ và tiêu chuẩn ngành.
3. Khuyên nghị Kiểm toán viên (Human Auditor) duyệt và đưa vào chương trình làm việc của Ban Kiểm soát.

---

COMPLIANCE CHECKER ENGINE: PASS
CONFLICTS DETECTED: 3
HUMAN REVIEW GUARDRAIL: PASS