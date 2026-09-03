# TÀI LIỆU ĐẶC TẢ KỸ THUẬT (SPECIFICATION) — BUỔI 09
## Multi-query Retrieval và Parent–Child Retrieval cho Văn bản Pháp luật Ngân hàng

---

## 1. Mục Tiêu & Sự Khác Biệt Giữa Buổi 08 và Buổi 09

### 1.1. Bối cảnh & Mục tiêu
Buổi 08 đã hoàn thiện **Advanced RAG Pipeline** (kết hợp BM25 + Semantic Retrieval + RRF Fusion + Cross-Encoder Reranker). Tuy nhiên, trong thực tế xử lý văn bản quy phạm pháp luật ngân hàng, hệ thống vẫn gặp hai bài toán nghẽn:
1. **Đơn biến thể truy vấn (Single Query Limitation):** Một câu hỏi phức tạp của người dùng có thể dùng từ ngữ đời thường, chưa khớp với thuật ngữ chuyên môn hoặc chỉ nhấn mạnh một khía cạnh, dẫn đến việc bỏ sót các điều khoản quan trọng.
2. **Ngữ cảnh bị phân mảnh (Fragmented Chunk Context):** Việc chia nhỏ văn bản thành các chunk nhỏ (ví dụ chỉ chứa một Điểm hoặc Khoản) rất tốt để tính toán độ tương đồng cosine và BM25, nhưng lại thiếu toàn bộ bức tranh của **Điều luật (Article)** hoặc **Chương (Chapter)**, khiến câu trả lời của LLM bị phiến diện hoặc thiếu điều kiện tiên quyết.

### 1.2. Bảng so sánh 8 điểm khác biệt then chốt
| Tiêu chí | Buổi 08 (Advanced RAG) | Buổi 09 (Multi-Query & Parent-Child) |
|---|---|---|
| **Số lượng truy vấn** | Duy nhất 1 câu hỏi gốc ($Q_0$) | $Q_0$ gốc + $N$ biến thể ($Q_1, Q_2, Q_3$) |
| **Quy trình Retrieval** | Retrieval 1 lần | Retrieval độc lập từng query variant |
| **Tầng Fusion** | RRF 1 tầng (hợp nhất BM25 + Semantic) | RRF 2 tầng: Tầng 1 (BM25+Sem/query), Tầng 2 (Cross-query RRF) |
| **Đơn vị tìm kiếm** | Chunk phẳng (Flat chunk) | Tìm kiếm trên Child chunk, mở rộng sang Parent Document |
| **Đơn vị Rerank** | Rerank các child chunk nhỏ | Rerank toàn bộ Parent Document bằng câu hỏi gốc $Q_0$ |
| **Bằng chứng & Trích dẫn** | Chỉ gồm các chunk trúng tuyển | Gồm Parent Document context và các Anchor Child chunk |
| **Trực quan hóa** | Bảng xếp hạng dịch chuyển rank | Ma trận Query Fan-out, Child-to-Parent tree & Rank Movement |
| **Chế độ so sánh** | BM25 / Semantic / Hybrid / Rerank | 4 chế độ: `single_flat`, `multi_flat`, `single_parent`, `multi_parent` |

---

## 2. Kiến Trúc Pipeline Đa Tầng Buổi 09

```text
                           ┌→ Q0: Câu hỏi gốc ───────────────┐
User Question ───► Multi-Query ────┼→ Q1: Paraphrase ngữ nghĩa ──────┤
                  Expansion        ├→ Q2: Trọng tâm pháp lý ─────────┤
                                   └→ Q3: Thuật ngữ chuyên môn ──────┘
                                                  ↓
                                  Hybrid Retrieval (BM25 + Semantic) cho từng query
                                                  ↓
                                  Cross-Query Reciprocal Rank Fusion (RRF)
                                                  ↓
                              Child → Parent Mapping & Parent Aggregation
                                                  ↓
                                Cross-Encoder Reranking Parent bằng Q0
                                                  ↓
                                  Grounded Generation & Citations
```

