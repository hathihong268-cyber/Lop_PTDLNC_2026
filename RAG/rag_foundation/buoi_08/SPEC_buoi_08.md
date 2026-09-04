# Agent Specification - Buổi 08: Advanced RAG (Hybrid Search & Reranking)

## 1. Workspace và Security
- **Vùng được đọc**:
  - `rag_foundation/buoi_05/output/chunks/` (dữ liệu chunks gốc)
  - `rag_foundation/buoi_05/.venv/` (Python virtual environment)
  - Toàn bộ `rag_foundation/buoi_08/`
- **Vùng được ghi**:
  - Chỉ ghi bên trong `rag_foundation/buoi_08/`.
- **Quy định tuyệt đối**:
  - Không sửa bất kỳ file nào của `rag_foundation/buoi_05/`, `rag_foundation/buoi_06/`, hoặc `rag_foundation/buoi_07/`.
  - Không import runtime trực tiếp từ `buoi_07`. Mọi hoạt động của Buổi 08 chạy độc lập trên bản sao nội bộ `rag_foundation/buoi_08/rag.py`.
  - Không hardcode API key / secrets trong source code, logs hay commit vào git.
  - Tuyệt đối không log hoặc xuất ra màn hình giá trị bí mật của `GEMINI_API_KEY`.

## 2. Quan hệ với Buổi 05 và Buổi 07
- **Buổi 05**: Nguồn cung cấp 9 file chunks JSON chuẩn hóa (510 chunks) theo 3 chiến lược (`fixed-size`, `hierarchical`, `semantic`). Buổi 08 chỉ đọc, không re-chunk, không OCR.
- **Buổi 07**: Nguồn baseline về Semantic Vector Search (ChromaDB + Gemini Embeddings `gemini-embedding-2` 768d + Generation `gemini-3.5-flash-lite` + Citation Mapping). Buổi 08 dùng làm mốc so sánh trực tiếp để đánh giá mức độ cải thiện của kiến trúc Hybrid & Reranker.
- **Buổi 08**: Mở rộng RAG thành kiến trúc 2 tầng (Two-stage Retrieval) & Đánh giá định lượng:
  - Tầng 1: Hybrid Retrieval (BM25 sparse search kết hợp Dense Vector search).
  - Fusion: Reciprocal Rank Fusion (RRF).
  - Tầng 2: Re-ranking bằng Cross-Encoder model.
  - Benchmark: Bộ công cụ đánh giá Information Retrieval (Hit@K, MRR, NDCG).

## 3. Data Contract
Mỗi chunk JSON đầu vào bắt buộc phải tuân thủ nghiêm ngặt schema 6 trường:
- `chunk_id` (`str`): Mã định danh duy nhất (không rỗng, không trùng lặp).
- `strategy` (`str`): Thuộc một trong 3 giá trị: `fixed-size`, `semantic`, `hierarchical`.
- `source` (`str`): Tên tài liệu nguồn (VD: `TT_39_2016_NHNN.pdf`).
- `page_start` (`int`): Trang bắt đầu (>= 1, `page_start <= page_end`).
- `page_end` (`int`): Trang kết thúc (>= 1).
- `text` (`str`): Nội dung văn bản của chunk (chuỗi không rỗng sau khi trim).

## 4. BM25 Tokenizer & Retrieval Contract
- **Preprocessing/Tokenizer**:
  - Chuẩn hóa văn bản tiếng Việt: Chuyển chữ thường (lowercase), loại bỏ ký tự đặc biệt vô nghĩa, giữ lại các ký hiệu số, Điều, Khoản, Thông tư (VD: `điều 3`, `khoản 1`, `thông tư 39/2016`).
  - Hỗ trợ tách từ đơn / từ ghép cơ bản, loại bỏ stopwords không mang giá trị ngữ nghĩa pháp lý.
- **Index Storage**:
  - Chỉ mục BM25 được lưu bền vững vào thư mục `storage/bm25/` theo từng `strategy`.
- **Retrieval**:
  - Nhận câu hỏi `query`, trả về Top-K ứng viên (mặc định K = 10) kèm theo điểm số `bm25_score`.
  - Phân loại rõ thứ hạng ban đầu (`bm25_rank`: 1..K).

## 5. Semantic Candidate Contract
- Kế thừa pipeline Vector Search của `rag.py`:
  - Sử dụng Gemini Embedding API (`gemini-embedding-2`, dim=768).
  - Truy vấn ChromaDB Persistent Collection tương ứng với `strategy`.
  - Lấy Top-K ứng viên (mặc định K = 10) kèm `distance` (cosine distance).
  - Phân loại rõ thứ hạng ban đầu (`semantic_rank`: 1..K).

## 6. RRF (Reciprocal Rank Fusion) Contract
- Hợp nhất 2 danh sách ứng viên (BM25 và Semantic) theo thuật toán Reciprocal Rank Fusion:
  $$\text{RRF\_Score}(d) = \sum_{m \in \{\text{BM25}, \text{Semantic}\}} \frac{1}{k + \text{rank}_m(d)}$$
  (với hằng số làm mượt mặc định $k = 60$).
