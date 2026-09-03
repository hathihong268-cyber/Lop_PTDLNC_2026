---
id: RR-006
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
category: Rui ro gian lan
inherent_level: Cao
residual_level: Trung binh
owner_unit_id: DV-OPS
---

# RR-006 - Gian lận giả mạo yêu cầu chuyển tiền

## 1. Thông tin rủi ro
- **Mã hồ sơ rủi ro:** `RR-006`
- **Phân loại (Category):** Rui ro gian lan
- **Mức độ rủi ro vốn có (Inherent Level):** Cao
- **Mức độ rủi ro còn lại (Residual Level):** Trung binh
- **Đơn vị quản lý (Owner Unit ID):** `DV-OPS`
- **Nguồn gốc dữ liệu:** SYNTHETIC
- **Trạng thái xác minh:** VERIFIED

## 2. Diễn biến cấu trúc rủi ro
- **Mô tả chung:** Nhận diện và xác thực yêu cầu chưa đủ mạnh
- **Nguyên nhân (Cause):** Nhân viên không xác minh kênh liên lạc
- **Sự kiện rủi ro (Event):** Yêu cầu chuyển tiền giả mạo được xử lý
- **Tác động / Hậu quả (Impact):** Tổn thất tài chính

## 3. Kiểm soát liên quan (Mitigating Controls)
- [[KS-006 - Xác thực hai kênh với lệnh chuyển tiền ngoại lệ]]
  - **Mối quan hệ:** `MITIGATES`
  - **Trích dẫn bằng chứng:** Dữ liệu mô phỏng: xác thực hai kênh giảm gian lận chuyển tiền
  - **Độ tin cậy:** 1.0 | **Trạng thái:** `VERIFIED`

## 4. Sự kiện rủi ro liên quan (Observed Risk Events)
- [[SK-006 - Yêu cầu chuyển tiền giả mạo được xử lý trước khi bị thu hồi]]
  - **Mối quan hệ:** `OBSERVED_AS`
  - **Trích dẫn bằng chứng:** Dữ liệu mô phỏng: sự kiện giả mạo chuyển tiền
  - **Độ tin cậy:** 1.0 | **Trạng thái:** `VERIFIED`

---
[[Home| Trang chủ Wiki]]
