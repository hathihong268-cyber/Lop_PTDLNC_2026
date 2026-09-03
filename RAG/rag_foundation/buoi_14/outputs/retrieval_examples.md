# BÁO CÁO THỰC THI RETRIEVAL & RERANKING ĐẦY ĐỦ — BUỔI 14
**So sánh 4 giai đoạn: BM25-only ➔ Dense-only ➔ Hybrid (RRF Fusion) ➔ Cross-Encoder Reranking**

---

## 1. Tổng Quan Kiến Trúc & Thiết Lập Pipeline

```text
Câu hỏi (Query)
    │
    ├──────────────► BM25 Retriever (candidate_k = 20)
    │                       │
    └──────────────► Dense Retriever (candidate_k = 20, Cache: dense_embeddings_cache.npz)
                            │
                            ▼
                    Reciprocal Rank Fusion (RRF k=60)
                            │
                            ▼
                    Hybrid Candidates Pool (20 chunks)
                            │
                            ▼
               Cross-Encoder Reranker (BAAI/bge-reranker-base)
                            │
                            ▼
                    Top-5 Precision Reranked Results
```

- **Corpus chuẩn**: `buoi_14/data/processed/chunks_normalized.csv` (720 chunks từ 15 văn bản pháp quy).
- **Mô hình Dense**: `thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5` (384 dims).
- **Mô hình Reranker**: `BAAI/bge-reranker-base` (Cross-Encoder đa ngôn ngữ, chuẩn hóa Sigmoid $1 / (1 + e^{-\text{logit}})$).
- **Nguyên tắc**: Reranker chỉ nhận danh sách ứng viên từ Hybrid Search, tuyệt đối không rerank toàn bộ corpus.

---

## 2. Kết Quả Thử Nghiệm 3 Loại Câu Hỏi Điển Hình

---

### 📌 Ví Dụ 1: Câu hỏi có Mã / Số Hiệu Cụ Thể (Specific Code / Article)
> **Câu hỏi**: *"Điều 73 Nghị định 46/2023/NĐ-CP quy định về chức danh nào?"*

#### Bảng so sánh BEFORE RERANK (Hybrid) vs AFTER RERANK (Cross-Encoder):
| Final Rank | Chunk ID | Hybrid Rank | Rank Shift | Rerank Score (Sigmoid) | Citation | Nội Dung & Đánh Giá |
|:---:|---|:---:|:---:|:---:|---|---|
| **1** | `doc_163441_dieu_73` | **#1** | **=** | **0.9957** | `[46/2023/NĐ-CP \| Điều 73 \| doc_163441_dieu_73]` | **Chính xác tuyệt đối**: Bổ nhiệm, thay đổi Chủ tịch HĐQT, Tổng giám đốc |
| **2** | `doc_163441_dieu_102` | **#13** | **+11** | **0.0047** | `[46/2023/NĐ-CP \| Điều 102 \| doc_163441_dieu_102]` | Quyền lợi hợp đồng bảo hiểm liên kết đầu tư |
| **3** | `doc_163441_dieu_2_3` | **#2** | **-1** | **0.0043** | `[46/2023/NĐ-CP \| Điều 2 \| doc_163441_dieu_2_3]` | Tên chính thức của Văn phòng đại diện |
| **4** | `doc_6e689cd0_dieu_2_3` | **#4** | **=** | **0.0032** | `[52/VBHN-NHNN \| Điều 2 \| doc_6e689cd0...]` | Thời hạn hoạt động ngân hàng |
| **5** | `doc_163441_dieu_5` | **#6** | **+1** | **0.0030** | `[46/2023/NĐ-CP \| Điều 5 \| doc_163441_dieu_5]` | Nghiệp vụ bảo hiểm sức khỏe |

> **Phân tích Reranker**:
> - Cross-Encoder chấm điểm **0.9957** (gần tuyệt đối) cho đúng `Điều 73`, đồng thời hạ toàn bộ các chunk khác xuống dưới **0.005**. Khoảng cách điểm (score gap) cực lớn giúp loại bỏ hoàn toàn nhiễu.

---

### 📌 Ví Dụ 2: Câu hỏi Diễn Đạt Ngữ Nghĩa (Pure Semantic Query)
> **Câu hỏi**: *"Quy định về bảo quản an toàn và giao nhận vận chuyển tiền mặt trong kho quỹ"*

#### Bảng so sánh BEFORE RERANK (Hybrid) vs AFTER RERANK (Cross-Encoder):
| Final Rank | Chunk ID | Hybrid Rank | Rank Shift | Rerank Score (Sigmoid) | Citation | Nội Dung & Đánh Giá |
|:---:|---|:---:|:---:|:---:|---|---|
| **1** | `doc_44209_dieu_52` | **#19** | **+18** 🚀 | **0.9933** | `[01/2014/TT-NHNN \| Điều 52 \| doc_44209_dieu_52]` | **Cực kỳ chuẩn xác**: Đảm bảo an toàn trên đường vận chuyển |
| **2** | `doc_44209_preamble` | **#17** | **+15** 🚀 | **0.9856** | `[01/2014/TT-NHNN \| Căn cứ ban hành \| doc_44209_preamble]` | Thẩm quyền ban hành về giao nhận, bảo quản, vận chuyển tiền mặt |
| **3** | `doc_44209_dieu_21` | **#9** | **+6** 🚀 | **0.9798** | `[01/2014/TT-NHNN \| Điều 21 \| doc_44209_dieu_21]` | Trách nhiệm của Trưởng kho tiền, Trưởng phòng Ngân quỹ |
| **4** | `doc_44209_dieu_50` | **#1** | **-3** | **0.9788** | `[01/2014/TT-NHNN \| Điều 50 \| doc_44209_dieu_50]` | Phương tiện vận chuyển tiền mặt, tài sản quý |
| **5** | `doc_44209_dieu_23` | **#3** | **-2** | **0.9693** | `[01/2014/TT-NHNN \| Điều 23 \| doc_44209_dieu_23]` | Nhiệm vụ của nhân viên an toàn kho tiền |

