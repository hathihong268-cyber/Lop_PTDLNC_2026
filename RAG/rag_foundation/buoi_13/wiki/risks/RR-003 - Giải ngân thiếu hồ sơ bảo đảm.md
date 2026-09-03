---
id: RR-003
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
category: Rui ro tin dung
inherent_level: Cao
residual_level: Trung binh
owner_unit_id: DV-CREDIT
---

# RR-003 - Giải ngân thiếu hồ sơ bảo đảm

## 1. Thông tin rủi ro
- **Mã hồ sơ rủi ro:** `RR-003`
- **Phân loại (Category):** Rui ro tin dung
- **Mức độ rủi ro vốn có (Inherent Level):** Cao
- **Mức độ rủi ro còn lại (Residual Level):** Trung binh
- **Đơn vị quản lý (Owner Unit ID):** `DV-CREDIT`
- **Nguồn gốc dữ liệu:** SYNTHETIC
- **Trạng thái xác minh:** VERIFIED

## 2. Diễn biến cấu trúc rủi ro
- **Mô tả chung:** Hồ sơ giải ngân chưa đủ điều kiện
- **Nguyên nhân (Cause):** Kiểm tra điều kiện tiên quyết bị bỏ qua
- **Sự kiện rủi ro (Event):** Giải ngân khi thiếu chứng từ bắt buộc
- **Tác động / Hậu quả (Impact):** Khó thu hồi nợ và vi phạm quy trình

## 3. Kiểm soát liên quan (Mitigating Controls)
- [[KS-003 - Checklist điều kiện giải ngân bắt buộc]]
  - **Mối quan hệ:** `MITIGATES`
  - **Trích dẫn bằng chứng:** Dữ liệu mô phỏng: checklist ngăn giải ngân thiếu hồ sơ
  - **Độ tin cậy:** 1.0 | **Trạng thái:** `VERIFIED`

## 4. Sự kiện rủi ro liên quan (Observed Risk Events)
- [[SK-003 - Giải ngân trước khi hoàn thiện chứng từ bảo đảm]]
  - **Mối quan hệ:** `OBSERVED_AS`
  - **Trích dẫn bằng chứng:** Dữ liệu mô phỏng: sự kiện giải ngân thiếu hồ sơ
  - **Độ tin cậy:** 1.0 | **Trạng thái:** `VERIFIED`

---
[[Home| Trang chủ Wiki]]
