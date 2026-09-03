# Agent Specification - Buổi 08: Advanced RAG (Hybrid Search, RRF & Cross-Encoder Reranking)

## 1. Workspace và Security
- **Vùng được đọc**:
  - `rag_foundation/buoi_05/output/chunks/`
  - `rag_foundation/buoi_05/.venv/`
  - `rag_foundation/buoi_07/`
  - `rag_foundation/buoi_08/`
- **Vùng được ghi**:
  - Chỉ ghi trong thư mục `rag_foundation/buoi_08/`
- **Quy định tuyệt đối**:
  - Không sửa bất kỳ file nào của Buổi 05, Buổi 06 hoặc Buổi 07.
  - Không lưu, không hard-code hoặc in các giá trị secret/API key ra console, logs, hay commit vào git.
  - Mọi cấu hình nhạy cảm được đọc qua biến môi trường hoặc file `.env` cục bộ của Buổi 08.

## 2. Quan hệ với Buổi 05 và Buổi 07
- **Buổi 05**: Cung cấp dữ liệu chunks thô đã được tiền xử lý (`fixed-size`, `hierarchical`, `semantic`) tại `buoi_05/output/chunks/`.
- **Buổi 07**: Cung cấp **Semantic Baseline** (`rag.py`) sử dụng thuần vector search với Google GenAI Embeddings và ChromaDB.
- **Buổi 08**: Mở rộng thành **Advanced RAG Pipeline**:
  - Tích hợp **Keyword Search (BM25)** xử lý từ khóa chính xác, số hiệu văn bản, Điều/Khoản.
  - Tích hợp **Dense Semantic Retrieval** từ ChromaDB persistent storage.
  - Hợp nhất xếp hạng ứng viên bằng **Reciprocal Rank Fusion (RRF)**.
  - Tái xếp hạng chính xác bằng **Cross-Encoder Reranker**.
  - Đánh giá định lượng hiệu năng bằng bộ chỉ số Retrieval & Ranking (Hit@k, MRR@k, Precision@k, Recall@k, MAP@k, NDCG@k).

## 3. Data Contract
Mỗi chunk JSON đầu vào bắt buộc phải tuân thủ chuẩn Buổi 07:
- `chunk_id`: Mã định danh duy nhất của chunk (chuỗi không rỗng).
- `strategy`: Chiến lược chunking (`fixed-size`, `semantic`, `hierarchical`).
- `source`: Tên hoặc đường dẫn file tài liệu gốc.
- `page_start`: Trang bắt đầu (số nguyên >= 1, không nhận boolean).
- `page_end`: Trang kết thúc (số nguyên >= page_start).
- `text`: Nội dung văn bản của chunk (chuỗi không rỗng sau khi strip).

## 4. BM25 Tokenizer & Retrieval Contract
- **Tokenizer**:
  - Bộ tách từ hỗ trợ tiếng Việt: chuyển chữ thường, chuẩn hóa dấu câu, xử lý stop words, bảo toàn số hiệu Điều/Khoản (ví dụ: "Điều 5", "Khoản 2", "Thông tư 39").
- **BM25 Retrieval**:
  - Tính toán điểm BM25 (tham số chuẩn $k_1 \in [1.2, 2.0]$, $b \in [0.5, 0.8]$).
  - Trả về danh sách ứng viên được sắp xếp giảm dần theo điểm BM25.
  - Mỗi kết quả chứa: `chunk_id`, `score`, `rank`, `source`, `page_start`, `page_end`, `text`.

## 5. Semantic Candidate Contract
- Sử dụng Google GenAI Embedding API (`gemini-embedding-2`, dimension = 768) và ChromaDB persistent storage (Cosine distance).
- Trích xuất top-$k_s$ ứng viên vector có khoảng cách nhỏ nhất (tương đồng cao nhất).
- Mỗi kết quả chứa: `chunk_id`, `distance`, `rank`, `source`, `page_start`, `page_end`, `text`.

