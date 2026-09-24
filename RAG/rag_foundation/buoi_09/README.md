# RAG Foundation — Buổi 09: Multi-Query & Parent–Child Retrieval

---

## 1. Mục Tiêu & Sự Khác Biệt Giữa Buổi 08 và Buổi 09

Hệ thống Buổi 08 đã giải quyết bài toán tìm kiếm kết hợp (**BM25 + Semantic**) và tinh chỉnh bằng **Cross-Encoder Reranker**. Tuy nhiên, văn bản quy phạm pháp luật ngành ngân hàng có tính chất đặc thù:
- **Đơn truy vấn bỏ sót góc nhìn:** Câu hỏi của người dùng thường mang tính đời thường, chưa đúng thuật ngữ pháp lý chuẩn tắc hoặc chứa nhiều khía cạnh phức tạp.
- **Phân mảnh ngữ cảnh (Fragmented Chunking):** Việc chia nhỏ văn bản thành các child chunk (chỉ chứa một Điểm hoặc Khoản) rất tốt để tính toán độ tương đồng vector, nhưng lại làm mất bức tranh tổng thể của cả Điều luật (Article), khiến mô hình ngôn ngữ lớn (LLM) trả lời thiếu sót điều kiện tiên quyết hoặc phạm vi loại trừ.

Buổi 09 nâng cấp toàn diện lên kiến trúc **Multi-Query Expansion** kết hợp **Retrieve Child, Return Parent**:

| Tiêu chí | Buổi 08 (Advanced RAG: Hybrid + Rerank) | Buổi 09 (Multi-Query & Parent–Child Retrieval) |
| :--- | :--- | :--- |
| **Số lượng truy vấn** | Đơn truy vấn ($Q_0$ duy nhất) | **Fan-out đa truy vấn**: $Q_0$ gốc + $N$ biến thể ($Q_1..Q_n$) |
| **Đơn vị lập chỉ mục** | Flat Chunks ($300 - 800$ ký tự) | **Child Chunks** trong ChromaDB + **Parent Document Registry** |
| **Tầng Hợp nhất (Fusion)** | 1 tầng Inner RRF (BM25 + Semantic) | **2 tầng Fusion**: Inner RRF per query $\to$ **Cross-Query RRF trên Child hits** |
| **Đơn vị trả về cho LLM** | Child Chunks nhỏ lẻ | **Parent Document hoàn chỉnh** ($1,000 - 6,000$ ký tự, trọn vẹn Điều luật) |
| **Rerank Input Pair** | `(Q0, Child Text)` | **`(Q0, Parent Text)`** — Giữ nguyên ngữ cảnh Điều luật, chống cụt bảng biểu |
| **Ngân sách gọi API LLM** | 1 Generation Call | **Tối đa 2 Generation Calls** (1 Query Expansion + 1 Answer Gen nếu qua Gate) |
| **Bảo vệ ranh giới pháp lý** | Cắt theo chunk đơn lẻ | **Retrieve Child $\to$ Return Parent**: Mở rộng toàn bộ Điều khoản chứa Child hit |
| **Chế độ so sánh** | BM25 / Semantic / Hybrid / Rerank | **4 chế độ định tuyến**: `single_flat`, `multi_flat`, `single_parent`, `multi_parent` |

---

## 2. Sơ Đồ Kiến Trúc Pipeline Đa Tầng

```
                               ┌→ Q0: Câu hỏi gốc (Original Intent, trọng số 1.5) ────────┐
User Question → Multi-Query ───┼→ Q1: Diễn đạt lại (Paraphrase, trọng số 1.0) ───────────┤
                Expansion      ├→ Q2: Trọng tâm pháp lý (Legal Focus, trọng số 1.0) ──────┤
                (Gemini API)   └→ Q3: Thuật ngữ chuyên môn (Terminology, trọng số 1.0) ───┘
                                                ↓
                               Hybrid Retrieval (BM25 + Semantic) độc lập cho từng query
                                                ↓
                               Tầng 2: Cross-Query Reciprocal Rank Fusion (RRF) trên Child hits
                                                ↓
                               Child → Parent Mapping & Parent Aggregation (Top-2 Child Score)
                                                ↓
                               Cross-Encoder Reranking toàn bộ Parent Document bằng câu hỏi gốc Q0
                                                ↓
                               Evidence Gate (Sigmoid Score ≥ 0.50) & Context Budgeting (≤ 16,000 chars)
                                                ↓
                               Grounded Generation (Gemini API) kèm Trích Dẫn Pháp Lý [P1, Anchor Chunk]
```

---

