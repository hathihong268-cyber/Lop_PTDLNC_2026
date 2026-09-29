# TÀI LIỆU ĐẶC TẢ KỸ THUẬT (SPECIFICATION) — BUỔI 09
## Multi-query Retrieval & Parent-Child Hierarchical Retrieval cho Văn bản Pháp luật Ngân hàng

---

## 1. Mục Tiêu & Sự Khác Biệt Giữa Buổi 08 và Buổi 09

### 1.1. Bối cảnh & Mục tiêu
Buổi 08 đã thiết lập kiến trúc **Two-Stage Advanced RAG** (Hybrid BM25 + Dense Semantic Retrieval, hợp nhất thứ hạng bằng RRF và tái sắp xếp bằng Cross-Encoder Reranker). Tuy nhiên, trên tập dữ liệu văn bản quy phạm pháp luật ngân hàng, hệ thống vẫn gặp hai hạn chế lớn:
1. **Truy vấn đơn biến thể (Single Query Limitation):** Câu hỏi người dùng thường mang tính tổng quát hoặc sử dụng ngôn ngữ đời thường, chưa bao quát được toàn bộ thuật ngữ pháp lý chính xác (ví dụ: "cơ cấu nợ" vs "điều chỉnh kỳ hạn trả nợ", "gia hạn nợ"). Chỉ dùng một câu hỏi gốc $Q_0$ dễ bỏ sót tài liệu liên quan trong tầng retrieval lexical (BM25) và semantic.
2. **Ngữ cảnh bị phân mảnh (Fragmented Chunk Context):** Các chunk con (child chunks ở cấp Khoản, Điểm) tuy tối ưu cho việc tính toán độ tương đồng cosine và BM25, nhưng khi đưa vào LLM để sinh câu trả lời thì bị thiếu bức tranh ngữ cảnh toàn cục của **Điều luật (Article)** hoặc **Chương (Chapter)** (ví dụ: điều kiện tiên quyết, chủ thể áp dụng ở Khoản 1 bị mất khi chỉ trúng Điểm b Khoản 3).

Buổi 09 mở rộng kiến trúc thành **Hierarchical & Multi-Query Advanced RAG** giải quyết triệt để 2 bài toán trên:
- Tầng mở rộng truy vấn: Sinh các biến thể câu hỏi đa khía cạnh ($Q_0, Q_1, Q_2, Q_3$).
- Tầng hợp nhất đa biến thể: Cross-query Reciprocal Rank Fusion.
- Tầng liên kết thứ bậc cha - con: Ánh xạ từ các child chunks trúng tuyển sang **Parent Document (Điều/Chương)**, gộp ngữ cảnh hoàn chỉnh trước khi Rerank và Generation.

### 1.2. Bảng so sánh Buổi 08 và Buổi 09
| Tiêu chí | Buổi 08 (Advanced RAG) | Buổi 09 (Hierarchical & Multi-Query) |
|---|---|---|
| **Số lượng truy vấn** | Duy nhất 1 câu hỏi gốc ($Q_0$) | $Q_0$ gốc + $N$ biến thể ($Q_1, Q_2, Q_3$) |
| **Quy trình Retrieval** | Truy xuất 1 lần cho $Q_0$ | Truy xuất độc lập cho từng query variant |
| **Tầng Fusion** | 1 tầng: RRF kết hợp BM25 + Semantic | 2 tầng: Tầng 1 (BM25 + Semantic/query), Tầng 2 (Cross-Query RRF) |
| **Đơn vị tìm kiếm** | Chunk phẳng (Flat child chunk) | Tìm kiếm trên Child chunk, mở rộng sang Parent Document |
| **Đơn vị Rerank** | Rerank các child chunk nhỏ | Rerank toàn bộ Parent Document bằng câu hỏi gốc $Q_0$ |
| **Bằng chứng & Trích dẫn** | Chỉ gồm các child chunk độc lập | Gồm Parent Document context và danh sách Child Anchor Chunks |
| **Chế độ so sánh** | BM25 / Semantic / Hybrid / Rerank | 4 chế độ: `single_flat`, `multi_flat`, `single_parent`, `multi_parent` |
| **Phạm vi tác động** | Độc lập trong `buoi_08` | Độc lập trong `buoi_09`, snapshot baseline Buổi 08 |

---

## 2. Sơ Đồ Pipeline Kiến Trúc Đa Tầng Buổi 09

