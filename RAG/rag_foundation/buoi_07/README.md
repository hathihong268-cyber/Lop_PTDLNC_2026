# BÀI THỰC HÀNH BUỔI 07: RAG FOUNDATION — HOÀN THIỆN RAG PIPELINE VỚI AI AGENT

---

## 1. Mục Tiêu Dự Án

Trong **Buổi 05**, tài liệu văn bản quy phạm pháp luật ngân hàng đã được đọc, trích xuất và chia thành các chunk JSON theo các chiến lược khác nhau (`hierarchical`, `semantic`, `fixed-size`).

Dự án **Buổi 07** xây dựng và hoàn thiện hệ thống **Retrieval-Augmented Generation (RAG)** theo tiêu chuẩn sản xuất, giải quyết triệt để các vấn đề cốt lõi:
- **Kiểm soát tính toàn vẹn dữ liệu (Validation):** Kiểm tra chặt chẽ Data Contract trước khi xử lý.
- **Định danh Vector Store (Collection Identity):** Phân biệt rõ ràng theo strategy, embedding model và dimension.
- **Tạo Embedding thật:** Sử dụng Google GenAI Embedding API, tuyệt đối không dùng vector giả.
- **Lưu trữ Persistent:** Lưu trữ vector và metadata cục bộ qua ChromaDB PersistentClient.
- **Lọc ngưỡng tin cậy (Confidence Gate):** Ngăn chặn bịa đặt (hallucination) bằng cách chặn gọi LLM khi ngữ cảnh không đủ độ tương đồng.
- **Trích dẫn nguồn thật (Citation Mapping):** Trích dẫn chính xác số trang và mã chunk từ metadata thực tế, không để LLM tự tạo nguồn.
- **Kiểm thử tự động (Unit Tests Offline):** 100% test chạy offline không cần API key thật và không kết nối Internet.
- **Giao diện trực quan (Streamlit UI):** Tương tác hỏi đáp và quản trị index dễ dàng.

---

## 2. Quan Hệ Với Buổi 05 và Buổi 06

```
┌─────────────────────────────────────────────────────────────┐
│ BUỔI 05: Dữ liệu nguồn & Môi trường Python                   │
│ - Chunks JSON: rag_foundation/buoi_05/output/chunks/        │
│ - Python .venv: rag_foundation/buoi_05/.venv/               │
└──────────────────────────────┬──────────────────────────────┘
                               │ (Đọc dữ liệu & Dùng .venv)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ BUỔI 07: RAG Pipeline Hoàn Chỉnh                           │
│ - Loader & Validator                                        │
│ - Gemini Embedding API (768 dim)                            │
│ - ChromaDB Persistent Client (storage/chroma/)              │
│ - Semantic Retrieval & Confidence Gate                      │
│ - Grounding Generation & Citation Mapping                   │
│ - Streamlit UI & CLI Tools & Offline Unit Tests             │
└─────────────────────────────────────────────────────────────┘
```

- **Buổi 05:** Là nguồn cung cấp dữ liệu chunks JSON đã được xử lý và môi trường ảo Python. Buổi 07 **không** thực hiện lại OCR, parse PDF hay re-chunking.
- **Buổi 06:** Là tài liệu tham khảo kiến thức demo cơ bản.
- **Buổi 07:** Phát triển độc lập toàn bộ pipeline chuẩn trong thư mục `rag_foundation/buoi_07/`. Tuyệt đối không chỉnh sửa mã nguồn hay dữ liệu của Buổi 05 và Buổi 06.

---

## 3. Sơ Đồ Pipeline RAG

```
[Câu hỏi người dùng]
        │
        ▼
 (1. Query Embedding API) ──> [Vector 768 chiều]
                                    │
                                    ▼
 (2. ChromaDB Cosine Query) ──> [Top-K Evidences kèm Distance]
                                    │
                                    ▼
 (3. Confidence Gate) ────────> [distance <= RAG_MAX_DISTANCE (0.45)?]
                                 ├── KHÔNG: status = "insufficient_evidence"
                                 │          (Không gọi LLM, trả thông báo không đủ thông tin)
                                 │
                                 └── CÓ: status = "answered"
                                      │
                                      ▼
 (4. Grounding Prompt) ───────> Cô lập ngữ cảnh <<< UNTRUSTED CONTEXT >>>
                                      │
                                      ▼
 (5. Gemini Generation API) ──> Câu trả lời thô có nhãn [E1], [E2]
                                      │
                                      ▼
 (6. Citation Mapping) ───────> Thay [E1] bằng [Nguồn: ..., tr. ..., chunk: ...]
                                      │
                                      ▼
 [Kết quả hoàn chỉnh: Answer + Citations Metadata + Evidence List]
```

