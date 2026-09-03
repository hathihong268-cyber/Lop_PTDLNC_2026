---
id: RR-009
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
category: Rui ro gian lan
inherent_level: Cao
residual_level: Trung binh
owner_unit_id: DV-OPS
---

# RR-009 - Không phát hiện giao dịch bất thường

## 1. Thông tin rủi ro
- **Mã hồ sơ rủi ro:** `RR-009`
- **Phân loại (Category):** Rui ro gian lan
- **Mức độ rủi ro vốn có (Inherent Level):** Cao
- **Mức độ rủi ro còn lại (Residual Level):** Trung binh
- **Đơn vị quản lý (Owner Unit ID):** `DV-OPS`
- **Nguồn gốc dữ liệu:** SYNTHETIC
- **Trạng thái xác minh:** VERIFIED

## 2. Diễn biến cấu trúc rủi ro
- **Mô tả chung:** Luật phát hiện gian lận không được cập nhật
- **Nguyên nhân (Cause):** Ngưỡng cảnh báo không phù hợp
- **Sự kiện rủi ro (Event):** Giao dịch nghi ngờ không bị chặn kịp thời
- **Tác động / Hậu quả (Impact):** Tổn thất tài chính và uy tín

## 3. Kiểm soát liên quan (Mitigating Controls)
- [[KS-009 - Hiệu chỉnh luật phát hiện giao dịch gian lận]]
  - **Mối quan hệ:** `MITIGATES`
  - **Trích dẫn bằng chứng:** Dữ liệu mô phỏng: hiệu chỉnh luật giảm bỏ sót giao dịch bất thường
  - **Độ tin cậy:** 1.0 | **Trạng thái:** `VERIFIED`

## 4. Sự kiện rủi ro liên quan (Observed Risk Events)
- [[SK-009 - Giao dịch bất thường chỉ bị phát hiện sau khi khách hàng khiếu nại]]
  - **Mối quan hệ:** `OBSERVED_AS`
  - **Trích dẫn bằng chứng:** Dữ liệu mô phỏng: sự kiện không phát hiện bất thường
  - **Độ tin cậy:** 1.0 | **Trạng thái:** `VERIFIED`

---
[[Home| Trang chủ Wiki]]
