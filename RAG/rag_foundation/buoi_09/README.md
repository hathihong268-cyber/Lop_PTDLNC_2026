# RAG Foundation — Buổi 09: Multi-Query & Parent–Child Retrieval

---

## 1. Mục Tiêu & Sự Khác Biệt Giữa Buổi 08 và Buổi 09

| Tiêu chí | Buổi 08 (Advanced RAG: Hybrid + Reranking) | Buổi 09 (Multi-Query & Parent–Child Retrieval) |
| :--- | :--- | :--- |
| **Số lượng truy vấn** | Đơn truy vấn ($Q_0$ duy nhất) | **Fan-out đa truy vấn** ($Q_0$ gốc + $Q_1..Q_n$ biến thể góc nhìn pháp lý) |
| **Đơn vị lập chỉ mục** | Child Chunks ($300 - 800$ chars) | **Child Chunks** trong ChromaDB + **Parent Documents Registry** |
| **Tầng Hợp nhất (Fusion)** | 1 tầng Inner RRF (BM25 + Semantic) | **2 tầng Fusion**: Inner RRF per query $\to$ **Cross-Query RRF trên Child hits** |
| **Đơn vị trả về & Rerank** | Child Chunks | **Parent Document hoàn chỉnh** ($1,000 - 6,000$ chars, trọn vẹn Điều khoản) |
| **Rerank Input Pair** | `(Q0, Child Text)` | **`(Q0, Parent Text)`** — Giữ nguyên ngữ cảnh Điều luật, chống cắt cụt bảng biểu |
| **Ngân sách gọi API LLM** | 1 Generation Call | **Tối đa 2 Generation Calls** (1 Query Expansion + 1 Answer Gen nếu qua Gate) |
| **Bảo vệ ranh giới pháp lý** | Cắt theo chunk đơn lẻ | **Retrieve Child $\to$ Return Parent**: Mở rộng toàn bộ Điều khoản chứa Child hit |

---

## 2. Sơ Đồ Kiến Trúc Pipeline Đa Tầng

```
                                ┌→ Q0: Câu hỏi gốc (Original Intent) ────────────┐
Câu hỏi gốc → Multi-query ──────┼→ Q1: Diễn đạt lại (Paraphrase) ───────────────┤
                                ├→ Q2: Thuật ngữ pháp lý chính xác ─────────────┤
                                └→ Q3: Khía cạnh pháp lý bổ sung ───────────────┘
                                                ↓
                              Hybrid Retrieval cho từng query (BM25 + Semantic)
                                                ↓
                              Cross-Query RRF hợp nhất trên Child hits
                                                ↓
                              Child → Parent Mapping & Parent Aggregation
                                                ↓
                              Cross-Encoder Rerank Parent bằng câu hỏi gốc Q0
                                                ↓
                              Evidence Gate (≥ 0.5) & Context Budgeting
                                                ↓
                              Gemini 2.5 Flash sinh câu trả lời kèm Citations [P1]
```

---

## 3. Bốn Chế Độ Thực Thi (4 Modes Comparison)

Hệ thống Buổi 09 hỗ trợ 4 chế độ định tuyến linh hoạt:

1. **`single_flat` (Baseline Buổi 08):**
   - $Q_0 \to$ Single Hybrid (BM25 + Semantic) $\to$ Rerank Child bằng $Q_0 \to$ Trả về Child Chunks.
2. **`multi_flat` (Multi-Query Flat):**
   - $Q_0..Q_n \to$ Per-query Hybrid $\to$ Cross-Query RRF trên Child $\to$ Rerank Child bằng $Q_0 \to$ Trả về Child Chunks.
3. **`single_parent` (Single Parent-Child):**
   - $Q_0 \to$ Single Hybrid $\to$ Child-to-Parent Lookup $\to$ Parent Aggregation & Budget $\to$ Rerank Parent bằng $Q_0$.
4. **`multi_parent` (Full Pipeline Buổi 09):**
   - $Q_0..Q_n \to$ Per-query Hybrid $\to$ Cross-Query RRF $\to$ Child-to-Parent Lookup $\to$ Parent Aggregation & Budget $\to$ Rerank Parent bằng $Q_0$.

---

## 4. Cấu Trúc Thư Mục & Thiết Lập Môi Trường

