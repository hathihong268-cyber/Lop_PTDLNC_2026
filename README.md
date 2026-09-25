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
│       ├── buoi_13/     # Wiki Risk Graph (Vibe Coding với Obsidian & Neo4j)
│       ├── buoi_14/     # Hybrid Search + Reranking + Mini Knowledge Graph
│       └── buoi_15/     # (Triển khai tại buoi_14) Role-Based Access Control (RBAC) & Secure Retrieval
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

### 🔹 [Buổi 14: Nâng Cấp RAG Với Hybrid Search + Reranking & Mini Knowledge Graph](RAG/rag_foundation/buoi_14/README.md)
- Chuẩn hóa corpus 720 chunks từ 15 văn bản pháp quy ngân hàng.
- Hợp nhất 4 tầng retrieval: BM25 (Lexical) + Dense (Vector Embedding) + Hybrid RRF + Cross-Encoder Reranker (ge-reranker-base).
- Benchmark định lượng trên 12 câu hỏi vàng: Nâng MRR từ 0.4611 lên 0.8083 và Hit@1 lên 75.0%.
- Mini Knowledge Graph với 15 :VanBan, 720 :DieuKhoan, 720 [:CONTAINS], 705 [:NEXT] và 8 quan hệ pháp lý liên văn bản trên Neo4j.
- Giao diện Streamlit Dashboard đa năng tích hợp trích xuất gợi ý quan hệ đồ thị (Graph Hints).

### 🔹 [Buổi 15: Phân Quyền RBAC Mức Dữ Liệu & Secure Retrieval Pipeline](RAG/rag_foundation/buoi_14/Cac%20lenh%20chay%20buoi_15.txt)
- Thiết kế 5 vai trò nghiệp vụ: Admin, HR_Manager, Risk_Officer, Employee, Guest.
- Gán thẻ bảo mật llowed_roles tự động cho 720 chunks (chunks_secure.csv) và cập nhật lên Node :VanBan, :DieuKhoan trong Neo4j.
- Pre-filtering và Post-filtering đảm bảo 100% ứng viên đưa sang Cross-Encoder Reranker đều thuộc quyền truy cập của người dùng.
- Bộ kiểm định an toàn tự động security_audit.py đạt 100% Pass Rate trên 6 kịch bản rò rỉ dữ liệu.
- Ứng dụng Streamlit RBAC pp_secure.py với tính năng đóng vai người dùng và so sánh kết quả đa vai trò.
