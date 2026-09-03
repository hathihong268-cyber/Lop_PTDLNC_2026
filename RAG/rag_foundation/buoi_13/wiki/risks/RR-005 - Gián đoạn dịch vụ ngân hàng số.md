---
id: RR-005
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
category: Rui ro cong nghe thong tin
inherent_level: Cao
residual_level: Trung binh
owner_unit_id: DV-IT
---

# RR-005 - Gián đoạn dịch vụ ngân hàng số

## 1. Thông tin rủi ro
- **Mã hồ sơ rủi ro:** `RR-005`
- **Phân loại (Category):** Rui ro cong nghe thong tin
- **Mức độ rủi ro vốn có (Inherent Level):** Cao
- **Mức độ rủi ro còn lại (Residual Level):** Trung binh
- **Đơn vị quản lý (Owner Unit ID):** `DV-IT`
- **Nguồn gốc dữ liệu:** SYNTHETIC
- **Trạng thái xác minh:** VERIFIED

## 2. Diễn biến cấu trúc rủi ro
- **Mô tả chung:** Hệ thống thanh toán trực tuyến không sẵn sàng
- **Nguyên nhân (Cause):** Kế hoạch năng lực và dự phòng chưa đầy đủ
- **Sự kiện rủi ro (Event):** Dịch vụ ngân hàng số bị gián đoạn
- **Tác động / Hậu quả (Impact):** Mất doanh thu và khiếu nại khách hàng

## 3. Kiểm soát liên quan (Mitigating Controls)
- [[KS-005 - Kiểm thử khả năng chịu tải và chuyển đổi dự phòng]]
  - **Mối quan hệ:** `MITIGATES`
  - **Trích dẫn bằng chứng:** Dữ liệu mô phỏng: kiểm thử dự phòng giảm gián đoạn dịch vụ
  - **Độ tin cậy:** 1.0 | **Trạng thái:** `VERIFIED`

## 4. Sự kiện rủi ro liên quan (Observed Risk Events)
- [[SK-005 - Dịch vụ ngân hàng số gián đoạn trong giờ cao điểm]]
  - **Mối quan hệ:** `OBSERVED_AS`
  - **Trích dẫn bằng chứng:** Dữ liệu mô phỏng: sự kiện gián đoạn dịch vụ
  - **Độ tin cậy:** 1.0 | **Trạng thái:** `VERIFIED`

---
[[Home| Trang chủ Wiki]]