- Giữ lại các metadata gốc của chunk, gán thêm:
  - `bm25_rank` (nếu có trong top BM25, ngược lại None/vô hạn)
  - `semantic_rank` (nếu có trong top Semantic, ngược lại None/vô hạn)
  - `rrf_score` và `rrf_rank` sau khi sắp xếp giảm dần theo điểm RRF.
- Lấy Top-N ứng viên sau fusion (mặc định N = 10) chuyển tiếp sang tầng Reranker.

## 7. Cross-Encoder Reranker Contract
- Mô hình: Sử dụng Cross-Encoder (mặc định `cross-encoder/ms-marco-MiniLM-L-6-v2` hoặc mô hình tương thích đa ngữ/tiếng Việt).
- Input: Cặp câu `(query, candidate_chunk_text)`.
- Output: Điểm tương đồng ngữ cảnh trực tiếp `rerank_score` (Logits/Sigmoid score).
- Sắp xếp lại toàn bộ ứng viên theo thứ tự giảm dần của `rerank_score` và cắt lấy Top-K cuối cùng (mặc định K = 5).
- Hỗ trợ cờ bật/tắt reranker (`enable_reranker=True/False`) để phân tích tác động độc lập.

## 8. Final Evidence và Citation Contract
- **Confidence Gate**:
  - Kiểm tra ngưỡng tin cậy của ứng viên Top-1 sau reranking.
  - Nếu điểm tin cậy dưới ngưỡng (hoặc distance quá lớn), kích hoạt fallback `insufficient_evidence` mà không gọi generation API tốn chi phí.
- **Generation & Citation**:
  - Gắn nhãn bằng chứng `[E1]`, `[E2]`, ...
  - LLM chỉ trả lời dựa trên ngữ cảnh cách ly an toàn (`<<< BEGIN UNTRUSTED CONTEXT DATA >>>`).
  - Ánh xạ nhãn `[E*]` thành trích dẫn minh bạch: `[Nguồn: <source>, tr. <page>, chunk: <chunk_id>]`.
  - Loại bỏ các trích dẫn ảo hoặc không nằm trong tập bằng chứng được chấp nhận.

## 9. Pipeline Trace Contract
Mỗi lượt truy vấn Advanced RAG phải ghi nhận cấu trúc `trace` chi tiết gồm:
- `query`: Câu hỏi đầu vào.
- `strategy`: Chiến lược chunking áp dụng.
- `bm25_candidates`: Danh sách chunk_id, rank và bm25_score.
- `semantic_candidates`: Danh sách chunk_id, rank và semantic_distance.
- `fused_candidates`: Danh sách chunk_id sau RRF kèm `rrf_score`.
- `reranked_candidates`: Danh sách chunk_id sau Cross-Encoder kèm `rerank_score`.
- `final_evidences`: Danh sách bằng chứng được chọn kèm cờ chấp thuận (`accepted`).
- `timings_ms`: Thời gian thực thi chi tiết của từng công đoạn (tokenize, sparse_search, dense_search, rrf, rerank, generation).

## 10. Evaluation Metrics Contract
Module `evaluate.py` đo lường hiệu năng truy xuất dựa trên tập `eval/questions.json`:
- **Hit@K**: Tỷ lệ câu hỏi mà ít nhất 1 chunk liên quan xuất hiện trong Top-K ($K \in \{1, 3, 5\}$).
- **MRR@K (Mean Reciprocal Rank)**: Trung bình của nghịch đảo vị trí xuất hiện đầu tiên của chunk liên quan.
- **NDCG@K (Normalized Discounted Cumulative Gain)**: Đánh giá chất lượng xếp hạng có tính đến trọng số vị trí.
- **Out-of-Scope Detection Accuracy**: Độ chính xác của Confidence Gate trong việc chặn các câu hỏi ngoài phạm vi tài liệu.
- **Latency (ms)**: P50, P90, P99 thời gian phản hồi.
- Tự động lưu bảng so sánh Markdown và file JSON vào thư mục `reports/`.

## 11. Offline Testing Contract
- Mọi bài kiểm thử trong `tests/` phải chạy thành công hoàn toàn **offline**:
  - Sử dụng Mock cho Gemini API (Embedding & Generation).
  - Sử dụng Mock / Local Dummy Model cho Cross-Encoder Reranker trong môi trường test nhẹ.
  - Sử dụng fixture `tests/fixtures/chunks_advanced_sample.json`.
  - Tạo thư mục Chroma/BM25 tạm thời (`tempfile.TemporaryDirectory`) và tự dọn dẹp sau khi chạy xong.

## 12. UI Comparison Contract
Giao diện Streamlit (`app.py`) hỗ trợ:
- Chế độ so sánh đối đầu song song (Side-by-side):
  - Cột trái: Baseline RAG (Semantic Vector Only).
  - Cột phải: Advanced RAG (Hybrid BM25 + Dense + RRF + Reranker).
- Xem bảng Trace chi tiết: Trực quan hóa đường đi của từng chunk qua các bộ lọc BM25, Chroma, RRF và Reranker.
- Hiển thị so sánh câu trả lời tổng hợp và danh sách citations.