## 3. Bốn Chế Độ Thực Thi (Four Operating Modes)

| Mode | Câu Hỏi Sử Dụng | Đơn Vị Bằng Chứng (Evidence) | Phương Thức Rerank | Mục Đích Đối Chuẩn |
| :--- | :--- | :--- | :--- | :--- |
| `single_flat` | Chỉ câu hỏi gốc $Q_0$ | Child Chunk phẳng | Rerank child bằng $Q_0$ | Baseline đối chuẩn Buổi 08 |
| `multi_flat` | $Q_0$ + các query variants | Child Chunk sau Cross-query RRF | Rerank child bằng $Q_0$ | Đo lường hiệu quả Multi-query trên chunk phẳng |
| `single_parent` | Chỉ câu hỏi gốc $Q_0$ | Parent Document mở rộng | Rerank parent bằng $Q_0$ | Đo lường hiệu quả Parent Document trên đơn truy vấn |
| **`multi_parent`** | $Q_0$ + các query variants | Parent Document mở rộng | Rerank parent bằng $Q_0$ | **Mặc định Buổi 09**: Toàn vẹn ngữ cảnh & đa góc nhìn |

---

## 4. Cấu Trúc Thư Mục & Thiết Lập `.env`

```
buoi_09/
├── .env.example                # File mẫu cấu hình biến môi trường
├── requirements.txt            # Danh mục thư viện phụ thuộc
├── hierarchical_rag.py         # Pipeline cốt lõi: Hierarchy, Multi-Query, RRF, Aggregation, Rerank, CLI
├── ui_helpers.py               # Helper thuần Python định dạng dữ liệu cho Streamlit UI & Tests
├── evaluate.py                 # Engine đối chuẩn 4 chế độ (Retrieval-Only Benchmark)
├── app.py                      # Giao diện Web Streamlit 5 Tabs tương tác cao
├── SPEC_buoi_09.md             # Đặc tả kỹ thuật chi tiết
├── README.md                   # Hướng dẫn kỹ thuật và vận hành
├── eval/
│   └── questions.json          # Bộ câu hỏi benchmark chuẩn hóa kèm nhãn ground truth
├── reports/
│   ├── eval_report_*.json      # Báo cáo đánh giá chi tiết theo timestamp
│   └── latest_report.json      # Báo cáo đánh giá mới nhất (ghi atomic)
├── storage/
│   ├── chroma/                 # ChromaDB Vector Storage (cố định strategy hierarchical)
│   ├── hierarchy/              # Hierarchy Registry (children.json, parents.json, manifest.json)
│   └── huggingface/            # Cache offline cho mô hình Cross-Encoder
└── tests/                      # Suite 78 unit tests (100% offline, 0 network, mock injection)
```

