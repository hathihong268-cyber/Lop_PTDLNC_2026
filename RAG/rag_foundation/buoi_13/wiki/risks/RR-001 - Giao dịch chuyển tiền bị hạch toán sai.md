---
id: RR-001
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
category: Rui ro van hanh
inherent_level: Cao
residual_level: Trung binh
owner_unit_id: DV-OPS
---

# RR-001 - Giao dịch chuyển tiền bị hạch toán sai

## 1. Thông tin rủi ro
- **Mã hồ sơ rủi ro:** `RR-001`
- **Phân loại (Category):** Rui ro van hanh
- **Mức độ rủi ro vốn có (Inherent Level):** Cao
- **Mức độ rủi ro còn lại (Residual Level):** Trung binh
- **Đơn vị quản lý (Owner Unit ID):** `DV-OPS`
- **Nguồn gốc dữ liệu:** SYNTHETIC
- **Trạng thái xác minh:** VERIFIED

## 2. Diễn biến cấu trúc rủi ro
- **Mô tả chung:** Đối soát giao dịch cuối ngày không đầy đủ
- **Nguyên nhân (Cause):** Thiếu đối chiếu giữa hệ thống thanh toán và sổ cái
- **Sự kiện rủi ro (Event):** Giao dịch được ghi nhận sai trạng thái
- **Tác động / Hậu quả (Impact):** Tổn thất tài chính và khiếu nại khách hàng

## 3. Kiểm soát liên quan (Mitigating Controls)
- [[KS-001 - Đối soát tự động giao dịch và sổ cái]]
  - **Mối quan hệ:** `MITIGATES`
  - **Trích dẫn bằng chứng:** Dữ liệu mô phỏng: đối soát tự động giảm nguy cơ hạch toán sai
  - **Độ tin cậy:** 1.0 | **Trạng thái:** `VERIFIED`

## 4. Sự kiện rủi ro liên quan (Observed Risk Events)
- [[SK-001 - Sai lệch trạng thái giao dịch được phát hiện khi đối soát cuối ngày]]
  - **Mối quan hệ:** `OBSERVED_AS`
  - **Trích dẫn bằng chứng:** Dữ liệu mô phỏng: sự kiện đối soát giao dịch
  - **Độ tin cậy:** 1.0 | **Trạng thái:** `VERIFIED`

---
[[Home| Trang chủ Wiki]]