```
rag_advanced/buoi_09/ (hoặc rag_foundation/buoi_09/)
├── .env.example                # File mẫu cấu hình biến môi trường
├── requirements.txt            # Danh mục thư viện phụ thuộc
├── hierarchical_rag.py         # Module cốt lõi: Hierarchy, Multi-Query, RRF, Aggregation, Rerank
├── ui_helpers.py               # Helper thuần Python cho Streamlit & Unit tests
├── evaluate.py                 # Engine đánh giá chất lượng 4 chế độ (Retrieval-only)
├── app.py                      # Giao diện Web Streamlit 5 Tabs tương tác cao
├── SPEC_buoi_09.md             # Đặc tả kỹ thuật chi tiết
├── README.md                   # Hướng dẫn kỹ thuật và vận hành
├── eval/
│   └── questions.json          # Bộ câu hỏi benchmark kèm nhãn kiểm thử
├── reports/
│   └── latest_report.json      # Báo cáo đánh giá hiệu năng mới nhất
├── storage/
│   ├── chroma/                 # ChromaDB Vector Storage (cố định strategy hierarchical)
│   ├── hierarchy/              # Hierarchy Registry (children.json, parents.json, manifest.json)
│   └── huggingface/            # Cache offline cho Cross-Encoder BAAI/bge-reranker-v2-m3
└── tests/                      # Suite 73 unit tests (100% offline, 0 network)
```

### Cấu hình `.env`
Tạo file `.env` tại thư mục gốc với các thông số chuẩn hóa:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
EMBEDDING_MODEL=text-embedding-004
GENERATION_MODEL=gemini-2.5-flash
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
RERANK_DEVICE=cpu
RERANK_MIN_SCORE=0.5
MULTI_QUERY_COUNT=3
PER_QUERY_CANDIDATES=12
PARENT_CANDIDATES=10
FINAL_PARENT_TOP_K=3
PARENT_MAX_CHARS=6000
TOTAL_CONTEXT_MAX_CHARS=8000
```

---

## 5. Hierarchy Registry & Quản Lý Cấu Trúc Pháp Lý

Hierarchy Builder phân giải **318 child chunks** thành **27 Parent Documents** mà không làm thay đổi hay cắt cụt văn bản:
- **Thứ tự ưu tiên trích xuất Điều/Chương:**
  1. Metadata `article` có sẵn từ chunking Buổi 05.
  2. Heading markdown `# Điều X` tại đầu chunk text.
  3. Cơ chế Carry-forward trong cùng một file PDF (`source`).
  4. Fallback: `document_fallback` (gắn cờ `ambiguous=True`).
- **Phân đoạn Parent Window:** Nếu một Điều luật vượt quá `PARENT_MAX_CHARS` (6,000 ký tự), hệ thống tự động chia thành các cửa sổ liên tiếp `w01`, `w02` tại đúng ranh giới của child chunks (không bao giờ cắt giữa chừng một chunk).
- **Tính toàn vẹn (Invariant):** Tổng số child chunks trong registry = 318; mỗi child thuộc về đúng 1 parent document duy nhất.

---

## 6. Công Thức Hợp Nhất Đa Tầng (Multi-Tier Fusion)

### A. Inner RRF (Per-Query Hybrid Fusion)
Với mỗi câu hỏi $q \in \{Q_0, Q_1..Q_n\}$:
$$\text{inner\_rrf}(c) = \frac{1.0}{k_{\text{inner}} + \text{rank}_{\text{BM25}}(c)} + \frac{1.0}{k_{\text{inner}} + \text{rank}_{\text{semantic}}(c)}$$

### B. Cross-Query RRF (Fusion trên Fused Child Hits)
Hợp nhất kết quả từ tất cả các nhánh truy vấn:
$$\text{multi\_query\_rrf}(c) = \sum_{q \in Q(c)} \frac{W(q)}{k_{\text{cross}} + \text{rank}_q(c)}$$
Trong đó:
- $W(Q_0) = 1.5$ (ưu tiên câu hỏi gốc của người dùng).
- $W(Q_i) = 1.0$ ($i \ge 1$, các biến thể mở rộng).
- $k_{\text{cross}} = 60$.

### C. Parent Aggregation Score
Tính điểm cho Parent Document $P$ từ tối đa `PARENT_SCORE_CHILD_LIMIT` (=2) child chunks có điểm cao nhất:
$$\text{parent\_rrf\_score}(P) = \sum_{c \in \text{Top2}(P)} \text{multi\_query\_rrf}(c)$$

---

## 7. Rerank Parent & Evidence Gate

1. **Cross-Encoder Pair:** `(Q0, Parent Text)` — Tuyệt đối không dùng các query biến thể $Q_1..Q_n$ để rerank.
2. **Sigmoid Normalization:**
   $$\text{parent\_rerank\_score} = \frac{1}{1 + e^{-\text{raw\_logit}}}$$
3. **Evidence Gate:** Chỉ chấp nhận các Parent Document có $\text{parent\_rerank\_score} \ge \text{RERANK\_MIN\_SCORE}$ (0.5).
4. **Context Budgeting:** Cắt ngữ cảnh tại ranh giới Parent Documents sao cho tổng độ dài $\le 8,000$ ký tự.

---

## 8. Hướng Dẫn Sử Dụng CLI & Streamlit

Tất cả các lệnh CLI được thực thi qua script venv:

```powershell
# 1. Kiểm tra trạng thái hệ thống (Read-only)
.\rag_foundation\buoi_05\.venv\Scripts\python.exe .\rag_foundation\buoi_09\hierarchical_rag.py status

# 2. Xây dựng Hierarchy Registry từ 318 chunks
.\rag_foundation\buoi_05\.venv\Scripts\python.exe .\rag_foundation\buoi_09\hierarchical_rag.py build-hierarchy

# 3. Mở rộng truy vấn (Multi-Query Expansion)
.\rag_foundation\buoi_05\.venv\Scripts\python.exe .\rag_foundation\buoi_09\hierarchical_rag.py expand-query --question "Điều 8 quy định nhu cầu vốn nào không được cho vay?"

# 4. Truy xuất Parent Documents (Retrieval Only)
.\rag_foundation\buoi_05\.venv\Scripts\python.exe .\rag_foundation\buoi_09\hierarchical_rag.py parent-retrieve --question "Điều kiện vay vốn ngân hàng?"

# 5. So sánh đối chuẩn 4 chế độ (Retrieval Only)
.\rag_foundation\buoi_05\.venv\Scripts\python.exe .\rag_foundation\buoi_09\hierarchical_rag.py compare --question "Thời hạn cho vay và cơ cấu nợ?"

# 6. Hỏi đáp Advanced RAG toàn diện (Full Pipeline)
.\rag_foundation\buoi_05\.venv\Scripts\python.exe .\rag_foundation\buoi_09\hierarchical_rag.py query --question "Điều kiện vay vốn theo Thông tư 39?" --mode multi_parent

# 7. Chạy đánh giá Benchmark toàn diện
.\rag_foundation\buoi_05\.venv\Scripts\python.exe .\rag_foundation\buoi_09\evaluate.py

# 8. Khởi chạy Ứng dụng Web Streamlit
.\rag_foundation\buoi_05\.venv\Scripts\python.exe -m streamlit run .\rag_foundation\buoi_09\app.py --server.port 8501
```

---

## 9. Báo Cáo Đánh Giá Hiệu Năng Đối Chuẩn (Benchmark Evaluation)

Kết quả thực thi `evaluate.py` trên 5 câu hỏi kiểm thử chuẩn hóa:

| Chế độ (Mode) | Parent Recall@K | Child Recall@K | MRR@K | nDCG@K | Latency P50 | Context Chars |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`single_flat`** | 93.33% | 46.00% | 0.6667 | 0.6000 | 9,193.5 ms | 2,199.2 chars |
| **`multi_flat`** | 93.33% | 46.00% | 0.6667 | 0.6000 | 22,194.2 ms | 2,199.2 chars |
| **`single_parent`** | 90.00% | 43.00% | **1.0000** | **0.9226** | **7,147.5 ms** | 4,593.0 chars |
| **`multi_parent`** | 90.00% | 43.00% | **1.0000** | **0.9226** | 10,040.3 ms | 4,869.2 chars |

> [!NOTE]
> - Chế độ `single_parent` và `multi_parent` đạt điểm **MRR@K = 1.0000** và **nDCG@K = 0.9226**, chứng minh các Parent Document đúng trọng tâm luôn được đưa lên vị trí Top 1 sau khi Rerank.
> - Ngữ cảnh Parent ($4,500 - 4,800$ chars) cung cấp trọn vẹn toàn văn Điều luật giúp LLM không bị ảo giác trích dẫn.

---

## 10. Xử Lý Sự Cố (Troubleshooting)

1. **Lỗi `hierarchy_not_ready`:**
   - *Nguyên nhân:* Thư mục `storage/hierarchy` chưa có file `manifest.json` hoặc fingerprint không khớp.
   - *Khắc phục:* Chạy lệnh `python hierarchical_rag.py build-hierarchy` hoặc bấm nút tại Sidebar Streamlit.
2. **Lỗi `collection_not_ready`:**
   - *Nguyên nhân:* Chroma collection chưa được lập chỉ mục vector.
   - *Khắc phục:* Chạy `python advanced_rag.py prepare-semantic --strategy hierarchical`.
3. **Cảnh báo `ambiguous_hierarchy_fallback`:**
   - *Nguyên nhân:* Chunk không chứa số hiệu Điều khoản và không kế thừa được từ ngữ cảnh trước đó.
   - *Xử lý:* Hệ thống tự động gắn cờ `ambiguous=True` và gom vào Parent `doc_fallback` an toàn.

---

## 11. Tuyên Bố Từ Chối Trách Nhiệm Pháp Lý

> [!WARNING]
> Hệ thống RAG này được xây dựng cho mục đích nghiên cứu công nghệ, thử nghiệm kiến trúc phân cấp retrieval và hỗ trợ tra cứu thông tin học tập. Các câu trả lời được tổng hợp tự động từ văn bản quy phạm pháp luật và **không cấu thành ý kiến tư vấn pháp lý chính thức**. Người dùng cần đối chiếu với văn bản pháp luật gốc do Ngân hàng Nhà nước Việt Nam ban hành trước khi áp dụng vào nghiệp vụ thực tế.