### Cấu hình `.env`
Sao chép `.env.example` thành `.env` tại thư mục `buoi_09`:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
EMBEDDING_MODEL=gemini-embedding-2
GENERATION_MODEL=gemini-3.5-flash-lite
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
RERANK_DEVICE=cpu
RERANK_MIN_SCORE=0.5
MULTI_QUERY_COUNT=3
PER_QUERY_CANDIDATES=12
PARENT_CANDIDATES=10
FINAL_PARENT_TOP_K=3
PARENT_MAX_CHARS=6000
TOTAL_CONTEXT_MAX_CHARS=16000
```

---

## 5. Xây Dựng Hierarchy Registry & Xử Lý Cảnh Báo

Lệnh `build-hierarchy` phân giải **318 child chunks** từ 3 thông tư ngân hàng thành **27 Parent Documents**:
- **Thứ tự ưu tiên phân giải cấu trúc (Resolution Precedence):**
  1. `metadata`: Chunk có sẵn metadata `article` chuẩn tắc từ bước chunking.
  2. `heading_inferred`: Chunk mở đầu bằng heading rõ ràng (ví dụ: `^Điều\s+\d+`).
  3. `carried_forward`: Kế thừa số hiệu Điều luật từ chunk liền trước trong cùng file nguồn.
  4. `document_fallback`: Toàn bộ phần mở đầu (căn cứ ban hành, mở đầu) không có điều khoản sẽ gom về một parent dự phòng và phát cảnh báo.
- **Quy tắc phân biệt Viện Dẫn (Cross-reference vs. Heading):** Cụm từ viện dẫn nằm giữa câu như `...theo quy định tại Điều 7...` tuyệt đối không bị nhận diện nhầm thành heading.
- **Ranh giới Cửa sổ Parent (Parent Window Splitting):** Nếu một Điều luật vượt quá `PARENT_MAX_CHARS` (6,000 ký tự), hệ thống tự động ngắt thành các cửa sổ `w01`, `w02` tại đúng ranh giới của child chunks (không bao giờ cắt giữa chừng một chunk).
- **Thống kê cảnh báo trên dữ liệu thật:**
  - `total_sources`: 3
  - `total_children`: 318
  - `total_parents`: 27
  - `ambiguous_count`: 50 (phần mở đầu căn cứ pháp lý của 3 thông tư trước khi vào Điều 1)
  - `oversized_single_children`: 0 (không có child chunk nào vượt 6,000 ký tự)
- **Bảo đảm bất biến (Invariant):** Số child chunks input = Số child chunks trong registry (318); mỗi child thuộc về đúng 1 parent document duy nhất.

---

## 6. Hợp Đồng Multi-Query & Ngân Sách Gọi API (API Call Budget)

1. **Hợp đồng Query Variant:**
   - Bảo toàn câu hỏi gốc: $Q_0$ luôn được giữ nguyên với trọng số ưu tiên cao nhất ($W_{Q_0} = 1.5$).
   - Các biến thể ($Q_1, Q_2, Q_3$): Chuẩn hóa Unicode NFC, loại bỏ trùng lặp, tối đa $N$ biến thể theo cấu hình.
   - Tránh biến thể rỗng: Nếu LLM trả về rỗng hoặc lỗi cú pháp, hệ thống ghi log rõ ràng và sử dụng $Q_0$.
2. **Bộ nhớ đệm trong phiên (In-memory Cache):**
   - Kết quả mở rộng query được lưu cache theo khóa băm SHA-256 của câu hỏi gốc $Q_0$, tránh gọi thừa API khi chạy lặp lại.
3. **Ngân sách gọi API (API Call Budget):**
   - **Generation Calls:** Tối đa 2 cuộc gọi cho một lượt hỏi đáp hoàn chỉnh (1 call sinh query expansion + 1 call sinh câu trả lời cuối cùng nếu vượt Evidence Gate). Trong chế độ benchmark hoặc so sánh `compare`, Generation Calls = 0.
   - **Embedding Calls:** $N + 1$ cuộc gọi (mỗi query variant gọi 1 embedding call cho nhánh semantic retrieval).

---

## 7. Công Thức Tính Toán Toàn Phần (Inner RRF, Cross-Query RRF, Parent Aggregation)

### A. Tầng 1: Per-Query Inner Hybrid Fusion
Cho mỗi query $q \in \{Q_0, Q_1..Q_m\}$:
$$\text{InnerRRF}(c, q) = \frac{1.0}{k_1 + \text{rank}_{\text{bm25}}(c, q)} + \frac{1.0}{k_1 + \text{rank}_{\text{sem}}(c, q)}$$
*(Mặc định $k_1 = 60$)*

### B. Tầng 2: Cross-Query Reciprocal Rank Fusion
Hợp nhất các child chunk từ tập hợp tất cả các nhánh truy vấn:
$$\text{CrossQueryRRF}(c) = \sum_{q \in Q(c)} \frac{W(q)}{k_{\text{multi}} + \text{rank}_{\text{inner}}(c, q)}$$
*(Trong đó $W(Q_0) = 1.5$, $W(Q_i) = 1.0$ cho $i \ge 1$, $k_{\text{multi}} = 60$)*

### C. Tầng 3: Parent Aggregation Score
Một Parent Document $P$ được gán điểm từ top $M$ child chunks có điểm cao nhất của nó (ngăn chặn hiện tượng văn bản dài có nhiều chunk áp đảo):
$$\text{Score}(P) = \sum_{c \in \text{TopM}(P)} \text{CrossQueryRRF}(c)$$
*(Mặc định $M = \text{PARENT\_SCORE\_CHILD\_LIMIT} = 3$)*

---

## 8. Quy Trình Child Retrieval $\to$ Parent Return $\to$ Rerank Parent

1. **Child Retrieval:** Thực hiện tìm kiếm hỗn hợp BM25 + Vector trên tập child chunks phẳng (đảm bảo độ nhạy ngữ nghĩa ở mức chi tiết).
2. **Parent Return:** Ánh xạ các child hits trúng tuyển sang Parent Document tương ứng qua `children.json`.
3. **Reranking Parent bằng $Q_0$:**
   Đưa cặp `(Q0, ParentDocument.text)` vào Cross-Encoder:
   $$\text{Logit} = \text{CrossEncoder}(Q_0, \text{ParentDocument.text})$$
   $$\text{ParentRerankScore} = \frac{1}{1 + e^{-\text{Logit}}}$$
   *Lưu ý:* Tuyệt đối không dùng các query biến thể $Q_1..Q_n$ để rerank, nhằm đảm bảo xếp hạng phản ánh đúng ý định ban đầu của người dùng.
4. **Evidence Gate & Context Budgeting:**
   - Ngưỡng tối thiểu: $\text{ParentRerankScore} \ge 0.50$.
   - Giới hạn Parent: Lấy tối đa `FINAL_PARENT_TOP_K` (=3) parent documents.
   - Giới hạn ký tự: Tổng độ dài toàn bộ parent documents đưa vào prompt $\le \text{TOTAL\_CONTEXT\_MAX\_CHARS}$ (16,000 ký tự).

---

## 9. Hướng Dẫn Lệnh Vận Hành (CLI & Streamlit)

Mọi lệnh được thực thi qua Python virtual environment:

```powershell
# 1. Kiểm tra cấu trúc và tính hợp lệ dữ liệu (không ghi disk)
.\rag_foundation\buoi_05\.venv\Scripts\python.exe .\rag_foundation\buoi_09\hierarchical_rag.py hierarchy-audit

