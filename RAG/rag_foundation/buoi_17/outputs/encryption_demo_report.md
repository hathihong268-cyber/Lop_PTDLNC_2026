# BÁO CÁO MÃ HÓA BẢO VỆ DỮ LIỆU TẠI CHỖ (DATA-AT-REST ENCRYPTION DEMO)

## 1. Mục tiêu và Phạm vi

Báo cáo này thử nghiệm và minh họa giải pháp mã hóa dữ liệu lưu trữ tại chỗ (Data-at-Rest) cho file Nhật ký kiểm toán ([`buoi_17/outputs/audit_log.jsonl`](file:///c:/Users/admins/Desktop/05_m%E1%BA%ABu/Rag_thuchanh/RAG/rag_foundation/buoi_17/outputs/audit_log.jsonl)) bằng chuẩn mã hóa đối xứng **Fernet** (thuộc thư viện `cryptography`, sử dụng thuật toán AES-128-CBC kèm HMAC-SHA256).

> ⚠️ **LƯU Ý GIẢNG DẠY / HỌC VIÊN:**
> Mô hình mã hóa này chỉ nhằm mục đích minh họa nguyên lý bảo vệ dữ liệu lưu trữ đối với học viên. Đây **KHÔNG** phải là giải pháp sẵn sàng cho môi trường Production. 
> 
> Trong hệ thống thực tế (Production), doanh nghiệp cần trang bị:
> 1. **Dữ liệu trên đường truyền (Data-in-Transit):** TLS 1.3 / mTLS bắt buộc giữa client, API gateway và database.
> 2. **Quản lý khóa tập trung (KMS & HSM):** Sử dụng AWS KMS, GCP KMS, HashiCorp Vault hoặc thiết bị Phần cứng Bảo mật (HSM) thay cho lưu file key cục bộ.
> 3. **Chính sách xoay vòng khóa (Key Rotation):** Tự động tái mã hóa và xoay khóa định kỳ (e.g., 90 ngày).
> 4. **Sao lưu & Kiểm soát truy cập (IAM & Backup):** Phân quyền IAM tối thiểu cho việc đọc key và mã hóa bản sao lưu.

---

## 2. Chi tiết Thực thi và Tuân thủ Bảo mật

* **Quản lý Key:** Key không bị hard-code trong mã nguồn. Key được khởi tạo động và lưu trữ tại file bí mật [`buoi_17/secret.key`](file:///c:/Users/admins/Desktop/05_m%E1%BA%ABu/Rag_thuchanh/RAG/rag_foundation/buoi_17/secret.key).
* **Cấu hình Git:** Đường dẫn `*.key` và `.env` đã được bổ sung vào file [`buoi_17/.gitignore`](file:///c:/Users/admins/Desktop/05_m%E1%BA%ABu/Rag_thuchanh/RAG/rag_foundation/buoi_17/.gitignore) để ngăn chặn lộ chìa khóa lên Repository.
* **Không sửa Dữ liệu nguồn:** File gốc `audit_log.jsonl` được bảo toàn nguyên trạng, kết quả mã hóa được ghi ra file riêng `audit_log.jsonl.enc`.

---

## 3. Bảng Kết quả Kiểm thử Mã hóa & Giải mã

| Tiêu chí Kiểm thử | Chi tiết kết quả | Trạng thái |
| :--- | :--- | :---: |
| **Tệp tin nguồn (Source)** | `audit_log.jsonl` (2179 bytes) | **VALID** |
| **Tệp tin mã hóa (Encrypted)** | `audit_log.jsonl.enc` (3000 bytes) | **PASS** |
| **Tệp chứa Key (.gitignore)** | `secret.key` (Đã chặn bởi `.gitignore`) | **PASS** |
| **Giải mã & Khớp dữ liệu (Decrypt Match)** | Giải mã khớp 100% từng byte dữ liệu gốc | **PASS** |
| **Sẵn sàng cho Production (Production Ready)** | Không (Chỉ sử dụng cho mô phỏng học tập) | **NO** |

---

## 4. Kết luận Trạng thái (Final Status)

```text
ENCRYPT: PASS
DECRYPT MATCH: PASS
PRODUCTION READY: NO
```