```text
                           ┌──► Q0: Câu hỏi gốc (weight=1.5) ───────────────┐
User Question ────► Multi-Query ───┼──► Q1: Paraphrase ngữ nghĩa (weight=1.0) ─────┤
                    Expansion      ├──► Q2: Trọng tâm pháp lý (weight=1.0) ─────────┤
                                   └──► Q3: Thuật ngữ chuyên môn (weight=1.0) ──────┘
                                                   │
                                                   ▼
                     ┌────────────────────────────────────────────────────────────┐
                     │ TẦNG 1: Per-Query Hybrid Retrieval (BM25 + Dense Semantic) │
                     │   - Thực thi song song/tuần tự cho từng query variant      │
                     │   - Hợp nhất cục bộ BM25 + Semantic qua RRF Tầng 1         │
                     └─────────────────────────────┬──────────────────────────────┘
                                                   │
                                                   ▼
                     ┌────────────────────────────────────────────────────────────┐
                     │ TẦNG 2: Cross-Query Reciprocal Rank Fusion (Cross-Query RRF)│
                     │   - Hợp nhất ứng viên từ tất cả các query variants         │
                     │   - Tính điểm trọng số: W(q) / (k + rank_q(c))             │
                     │   - Giữ lại trace: matched_by_queries, best_rank           │
                     └─────────────────────────────┬──────────────────────────────┘
                                                   │
                                                   ▼
                     ┌────────────────────────────────────────────────────────────┐
                     │ TẦNG 3: Child-to-Parent Resolution & Parent Aggregation   │
                     │   - Tra cứu Parent ID qua Hierarchy Registry               │
                     │   - Gom nhóm các child hits thuộc cùng một Parent          │
                     │   - Tính Parent Score = sum(Child_Scores) + Coverage_Bonus │
                     │   - Ghép toàn văn Parent Document (có context budget cap)  │
                     └─────────────────────────────┬──────────────────────────────┘
                                                   │
                                                   ▼
                     ┌────────────────────────────────────────────────────────────┐
                     │ TẦNG 4: Parent Cross-Encoder Reranking (dùng câu hỏi gốc Q0)│
                     │   - Input: Cặp (Q0, ParentDocument.text)                   │
                     │   - Confidence Gate: rerank_score >= 0.50                  │
                     │   - Cắt lấy Top-K Parent Documents cuối cùng (default K=3) │
                     └─────────────────────────────┬──────────────────────────────┘
                                                   │
                                                   ▼
                     ┌────────────────────────────────────────────────────────────┐
                     │ TẦNG 5: Grounded Answer Generation & Citation Mapping      │
                     │   - Prompt cách ly: <<< BEGIN UNTRUSTED CONTEXT DATA >>>   │
                     │   - LLM sinh câu trả lời kèm nhãn bằng chứng [E1], [E2]    │
                     │   - Ánh xạ trích dẫn: [Nguồn: <source>, Điều <art>, tr. <p>]│
                     └────────────────────────────────────────────────────────────┘
```

---

## 3. Bốn Chế Độ So Sánh (Four Operating Modes)

| Mode | Câu hỏi sử dụng | Đơn vị Evidence nạp Rerank / Prompt | Phương thức Reranker | Mục đích đối chuẩn |
|---|---|---|---|---|
| `single_flat` | Chỉ câu hỏi gốc $Q_0$ | Child chunk phẳng (Khoản, Điểm) | Rerank child chunks bằng $Q_0$ | Baseline trực tiếp từ Buổi 08 |
| `multi_flat` | $Q_0$ + các query variants | Child chunk sau Cross-Query RRF | Rerank child chunks bằng $Q_0$ | Đánh giá tác động độc lập của Multi-Query |
| `single_parent` | Chỉ câu hỏi gốc $Q_0$ | Parent Document mở rộng từ child hits | Rerank Parent Documents bằng $Q_0$ | Đánh giá tác động độc lập của Parent-Child |
| `multi_parent` | $Q_0$ + các query variants | Parent Document mở rộng từ cross-query child hits | Rerank Parent Documents bằng $Q_0$ | **Kiến trúc tối ưu hoàn chỉnh của Buổi 09** |

---

## 4. QueryVariant Schema và Quy Trình Validation

### 4.1. Schema của QueryVariant
Mỗi biến thể câu hỏi do LLM sinh ra bắt buộc tuân thủ:
```json
{
  "query_id": "q0",
  "query_text": "Khách hàng cần đáp ứng những điều kiện gì để được vay vốn?",
  "query_type": "original",
  "weight": 1.5
}
```
- `query_id` (`str`): `"q0"`, `"q1"`, `"q2"`, `"q3"`.
- `query_text` (`str`): Chuỗi văn bản không rỗng sau trim, độ dài tối đa `MULTI_QUERY_MAX_CHARS` (mặc định 300 ký tự).
- `query_type` (`str`): Thuộc một trong các loại:
  - `"original"`: Câu hỏi nguyên bản $Q_0$ (trọng số mặc định 1.5).
  - `"paraphrase"`: Diễn đạt lại tương đương ngữ nghĩa.
  - `"legal_focus"`: Nhấn mạnh vào thuật ngữ định danh pháp lý (Điều, Khoản, Thông tư, chủ thể).
  - `"terminology"`: Sử dụng thuật ngữ chuyên môn ngân hàng / tài chính.
