# Buổi 14: Hybrid Search + Reranking + Mini Knowledge Graph

Dự án thực hành nâng cấp hệ thống RAG chuẩn ngân hàng kết hợp:
1. **Hybrid Retrieval**: BM25 (Lexical) + Dense Embedding + RRF Fusion.
2. **Reranking**: Đánh giá lại Top ứng viên bằng mô hình Cross-Encoder trước khi sinh ngữ cảnh.
3. **Evaluation Framework**: Đo lường định lượng Hit@1, Hit@3, Hit@5, MRR trên tập 12 câu hỏi vàng.
4. **Mini Knowledge Graph**: Nạp cấu trúc phân cấp văn bản và 8 quan hệ pháp lý thực tế vào Neo4j.
5. **Unified Retrieval & Graph Hints**: Hàm `retrieve(question, method, top_k)` tích hợp trích xuất gợi ý quan hệ đồ thị.
6. **Interactive Streamlit Web Dashboard**: Giao diện trực quan khám phá đa chiều toàn bộ hệ thống.

---

## 📂 Cấu Trúc Thư Mục

```text
buoi_14/
├── app.py                            # Giao diện Web tương tác Streamlit đa năng
├── src/
│   ├── __init__.py
│   ├── citation.py                   # Định dạng trích dẫn chuẩn từ metadata
│   ├── bm25_retriever.py             # Bộ truy xuất Lexical BM25 tiếng Việt
│   ├── dense_retriever.py            # Bộ truy xuất Vector Embedding kèm Cache
│   ├── hybrid_retriever.py           # Bộ truy xuất Hybrid Search (BM25 + Dense + RRF)
│   ├── reranker.py                   # Tầng Cross-Encoder Reranker (BAAI/bge-reranker-base)
│   └── unified_retriever.py          # Hàm retrieve() thống nhất hỗ trợ cả 4 phương pháp
├── scripts/
│   ├── prepare_corpus.py             # Script chuẩn hóa dữ liệu từ kb+hops
│   ├── baseline_retrieval.py         # Script chạy thử nghiệm Baseline (BM25 vs Dense)
│   ├── hybrid_search.py              # Script chạy thử nghiệm Hybrid Search
│   ├── rerank.py                     # Script chạy Pipeline đầy đủ (Hybrid -> Reranking)
│   ├── compare_retrieval.py          # Script chạy Benchmark đánh giá định lượng 4 cấu hình
│   ├── load_mini_kg.py               # Script nạp Mini Knowledge Graph vào Neo4j
│   └── query_demo.py                 # Script CLI tương tác chính kèm Graph Hints
├── cypher/
│   ├── schema.cypher                 # Khởi tạo Constraints và Indexes trên Neo4j
│   └── demo_queries.cypher           # Các câu truy vấn Cypher mẫu khám phá đồ thị
├── data/
│   ├── processed/
│   │   └── chunks_normalized.csv     # Corpus 720 chunks chuẩn hóa cho retrieval
│   └── eval/
│       └── questions.csv             # Tập 12 câu hỏi vàng đánh giá (EXACT, SEMANTIC, MIXED)
├── cache/
│   └── dense_embeddings_cache.npz    # Cache embeddings 720 chunks (384 dims)
├── outputs/
│   ├── inspection_report.md          # Báo cáo thẩm định dữ liệu & môi trường
│   ├── retrieval_examples.md         # Báo cáo so sánh ví dụ 4 giai đoạn
│   ├── retrieval_comparison.csv      # Bảng kết quả định lượng chi tiết từng câu hỏi
│   ├── evaluation_report.md          # Báo cáo phân tích chuyên sâu Benchmark định lượng
│   └── kg_build_report.md            # Báo cáo thống kê nạp Mini Knowledge Graph Neo4j
├── .streamlit/
│   └── config.toml                   # Cấu hình tối ưu máy chủ Streamlit
├── .venv/                            # Môi trường ảo Python 3.14
├── .env.example                      # File mẫu cấu hình biến môi trường
├── .env                              # Cấu hình kết nối thực tế
├── requirements.txt                  # Danh mục phụ thuộc chuẩn hóa
├── buoi_14.md                        # Hướng dẫn chi tiết bài học
└── README.md                         # Hướng dẫn chạy dự án
```

---

## 🚀 HƯỚNG DẪN CÁC LỆNH CHẠY BUỔI 14 (TỪNG BƯỚC)

### 📌 Bước 1: Kích Hoạt Môi Trường Ảo & Cài Đặt Thư Viện

Mở PowerShell tại thư mục `buoi_14/`:

```powershell
# 1. Kích hoạt môi trường ảo
.venv\Scripts\activate

# 2. Cài đặt toàn bộ dependencies (nếu thiết lập mới)
pip install -r requirements.txt
```

---

### 📌 Bước 2: Chuẩn Hóa Dữ Liệu Nguồn (Corpus Normalization)
Trích xuất và chuẩn hóa 15 văn bản pháp quy từ `kb+hops/` thành 720 chunks:

```powershell
python scripts/prepare_corpus.py
```
*Output sinh ra*: `data/processed/chunks_normalized.csv` (100% chunks có mã định danh duy nhất và metadata chuẩn).

---

### 📌 Bước 3: Nạp Mini Knowledge Graph Vào Neo4j
Đảm bảo Neo4j đang chạy tại `bolt://localhost:7687`, sau đó thực thi:

```powershell
python scripts/load_mini_kg.py
```
*Kết quả nạp*: 15 Nodes `:VanBan`, 720 Nodes `:DieuKhoan`, 720 quan hệ `[:CONTAINS]`, 705 quan hệ `[:NEXT]` và 8 quan hệ pháp lý liên văn bản.

---

### 📌 Bước 4: Chạy Thử Nghiệm Baseline Retrieval (BM25 vs Dense)

So sánh giữa tìm kiếm từ khóa (BM25) và tìm kiếm ngữ nghĩa vector (Dense):

```powershell
python scripts/baseline_retrieval.py --query "Điều 73 Nghị định 46/2023/NĐ-CP quy định về chức danh nào?" --top-k 5
```

---

### 📌 Bước 5: Chạy Thử Nghiệm Hybrid Search (RRF Fusion)

Kết hợp BM25 + Dense qua thuật toán Reciprocal Rank Fusion:

```powershell
python scripts/hybrid_search.py --query "Theo Thông tư 01/2014/TT-NHNN thì trách nhiệm của người áp tải tiền mặt là gì?" --candidate-k 20 --top-k 5
```

---

### 📌 Bước 6: Chạy Pipeline Đầy Đủ (Hybrid Search ➔ Cross-Encoder Reranker)

Thu thập 20 ứng viên từ Hybrid Search, sau đó chấm điểm lại bằng Cross-Encoder `BAAI/bge-reranker-base`:

```powershell
python scripts/rerank.py --query "Theo Thông tư 01/2014/TT-NHNN thì trách nhiệm của người áp tải tiền mặt là gì?" --candidate-k 20 --top-k 5
```

---

### 📌 Bước 7: Chạy Benchmark Đánh Giá Định Lượng (Hit@k & MRR)

Đánh giá định lượng trên 12 câu hỏi vàng (`EXACT_KEYWORD`, `SEMANTIC`, `MIXED`):

```powershell
python scripts/compare_retrieval.py --candidate-k 20 --top-k 5
```
*Output sinh ra*: 
- `outputs/retrieval_comparison.csv`
- `outputs/evaluation_report.md`

---

### 📌 Bước 8: Chạy Truy Vấn Thống Nhất & Trích Xuất Gợi Ý Đồ Thị (GRAPH HINTS)

Sử dụng script CLI đa năng hỗ trợ cả 4 phương pháp và tự động trích xuất các mối quan hệ đồ thị liên quan:

```powershell
# Chạy với phương pháp tối ưu nhất (Hybrid + Rerank)
python scripts/query_demo.py --query "Theo Thông tư 01/2014/TT-NHNN thì trách nhiệm của người áp tải tiền mặt là gì?" --method hybrid_rerank --top-k 5

# Thử nghiệm với các phương pháp khác: bm25, dense, hybrid
python scripts/query_demo.py --query "Điều 73 Nghị định 46/2023/NĐ-CP quy định về chức danh nào?" --method bm25 --top-k 3
python scripts/query_demo.py --query "Quy định về bảo quản và vận chuyển tiền mặt trong kho quỹ" --method dense --top-k 3
python scripts/query_demo.py --query "Quy định về bảo quản và vận chuyển tiền mặt trong kho quỹ" --method hybrid --top-k 3
```

---

### 📌 Bước 9: Khởi Chạy Giao Diện Web Trực Quan (Streamlit Dashboard)

Khởi chạy ứng dụng Web đa tính năng (Truy xuất, So sánh song song, Benchmark Dashboard, Khám phá Neo4j):

```powershell
streamlit run app.py
```
*(Hoặc: `python -m streamlit run app.py`)*

👉 Mở trình duyệt tại: **[http://localhost:8501](http://localhost:8501)**
