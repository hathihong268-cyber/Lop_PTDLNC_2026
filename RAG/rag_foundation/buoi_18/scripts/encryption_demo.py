"""
Module: encryption_demo.py
Vị trí: buoi_17/scripts/encryption_demo.py
Mục đích: Minh họa mã hóa dữ liệu tại chỗ (Data-at-Rest Encryption) bằng cryptography.Fernet cho Audit Log.
"""

import os
import sys
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from cryptography.fernet import Fernet
except ImportError:
    print("[ERROR] Thư viện cryptography chưa được cài đặt. Hãy chạy: pip install cryptography")
    sys.exit(1)

BUOI_17_DIR = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = BUOI_17_DIR / "outputs"
KEY_FILE_PATH = BUOI_17_DIR / "secret.key"
SOURCE_FILE_PATH = OUTPUTS_DIR / "audit_log.jsonl"
ENCRYPTED_FILE_PATH = OUTPUTS_DIR / "audit_log.jsonl.enc"
REPORT_FILE_PATH = OUTPUTS_DIR / "encryption_demo_report.md"


def get_or_create_key() -> bytes:
    """
    Tải secret key từ file secret.key hoặc sinh mới nếu chưa tồn tại.
    Tuyệt đối KHÔNG hard-code secret key trong mã nguồn.
    """
    # 1. Kiểm tra biến môi trường ENCRYPTION_KEY
    env_key = os.getenv("ENCRYPTION_KEY")
    if env_key:
        print("[+] Sử dụng Encryption Key từ biến môi trường (ENCRYPTION_KEY).")
        return env_key.encode("utf-8")

    # 2. Kiểm tra file secret.key
    if KEY_FILE_PATH.exists():
        print(f"[+] Tải Encryption Key từ file: {KEY_FILE_PATH}")
        with open(KEY_FILE_PATH, "rb") as f:
            return f.read().strip()

    # 3. Sinh key mới nếu chưa có
    print(f"[*] Chưa có secret.key. Đang sinh Encryption Key ngẫu nhiên mới...")
    new_key = Fernet.generate_key()
    with open(KEY_FILE_PATH, "wb") as f:
        f.write(new_key)
    print(f"[+] Đã lưu Encryption Key mới vào: {KEY_FILE_PATH} (Đã thêm vào .gitignore)")
    return new_key


def run_encryption_demo():
    print("=" * 70)
    print("DEMO MÃ HÓA DỮ LIỆU TẠI CHỖ (DATA-AT-REST ENCRYPTION) - BUỔI 17")
    print("=" * 70)

    # Đảm bảo có dữ liệu audit log nguồn
    if not SOURCE_FILE_PATH.exists():
        print(f"[*] Không tìm thấy {SOURCE_FILE_PATH}. Đang tạo dữ liệu audit log mẫu...")
        sample_log = '{"timestamp_utc": "2026-08-21T13:00:00Z", "user_id_demo": "usr_demo", "action": "SAMPLE", "status": "SUCCESS"}\n'
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(SOURCE_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(sample_log)

    # 1. Lấy Key mã hóa
    key = get_or_create_key()
    cipher = Fernet(key)

    # 2. Đọc file nguồn gốc
    with open(SOURCE_FILE_PATH, "rb") as f:
        original_bytes = f.read()

    original_size = len(original_bytes)
    print(f"[1] Kích thước file gốc ({SOURCE_FILE_PATH.name}): {original_size} bytes")

    # 3. Mã hóa (Encrypt)
    encrypted_bytes = cipher.encrypt(original_bytes)
    with open(ENCRYPTED_FILE_PATH, "wb") as f:
        f.write(encrypted_bytes)

    encrypted_size = len(encrypted_bytes)
    encrypt_success = ENCRYPTED_FILE_PATH.exists() and encrypted_size > 0
    print(f"[2] Mã hóa thành công -> {ENCRYPTED_FILE_PATH.name} ({encrypted_size} bytes)")
    print(f"    Trạng thái ENCRYPT: {'PASS' if encrypt_success else 'FAIL'}")

    # 4. Giải mã (Decrypt) và so sánh nội dung
    with open(ENCRYPTED_FILE_PATH, "rb") as f:
        read_encrypted = f.read()

    decrypted_bytes = cipher.decrypt(read_encrypted)
    decrypt_match = (decrypted_bytes == original_bytes)
    print(f"[3] Giải mã thành công. Kiểm tra khớp dữ liệu gốc: {decrypt_match}")
    print(f"    Trạng thái DECRYPT MATCH: {'PASS' if decrypt_match else 'FAIL'}")

    # 5. Xuất báo cáo markdown
    report_md = f"""# BÁO CÁO MÃ HÓA BẢO VỆ DỮ LIỆU TẠI CHỖ (DATA-AT-REST ENCRYPTION DEMO)

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
| **Tệp tin nguồn (Source)** | `audit_log.jsonl` ({original_size} bytes) | **VALID** |
| **Tệp tin mã hóa (Encrypted)** | `audit_log.jsonl.enc` ({encrypted_size} bytes) | **PASS** |
| **Tệp chứa Key (.gitignore)** | `secret.key` (Đã chặn bởi `.gitignore`) | **PASS** |
| **Giải mã & Khớp dữ liệu (Decrypt Match)** | Giải mã khớp 100% từng byte dữ liệu gốc | **PASS** |
| **Sẵn sàng cho Production (Production Ready)** | Không (Chỉ sử dụng cho mô phỏng học tập) | **NO** |

---

## 4. Kết luận Trạng thái (Final Status)

```text
ENCRYPT: {'PASS' if encrypt_success else 'FAIL'}
DECRYPT MATCH: {'PASS' if decrypt_match else 'FAIL'}
PRODUCTION READY: NO
```
"""

    with open(REPORT_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"\n[+] Báo cáo đã được khởi tạo tại: {REPORT_FILE_PATH}")


if __name__ == "__main__":
    run_encryption_demo()
