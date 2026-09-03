---
id: RR-007
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
category: Rui ro tuan thu
inherent_level: Cao
residual_level: Trung binh
owner_unit_id: DV-COMPLIANCE
---

# RR-007 - Chậm báo cáo giao dịch đáng ngờ

## 1. Thông tin rủi ro
- **Mã hồ sơ rủi ro:** `RR-007`
- **Phân loại (Category):** Rui ro tuan thu
- **Mức độ rủi ro vốn có (Inherent Level):** Cao
- **Mức độ rủi ro còn lại (Residual Level):** Trung binh
- **Đơn vị quản lý (Owner Unit ID):** `DV-COMPLIANCE`
- **Nguồn gốc dữ liệu:** SYNTHETIC
- **Trạng thái xác minh:** VERIFIED

## 2. Diễn biến cấu trúc rủi ro
- **Mô tả chung:** Theo dõi cảnh báo AML không kịp thời
- **Nguyên nhân (Cause):** Khối lượng cảnh báo vượt năng lực xử lý
- **Sự kiện rủi ro (Event):** Báo cáo giao dịch đáng ngờ nộp muộn
- **Tác động / Hậu quả (Impact):** Chế tài và rủi ro pháp lý

## 3. Kiểm soát liên quan (Mitigating Controls)
- [[KS-007 - Theo dõi SLA xử lý cảnh báo AML]]
  - **Mối quan hệ:** `MITIGATES`
  - **Trích dẫn bằng chứng:** Dữ liệu mô phỏng: theo dõi SLA giảm nguy cơ báo cáo muộn
  - **Độ tin cậy:** 1.0 | **Trạng thái:** `VERIFIED`

## 4. Sự kiện rủi ro liên quan (Observed Risk Events)
- [[SK-007 - Báo cáo giao dịch đáng ngờ nộp quá hạn nội bộ]]
  - **Mối quan hệ:** `OBSERVED_AS`
  - **Trích dẫn bằng chứng:** Dữ liệu mô phỏng: sự kiện báo cáo AML muộn
  - **Độ tin cậy:** 1.0 | **Trạng thái:** `VERIFIED`

---
[[Home| Trang chủ Wiki]]
