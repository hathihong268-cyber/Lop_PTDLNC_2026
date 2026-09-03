# BÁO CÁO ĐÁNH GIÁ ĐỊNH LƯỢNG RETRIEVAL BENCHMARK — BUỔI 14
**So sánh định lượng 4 cấu hình: BM25 vs Dense vs Hybrid (RRF) vs Hybrid + Cross-Encoder Reranking**

---

## 1. Thiết Lập Thử Nghiệm & Phương Pháp Đánh Giá

- **Tập dữ liệu câu hỏi vàng (`buoi_14/data/eval/questions.csv`)**: 12 câu hỏi thực tế được xây dựng trực tiếp từ 15 văn bản pháp quy trong corpus, chia đều 3 nhóm truy vấn:
  1. `EXACT_KEYWORD` (4 câu): Truy vấn chứa đích danh số hiệu văn bản (`46/2023/NĐ-CP`, `01/2014/TT-NHNN`, `41/2016/TT-NHNN`, `73/2016/NĐ-CP`) và số điều.
  2. `SEMANTIC` (4 câu): Diễn đạt hoàn toàn bằng thuật ngữ nghiệp vụ ngân hàng / bảo hiểm, không có số hiệu điều khoản.
  3. `MIXED` (4 câu): Kết hợp giữa số hiệu văn bản và mô tả nghiệp vụ cụ thể.
- **Tập Corpus**: `buoi_14/data/processed/chunks_normalized.csv` (720 chunks).
- **Các cấu hình so sánh**:
  - `bm25`: BM25Okapi với Tokenizer pháp lý bảo toàn mã hiệu.
  - `dense`: `thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5` (384 dims, L2 Normalized, Cache NPZ).
  - `hybrid`: Reciprocal Rank Fusion ($k=60$) từ 20 ứng viên mỗi bên.
  - `hybrid_rerank`: Cross-Encoder `BAAI/bge-reranker-base` chấm điểm lại 20 ứng viên từ Hybrid.
- **Chỉ số đánh giá (Evaluation Metrics)**:
  - **Hit@1**: Tỷ lệ câu hỏi mà chunk vàng đứng ở vị trí Rank 1.
  - **Hit@3**: Tỷ lệ câu hỏi mà chunk vàng nằm trong Top 3.
  - **Hit@5**: Tỷ lệ câu hỏi mà chunk vàng nằm trong Top 5.
  - **MRR (Mean Reciprocal Rank)**: $\frac{1}{|Q|} \sum_{q=1}^{|Q|} \frac{1}{\text{rank}_q}$ (với $\text{rank}_q = \infty \implies 0$ nếu không lọt Top 5).

---

## 2. Bảng Tổng Kết Kết Quả Định Lượng (Overall Metrics)

| Cấu Hình Pipeline | Hit@1 (%) | Hit@3 (%) | Hit@5 (%) | MRR | Đánh Giá Hiệu Năng |
|---|:---:|:---:|:---:|:---:|---|
| **1. BM25-only** | 58.3% | 75.0% | 75.0% | 0.6528 | Rất mạnh trên từ khóa chính xác, yếu trên semantic |
| **2. Dense-only** | 0.0% | 8.3% | 16.7% | 0.0486 | Bắt được cụm chủ đề chung nhưng trượt số điều cụ thể |
| **3. Hybrid (RRF)** | 25.0% | 58.3% | **83.3%** | 0.4611 | **Độ phủ ứng viên (Recall@5) cao nhất** |
| **4. Hybrid + Rerank** | **75.0%** 🚀 | **83.3%** 🚀 | **91.7%** 🚀 | **0.8083** 🚀 | **Chính xác nhất và toàn diện nhất trên mọi chỉ số** |

---

## 3. Chi Tiết Hiệu Năng Theo Từng Nhóm Truy Vấn (Query Type Breakdown)

### 3.1. Nhóm `EXACT_KEYWORD` (Truy vấn từ khóa & số hiệu chính xác)
| Cấu Hình | Hit@1 | Hit@5 | MRR | Nhận Xét |
|---|:---:|:---:|:---:|---|
| `bm25` | **100%** | **100%** | **1.0000** | Tuyệt đối chính xác nhờ tokenizer bảo toàn số hiệu |
| `dense` | 0% | 0% | 0.0000 | Không phân biệt được số điều trong cùng văn bản |
| `hybrid` | 25% | 100% | 0.5625 | Đảm bảo 100% Hit@5 nhưng bị Rank Dilution |
| `hybrid_rerank` | **100%** | **100%** | **1.0000** | Reranker phục hồi vị trí số 1 cho 100% các câu hỏi |

### 3.2. Nhóm `SEMANTIC` (Truy vấn diễn đạt ngữ nghĩa nghiệp vụ)
| Cấu Hình | Hit@1 | Hit@5 | MRR | Nhận Xét |
|---|:---:|:---:|:---:|---|
| `bm25` | 25% | 50% | 0.3333 | Gặp khó khăn khi câu hỏi dùng từ đồng nghĩa |
| `dense` | 0% | 0% | 0.0000 | Bị nhiễu bởi các điều khoản quy định chung |
| `hybrid` | 25% | 50% | 0.3000 | Gom được ứng viên nhưng chưa tối ưu thứ hạng |
| `hybrid_rerank` | **50%** | **75%** | **0.6250** | **Tăng gấp đôi Hit@1 và MRR so với BM25/Hybrid** |

