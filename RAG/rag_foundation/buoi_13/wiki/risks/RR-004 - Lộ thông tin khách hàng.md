---
id: RR-004
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
category: Rui ro cong nghe thong tin
inherent_level: Cao
residual_level: Trung binh
owner_unit_id: DV-IT
---

# RR-004 - Lộ thông tin khách hàng

## 1. Thông tin rủi ro
- **Mã hồ sơ rủi ro:** `RR-004`
- **Phân loại (Category):** Rui ro cong nghe thong tin
- **Mức độ rủi ro vốn có (Inherent Level):** Cao
- **Mức độ rủi ro còn lại (Residual Level):** Trung binh
- **Đơn vị quản lý (Owner Unit ID):** `DV-IT`
- **Nguồn gốc dữ liệu:** SYNTHETIC
- **Trạng thái xác minh:** VERIFIED

## 2. Diễn biến cấu trúc rủi ro
- **Mô tả chung:** Quyền truy cập dữ liệu không được kiểm soát phù hợp
- **Nguyên nhân (Cause):** Cấp quyền vượt nhu cầu công việc
- **Sự kiện rủi ro (Event):** Dữ liệu khách hàng bị truy cập hoặc chia sẻ trái phép
- **Tác động / Hậu quả (Impact):** Vi phạm bảo mật và tổn hại uy tín

## 3. Kiểm soát liên quan (Mitigating Controls)
- [[KS-004 - Rà soát quyền truy cập định kỳ]]
  - **Mối quan hệ:** `MITIGATES`
  - **Trích dẫn bằng chứng:** Dữ liệu mô phỏng: rà soát quyền hạn giảm lộ dữ liệu
  - **Độ tin cậy:** 1.0 | **Trạng thái:** `VERIFIED`

## 4. Sự kiện rủi ro liên quan (Observed Risk Events)
- [[SK-004 - Tài khoản có quyền truy cập dữ liệu vượt phạm vi công việc]]
  - **Mối quan hệ:** `OBSERVED_AS`
  - **Trích dẫn bằng chứng:** Dữ liệu mô phỏng: sự kiện quyền truy cập quá mức
  - **Độ tin cậy:** 1.0 | **Trạng thái:** `VERIFIED`

---
[[Home| Trang chủ Wiki]]