---

## 4. Cấu Trúc Thư Mục

```text
rag_foundation/buoi_07/
├── .env.example              # File mẫu khai báo các biến môi trường
├── .env                      # File cấu hình biến môi trường thực tế (không commit git)
├── .gitignore                # Bỏ qua .env, cache, chroma storage
├── README.md                 # Tài liệu hướng dẫn chi tiết toàn bộ dự án
├── SPEC_buoi_07.md           # Đặc tả kỹ thuật (Agent Specification)
├── buoi_07.md                # Tài liệu bài học gốc
├── requirements.txt          # Danh sách thư viện trực tiếp của Buổi 07
├── rag.py                    # Module lõi: Loader, Validator, Embedding, Chroma, Query, CLI
├── app.py                    # Giao diện ứng dụng Streamlit UI
├── storage/                  # Thư mục lưu trữ dữ liệu
│   ├── .gitkeep
│   └── chroma/               # ChromaDB Persistent Storage
└── tests/                    # Bộ kiểm thử tự động
    ├── __init__.py
    ├── test_rag.py           # 43 Unit test cases kiểm thử offline
    └── fixtures/
        └── chunks_sample.json # Fixture dữ liệu mẫu giả lập
```

---

## 5. Điều Kiện Đầu Vào & Yêu Cầu Môi Trường

1. **Python Interpreter:** Sử dụng trực tiếp `.venv` của Buổi 05 (Python `>= 3.11`).
2. **Dữ liệu Chunks:** Thư mục `rag_foundation/buoi_05/output/chunks/` chứa các file JSON hợp lệ của các văn bản Thông tư NHNN (`TT_02_2023_NHNN`, `TT_06_2023_NHNN`, `TT_39_2016_NHNN`).

---

## 6. Hướng Dẫn Cài Đặt & Cấu Hình

### 6.1. Cài đặt Thư viện
Từ thư mục gốc `RAG`, chạy lệnh cài đặt vào môi trường ảo Buổi 05:

* **Windows PowerShell:**
  ```powershell
  .\rag_foundation\buoi_05\.venv\Scripts\python.exe -m pip install -r rag_foundation/buoi_07/requirements.txt
  ```
* **Linux/macOS:**
  ```bash
  ./rag_foundation/buoi_05/.venv/bin/python -m pip install -r rag_foundation/buoi_07/requirements.txt
  ```

### 6.2. Cấu hình Biến Môi Trường (`.env`)
Sao chép file `.env.example` thành `.env`:

* **Windows PowerShell:**
  ```powershell
  Copy-Item rag_foundation/buoi_07/.env.example -Destination rag_foundation/buoi_07/.env
  ```
* **Linux/macOS:**
  ```bash
  cp rag_foundation/buoi_07/.env.example rag_foundation/buoi_07/.env
  ```

