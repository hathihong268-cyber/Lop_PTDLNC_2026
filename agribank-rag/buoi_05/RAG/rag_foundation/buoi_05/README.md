# Buổi 5 – PDF tiếng Việt, OCR fallback và chunking

`src/rag_pipeline.py` không tạo embedding và không gọi LLM. PyMuPDF được thử trước cho từng trang. Nếu một trang rỗng, có ký tự thay thế, dấu hiệu mojibake/lỗi encoding, nhiều ký tự điều khiển, hoặc PyMuPDF ném lỗi, toàn bộ PDF được raster hoá thành PDF dẫn xuất tạm thời và gửi một lần tới LlamaParse. PDF gốc trong `datademo/` chỉ được đọc.

## Cài môi trường

```powershell
.\RAG\rag_foundation\buoi_05\.venv\Scripts\python.exe -m pip install -r .\RAG\rag_foundation\buoi_05\requirements.txt
```

Key Llama Cloud nằm trong `src/.env`; chương trình nạp key để gọi API khi cần nhưng không in giá trị key.

## Chạy

Dry-run chỉ kiểm tra text layer và dự báo có dùng OCR hay không; không ghi file và không gọi API:

```powershell
.\RAG\rag_foundation\buoi_05\.venv\Scripts\python.exe .\RAG\rag_foundation\buoi_05\src\rag_pipeline.py
```

`--write` lưu raw text NFC, chunks và báo cáo. Chỉ lúc này fallback OCR mới được phép gọi LlamaParse:

```powershell
.\RAG\rag_foundation\buoi_05\.venv\Scripts\python.exe .\RAG\rag_foundation\buoi_05\src\rag_pipeline.py --write
```

Đầu ra là `output/raw/`, `output/chunks/`, `output/reports/`. Tên tệp theo PDF nên không thay đổi PDF nguồn.

Ví dụ metadata chunk:

```json
{
  "chunk_id": "TT_02_2023_NHNN:hierarchical:0001",
  "strategy": "hierarchical",
  "source": "TT_02_2023_NHNN.pdf",
  "page_start": 1,
  "page_end": 2,
  "text": "...",
  "structure": {"chapter": "CHƯƠNG I ...", "article": "ĐIỀU 1. ..."}
}
```

Với PDF không có heading nhận diện được, chiến lược `hierarchical` vẫn tạo chunks nhưng report sẽ có cảnh báo; không tự đặt heading giả.
