---
id: RR-010
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
category: Rui ro bao cao
inherent_level: Trung binh
residual_level: Thap
owner_unit_id: DV-FINANCE
---

# RR-010 - Sai lệch số liệu báo cáo quản trị

## 1. Thông tin rủi ro
- **Mã hồ sơ rủi ro:** `RR-010`
- **Phân loại (Category):** Rui ro bao cao
- **Mức độ rủi ro vốn có (Inherent Level):** Trung binh
- **Mức độ rủi ro còn lại (Residual Level):** Thap
- **Đơn vị quản lý (Owner Unit ID):** `DV-FINANCE`
- **Nguồn gốc dữ liệu:** SYNTHETIC
- **Trạng thái xác minh:** VERIFIED

## 2. Diễn biến cấu trúc rủi ro
- **Mô tả chung:** Dữ liệu nguồn không được đối chiếu
- **Nguyên nhân (Cause):** Thay đổi dữ liệu không có kiểm soát
- **Sự kiện rủi ro (Event):** Báo cáo quản trị có số liệu sai
- **Tác động / Hậu quả (Impact):** Quyết định quản trị sai lệch

## 3. Kiểm soát liên quan (Mitigating Controls)
- [[KS-010 - Đối chiếu dữ liệu nguồn trước khi phát hành báo cáo]]
  - **Mối quan hệ:** `MITIGATES`
  - **Trích dẫn bằng chứng:** Dữ liệu mô phỏng: đối chiếu nguồn giảm sai lệch báo cáo
  - **Độ tin cậy:** 1.0 | **Trạng thái:** `VERIFIED`

## 4. Sự kiện rủi ro liên quan (Observed Risk Events)
- [[SK-010 - Báo cáo quản trị sử dụng dữ liệu nguồn chưa đối chiếu]]
  - **Mối quan hệ:** `OBSERVED_AS`
  - **Trích dẫn bằng chứng:** Dữ liệu mô phỏng: sự kiện sai lệch báo cáo
  - **Độ tin cậy:** 1.0 | **Trạng thái:** `VERIFIED`

---
[[Home| Trang chủ Wiki]]