---

## 3. Bốn Chế Độ So Sánh (Four Operating Modes)

| Mode | Query Sử Dụng | Đơn Vị Evidence | Phương Thức Rerank |
|---|---|---|---|
| `single_flat` | Chỉ câu hỏi gốc $Q_0$ | Child chunk phẳng | Rerank child bằng $Q_0$ (Baseline Buổi 08) |
| `multi_flat` | $Q_0$ + các query variants | Child chunk sau Cross-query RRF | Rerank child bằng $Q_0$ |
| `single_parent` | Chỉ câu hỏi gốc $Q_0$ | Parent Document mở rộng từ child hit | Rerank parent bằng $Q_0$ |
| `multi_parent` | $Q_0$ + các query variants | Parent Document mở rộng từ fused child hits | Rerank parent bằng $Q_0$ (**Mặc định Buổi 09**) |

---

## 4. Đặc Tả Schema và Hợp Đồng Dữ Liệu

### 4.1. QueryVariant Schema
```python
{
    "variant_id": "Q1",                # str: Q0 (gốc), Q1, Q2, Q3
    "query_text": str,                 # str: Nội dung câu truy vấn
    "intent_type": str,                # 'original' | 'paraphrase' | 'legal_focus' | 'terminology'
    "weight": float                    # float: Trọng số RRF (Q0=1.5, Variants=1.0)
}
```

### 4.2. Hierarchy Registry & ParentDocument Schema
```python
{
    "parent_id": "TT_02_2023_NHNN:parent:d04",  # str: ID duy nhất của parent document
    "source": "TT_02_2023_NHNN.pdf",            # str: Tên file văn bản gốc
    "chapter": "Chương I",                      # str | None
    "article": "Điều 4",                        # str: Tên Điều luật chuẩn tắc
    "title": "Phạm vi cơ cấu lại thời hạn trả nợ", # str
    "page_start": 2,                            # int >= 1
    "page_end": 4,                              # int >= page_start
    "full_text": str,                           # str: Toàn bộ nội dung của Điều/Parent (ghép từ các child hoặc raw)
    "child_chunk_ids": ["...:0004", "...:0005"],# list[str]: Danh sách child IDs thuộc parent
    "resolution_method": "structural_heading"   # 'structural_heading' | 'sequential_flow' | 'source_fallback'
}
```

### 4.3. MultiQueryChildHit & ParentCandidate Schema
```python
{
    "parent_id": str,
    "parent_text": str,
    "source": str,
    "page_start": int,
    "page_end": int,
    "article": str,
    "anchor_children": [
        {
            "chunk_id": str,
            "fused_rank": int,
            "cross_query_rrf_score": float,
            "hit_by_queries": ["Q0", "Q1"]
        }
    ],
    "parent_score": float,             # Điểm tổng hợp từ các anchor children
    "rerank_score": float,             # Điểm Sigmoid từ Cross-Encoder
    "rerank_rank": int,
    "rank_change": int
}
```

---

## 5. Quy Tắc Hierarchy Resolution & Fallback Warnings

1. **State Machine Duyệt Tuần Tự (Sequential Document Flow):**
   - Khi quét qua danh sách chunk của một `source` được sắp xếp theo thứ tự số:
     - Nếu gặp chunk có metadata `structure.article` hoặc text mở đầu bằng `Điều X.`, ghi nhận `current_article = "Điều X"`.
     - Tất cả các child chunk kế tiếp (`Khoản Y`, `Điểm Z`) không có metadata `article` sẽ tự động kế thừa `current_article`.
2. **Phân biệt Viện Dẫn (Cross-reference vs. Heading):**
   - Regex nhận diện heading phải yêu cầu `Điều X` nằm ở vị trí đầu dòng (`^Điều\s+\d+`) hoặc sau dấu xuống dòng, không nhận các cụm từ trích dẫn nằm giữa câu (`...theo quy định tại Điều 7...`).