> **Phân tích Reranker**:
> - **Cải thiện ngoạn mục**: Ở bước Hybrid, các tài liệu không liên quan như `27/2024/TT-NHNN Điều 1` (Quỹ bảo đảm QTDND) và `52/VBHN-NHNN Điều 3` lọt vào Top 5.
> - Sau khi Rerank, Cross-Encoder đã kéo `Điều 52` (Đảm bảo an toàn trên đường vận chuyển) từ **#19 lên #1** (+18 bậc), đồng thời toàn bộ Top 5 đều thuộc đúng Thông tư `01/2014/TT-NHNN`.

---

### 📌 Ví Dụ 3: Câu hỏi Kết Hợp Cả Mã Văn Bản và Ngữ Nghĩa Chi Tiết (Combined Query)
> **Câu hỏi**: *"Theo Thông tư 01/2014/TT-NHNN thì trách nhiệm của người áp tải tiền mặt là gì?"*

#### Bảng so sánh BEFORE RERANK (Hybrid) vs AFTER RERANK (Cross-Encoder):
| Final Rank | Chunk ID | Hybrid Rank | Rank Shift | Rerank Score (Sigmoid) | Citation | Nội Dung & Đánh Giá |
|:---:|---|:---:|:---:|:---:|---|---|
| **1** | `doc_44209_dieu_55` | **#4** | **+3** 🚀 | **0.9988** | `[01/2014/TT-NHNN \| Điều 55 \| doc_44209_dieu_55]` | **Trúng đích trực tiếp**: Điều 55. Lực lượng tham gia vận chuyển và trách nhiệm của người áp tải |
| **2** | `doc_44209_dieu_48` | **#7** | **+5** 🚀 | **0.9386** | `[01/2014/TT-NHNN \| Điều 48 \| doc_44209_dieu_48]` | Trách nhiệm tổ chức vận chuyển tiền mặt |
| **3** | `doc_44209_dieu_57` | **#2** | **-1** | **0.9061** | `[01/2014/TT-NHNN \| Điều 57 \| doc_44209_dieu_57]` | Trách nhiệm của người điều khiển phương tiện vận chuyển |
| **4** | `doc_44209_dieu_49` | **#1** | **-3** | **0.9037** | `[01/2014/TT-NHNN \| Điều 49 \| doc_44209_dieu_49]` | Giấy ủy quyền áp tải vận chuyển tiền mặt |
| **5** | `doc_44209_dieu_46` | **#5** | **=** | **0.8776** | `[01/2014/TT-NHNN \| Điều 46 \| doc_44209_dieu_46]` | Trách nhiệm của người bảo vệ kho tiền |

> **Phân tích Reranker**:
> - **Khắc phục triệt để nhược điểm của RRF Fusion**: Ở bước Hybrid, `Điều 55` bị xếp thứ #4 do chỉ có điểm cao từ BM25. 
> - Reranker đọc trực tiếp nội dung ngữ nghĩa của `Điều 55` và nhận diện đây là câu trả lời trực tiếp cho "trách nhiệm người áp tải", lập tức đưa lên **Rank 1** với điểm số áp đảo **0.9988**.
> - Đồng thời `Điều 72` (Hiệu lực thi hành - chỉ là điều khoản thủ tục) ở Rank 3 của Hybrid đã bị loại bỏ hoàn toàn khỏi Top 5.

---

## 3. Tổng Kết Đánh Giá Toàn Diện

| Phương Pháp | Ưu Điểm | Nhược Điểm | Vai Trò Trong Pipeline |
|---|---|---|---|
| **BM25 (Lexical)** | Bắt số hiệu/mã văn bản chính xác | Bỏ sót từ đồng nghĩa | Thu thập ứng viên từ khóa |
| **Dense (Vector)** | Hiểu ngữ nghĩa tổng quan, chủ đề | Dễ mờ số hiệu/điều khoản cụ thể | Thu thập ứng viên ngữ nghĩa |
| **Hybrid (RRF)** | Gom 2 danh sách, không lo lệch thang điểm | Hiện tượng pha loãng thứ hạng (Rank Dilution) | Tạo tập ứng viên chất lượng (Candidate Pool) |
| **Cross-Encoder Reranker** | Chấm điểm tương quan sâu `(Query, Passage)`, chính xác cao nhất | Chi phí tính toán cao nếu chạy toàn corpus | **Chốt chặn xếp hạng Top-k chính xác nhất** |

👉 **Pipeline hoàn chỉnh `Hybrid Search -> Cross-Encoder Reranker` kết hợp trọn vẹn điểm mạnh của cả 3 phương pháp và triệt tiêu toàn bộ điểm yếu của từng phương pháp đơn lẻ.**
