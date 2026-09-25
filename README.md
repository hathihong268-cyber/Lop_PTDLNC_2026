# Khóa Học Phân Tích Dữ Liệu Nâng Cao 2026 (Lop_PTDLNC_2026)

Kho lưu trữ mã nguồn, bài tập thực hành và tài liệu nghiên cứu về **Retrieval-Augmented Generation (RAG)** và **Knowledge Graph (Đồ thị Tri thức)**.

---

## 📂 Cấu Trúc Khóa Học

`	ext
Lop_PTDLNC_2026/
├── RAG/
│   └── rag_foundation/
│       ├── buoi_05/     # Chunking & Tokenization
│       ├── buoi_06/     # Vector Database & Semantic Search
│       ├── buoi_07/     # RAG Pipeline Hoàn chỉnh & Giao diện Streamlit
│       ├── buoi_08/     # Hybrid Retrieval (BM25 + Semantic + RRF) & Reranking
│       ├── buoi_09/     # Hierarchical RAG & Retrieval Đa Tầng
│       ├── buoi_10/     # Knowledge Graph RAG & Trực quan hóa Neo4j
│       ├── buoi_11/     # RAG Evaluation & Đánh giá tự động với LLM-as-a-Judge
│       ├── buoi_12/     # Chuẩn hóa, Làm giàu Metadata & Xây dựng Đồ thị Tri thức (9 Bước)
│       └── buoi_13/     # Wiki Risk Graph (Vibe Coding với Obsidian & Neo4j)
└── README.md
`

---

## 🚀 Điểm Nhấn Các Buổi Thực Hành Mới Nhất

### 🔹 [Buổi 12: Chuẩn Hóa, Làm Giàu Metadata và Xây Dựng Đồ Thị Tri Thức](RAG/rag_foundation/buoi_12/README.md)
- Pipeline 9 bước hoàn chỉnh xử lý 30 văn bản pháp luật ngân hàng.
- Kết hợp trích xuất rule-based với LLM Google Gemini để làm giàu metadata.
- Chuẩn hóa thực thể và bóc tách quan hệ trích dẫn văn bản (THAM_CHIEU, SUA_DOI_BO_SUNG, THAY_THE_BOI).
- Kiểm định bằng chứng (evidence validation) và nạp vào Neo4j bằng Parameterized Cypher.

### 🔹 [Buổi 13: Xây Dựng Wiki Risk Graph Bằng Vibe Coding](RAG/rag_foundation/buoi_13/README.md)
- Xây dựng hệ thống Wiki tri thức rủi ro ngân hàng từ 4 file dữ liệu seed.
- Chuẩn hóa 34 thực thể (RuiRo, KiemSoat, SuKienRuiRo) và 22 liên kết hạt nhân (MITIGATES, OBSERVED_AS).
- Khởi tạo Vault Obsidian 35 trang với liên kết 2 chiều và cấu hình Graph View.
- Báo cáo kiểm định toàn vẹn 0 lỗi gãy link và tích hợp đồng bộ dữ liệu vào Neo4j.