- `weight` (`float`): Hệ số trọng số đóng góp trong Cross-query RRF ($W_{q0} = 1.5, W_{var} = 1.0$).

### 4.2. Validation & Fallback
- Nếu LLM không thể sinh biến thể (do lỗi kết nối mạng, hết quota hoặc nội dung vi phạm an toàn), pipeline **bắt buộc fallback an toàn** về danh sách chỉ chứa duy nhất câu hỏi gốc $Q_0$ (`query_type="original"`), ghi nhận cảnh báo `multi_query_fallback_to_original` trong trace mà không được dừng đột ngột hệ thống.

---

## 5. Hierarchy Registry Schema

Hierarchy Registry được xây dựng trước hoặc nạp từ cache `storage/hierarchy/registry_<strategy>.json`:
```json
{
  "source_documents": {
    "TT_39_2016_NHNN.pdf": {
      "document_title": "Thông tư 39/2016/TT-NHNN",
      "total_chunks": 193,
      "parent_keys": [
        "TT_39_2016_NHNN.pdf::Dieu_1",
        "TT_39_2016_NHNN.pdf::Dieu_2",
        "TT_39_2016_NHNN.pdf::Dieu_7"
      ]
    }
  },
  "child_to_parent": {
    "TT_39_2016_NHNN:hierarchical:0010": {
      "parent_id": "TT_39_2016_NHNN.pdf::Dieu_7",
      "source": "TT_39_2016_NHNN.pdf",
      "level": "article",
      "local_order": 1,
      "resolution_method": "metadata_explicit"
    },
    "TT_39_2016_NHNN:hierarchical:0011": {
      "parent_id": "TT_39_2016_NHNN.pdf::Dieu_7",
      "source": "TT_39_2016_NHNN.pdf",
      "level": "article",
      "local_order": 2,
      "resolution_method": "sequential_carry_forward"
    }
  },
  "parents": {
    "TT_39_2016_NHNN.pdf::Dieu_7": {
      "parent_id": "TT_39_2016_NHNN.pdf::Dieu_7",
      "source": "TT_39_2016_NHNN.pdf",
      "level": "article",
      "title": "Điều 7. Điều kiện vay vốn",
      "chapter": "Chương I: QUY ĐỊNH CHUNG",
      "child_chunk_ids": [
        "TT_39_2016_NHNN:hierarchical:0010",
        "TT_39_2016_NHNN:hierarchical:0011",
        "TT_39_2016_NHNN:hierarchical:0012",
        "TT_39_2016_NHNN:hierarchical:0013"
      ],
      "page_start": 4,
      "page_end": 4
    }
  }
}
```

---

## 6. ParentDocument Schema

Khi gom nhóm và nạp toàn văn parent, đối tượng `ParentDocument` tuân thủ:
```json
{
  "parent_id": "TT_39_2016_NHNN.pdf::Dieu_7",
  "source": "TT_39_2016_NHNN.pdf",
  "title": "Điều 7. Điều kiện vay vốn",
  "chapter": "Chương I: QUY ĐỊNH CHUNG",
  "page_start": 4,
  "page_end": 4,
  "full_text": "Điều 7. Điều kiện vay vốn\nTổ chức tín dụng xem xét, quyết định cho vay khi khách hàng có đủ các điều kiện sau đây:\n1. Khách hàng là pháp nhân...\n2. Nhu cầu vay vốn...\n3. Có phương án...\n4. Có khả năng...",
  "text_length": 620,
  "child_count": 4,
  "is_truncated": false
}
```

---

## 7. MultiQueryChildHit và ParentCandidate Schema

### 7.1. Schema của `MultiQueryChildHit` (sau Cross-Query RRF)
```json
{
  "chunk_id": "TT_39_2016_NHNN:hierarchical:0010",
  "source": "TT_39_2016_NHNN.pdf",
  "page_start": 4,
  "page_end": 4,
  "text": "Điều 7. Điều kiện vay vốn...",
  "parent_id": "TT_39_2016_NHNN.pdf::Dieu_7",
  "matched_by_queries": ["q0", "q1", "q2"],
  "cross_query_rrf_score": 0.054231,
  "best_rank": 1
}
```

