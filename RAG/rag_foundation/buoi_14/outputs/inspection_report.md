# BÁO CÁO KIỂM TRA DỮ LIỆU VÀ MÔI TRƯỜNG DỰ ÁN — BUỔI 14

**Chủ đề**: *Hybrid Search + Reranking + Mini Knowledge Graph*  
**Thư mục làm việc**: `RAG/rag_foundation/buoi_14`  

---

## 1. Cấu Trúc Thư Mục & File Hiện Có Trong `buoi_14/`

- **Scripts**: prepare_corpus.py, baseline_retrieval.py, hybrid_search.py, rerank.py, compare_retrieval.py, load_mini_kg.py, query_demo.py, inspect_project.py.
- **Src**: bm25_retriever.py, dense_retriever.py, hybrid_retriever.py, reranker.py, citation.py, unified_retriever.py.
- **Outputs**: inspection_report.md, retrieval_examples.md, retrieval_comparison.csv, evaluation_report.md, kg_build_report.md.
- **Cypher**: schema.cypher, demo_queries.cypher.
- **Web App**: app.py (Streamlit).

---

## 2. Thẩm Định Chi Tiết 3 File Dữ Liệu Nguồn (`kb+hops/`)

> [!IMPORTANT]
> Toàn bộ 3 file nguồn trong `D:\Lop PTDLNC 2026\RAG\rag_foundation\buoi_10\graph_rag_labs\kb+hops` được **đọc trực tiếp ở chế độ CHỈ ĐỌC (Read-Only)**. Không copy, move, sửa đổi hay ghi đè.

### 2.1. `metadata.csv`
- **Đường dẫn**: `D:\Lop PTDLNC 2026\RAG\rag_foundation\buoi_10\graph_rag_labs\kb+hops\metadata.csv`
- **Dung lượng**: 5,966 bytes
- **Encoding**: `UTF-8`
- **Tổng số dòng**: **15 dòng** (15 văn bản pháp quy)
- **Số cột**: 17 cột: id, title, so_ky_hieu, ngay_ban_hanh, loai_van_ban, ngay_co_hieu_luc, ngay_het_hieu_luc, nguon_thu_thap, ngay_dang_cong_bao, nganh, linh_vuc, co_quan_ban_hanh, chuc_danh, nguoi_ky, pham_vi, thong_tin_ap_dung, tinh_trang_hieu_luc
- **Trùng lặp**: 0 dòng
- **Khóa chính**: `id` và `so_ky_hieu`
- **Trường text phù hợp retrieval**: `title`
- **Metadata phù hợp citation**: `id`, `so_ky_hieu`, `title`, `loai_van_ban`, `ngay_ban_hanh`, `co_quan_ban_hanh`, `tinh_trang_hieu_luc`

### 2.2. `content.csv`
- **Đường dẫn**: `D:\Lop PTDLNC 2026\RAG\rag_foundation\buoi_10\graph_rag_labs\kb+hops\content.csv`
- **Dung lượng**: 3,064,964 bytes
- **Encoding**: `UTF-8`
- **Tổng số dòng**: **15 dòng** (15 văn bản HTML)
- **Số cột**: 2 cột: id, content_html
- **Trùng lặp**: 0 dòng
- **Khóa chính**: `id` khớp 1-1 với `metadata.csv`

### 2.3. `relationships.csv`
- **Đường dẫn**: `D:\Lop PTDLNC 2026\RAG\rag_foundation\buoi_10\graph_rag_labs\kb+hops\relationships.csv`
- **Dung lượng**: 378 bytes
- **Encoding**: `UTF-8`
- **Tổng số dòng**: **8 dòng** (quan hệ liên văn bản thực tế)
- **Số cột**: 4 cột: doc_id, other_doc_id, relationship, relationship_type
- **Trùng lặp**: 0 dòng
- **Loại quan hệ thực tế**: `CAN_CU`, `THAY_THE`, `SUA_DOI_BO_SUNG`, `HOP_NHAT`, `VAN_BAN_BO_SUNG`

---

## 3. Kiểm Tra An Toàn Mã Nguồn
- Không có lệnh xóa trắng đồ thị Neo4j (`DETACH DELETE n` toàn cục bị cấm tuyệt đối).
- Mọi node/cạnh đều có nhãn `lab_session = 'buoi_14'`.
- Toàn bộ dữ liệu trung gian và output được ghi độc lập trong `buoi_14/`.

---

## 4. Kết Luận Kiểm Tra
- **Python**: 3.14.7
- **Safe to continue**: YES
