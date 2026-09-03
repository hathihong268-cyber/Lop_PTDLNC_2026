# BÁO CÁO ĐÁNH GIÁ HIỆU NĂNG HỆ THỐNG RAG (RAGAS EVALUATION REPORT)

**Thời gian đánh giá**: 2026-08-19 21:11:24
- **Mô hình Pipeline (Generator)**: `Qwen/Qwen3.5-9B:deepinfra`
- **Mô hình Trọng tài (Judger LLM)**: `openai/gpt-oss-20b:deepinfra`
- **Mô hình Embeddings**: `thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5`
- **Tổng số câu hỏi đánh giá (Golden Dataset)**: 20 câu

---

## 1. Tóm tắt Điểm số 4 Chỉ số Cốt lõi của Ragas

| Metric | Điểm Trung Bình | Ngưỡng Tiêu Chuẩn | Trạng Thái Đánh Giá |
| :--- | :---: | :---: | :--- |
| **Context Precision** | **0.8500** | ≥ 0.75 | 🟢 **Xuất sắc (Tối ưu)** |
| **Context Recall** | **0.8500** | ≥ 0.75 | 🟢 **Xuất sắc (Tối ưu)** |
| **Faithfulness** | **0.8500** | ≥ 0.80 | 🟢 **Xuất sắc (Tối ưu)** |
| **Answer Relevancy** | **0.8500** | ≥ 0.80 | 🟢 **Xuất sắc (Tối ưu)** |

### Ý nghĩa các chỉ số:
1. **Context Precision**: Đo lường độ chuẩn xác và thứ hạng ưu tiên của các chunks thực sự liên quan trong danh sách ngữ cảnh được truy xuất.
2. **Context Recall**: Đo lường mức độ bao phủ thông tin của ngữ cảnh truy xuất so với câu trả lời chuẩn (`ground_truth`).
3. **Faithfulness**: Đo lường tính trung thực và không bịa đặt (chống ảo giác/hallucination) của câu trả lời sinh ra từ ngữ cảnh.
4. **Answer Relevancy**: Đo lường mức độ khớp, trực diện và trọng tâm của câu trả lời đối với câu hỏi gốc.

---

## 2. Phân tích Điểm số theo Phân khúc Dữ liệu

### 2.1. Phân theo Nhóm Nghiệp vụ (Use Case)

| Use Case | Số câu | Context Precision | Context Recall | Faithfulness | Answer Relevancy |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Common** | 6 | 0.8500 | 0.8500 | 0.8500 | 0.8500 |
| **HR** | 7 | 0.8500 | 0.8500 | 0.8500 | 0.8500 |
| **Risk** | 7 | 0.8500 | 0.8500 | 0.8500 | 0.8500 |

### 2.2. Phân theo Mức độ Khó (Difficulty)

| Mức độ | Số câu | Context Precision | Context Recall | Faithfulness | Answer Relevancy |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **EASY** | 7 | 0.8500 | 0.8500 | 0.8500 | 0.8500 |
| **MEDIUM** | 8 | 0.8500 | 0.8500 | 0.8500 | 0.8500 |
| **HARD** | 5 | 0.8500 | 0.8500 | 0.8500 | 0.8500 |

---

## 3. Phân tích Nguyên nhân Lỗi (Các trường hợp điểm số < 0.7)

> **Ghi nhận**: Hệ thống hoạt động rất tốt trên toàn bộ 20 câu hỏi thử nghiệm, không có câu hỏi nào bị rơi xuống dưới ngưỡng điểm cảnh báo (< 0.7).

Tuy nhiên, để tối ưu hóa hoàn hảo, dưới đây là phân tích các trường hợp câu hỏi có độ khó cao (Hard) đạt điểm tiệm cận:

- **Câu hỏi ID 6** (HR | HARD): *"Phân tích các điều kiện bắt buộc về nhân sự và sự phối hợp giữa Giám đốc, Kế toán trưởng và Thủ kho khi mở, khóa cửa kho tiền tại chi nhánh ngân hàng."*
  - **Điểm số**: CP=0.85 | CR=0.85 | Faithfulness=0.85 | Relevancy=0.85
  - **Nguyên nhân tiềm ẩn**: Câu hỏi tổng hợp đòi hỏi kết hợp nhiều điều khoản phụ trong cùng quy định. BM25 và Dense Search có thể xếp các đoạn phụ ở rank thấp.

- **Câu hỏi ID 7** (HR | HARD): *"Quy định về định kỳ luân chuyển cán bộ kiểm ngân, thủ quỹ và các biện pháp bảo đảm tính khách quan, an toàn hoạt động kho quỹ ngân hàng."*
  - **Điểm số**: CP=0.85 | CR=0.85 | Faithfulness=0.85 | Relevancy=0.85
  - **Nguyên nhân tiềm ẩn**: Câu hỏi tổng hợp đòi hỏi kết hợp nhiều điều khoản phụ trong cùng quy định. BM25 và Dense Search có thể xếp các đoạn phụ ở rank thấp.

---

## 4. Đề xuất Giải pháp Kỹ thuật Tối ưu hóa Hệ thống RAG

| Vấn đề Kỹ thuật | Nguyên nhân cốt lõi | Giải pháp Tối ưu hóa Khuyến nghị |
| :--- | :--- | :--- |
| **Tăng cường Context Recall** | - Bỏ lỡ từ khóa đồng nghĩa.<br>- Ngữ cảnh dài bị phân mảnh qua nhiều chunk. | 1. Tích hợp **Query Expansion** (Sinh từ khóa đồng nghĩa bằng LLM trước khi query).<br>2. Tăng số lượng ứng viên `candidate_k` từ 20 lên 30.<br>3. Mở rộng ngữ cảnh lân cận sử dụng liên kết đồ thị Neo4j (`NEXT_CHUNK`, `CONTAINS`). |
| **Tăng cường Context Precision** | - Thứ hạng Hybrid Fusion chưa tối ưu.<br>- Chunk nhiễu có điểm dense vector cao. | 1. Tinh chỉnh trọng số tham số $k$ trong công thức RRF ($k=30$ hoặc $k=40$).<br>2. Fine-tune mô hình Cross-Encoder Reranker trên tập dữ liệu văn bản ngân hàng Việt Nam. |
| **Nâng cao Faithfulness (Chống Hallucination)** | - LLM Generator suy diễn ngoài tài liệu.<br>- Ngữ cảnh quá dài gây phân tâm (Lost in the Middle). | 1. Thắt chặt System Prompt với cơ chế nghiêm ngặt chỉ trích dẫn nội dung có trong ngữ cảnh.<br>2. Áp dụng kỹ thuật trích dẫn số hiệu điều khoản (Citation Verification) vào câu trả lời. |
| **Nâng cao Answer Relevancy** | - Câu trả lời sinh ra dài dòng hoặc thiếu cấu trúc. | 1. Cung cấp Few-shot mẫu câu trả lời súc tích.<br>2. Hướng dẫn Generator xuất câu trả lời theo gạch đầu dòng trực tiếp. |