## 6. RRF Fusion Contract (Reciprocal Rank Fusion)
- **Công thức tính điểm**:
  $$RRF\_Score(d) = \sum_{m \in M} \frac{w_m}{k_{rrf} + r_m(d)}$$
  Trong đó:
  - $M = \{BM25, Semantic\}$: Các phương pháp retrieval.
  - $w_m$: Trọng số của từng phương pháp (mặc định $w_{bm25}=1.0$, $w_{semantic}=1.0$).
  - $k_{rrf}$: Hằng số làm mượt (mặc định $k_{rrf} = 60$).
  - $r_m(d)$: Thứ hạng (1-based index) của tài liệu $d$ trong danh sách kết quả của phương pháp $m$. Nếu $d$ không xuất hiện trong top của phương pháp $m$, coi như không đóng góp điểm.
- Hợp nhất và loại bỏ trùng lặp ứng viên, sắp xếp giảm dần theo $RRF\_Score$.

## 7. Cross-Encoder Reranker Contract
- Nhận danh sách top-$N$ ứng viên từ RRF Fusion ($N \ge Top\_K$).
- Đánh giá sự liên quan trực tiếp giữa cặp `(query, document_text)`.
- Chuẩn hóa điểm số rerank về khoảng $[0.0, 1.0]$.
- Sắp xếp lại danh sách ứng viên theo điểm reranker giảm dần để chọn ra top-$K$ bằng chứng cuối cùng.

## 8. Final Evidence & Citation Contract
- Bằng chứng cuối cùng (final evidence) phải giữ nguyên vẹn metadata thật (`source`, `page_start`, `page_end`, `chunk_id`).
- Áp dụng **Confidence Gate** lọc bỏ các bằng chứng có điểm rerank dưới ngưỡng tin cậy tối thiểu.
- Khi sinh câu trả lời, trích dẫn (citation) bắt buộc phải đối chiếu nhãn `[E1]`, `[E2]` với metadata thực tế, không chấp nhận trích dẫn hallucinated do LLM tự bịa.

## 9. Pipeline Trace Contract
Mỗi lượt thực thi Advanced RAG phải ghi nhận đầy đủ trace thông tin:
- `query`: Câu hỏi đầu vào.
- `bm25_candidates`: Top ứng viên từ BM25 kèm rank & score.
- `semantic_candidates`: Top ứng viên từ Vector search kèm rank & distance.
- `rrf_candidates`: Top ứng viên sau khi fusion kèm RRF score.
- `reranked_candidates`: Top ứng viên sau khi rerank kèm điểm và trạng thái accepted/rejected.
- `generation_input`: Prompt và ngữ cảnh chuyển cho LLM.
- `latency_ms`: Thời gian thực thi từng chặng (BM25, Semantic, RRF, Rerank, Generation).

## 10. Evaluation Metrics Contract
Module đánh giá (`evaluate.py`) thực hiện tính toán định lượng trên tập gold questions (`eval/questions.json`):
- **Hit@k**: Tỷ lệ câu hỏi có ít nhất một chunk đúng nằm trong top-$k$ ($\in [0.0, 1.0]$).
- **MRR@k** (Mean Reciprocal Rank): Nghịch đảo vị trí xuất hiện đầu tiên của chunk đúng trong top-$k$.
- **Precision@k**: Tỷ lệ chunk đúng trong số $k$ chunk được truy xuất.
- **Recall@k**: Tỷ lệ chunk đúng được truy xuất trên tổng số chunk đúng cần tìm.
- **MAP@k** (Mean Average Precision): Độ chính xác trung bình có xét đến thứ tự xếp hạng.
- **NDCG@k** (Normalized Discounted Cumulative Gain): Đánh giá chất lượng xếp hạng có chiết khấu theo vị trí.

## 11. Offline Testing Contract
- 100% unit tests trong `tests/` phải chạy được hoàn toàn **offline**, không yêu cầu kết nối mạng hay API key thật.
- Sử dụng mock cho Google GenAI API và Cross-Encoder model.
- Sử dụng thư mục tạm (`tempfile.TemporaryDirectory`) cho ChromaDB storage trong các bài kiểm thử.

## 12. UI Comparison Contract
- Ứng dụng Streamlit (`app.py`) cung cấp giao diện so sánh trực quan song song (Side-by-Side):
  - **Baseline RAG (Buổi 07)** vs. **Advanced Hybrid RAG (Buổi 08)**.
  - Hiển thị bảng so sánh chi tiết: Candidates retrieved, RRF rank, Rerank score, Response quality, Latency và Citations.