### 7.2. Schema của `ParentCandidate` (sau Parent Aggregation & Rerank)
```json
{
  "parent_id": "TT_39_2016_NHNN.pdf::Dieu_7",
  "source": "TT_39_2016_NHNN.pdf",
  "title": "Điều 7. Điều kiện vay vốn",
  "page_start": 4,
  "page_end": 4,
  "full_text": "Điều 7. Điều kiện vay vốn\n...",
  "aggregated_score": 0.098412,
  "anchor_child_ids": [
    "TT_39_2016_NHNN:hierarchical:0010",
    "TT_39_2016_NHNN:hierarchical:0011"
  ],
  "anchor_child_count": 2,
  "total_child_count": 4,
  "child_coverage_ratio": 0.50,
  "rerank_score": 0.8924,
  "rerank_rank": 1,
  "accepted": true
}
```

---

## 8. Quy Tắc Hierarchy Resolution và Ambiguous Warning

Do kết quả audit Bước 01 cho thấy 82.1% chunks bị khuyết trường `article` trong metadata `structure`, bộ phân giải cấp bậc phải áp dụng thuật toán 3 bước:
1. **Ưu tiên 1 - Explicit Metadata**: Nếu chunk có `structure.article`, trích xuất số hiệu Điều (ví dụ `"Điều 7"`) và kết hợp với `source` để tạo Parent ID: `<source>::Dieu_<N>`.
2. **Ưu tiên 2 - Heading Regex ở đầu chunk**: Nếu chunk bắt đầu bằng mẫu tiêu đề Điều (`^\s*Điều\s+(\d+)`), ghi nhận mở đầu một Parent mới.
3. **Ưu tiên 3 - Sequential Carry-Forward (Kế thừa đơn điệu theo source)**:
   - Các chunk con tiếp theo (Khoản, Điểm) có số thứ tự `chunk_id` tăng dần trong cùng một `source` sẽ tự động kế thừa `parent_id` của Điều đang mở gần nhất, cho đến khi gặp một Điều mới hoặc hết văn bản.
4. **Xử lý trích dẫn Điều trong văn bản sửa đổi (Ambiguous Warning)**:
   - Khi gặp trường hợp trích dẫn Điều của văn bản khác (như trong `TT_06_2023_NHNN` sửa đổi Điều 8 của `TT_39_2016`), hệ thống kiểm tra `source` và ranh giới:
     - Nếu chunk thuộc Thông tư 06 nhưng có chứa cụm từ trích dẫn `sửa đổi, bổ sung Điều X của Thông tư 39`, Parent ID thuộc về Điều của Thông tư 06 (hoặc tạo alias liên kết chéo), đồng thời kích hoạt cảnh báo: `[HIERARCHY_WARNING] Chunk <chunk_id> contains cited article reference. Assigned to primary parent <parent_id> with cross_reference.`
5. **Chunk mồ côi (Unassigned Chunks)**:
   - Các chunk tiêu ngữ, mở đầu (như 5 chunk metadata `NONE`) không thuộc Điều nào sẽ được gán vào parent đặc biệt: `<source>::Preamble` hoặc giữ độc lập, không ép buộc ghép vào Điều sai lệch.

---

## 9. Công Thức Cross-Query RRF và Parent Aggregation

### 9.1. Công thức Cross-Query Reciprocal Rank Fusion (Tầng 2)
Cho tập biến thể truy vấn $Q = \{q_0, q_1, \dots, q_m\}$ và hằng số làm mượt $k = 60$:
$$\text{Score}_{\text{cross\_rrf}}(c) = \sum_{q \in Q, c \in \text{Top}(q)} \frac{W(q)}{k + \text{Rank}_q(c)}$$
Trong đó:
- $W(q_0) = 1.5$ (ưu tiên câu hỏi gốc), $W(q_i) = 1.0$ cho các biến thể.
- $\text{Rank}_q(c)$ là thứ hạng của child chunk $c$ trong danh sách kết quả Hybrid của truy vấn $q$.

### 9.2. Công thức Parent Score Aggregation
Khi gom các child hits $c \in \text{Hits}(P)$ vào Parent Document $P$:
$$\text{Score}_{\text{parent}}(P) = \sum_{c \in \text{Hits}(P)} \text{Score}_{\text{cross\_rrf}}(c) \times \left(1.0 + \gamma \times \frac{|\text{Hits}(P)|}{|\text{TotalChildren}(P)|}\right)$$
Với $\gamma = 0.2$ là hệ số thưởng độ phủ (coverage bonus), nhằm ưu tiên các Điều luật có nhiều Khoản cùng được kích hoạt bởi các câu hỏi truy vấn.

