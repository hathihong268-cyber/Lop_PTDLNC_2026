---
id: RR-002
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
category: Rui ro tin dung
inherent_level: Cao
residual_level: Trung binh
owner_unit_id: DV-CREDIT
---

# RR-002 - Phê duyệt tín dụng vượt thẩm quyền

## 1. Thông tin rủi ro
- **Mã hồ sơ rủi ro:** `RR-002`
- **Phân loại (Category):** Rui ro tin dung
- **Mức độ rủi ro vốn có (Inherent Level):** Cao
- **Mức độ rủi ro còn lại (Residual Level):** Trung binh
- **Đơn vị quản lý (Owner Unit ID):** `DV-CREDIT`
- **Nguồn gốc dữ liệu:** SYNTHETIC
- **Trạng thái xác minh:** VERIFIED

## 2. Diễn biến cấu trúc rủi ro
- **Mô tả chung:** Kiểm tra hạn mức phê duyệt không hiệu lực
- **Nguyên nhân (Cause):** Phân quyền trên hệ thống không cập nhật
- **Sự kiện rủi ro (Event):** Khoản vay được phê duyệt vượt thẩm quyền
- **Tác động / Hậu quả (Impact):** Tăng nợ xấu và vi phạm quy định

## 3. Kiểm soát liên quan (Mitigating Controls)
- [[KS-002 - Kiểm tra hạn mức phê duyệt trên hệ thống]]
  - **Mối quan hệ:** `MITIGATES`
  - **Trích dẫn bằng chứng:** Dữ liệu mô phỏng: kiểm tra hạn mức ngăn phê duyệt vượt thẩm quyền
  - **Độ tin cậy:** 1.0 | **Trạng thái:** `VERIFIED`

## 4. Sự kiện rủi ro liên quan (Observed Risk Events)
- [[SK-002 - Hồ sơ tín dụng được phê duyệt vượt hạn mức của người phê duyệt]]
  - **Mối quan hệ:** `OBSERVED_AS`
  - **Trích dẫn bằng chứng:** Dữ liệu mô phỏng: sự kiện vượt thẩm quyền
  - **Độ tin cậy:** 1.0 | **Trạng thái:** `VERIFIED`

---
[[Home| Trang chủ Wiki]]
