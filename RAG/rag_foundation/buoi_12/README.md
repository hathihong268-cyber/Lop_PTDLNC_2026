# Buổi 12: Chuẩn Hóa, Làm Giàu Metadata và Xây Dựng Đồ Thị Tri Thức (Knowledge Graph)

## 📌 1. Tổng Quan

Bài thực hành tập trung vào việc chuẩn hóa và làm giàu metadata từ tập 30 văn bản pháp quy ngân hàng (`ner_kb/metadata.csv` và `ner_kb/content.csv`) bằng cách kết hợp:
1. **Rule-based Extraction & HTML Cleaning**: Xử lý dữ liệu văn bản pháp luật, bóc tách cấu trúc số hiệu, căn cứ, điều khoản.
2. **LLM với Google Gemini**: Trích xuất thực thể chuyên sâu (Cơ quan ban hành, Người ký, Đối tượng áp dụng, Phạm vi điều chỉnh).
3. **Graph Construction & Validation**: Chuẩn hóa thực thể, xây dựng các liên kết quan hệ (Căn cứ, Sửa đổi bổ sung, Thay thế, Đối tượng áp dụng) và kiểm định bằng chứng trích xuất.
4. **Neo4j Graph Database**: Nạp toàn bộ thực thể và quan hệ vào cơ sở dữ liệu đồ thị, thiết lập ràng buộc duy nhất và truy vấn multi-hop.

---

## 🏗️ 2. Kiến Trúc Pipeline (9 Bước)

```text
Raw Data (HTML & CSV)
   │
   ▼
[Bước 1: buoi_12_step1.py] ──► Làm sạch HTML & Kiểm tra dữ liệu (cleaned_documents.csv)
   │
   ▼
[Bước 2: buoi_12_step2.py] ──► Rule-based Candidate Extraction (relation_candidates.csv)
   │
   ▼
[Bước 3: buoi_12_step3.py] ──► Gemini Entity Extraction & Metadata Enrichment (enriched_metadata.csv)
   │
   ▼
[Bước 4: buoi_12_step4.py] ──► Chuẩn hóa Entity / Normalization (entities.csv)
   │
   ▼
[Bước 5: buoi_12_step5.py] ──► Relationship Extraction (relationships_raw.csv)
   │
   ▼
[Bước 6: buoi_12_step6.py] ──► Relationship Validation & Deduplication (relationships.csv, validation_report.csv)
   │
   ▼
[Bước 7: buoi_12_step7.py] ──► Kiểm tra kết nối Neo4j (Connectivity & Driver verification)
   │
   ▼
[Bước 8: buoi_12_step8.py] ──► Import Knowledge Graph vào Neo4j (Parameterized MERGE & Constraints)
   │
   ▼
[Bước 9: buoi_12_step9.py] ──► Kiểm tra và đánh giá Knowledge Graph sau Import (Multi-hop verification)
```

---

## 📂 3. Cấu Trúc Thư Mục

```text
buoi_12/
├── ner_kb/
│   ├── metadata.csv                 # 30 văn bản pháp quy gốc
│   ├── content.csv                  # Nội dung HTML nguyên bản
│   ├── cleaned_documents.csv        # Văn bản sau khi bóc tách & làm sạch HTML
│   ├── relation_candidates.csv      # Các ứng viên quan hệ trích xuất bằng quy tắc regex
│   ├── extracted_entities_raw.csv   # Thực thể thô do Gemini trích xuất
│   ├── enriched_metadata.csv        # Metadata đã làm giàu (Người ký, Ngày, Cơ quan...)
│   ├── entities.csv                 # Tập thực thể đã chuẩn hóa ID và Type
│   ├── relationships_raw.csv        # Tập quan hệ thô kèm trích dẫn văn bản
│   ├── relationships.csv            # Tập quan hệ chính thức đã kiểm định
│   └── validation_report.csv        # Báo cáo đánh giá bằng chứng và độ tin cậy
│
├── buoi_12_step1.py                 # Bước 1: HTML Cleaning & Text Extraction
├── buoi_12_step2.py                 # Bước 2: Rule-based Candidate Extraction
├── buoi_12_step3.py                 # Bước 3: Entity Extraction & Metadata Enrichment bằng Gemini
├── buoi_12_step4.py                 # Bước 4: Chuẩn hóa thực thể (CoQuan, NguoiKy, DoiTuong...)
├── buoi_12_step5.py                 # Bước 5: Bóc tách quan hệ đa chiều
├── buoi_12_step6.py                 # Bước 6: Kiểm tra tính toàn vẹn quan hệ & Bằng chứng
├── buoi_12_step7.py                 # Bước 7: Kiểm tra kết nối cơ sở dữ liệu Neo4j
├── buoi_12_step8.py                 # Bước 8: Nạp Knowledge Graph vào Neo4j
├── buoi_12_step9.py                 # Bước 9: Kiểm tra đồ thị & Truy vấn chuỗi quan hệ
│
├── buoi_12.md                       # Tài liệu hướng dẫn chi tiết từng prompt
└── README.md                        # Hướng dẫn tổng quan & Lệnh thực thi
```

---

## 🚀 4. Hướng Dẫn Chạy Pipeline

Chạy lần lượt các bước từ terminal:

```bash
# Bước 1: Làm sạch dữ liệu HTML
python buoi_12_step1.py

# Bước 2: Trích xuất quan hệ căn cứ ban đầu
python buoi_12_step2.py

# Bước 3: Làm giàu Metadata với Gemini LLM (cần cấu hình GEMINI_API_KEY)
python buoi_12_step3.py

# Bước 4: Chuẩn hóa thực thể
python buoi_12_step4.py

# Bước 5: Bóc tách quan hệ
python buoi_12_step5.py

# Bước 6: Xác thực quan hệ và trích dẫn bằng chứng
python buoi_12_step6.py

# Bước 7: Kiểm tra kết nối Neo4j
python buoi_12_step7.py

# Bước 8: Import dữ liệu vào Neo4j
python buoi_12_step8.py

# Bước 9: Kiểm thử đồ thị tri thức
python buoi_12_step9.py
```

---

## 🛡️ 5. Các Ràng Buộc & Nguyên Tắc Vàng

1. **Bảo toàn dữ liệu gốc**: Không ghi đè hoặc chỉnh sửa trực tiếp 2 file dữ liệu nguồn `metadata.csv` và `content.csv`.
2. **Không ảo giác (Zero Hallucination)**: Mọi quan hệ giữa các văn bản hoặc thực thể đều phải có trích dẫn bằng chứng (`evidence_quote`) cụ thể từ văn bản.
3. **Kiểm tra trước khi nạp**: Toàn bộ output của LLM được chuẩn hóa và kiểm tra qua quy tắc trước khi nạp vào Neo4j.
4. **Parameterized Cypher**: Quá trình nạp Neo4j sử dụng tham số hóa và lệnh `MERGE` để đảm bảo tính an toàn và khả năng chạy lại (Idempotent).