3. **Fallback & Resolution Method:**
   - Mỗi parent document bắt buộc phải có trường `resolution_method`.
   - Nếu một văn bản không có bất kỳ cấu trúc Chương/Điều nào, gom toàn bộ source thành 1 parent fallback và phát cảnh báo `ambiguous_hierarchy_fallback`.

---

## 6. Công Thức Tính Toán Toàn Phần

### 6.1. Per-Query Hybrid Retrieval (Tầng 1)
Cho mỗi truy vấn $q \in \{Q_0, Q_1, \dots, Q_m\}$:
$$\text{RRF}_1(c, q) = \frac{w_{\text{bm25}}}{k_1 + \text{rank}_{\text{bm25}}(c, q)} + \frac{w_{\text{sem}}}{k_1 + \text{rank}_{\text{sem}}(c, q)}$$

### 6.2. Cross-Query RRF Fusion (Tầng 2)
Hợp nhất các child chunk từ tất cả các truy vấn:
$$\text{CrossQueryRRF}(c) = \sum_{q \in Q} \frac{w_q}{k_{\text{multi}} + \text{rank}_{\text{fused}}(c, q)}$$
*(Trong đó $w_{Q_0} = 1.5$, $w_{Q_i} = 1.0$, $k_{\text{multi}} = 60$)*

### 6.3. Parent Aggregation Score
Một Parent Document $P$ được gán điểm từ top $M$ anchor child có điểm cao nhất của nó:
$$\text{Score}(P) = \sum_{c \in \text{TopM}(P)} \text{CrossQueryRRF}(c)$$

### 6.4. Cross-Encoder Parent Reranking
Đưa cặp `(Q0, ParentDocument.full_text)` vào Cross-Encoder:
$$\text{Logit} = \text{Model}(Q_0, \text{ParentDocument.full_text})$$
$$\text{RerankScore} = \frac{1}{1 + e^{-\text{Logit}}}$$

---

## 7. Context Budget & Citation Contract

1. **Context Budget:**
   - Giới hạn tối đa một Parent Document: `PARENT_MAX_CHARS = 6000`.
   - Giới hạn tổng ngữ cảnh đưa vào LLM Generation: `TOTAL_CONTEXT_MAX_CHARS = 16000`.
   - Giới hạn số lượng Parent đưa vào LLM: `FINAL_PARENT_TOP_K = 3`.
2. **Citation Contract:**
   - Trích dẫn bắt buộc hiển thị: `[Nguồn: <source>, tr. <page_start>-<page_end>, <article>, chunk: <anchor_chunk_id>]`.

---

## 8. Trạng Thái & Xử Lý Lỗi (Status & Failure Contract)

| Trạng Thái | Điều Kiện Kích Hoạt | Hành Vi Hệ Thống |
|---|---|---|
| `answered` | Có ít nhất 1 Parent Document vượt ngưỡng `RERANK_MIN_SCORE` (0.50) | Sinh câu trả lời kèm nhãn trích dẫn `[E1], [E2]` |
| `insufficient_evidence` | Tất cả Parent Document đều có `rerank_score < 0.50` | Chặn generation, trả về thông báo không đủ thông tin |
| `retrieval_only` | Generation API gặp sự cố hoặc trả về rỗng | Trả về evidence đã retrieval mà không có câu trả lời |
| `reranker_unavailable` | Không tải được mô hình Cross-Encoder | Báo lỗi rõ ràng, không âm thầm fallback giả mạo |

---

## 9. Tiêu Chuẩn Kiểm Thử & Nghiệm Thu (Acceptance Criteria)

1. **100% Offline Testing:** Bộ kiểm thử `tests/` phải chạy hoàn toàn offline không gọi API ngoài và không tải trọng số từ Internet.
2. **Chế Độ Dependency Injection:** Hỗ trợ inject mock query generator, mock retriever và mock cross-encoder trong unit tests.
3. **Bảo Vệ Toàn Vẹn Thư Mục:** Không thay đổi bất kỳ file nào trong `rag_foundation/buoi_05` đến `rag_foundation/buoi_08`.