### 6.3. Ý Nghĩa Các Biến Môi Trường Trong `.env`
| Biến môi trường | Giá trị mặc định | Ý nghĩa & Quy chuẩn |
|---|---|---|
| `GEMINI_API_KEY` | *(Điền API Key của bạn)* | Khóa bí mật gọi Google GenAI API. |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-2` | Mô hình tạo vector embedding văn bản. |
| `GEMINI_EMBEDDING_DIM` | `768` | Số chiều vector embedding (hợp lệ trong khoảng 128 đến 3072). |
| `GEMINI_GENERATION_MODEL` | `gemini-3.5-flash-lite` | Mô hình ngôn ngữ lớn (LLM) tổng hợp câu trả lời. |
| `DEFAULT_TOP_K` | `5` | Số lượng chunk trích xuất mặc định từ retrieval (1 đến 20). |
| `RAG_MAX_DISTANCE` | `0.45` | Ngưỡng khoảng cách Cosine tối đa cho phép chunk đi vào context generation. |

---

## 7. Hướng Dẫn Lệnh Chạy CLI (Dành cho Học Viên)

> **Lưu ý:** Tất cả các lệnh dưới đây đều thực hiện khi terminal đang đứng tại **thư mục gốc `RAG`**.

### 7.1. Lệnh Kiểm tra dữ liệu (Validate)
Duyệt và kiểm tra tính hợp lệ của dữ liệu chunks theo chiến lược mong muốn:
* **Windows PowerShell:**
  ```powershell
  .\rag_foundation\buoi_05\.venv\Scripts\python.exe rag_foundation/buoi_07/rag.py validate --strategy hierarchical
  ```
* **Linux/macOS:**
  ```bash
  ./rag_foundation/buoi_05/.venv/bin/python rag_foundation/buoi_07/rag.py validate --strategy hierarchical
  ```

### 7.2. Lệnh Kiểm tra trạng thái hệ thống (Status - Read-Only)
Kiểm tra thông số cấu hình và số lượng bản ghi trong Collection hiện tại:
* **Windows PowerShell:**
  ```powershell
  .\rag_foundation\buoi_05\.venv\Scripts\python.exe rag_foundation/buoi_07/rag.py status --strategy hierarchical
  ```
* **Linux/macOS:**
  ```bash
  ./rag_foundation/buoi_05/.venv/bin/python rag_foundation/buoi_07/rag.py status --strategy hierarchical
  ```

### 7.3. Lệnh Nạp và Index Dữ Liệu (Index)
Nạp dữ liệu chunks vào ChromaDB Persistent Storage:
* **Windows PowerShell:**
  ```powershell
  .\rag_foundation\buoi_05\.venv\Scripts\python.exe rag_foundation/buoi_07/rag.py index --strategy hierarchical
  ```
* **Linux/macOS:**
  ```bash
  ./rag_foundation/buoi_05/.venv/bin/python rag_foundation/buoi_07/rag.py index --strategy hierarchical
  ```

### 7.4. Lệnh Reset Collection đích rồi Index lại
* **Windows PowerShell:**
  ```powershell
  .\rag_foundation\buoi_05\.venv\Scripts\python.exe rag_foundation/buoi_07/rag.py index --strategy hierarchical --reset
  ```
* **Linux/macOS:**
  ```bash
  ./rag_foundation/buoi_05/.venv/bin/python rag_foundation/buoi_07/rag.py index --strategy hierarchical --reset
  ```

### 7.5. Lệnh Truy Vấn Hỏi Đáp (Query CLI)
* **Windows PowerShell:**
  ```powershell
  .\rag_foundation\buoi_05\.venv\Scripts\python.exe rag_foundation/buoi_07/rag.py query --strategy hierarchical --top-k 5 --question "Cơ cấu lại thời hạn trả nợ được quy định như thế nào?"
  ```
* **Linux/macOS:**
  ```bash
  ./rag_foundation/buoi_05/.venv/bin/python rag_foundation/buoi_07/rag.py query --strategy hierarchical --top-k 5 --question "Cơ cấu lại thời hạn trả nợ được quy định như thế nào?"
  ```

### 7.6. Lệnh Chạy Toàn Bộ Kiểm Thử Tự Động (Unit Tests)
* **Windows PowerShell:**
  ```powershell
  .\rag_foundation\buoi_05\.venv\Scripts\python.exe -m unittest discover -s rag_foundation/buoi_07/tests -v
  ```
* **Linux/macOS:**
  ```bash
  ./rag_foundation/buoi_05/.venv/bin/python -m unittest discover -s rag_foundation/buoi_07/tests -v
  ```

### 7.7. Lệnh Khởi Chạy Giao Diện Streamlit UI
* **Windows PowerShell:**
  ```powershell
  .\rag_foundation\buoi_05\.venv\Scripts\python.exe -m streamlit run rag_foundation/buoi_07/app.py
  ```
* **Linux/macOS:**
  ```bash
  ./rag_foundation/buoi_05/.venv/bin/python -m streamlit run rag_foundation/buoi_07/app.py
  ```
> **Dừng ứng dụng:** Nhấn tổ hợp phím `Ctrl + C` trên terminal để tắt server Streamlit.

---

## 8. Giải Thích Các Khái Niệm Cốt Lõi

1. **Strategy (Chiến lược chunking):** Cách thức chia nhỏ văn bản từ Buổi 05. `hierarchical` giữ ngữ cảnh theo cấu trúc phân cấp (Điều/Khoản), `semantic` cắt theo sự thay đổi ngữ nghĩa, `fixed-size` cắt theo độ dài ký tự cố định.
2. **Collection Identity:** Tên collection trong ChromaDB phân biệt rạch ròi theo quy tắc: `nhnn-<strategy>-<dimension>-<model_hash>`. Giúp lưu trữ độc lập các bộ index mà không bị ghi đè hay lẫn lộn dữ liệu.
3. **Cosine Distance:** Thước đo khoảng cách góc giữa 2 vector. Giá trị nằm trong khoảng $[0, 2]$. Khoảng cách **càng nhỏ thể hiện độ tương đồng ngữ nghĩa càng cao**. Không phải là phần trăm xác suất.
4. **Confidence Gate (`RAG_MAX_DISTANCE`):** Bộ lọc an toàn. Chỉ những đoạn dữ liệu có khoảng cách `distance <= RAG_MAX_DISTANCE` mới được xem là liên quan và được phép gửi vào prompt cho Gemini.
5. **Retrieval-Only:** Trạng thái khi hệ thống đã tìm thấy văn bản liên quan nhưng quá trình gọi LLM gặp sự cố hoặc trả về rỗng. Người dùng vẫn xem được các đoạn văn bản gốc đã truy xuất.
6. **Citation Mapping:** Quá trình code tự động thay thế các nhãn trích dẫn `[E1]`, `[E2]` do LLM sinh ra bằng thông tin nguồn thực tế `[Nguồn: ..., tr. ..., chunk: ...]` lấy trực tiếp từ metadata của ChromaDB.

---

## 9. Kế Hoạch Kiểm Thử Thủ Công (Manual Test Plan)

Sau khi index dữ liệu thật với strategy `hierarchical`, thực hiện kiểm tra với 3 câu hỏi mẫu:

### Câu hỏi A (Thuộc phạm vi tài liệu):
> *"Cơ cấu lại thời hạn trả nợ được quy định như thế nào?"*
- **Kỳ vọng:** Retrieval tìm thấy các chunk liên quan trong Thông tư 02/2023/TT-NHNN (Điều 4), đạt Confidence Gate, câu trả lời giải thích điều kiện cơ cấu nợ kèm trích dẫn `[Nguồn: TT_02_2023_NHNN.pdf, tr. ..., chunk: ...]`.

### Câu hỏi B (Thuộc phạm vi tài liệu):
> *"Việc phân loại nợ và trích lập dự phòng được thực hiện như thế nào?"*
- **Kỳ vọng:** Retrieval tìm thấy các chunk trong Thông tư 02/2023/TT-NHNN hoặc 39/2016/TT-NHNN (Điều 5, Điều 6), đạt Confidence Gate, câu trả lời nêu rõ quy tắc giữ nguyên nhóm nợ và trích lập dự phòng cụ thể.

### Câu hỏi C (Ngoài phạm vi tài liệu):
> *"Ngân hàng nào có lãi suất tiết kiệm cao nhất hôm nay?"*
- **Kỳ vọng:** Các chunk truy xuất được đều có khoảng cách lớn (`distance > 0.45`), không đạt Confidence Gate. Hệ thống chuyển sang trạng thái `insufficient_evidence` và trả về: *"Không tìm thấy đủ thông tin liên quan trong tài liệu đã cung cấp."* — Tuyệt đối không bịa đặt tên ngân hàng hay lãi suất.

---

## 10. Xử Lý Sự Cố Thường Gặp (Troubleshooting)

1. **Lỗi `ModuleNotFoundError` (Thiếu package):**
   - *Nguyên nhân:* Chưa cài đặt requirements hoặc chạy nhầm Python toàn cục ngoài `.venv`.
   - *Khắc phục:* Chạy lại lệnh cài đặt với đúng đường dẫn Python trong `.venv` Buổi 05.
2. **Lỗi `GEMINI_API_KEY chưa được cấu hình`:**
   - *Khắc phục:* Mở file `rag_foundation/buoi_07/.env` và điền khóa API vào sau dấu `=`: `GEMINI_API_KEY=AIzaSy...`
3. **Lỗi `Collection chưa tồn tại` hoặc `0 records`:**
   - *Khắc phục:* Chạy lệnh `index --strategy <strategy>` để nạp dữ liệu vào vector database trước khi thực hiện câu hỏi.
4. **Lỗi `cấu hình không tương thích về strategy/dimension`:**
   - *Khắc phục:* Chạy lại lệnh index với cờ `--reset` để tạo lại collection đúng cấu hình.
5. **Lỗi `Quota / Rate Limit Exceeded` khi gọi Gemini:**
   - *Khắc phục:* Chờ 1 phút để reset hạn mức gọi API miễn phí hoặc kiểm tra lại kết nối mạng.

---

## 11. Giới Hạn và Cảnh Báo An Toàn

> [!WARNING]
> 1. **Không phải tư vấn pháp lý:** Toàn bộ nội dung trả lời từ hệ thống mang tính chất nghiên cứu thực hành công nghệ RAG, không thay thế văn bản quy phạm pháp luật chính thức hoặc tư vấn pháp lý chuyên nghiệp.
> 2. **Hiệu chỉnh ngưỡng tin cậy:** Ngưỡng `RAG_MAX_DISTANCE = 0.45` là giá trị mặc định cho bài học. Trong môi trường thực tế, ngưỡng này cần được tinh chỉnh (calibrate) dựa trên tập dữ liệu đánh giá thực nghiệm.
> 3. **Bảo mật dữ liệu:** Khi thực hiện embedding hoặc generation, nội dung văn bản sẽ được gửi tới Google GenAI API. Chỉ index và truy vấn các tài liệu được phép chia sẻ với dịch vụ bên ngoài.
