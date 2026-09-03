---
id: RR-008
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
category: Rui ro tin dung
inherent_level: Cao
residual_level: Trung binh
owner_unit_id: DV-CREDIT
---

# RR-008 - Định giá tài sản bảo đảm không chính xác

## 1. Thông tin rủi ro
- **Mã hồ sơ rủi ro:** `RR-008`
- **Phân loại (Category):** Rui ro tin dung
- **Mức độ rủi ro vốn có (Inherent Level):** Cao
- **Mức độ rủi ro còn lại (Residual Level):** Trung binh
- **Đơn vị quản lý (Owner Unit ID):** `DV-CREDIT`
- **Nguồn gốc dữ liệu:** SYNTHETIC
- **Trạng thái xác minh:** VERIFIED

## 2. Diễn biến cấu trúc rủi ro
- **Mô tả chung:** Dữ liệu định giá không độc lập hoặc hết hạn
- **Nguyên nhân (Cause):** Thiếu rà soát lại giá trị tài sản
- **Sự kiện rủi ro (Event):** Tài sản bảo đảm được định giá cao hơn thực tế
- **Tác động / Hậu quả (Impact):** Tăng tổn thất khi xử lý nợ

## 3. Kiểm soát liên quan (Mitigating Controls)
- [[KS-008 - Rà soát độc lập định giá tài sản bảo đảm]]
  - **Mối quan hệ:** `MITIGATES`
  - **Trích dẫn bằng chứng:** Dữ liệu mô phỏng: rà soát độc lập giảm sai định giá
  - **Độ tin cậy:** 1.0 | **Trạng thái:** `VERIFIED`

## 4. Sự kiện rủi ro liên quan (Observed Risk Events)
- [[SK-008 - Rà soát phát hiện giá trị tài sản bảo đảm đã hết hiệu lực]]
  - **Mối quan hệ:** `OBSERVED_AS`
  - **Trích dẫn bằng chứng:** Dữ liệu mô phỏng: sự kiện sai định giá tài sản
  - **Độ tin cậy:** 1.0 | **Trạng thái:** `VERIFIED`

---
[[Home| Trang chủ Wiki]]
