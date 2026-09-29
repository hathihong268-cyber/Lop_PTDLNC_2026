# Buổi 09: Hierarchical & Multi-Query Advanced RAG

> **Lưu ý:** Đây là dự án học thuật nghiên cứu kỹ thuật RAG trên văn bản pháp luật ngân hàng, không phải tư vấn pháp lý.

---

## 1. Tổng Quan Kiến Trúc
Buổi 09 nâng cấp hệ thống RAG từ Buổi 08 thành kiến trúc phân cấp hai tầng truy xuất và mở rộng câu hỏi:
1. **Multi-Query Expansion:** Mở rộng câu hỏi gốc $Q_0$ thành các biến thể $Q_1, Q_2, Q_3$ (paraphrase, legal focus, terminology).
2. **Per-Query Hybrid Retrieval:** Thực hiện tìm kiếm kết hợp BM25 + Dense Semantic cho từng biến thể.
3. **Cross-Query Reciprocal Rank Fusion:** Hợp nhất ứng viên từ tất cả các biến thể với trọng số ưu tiên câu gốc ($W_{q0} = 1.5$).
4. **Parent-Child Resolution & Aggregation:** Tra cứu cây phân cấp Điều/Khoản, mở rộng các child hits thành Parent Document hoàn chỉnh (có context budget cap).
5. **Parent Cross-Encoder Reranking:** Tái xếp hạng các Parent Documents bằng câu hỏi gốc $Q_0$ qua Cross-Encoder.
6. **Grounded Answer & Citations:** Sinh câu trả lời có kiểm chứng với trích dẫn cấp Điều và nguồn văn bản.

---

## 2. Cấu Trúc Thư Mục

```text
rag_advanced/buoi_09/
├── .env.example                     # Mẫu cấu hình tham số Buổi 09
├── .gitignore                       # Quy tắc loại trừ tệp nhạy cảm & storage
├── requirements.txt                 # Danh sách dependencies trực tiếp
├── rag.py                           # Baseline Semantic RAG (snapshot từ Buổi 08)
├── advanced_rag.py                  # Baseline Advanced RAG (snapshot từ Buổi 08)
├── hierarchical_rag.py              # Module chính Buổi 09 (Skeleton Bước 02)
├── evaluate.py                      # Benchmark đánh giá 4 chế độ (Skeleton Bước 02)
├── app.py                           # Streamlit UI đối đầu 4 chế độ (Skeleton Bước 02)
├── README.md                        # Tài liệu hướng dẫn
├── SPEC_buoi_09.md                  # Tài liệu đặc tả kỹ thuật chi tiết
├── eval/
│   └── questions.json               # Bộ câu hỏi benchmark (gold labels)
├── reports/
│   └── .gitkeep                     # Thư mục lưu báo cáo đánh giá
├── storage/
│   ├── chroma/
│   │   └── .gitkeep                 # Persistent vector store ChromaDB
│   ├── hierarchy/
│   │   └── .gitkeep                 # Cache Registry cây phân cấp
│   └── huggingface/
│       └── .gitkeep                 # Cache Cross-Encoder model
└── tests/
    ├── __init__.py
    └── fixtures/
        └── hierarchical_sample.json # Fixture dữ liệu mẫu cho offline test
```

---

## 3. Trạng Thái Hiện Tại (Bước 02)
- Dự án đang ở trạng thái **Skeleton & Specification**:
  - Baseline `rag.py` và `advanced_rag.py` đã được sao chép và gắn snapshot docstring, sẵn sàng hoạt động độc lập.
  - Các module mới `hierarchical_rag.py`, `evaluate.py`, `app.py` là các placeholder an toàn, không có side effects khi import.
  - Cấu hình `.env.example`, fixture dữ liệu và đặc tả `SPEC_buoi_09.md` đã hoàn tất.