---

## 10. Hợp Đồng Ngân Sách Ngữ Cảnh (Context Budget) và Trích Dẫn (Citations)

### 10.1. Giới hạn độ dài và Ngân sách Context
- `PARENT_MAX_CHARS = 6000`: Độ dài văn bản tối đa của 1 Parent Document. Nếu một Điều quá dài (vượt 6,000 ký tự), thực hiện cắt tỉa thông minh (giữ lại các anchor child chunks trúng tuyển và tóm lược/cắt bớt các khoản không trúng tuyển).
- `TOTAL_CONTEXT_MAX_CHARS = 16000`: Tổng độ dài tối đa của toàn bộ context đưa vào Prompt Generation. Cắt lấy tối đa `FINAL_PARENT_TOP_K = 3` Parent Documents có điểm rerank cao nhất.

### 10.2. Citation Contract
- Mỗi Parent Document đưa vào context được gán mã bằng chứng `[E1]`, `[E2]`, ...
- Định dạng hiển thị trích dẫn chính thức:
  `[Nguồn: <source>, <title_parent>, tr. <page_start>-<page_end>, các chunks kích hoạt: <chunk_id_1>, <chunk_id_2>]`

---

## 11. Status & Failure Contract

- Lệnh `status` phải hoạt động **hoàn toàn Read-Only**: không tạo mới collection, không ghi tệp registry, không gọi Gemini API và không nạp Cross-Encoder model.
- Khi thiếu API key hoặc model reranker gặp sự cố, hệ thống phải trả mã lỗi rõ ràng (`api_key_missing`, `reranker_unavailable`), tuyệt đối không âm thầm sinh kết quả giả.
- Khi không tìm thấy văn bản phù hợp hoặc điểm tin cậy dưới ngưỡng `RERANK_MIN_SCORE = 0.50`, kích hoạt fallback `insufficient_evidence` mà không gọi LLM generation.

---

## 12. Testability & Dependency Injection

Mọi thành phần của Buổi 09 phải được thiết kế có thể kiểm thử **hoàn toàn offline**:
1. `MultiQueryGenerator`: Nhận `generator_fn` (hỗ trợ Mock LLM sinh cố định $N$ variants).
2. `CrossEncoderReranker`: Nhận `reranker_instance` qua Dependency Injection (hỗ trợ Mock tính điểm số).
3. `ChromaClient`: Nhận `storage_dir` tạm thời (`tempfile.TemporaryDirectory`).
4. `HierarchyRegistry`: Có khả năng khởi tạo trực tiếp từ file fixture JSON `tests/fixtures/hierarchical_sample.json`.

---

## 13. Evaluation Metrics & Acceptance Criteria

### 13.1. Các chỉ số đo lường
Đánh giá trên tập `eval/questions.json` với danh sách $K \in \{1, 3, 5\}$:
- **Hit@K**: Tỷ lệ câu hỏi mà ít nhất 1 chunk/parent liên quan xuất hiện trong Top-K.
- **MRR@K**: Mean Reciprocal Rank của tài liệu liên quan đầu tiên.
- **nDCG@K**: Normalized Discounted Cumulative Gain.
- **Parent Coverage**: Tỷ lệ các child chunks liên quan được bao hàm bên trong Parent trúng tuyển.
- **Latency (ms)**: Thời gian thực thi của từng công đoạn (multi-query generation, per-query retrieval, cross-rrf, parent aggregation, rerank, generation).

### 13.2. Tiêu chí chấp thuận (Acceptance Criteria)
- Chế độ `multi_parent` đạt Hit@3 và nDCG@3 cao hơn hoặc tương đương `single_flat` trên các câu hỏi phức tạp.
- Phát hiện chính xác 100% câu hỏi out-of-scope mà không sinh ảo giác.
- Toàn bộ suite bài kiểm thử offline chạy thành công 100% với thời gian dưới 10 giây.

---

## 14. Xác Nhận Phạm Vi Ghi (Write Scope Confirmation)

- **Cam kết tuyệt đối**: Mọi tệp tin, mã nguồn, cấu hình và storage của Buổi 09 chỉ được ghi duy nhất bên trong thư mục [rag_advanced/buoi_09/](file:///d:/Lop%20PTDLNC%202026/RAG/rag_advanced/buoi_09/).
- Tuyệt đối không chỉnh sửa bất kỳ tệp tin nào thuộc các buổi trước: Buổi 05, Buổi 06, Buổi 07, Buổi 08.