# 2. Xây dựng Hierarchy Registry (ghi atomically vào storage/hierarchy/)
.\rag_foundation\buoi_05\.venv\Scripts\python.exe .\rag_foundation\buoi_09\hierarchical_rag.py build-hierarchy

# 3. Kiểm tra trạng thái Hierarchy Store (Read-Only)
.\rag_foundation\buoi_05\.venv\Scripts\python.exe .\rag_foundation\buoi_09\hierarchical_rag.py hierarchy-status

# 4. Mở rộng truy vấn (Multi-Query Expansion)
.\rag_foundation\buoi_05\.venv\Scripts\python.exe .\rag_foundation\buoi_09\hierarchical_rag.py expand-query --question "Điều 8 quy định những nhu cầu vốn nào không được cho vay?"

# 5. Truy xuất đa biến thể tầng Child (Multi-Child)
.\rag_foundation\buoi_05\.venv\Scripts\python.exe .\rag_foundation\buoi_09\hierarchical_rag.py multi-child --question "Điều kiện vay vốn tổ chức tín dụng?"

# 6. Truy xuất Parent Documents (Retrieve Child, Return Parent)
.\rag_foundation\buoi_05\.venv\Scripts\python.exe .\rag_foundation\buoi_09\hierarchical_rag.py parent-retrieve --question "Quy định cơ cấu lại nợ?" --mode multi_parent

# 7. So sánh đối chuẩn 4 chế độ (Retrieval & Rerank Only, KHÔNG gọi LLM sinh text)
.\rag_foundation\buoi_05\.venv\Scripts\python.exe .\rag_foundation\buoi_09\hierarchical_rag.py compare --question "Thời hạn cho vay và lãi suất?"

# 8. Hỏi đáp RAG toàn trình (End-to-End: Expand -> Retrieve -> Rerank -> Gate -> Gemini Answer)
.\rag_foundation\buoi_05\.venv\Scripts\python.exe .\rag_foundation\buoi_09\hierarchical_rag.py query --question "Nhu cầu vốn nào bị cấm cho vay?" --mode multi_parent

# 9. Chạy benchmark đối chuẩn 4 chế độ (Offline Mock hoặc Live)
.\rag_foundation\buoi_05\.venv\Scripts\python.exe .\rag_foundation\buoi_09\evaluate.py --mock

# 10. Chạy bộ 78 Unit Tests offline (không Internet, không gọi API ngoài)
.\rag_foundation\buoi_05\.venv\Scripts\python.exe -m unittest discover -s .\rag_foundation\buoi_09\tests -p "test_*.py"

