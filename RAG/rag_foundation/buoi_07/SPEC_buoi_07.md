# Agent Specification - Buổi 07: RAG Foundation

## Workspace
- **Vùng được đọc**:
  - `rag_foundation/buoi_05/output/chunks/`
  - `rag_foundation/buoi_05/.venv/`
  - `rag_foundation/buoi_06/`
  - `rag_foundation/buoi_07/`
- **Vùng được ghi**:
  - Chỉ ghi trong `rag_foundation/buoi_07/`
- **Quy định tuyệt đối**: Không sửa bất kỳ file nào của Buổi 05 hoặc Buổi 06.

## Python
- Sử dụng trực tiếp `.venv` của Buổi 05 tại `rag_foundation/buoi_05/.venv/`.
- Không tạo Virtual Environment mới.

## Input
- Dữ liệu đầu vào dạng JSON nằm trong thư mục `rag_foundation/buoi_05/output/chunks/`.
- Buổi 05 là nguồn dữ liệu đã được chunking và chuẩn bị sẵn.
- Không thực hiện OCR, không parse PDF lại, không thực hiện re-chunking.

## Packages
- Chỉ sử dụng các package được quy định trong `requirements.txt`:
  - `streamlit>=1.61,<2`
  - `google-genai>=2.16,<3`
  - `chromadb>=1.5,<2`
  - `python-dotenv>=1.2,<2`

## Pipeline
Quy trình xử lý RAG gồm các bước:
1. **Validate**: Kiểm tra cấu trúc và tính hợp lệ của dữ liệu đầu vào.
2. **Embedding**: Tạo vector biểu diễn cho chunks sử dụng Google GenAI Embedding API (`gemini-embedding-2`).
3. **Chroma persistent**: Lưu trữ và truy vấn vector trong ChromaDB với chế độ lưu trữ đĩa (persistent storage).
4. **Retrieval**: Truy vấn top-k chunks liên quan nhất theo khoảng cách vector (distance).
5. **Confidence Gate**: Lọc các kết quả truy vấn dựa trên ngưỡng khoảng cách `RAG_MAX_DISTANCE` (mặc định 0.45).
6. **Generation**: Sinh câu trả lời với Google GenAI (`gemini-3.5-flash-lite`) khi ngữ cảnh đạt ngưỡng tin cậy.
7. **Citation**: Trích dẫn nguồn chính xác (source, page, chunk_id) từ metadata thật.
8. **Streamlit**: Giao diện ứng dụng minh họa và tương tác.
9. **Unittest offline**: Kiểm thử tự động không cần kết nối Internet hoặc API key thật bằng mock.

## Data Contract
Mỗi chunk JSON đầu vào bắt buộc phải có đầy đủ các trường sau:
- `chunk_id`: Mã định danh duy nhất của chunk.
- `strategy`: Chiến lược chunking (`auto`, `by_page`, `semantic`, `hierarchical`, v.v.).
- `source`: Đường dẫn file nguồn.
- `page_start`: Trang bắt đầu.
- `page_end`: Trang kết thúc.
- `text`: Nội dung văn bản của chunk.

## Index Contract
- Mỗi `strategy` được lưu trữ trong một Chroma Collection riêng biệt.
- Model và chiều vector (dimension = 768) của index và query phải hoàn toàn trùng khớp.
- Phải dùng embedding thật từ Google GenAI Embedding API, không dùng vector giả.
- Chặn các vector chứa `NaN`, `Infinity`, giá trị `boolean` hoặc vector toàn số `0` (zero vector).
- Sử dụng ChromaDB với khoảng cách Cosine (`metadata={"hnsw:space": "cosine"}`) và thiết lập `embedding_function=None`.
- Đảm bảo tính idempotent khi nạp dữ liệu vào index.
- Kiểm tra trạng thái index ở chế độ read-only trước khi đọc/ghi.
- Validate toàn bộ vector embedding thành công trước khi thực hiện reset hoặc upsert vào Chroma collection.

## Retrieval Contract
- Trả về evidence thật từ Chroma collection kèm giá trị khoảng cách (`distance`).
- Chỉ các evidence đạt ngưỡng khoảng cách (`distance <= RAG_MAX_DISTANCE`) mới được đưa vào ngữ cảnh generation.
- Nếu tất cả evidence đều yếu (vượt ngưỡng `RAG_MAX_DISTANCE`), ngắt quy trình và không gọi API generation.

## Citation Contract
- Trích dẫn (citation) bắt buộc phải lấy từ metadata thật (`source`, `page_start`, `page_end`, `chunk_id`).
- Không tin tưởng hoặc sử dụng thông tin nguồn/trang do LLM tự sinh ra trong văn bản.
- Kết quả trả về gồm danh sách `citations` và `warnings`; code sẽ chủ động thay thế các label trích dẫn hợp lệ bằng thông tin trích dẫn thực tế.

## Security
- Không hard-code hoặc làm lộ API key / secrets trong source code, logs hoặc repository.

## Testing
- Sử dụng `unittest` cho kiểm thử tự động.
- Sử dụng mock API cho các dịch vụ bên ngoài (Google GenAI API).
- Sử dụng thư mục tạm thời (temporary storage) cho ChromaDB khi chạy unit test.
- Đảm bảo unit test chạy hoàn toàn offline, không yêu cầu kết nối Internet hoặc API key thật.

## Coding Style
- Cấu trúc tối giản: ít file, ít class, ít hàm.
- Tránh thiết kế kiến trúc quá phức tạp không cần thiết (clean architecture / over-engineering).