### 3.3. Nhóm `MIXED` (Kết hợp mã văn bản & nghiệp vụ)
| Cấu Hình | Hit@1 | Hit@5 | MRR | Nhận Xét |
|---|:---:|:---:|:---:|---|
| `bm25` | 50% | 75% | 0.6250 | Khá tốt ở việc lọc văn bản |
| `dense` | 0% | 50% | 0.1458 | Bắt được một số điều khoản liên quan trong top 5 |
| `hybrid` | 25% | **100%** | 0.5208 | **100% câu hỏi đều giữ được chunk đúng trong Top 5** |
| `hybrid_rerank` | **75%** | **100%** | **0.8000** | Đạt độ chính xác tối ưu |

---

## 4. Phân Tích Chuyên Sâu

### 4.1. Hybrid Search có thực sự giúp ích không?
**CÓ, ĐÓNG VAI TRÒ BẢO ĐẢM ĐỘ PHỦ (RECALL GENERATOR)**:
- Trên toàn bộ 12 câu hỏi, Hybrid Search đạt **Hit@5 = 83.3%** (cao hơn cả BM25 75.0% và Dense 16.7%). Đặc biệt trên nhóm câu hỏi hỗn hợp `MIXED`, Hybrid đạt **100% Hit@5**.
- Nếu chỉ dùng Dense đơn lẻ, 83.3% tài liệu bị bỏ sót. Nếu chỉ dùng BM25, các tài liệu đồng nghĩa bị rớt. Hybrid tạo ra **tập ứng viên 20 candidates toàn diện nhất** làm nguồn cho Reranker.

### 4.2. Tầng Cross-Encoder Reranking thay đổi thứ tự như thế nào?
**RERANKER LÀ BƯỚC ĐỘT PHÁ VỀ ĐỘ CHÍNH XÁC (PRECISION BOOSTER)**:
- **Hit@1 tăng vọt từ 25.0% lên 75.0% (+50% tuyệt đối)**.
- **MRR tăng từ 0.4611 lên 0.8083 (+75.3% tương đối)**.
- Các trường hợp đảo thứ hạng ngoạn mục:
  - **Q07**: Hybrid không có trong Top 5 ➔ Reranker kéo từ ứng viên #16 lên **Rank #1**.
  - **Q02, Q03, Q04, Q09, Q12**: Đều được Reranker thăng hạng từ #2, #4 lên **Rank #1**.

---

## 5. Phân Tích Các Trường Hợp Thất Bại (Failure Cases)

### ❌ Case 1: [Q06] `"Tiêu chuẩn và điều kiện bổ nhiệm Tổng giám đốc doanh nghiệp bảo hiểm"` (Expected: `doc_163441_dieu_73`)
- **Kết quả**: Cả 4 phương pháp đều không đưa `doc_163441_dieu_73` (Nghị định 46/2023) vào Top 5.
- **Nguyên nhân**: Trong tập dữ liệu có văn bản cũ `Nghị định 73/2016/NĐ-CP Điều 28` và `Thông tư 27/2024 Điều 9` cũng quy định về điều kiện bổ nhiệm Tổng giám đốc. Do câu hỏi không nêu rõ năm/mã văn bản, Reranker chấm điểm `doc_112025_dieu_28` cao hơn vì tiêu đề chứa chính xác cụm "Điều kiện của Tổng giám đốc".
- **Giải pháp**: Cần kết hợp Metadata Filtering theo trạng thái văn bản còn hiệu lực (`status == 'Còn hiệu lực'`).

### ❌ Case 2: [Q08] `"Biện pháp đảm bảo an toàn và bảo vệ xe chuyên dùng trên đường vận chuyển tiền mặt"` (Expected: `doc_44209_dieu_52`)
- **Kết quả**: Reranker xếp `doc_44209_dieu_52` ở **Rank #2**, vị trí Rank #1 thuộc về `doc_44209_dieu_53` (`Điều 53. Vận chuyển tiền mặt bằng xe ô tô chuyên dùng`).
- **Nguyên nhân**: Cả hai Điều 52 và Điều 53 đều cùng nằm trong Chương IV Thông tư 01/2014 và có nội dung tương đồng cao.

### ❌ Case 3: [Q10] `"Hồ sơ đề nghị chấp thuận nguyên tắc hợp nhất ngân hàng theo Thông tư 62/2024/TT-NHNN"` (Expected: `doc_174218_dieu_11`)
- **Kết quả**: Reranker xếp `doc_174218_dieu_11` ở **Rank #5**, trong khi `doc_174218_dieu_14` (`Trình tự, thủ tục chấp thuận hợp nhất`) đứng Rank #1.
- **Nguyên nhân**: Trình tự và Hồ sơ hợp nhất có liên kết ngữ nghĩa chặt chẽ với nhau trong cùng Thông tư 62/2024.

---

## 6. Kết Luận & Khuyến Nghị Kiến Trúc

1. **Không có một retriever đơn lẻ nào là hoàn hảo**:
   - BM25 thống trị trên câu hỏi có mã hiệu chính xác nhưng yếu thế trên diễn đạt tự nhiên.
   - Dense hiểu ngữ cảnh nhưng dễ mờ các thực thể số.
2. **Kiến trúc tối ưu chuẩn sản phẩm (Production Standard)**:
   $$\text{Lexical (BM25)} + \text{Semantic (Dense)} \xrightarrow{\text{RRF Fusion}} \text{Top-20 Candidates} \xrightarrow{\text{Cross-Encoder}} \text{Top-5 Answers}$$
3. Kiến trúc này đạt **Hit@5 = 91.7%** và **MRR = 0.8083**, sẵn sàng làm nguồn Context tin cậy cho phần Generation và Knowledge Graph tiếp theo.
