# BUỔI 17: SECURE RAG, RBAC DATA GOVERNANCE, AUDIT TRAIL & AI COMPLIANCE GAP ANALYSIS

Dự án Buổi 17 tập trung xây dựng giải pháp RAG bảo mật (Secure RAG), quản trị phân quyền dữ liệu theo vai trò (RBAC), ghi nhận nhật ký kiểm toán (Audit Trail) và mô phỏng đánh giá khoảng trống tuân thủ (Compliance Gap Analysis) cho hệ thống AI trong Ngành Ngân hàng.

---

## 📁 CẤU TRÚC THƯ MỤC NỘP BÀI (SUBMISSION DIRECTORY)

```text
buoi_17/
├── config/
│   └── rbac_policy.json            # Cấu hình chính sách phân quyền RBAC
├── scripts/
│   ├── rbac.py                     # Quản lý chính sách và kiểm tra vai trò RBAC
│   ├── secure_retrieval.py         # Wrapper tái sử dụng SecureRetriever
│   ├── secure_retrieval_adapter.py # Adapter chuẩn hóa schema 9 trường cho SecureRetriever
│   ├── audit_logger.py             # Ghi nhật ký kiểm toán Audit Trail chuẩn JSONL
│   ├── encryption_demo.py          # Demo mã hóa dữ liệu tại chỗ (Fernet AES-128)
│   ├── internal_lookup.py          # Use Case 1: AI Tra cứu Quy định Nội bộ kèm Citations
│   ├── compliance_gap.py           # Use Case 2: AI Compliance Gap Checker 8 bước
│   ├── security_tests.py           # Bộ kiểm thử an toàn thông tin 10 tiêu chí
│   └── final_validation.py         # Script audit toàn bộ dự án
├── outputs/
│   ├── dependency_report.md        # Báo cáo đánh giá phụ thuộc dữ liệu Buổi 14 -> 17
│   ├── rbac_reuse_report.md        # Báo cáo phân tích phân bố RBAC trên 720 chunks
│   ├── rbac_test_report.md         # Báo cáo kết quả kiểm thử phân quyền 5 roles
│   ├── secure_retrieval_test.md    # Báo cáo 4 bài test chứng minh Secure Retrieval
│   ├── audit_log.jsonl             # File nhật ký kiểm toán chứa các Audit Events
│   ├── encryption_demo_report.md   # Báo cáo mô phỏng mã hóa Data-at-Rest
│   ├── internal_lookup_demo.md     # Báo cáo kết quả thử nghiệm AI Tra cứu Quy định
│   ├── gap_input_catalog.md        # Phân loại danh mục 15 văn bản & Data Gap Notice
│   ├── compliance_gap_results.csv  # Kết quả đánh giá Compliance Gap dạng CSV
│   ├── compliance_gap_report.md   # Báo cáo kiến trúc & kết quả Compliance Gap Analysis
│   ├── graph_gap_integration_report.md # Khảo sát Neo4j & đánh giá tích hợp Graph
│   ├── security_test_report.md     # Báo cáo kiểm thử 10 tiêu chí Security
│   └── final_validation_report.md  # Báo cáo audit xác nhận toàn dự án
├── app.py                          # Giao diện Streamlit UI (3 Tabs, Banner, Sidebar RBAC)
├── .env                            # Biến môi trường (API Key, Model name)
├── .gitignore                      # Chặn secret.key, .env, *.enc
└── README.md                       # Tài liệu hướng dẫn dự án
```

---

## 🚀 HƯỚNG DẪN KHỞI CHẠY HỆ THỐNG

### 1. Kích hoạt Môi trường Virtual Environment

```bash
# Windows PowerShell
..\..\..\.venv\Scripts\Activate.ps1
```

### 2. Khởi chạy Giao diện Streamlit UI

```bash
streamlit run app.py --server.port 8501
```
Giao diện sẽ chạy tại địa chỉ: **`http://localhost:8501`**

### 3. Chạy Bộ Kiểm thử An toàn Thông tin (Security Tests)

```bash
python scripts/security_tests.py
```

### 4. Chạy Script Audit toàn bộ dự án (Final Validation)

```bash
python scripts/final_validation.py
```

---

## 🔒 NGUYÊN TẮC BẢO MẬT & QUẢN TRỊ DỮ LIỆU

1. **Tái sử dụng & Bảo toàn Dữ liệu:** Không sửa dữ liệu nguồn `chunks_secure.csv`, tái sử dụng `SecureRetriever` của Buổi 14 qua Adapter.
2. **RBAC Pre-filtering:** Lọc quyền truy cập nghiêm ngặt trước khi trả ứng viên về cho LLM Context, đảm bảo 0% rò rỉ văn bản nhạy cảm.
3. **Audit Trail An toàn:** Ghi nhận mọi yêu cầu (`SUCCESS` và `DENIED`), bảo mật 100% bí mật (không ghi password, API key).
4. **Human-in-the-loop Guardrail:** Mọi kết quả phân tích khoảng trống tuân thủ đều bắt buộc gắn `review_status = NEEDS_HUMAN_REVIEW`.
