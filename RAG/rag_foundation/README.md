# Khóa Học Phân Tích Dữ Liệu Nâng Cao 2026 — RAG Foundation & Knowledge Graph

Thư mục lưu trữ mã nguồn, bài thực hành và tài liệu nghiên cứu về **Retrieval-Augmented Generation (RAG)** và **Knowledge Graph (Đồ thị Tri thức)**.

---

## 📚 Mục Lục Các Buổi Thực Hành

| Buổi | Chủ đề chính | Nội dung trọng tâm | Trạng thái |
| :---: | :--- | :--- | :---: |
| **Buổi 05** | Chunking & Tokenization | Chiến lược phân đoạn văn bản, quản lý ngữ cảnh và bộ đếm token. | ✅ Hoàn thành |
| **Buổi 06** | Vector Database & Semantic Search | Nhúng embedding, lưu trữ và tìm kiếm vector tương đồng (FAISS / Chroma). | ✅ Hoàn thành |
| **Buổi 07** | RAG Pipeline Hoàn chỉnh | Xây dựng pipeline RAG đầu-cuối với giao diện người dùng tương tác Streamlit. | ✅ Hoàn thành |
| **Buổi 08** | Hybrid Retrieval & Reranker | Tìm kiếm lai BM25 + Semantic, kết hợp thuật toán RRF và Cross-Encoder Reranker. | ✅ Hoàn thành |
| **Buổi 09** | Hierarchical RAG | Retrieval đa tầng (Parent-Child Chunks), tối ưu hóa ngữ cảnh truy xuất. | ✅ Hoàn thành |
| **Buổi 10** | Graph RAG & Neo4j Visualization | Kết hợp cơ sở dữ liệu đồ thị Neo4j và giao diện trực quan hóa đồ thị tri thức. | ✅ Hoàn thành |
| **Buổi 11** | RAG Evaluation & LLM-as-a-Judge | Đánh giá hệ thống RAG với bộ câu hỏi kiểm thử và chấm điểm tự động. | ✅ Hoàn thành |
| **Buổi 12** | Metadata Enrichment & Knowledge Graph | Pipeline 9 bước làm giàu metadata văn bản pháp quy ngân hàng với Gemini & Neo4j. | ✅ Hoàn thành |
| **Buổi 13** | Wiki Risk Graph (Vibe Coding) | Xây dựng Wiki đồ thị rủi ro với Obsidian Vault, Graph View và Neo4j Cypher. | ✅ Hoàn thành |
| **Buổi 14** | Hybrid Search + Reranking + Mini KG | Nâng cấp RAG với BM25, Dense Vector, RRF Fusion, Cross-Encoder Reranker và Mini KG Neo4j. | ✅ Hoàn thành |

---

## 🌟 Điểm Nhấn Các Buổi Thực Hành Gần Nhất

### 📌 [Buổi 12: Chuẩn Hóa, Làm Giàu Metadata và Xây Dựng Đồ Thị Tri Thức](buoi_12/README.md)
- Pipeline 9 bước tự động hóa xử lý 30 văn bản pháp luật ngân hàng.
- Kết hợp Rule-based Regex và LLM Google Gemini để trích xuất thực thể (`CoQuan`, `NguoiKy`, `DoiTuongApDung`).
- Bóc tách và thẩm định quan hệ trích dẫn văn bản (`THAM_CHIEU`, `SUA_DOI_BO_SUNG`, `THAY_THE_BOI`).
- Nạp đồ thị vào Neo4j bằng Parameterized Cypher đảm bảo an toàn và tính duy nhất.

### 📌 [Buổi 13: Xây Dựng Wiki Risk Graph Bằng Vibe Coding](buoi_13/README.md)
- Xây dựng hệ thống tri thức rủi ro từ 4 tập dữ liệu seed (`risk_profiles_seed.csv`, `controls_seed.csv`, `risk_events_seed.csv`, `relationships_seed.csv`).
- Chuẩn hóa thành 34 entities và 22 quan hệ nghiệp vụ hạt nhân (`MITIGATES`, `OBSERVED_AS`).
- Sinh 35 trang Obsidian Wiki Vault với liên kết 2 chiều `[[wikilink]]` và cấu hình Graph View.
- Báo cáo kiểm thử toàn vẹn tự động (`0` broken links, `0` orphan pages) và bộ truy vấn mẫu Neo4j Cypher từ A đến F.

### 📌 [Buổi 14: Nâng Cấp RAG Với Hybrid Search + Reranking & Mini Knowledge Graph](buoi_14/README.md)
- Chuẩn hóa corpus 720 chunks từ 15 văn bản pháp quy ngân hàng.
- Kết hợp 4 tầng retrieval: BM25 (Lexical) + Dense (Vector Embedding) + Hybrid RRF + Cross-Encoder Reranker (`bge-reranker-base`).
- Benchmark định lượng trên 12 câu hỏi vàng: Nâng MRR từ 0.4611 lên 0.8083 và Hit@1 lên 75.0%.
- Mini Knowledge Graph với 15 `:VanBan`, 720 `:DieuKhoan`, 720 `[:CONTAINS]`, 705 `[:NEXT]` và 8 quan hệ pháp lý liên văn bản trên Neo4j.
- Giao diện Streamlit Dashboard đa năng tích hợp trích xuất gợi ý quan hệ đồ thị (Graph Hints).