# 11. Khởi chạy Ứng dụng Web Streamlit
.\rag_foundation\buoi_05\.venv\Scripts\python.exe -m streamlit run .\rag_foundation\buoi_09\app.py --server.port 8501
```

---

## 10. Giải Thích Các Tham Số Cấu Hình & Context Budget

- `per_query_candidates` (=12): Số lượng child chunks lấy ra cho mỗi nhánh query ở Tầng 1.
- `parent_candidates` (=10): Số lượng Parent Documents tối đa được tổng hợp từ danh sách child hits để đưa vào Cross-Encoder reranking.
- `parent_score_child_limit` (=3): Số lượng child chunks tốt nhất của mỗi parent được dùng để cộng dồn điểm Parent Aggregation.
- `final_parent_top_k` (=3): Số lượng Parent Documents vượt qua Evidence Gate được đưa vào làm ngữ cảnh sinh câu trả lời.
- `parent_max_chars` (=6,000): Giới hạn ký tự tối đa của một Parent Document (ngăn chặn các Điều luật quá dài vượt context window).
- `total_context_max_chars` (=16,000): Ngân sách ký tự tối đa cho toàn bộ bằng chứng đưa vào prompt LLM (đảm bảo độ trễ và tránh vượt quota token).

---

## 11. Chỉ Số Đánh Giá & Giới Hạn Của Tập Nhãn Ground Truth

Engine đánh giá `evaluate.py` đo lường các chỉ số sau trên cả 4 chế độ:
- **Child Recall@K:** Tỷ lệ child chunks đúng mục tiêu được tìm thấy trong top K.
- **Parent Recall@K:** Tỷ lệ Parent Documents đúng mục tiêu được xếp hạng trong top K.
- **MRR@K (Mean Reciprocal Rank):** Đánh giá thứ hạng xuất hiện của tài liệu liên quan đầu tiên ($1/\text{rank}$).
- **nDCG@K:** Đo lường chất lượng xếp hạng phân cấp có tính đến vị trí ưu tiên.
- **Unique Relevant Parents/Sources:** Số lượng văn bản và điều luật độc nhất được bao phủ.
- **Expansion Factor & Context Chars:** Hệ số mở rộng ký tự từ Child sang Parent document.
- **Mean & P50 Latency:** Độ trễ trung bình và trung vị của từng giai đoạn pipeline.

> [!WARNING]
> **Giới hạn kỹ thuật của tập nhãn (Disclaimer):**
> Tập câu hỏi `eval/questions.json` được gắn cờ `needs_human_review = True`. Các nhãn liên quan chưa qua hội đồng chuyên gia pháp lý thẩm định độc lập. Do đó, kết quả đối chuẩn thể hiện sự so sánh tương đối giữa các chiến lược truy xuất trong môi trường thí nghiệm; **tuyệt đối không khẳng định một chế độ chiến thắng tuyệt đối nếu thiếu ground truth chuẩn hóa**.

---

## 12. Hướng Dẫn Xử Lý Sự Cố (Troubleshooting)

1. **Lỗi `hierarchy_not_ready` hoặc Stale Parent ID:**
   - *Nguyên nhân:* Thư mục `storage/hierarchy` chưa được khởi tạo, thiếu file manifest hoặc ID câu hỏi không khớp với registry.
   - *Khắc phục:* Chạy `python hierarchical_rag.py build-hierarchy` để tạo lại registry nguyên tử.
2. **Lỗi `reranker_unavailable` hoặc ModuleNotFoundError (torch):**
   - *Nguyên nhân:* Môi trường máy chủ chưa cài đặt PyTorch hoặc không tải được trọng số Hugging Face.
   - *Khắc phục:* Cài đặt `torch` phù hợp với phần cứng hoặc inject `score_fn` giả lập trong unit tests. Hệ thống sẽ báo lỗi minh bạch, không âm thầm fallback gây sai lệch kết quả.
3. **Độ trễ cao (High Latency):**
   - *Nguyên nhân:* Chạy Cross-Encoder trên CPU với số lượng ứng viên lớn hoặc gọi nhiều biến thể query qua mạng.
   - *Khắc phục:* Giảm `parent_candidates` xuống 5, bật GPU acceleration (`RERANK_DEVICE=cuda`) nếu khả dụng, hoặc sử dụng in-memory query cache.
4. **Vượt ngân sách ngữ cảnh (Context Budget Overflow):**
   - *Nguyên nhân:* Các điều luật dài đưa vào làm vượt `total_context_max_chars`.
   - *Khắc phục:* Bộ lọc `apply_context_budget` sẽ tự động cắt bớt các parent có thứ hạng thấp hơn và phát cảnh báo `dropped_by_context_budget`.

---

## 13. Tuyên Bố Từ Chối Trách Nhiệm Pháp Lý (Disclaimer)

> [!CAUTION]
> Hệ thống phần mềm này được phát triển phục vụ mục đích nghiên cứu khoa học, thử nghiệm kỹ thuật công nghệ RAG nâng cao và hỗ trợ học thuật. Mọi câu trả lời và trích dẫn được trích xuất tự động và **tuyệt đối không cấu thành ý kiến tư vấn pháp lý, tài chính hoặc ngân hàng chính thức**. Người dùng và doanh nghiệp có trách nhiệm đối chiếu trực tiếp với các văn bản quy phạm pháp luật gốc do Ngân hàng Nhà nước Việt Nam ban hành trước khi đưa ra bất kỳ quyết định nghiệp vụ nào.
