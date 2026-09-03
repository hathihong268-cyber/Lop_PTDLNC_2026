# Wiki Risk Graph — Hệ Thống Tri Thức Đồ Thị Quản Trị Rủi Ro

Dự án xây dựng **Wiki Tri Thức Rủi Ro dạng Đồ thị (Wiki Risk Graph)** từ dữ liệu hồ sơ rủi ro, chốt kiểm soát và sự kiện rủi ro mô phỏng ngân hàng. Hệ thống hỗ trợ tra cứu đa chiều, duyệt đồ thị trên **Obsidian Graph View** và đồng bộ trực tiếp vào cơ sở dữ liệu đồ thị **Neo4j**.

---

## 🏗️ 1. Kiến Trúc Luồng Dữ Liệu (Pipeline)

```
[CSV Seed Data] ──► [Chuẩn hóa] ──► [entities.csv & relations.csv]
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
    [Wiki Markdown Vault]         [Neo4j Graph Database]
     (Obsidian Graph View)          (Cypher Queries / RAG)
```

### Mô hình Đồ thị MVP:
```
(:KiemSoat) ──[:MITIGATES]──► (:RuiRo) ──[:OBSERVED_AS]──► (:SuKienRuiRo)
```

---

## 📂 2. Cấu Trúc Thư Mục Dự Án

```text
buoi_13/
├── data/                               # Dữ liệu CSV seed ban đầu
│   ├── risk_profiles_seed.csv          # 12 hồ sơ rủi ro
│   ├── controls_seed.csv               # 10 chốt kiểm soát
│   ├── risk_events_seed.csv            # 12 sự kiện rủi ro
│   └── relationships_seed.csv          # 22 quan hệ (MITIGATES, OBSERVED_AS)
│
├── outputs/                            # Dữ liệu chuẩn hóa & báo cáo
│   ├── entities.csv                    # 34 thực thể chuẩn hóa
│   ├── relations.csv                   # 22 quan hệ chuẩn hóa
│   └── wiki_validation_report.md       # Báo cáo kiểm thử toàn vẹn Wiki
│
├── wiki/                               # Obsidian Vault
│   ├── Home.md                         # Trang chủ điều hướng Dashboard
│   ├── risks/                          # 12 trang hồ sơ rủi ro
│   ├── controls/                       # 10 trang chốt kiểm soát
│   └── events/                         # 12 trang sự kiện rủi ro
│
├── scripts/                            # Các script tự động hóa
│   ├── inspect_data.py                 # Bước 1: Kiểm tra dữ liệu seed
│   ├── build_entities.py               # Bước 2: Chuẩn hóa entities & relations
│   ├── build_wiki.py                   # Bước 3: Sinh Obsidian Wiki Vault
│   ├── validate_wiki.py                # Bước 4: Kiểm thử toàn vẹn Wiki
│   └── load_neo4j.py                   # Bước 6: Nạp dữ liệu vào Neo4j
│
├── cypher/                             # Định nghĩa Schema & Truy vấn Neo4j
│   ├── schema.cypher                   # Khởi tạo Constraints & Indexes
│   └── demo_queries.cypher             # Các truy vấn Cypher mẫu từ A -> F
│
├── .env.example                        # Mẫu cấu hình biến môi trường Neo4j
├── .env                                # Cấu hình kết nối thực tế
└── README.md                           # Hướng dẫn chi tiết dự án
```

---

## 🚀 3. Thứ Tự Các Lệnh Chạy Dự Án (Execution Workflow)

Thực hiện lần lượt các bước sau:

### Bước 1: Kiểm tra tính toàn vẹn dữ liệu gốc (Data Inspection)
Kiểm tra cấu trúc cột, số dòng, khóa chính, khóa ngoại, giá trị null và trùng lặp của 4 file seed CSV.
```bash
python scripts/inspect_data.py
```

---

### Bước 2: Chuẩn hóa dữ liệu sang Entities & Relations
Ánh xạ các bảng seed thành `outputs/entities.csv` (34 thực thể) và `outputs/relations.csv` (22 liên kết).
```bash
python scripts/build_entities.py
```

---

### Bước 3: Khởi tạo Wiki Markdown (Obsidian Vault)
Tự động sinh 35 trang Markdown với đầy đủ YAML Frontmatter, thuộc tính nghiệp vụ và các liên kết 2 chiều `[[wikilink]]`.
```bash
python scripts/build_wiki.py
```

---

### Bước 4: Kiểm thử tính toàn vẹn của Wiki (Validation)
Quét toàn bộ Vault để kiểm tra link gãy (broken links), trang mồ côi (orphan pages) và thống kê rủi ro chưa có kiểm soát (Unmitigated Risks).
```bash
python scripts/validate_wiki.py
```
> Kết quả báo cáo được lưu tại: `outputs/wiki_validation_report.md`.

---

### Bước 5: Mở và Quan Sát Trực Quan trên Obsidian
1. Khởi động ứng dụng **Obsidian**.
2. Chọn **Open folder as vault** $\rightarrow$ chọn thư mục `wiki/`.
3. Mở file `Home.md` để duyệt danh mục hoặc mở **Graph View** (`Ctrl + G`) để quan sát mạng lưới quan hệ giữa Kiểm soát, Rủi ro và Sự kiện.

---

### Bước 6: Đồng Bộ Dữ Liệu Vào Neo4j Graph Database
1. Đảm bảo Neo4j đang hoạt động và cấu hình kết nối trong file `.env`:
   ```env
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password_here
   NEO4J_DATABASE=neo4j
   ```
2. Chạy script nạp dữ liệu bằng Parameterized Cypher & `MERGE`:
   ```bash
   python scripts/load_neo4j.py
   ```

---

## 🔍 4. Bộ Truy Vấn Cypher Mẫu (Demo Queries)

Các truy vấn được lưu sẵn trong [`cypher/demo_queries.cypher`](file:///c:/Users/admins/Desktop/05_mẫu/Rag_thuchanh/RAG/rag_foundation/buoi_13/cypher/demo_queries.cypher):

- **Query A (Xem toàn bộ đồ thị):**
  ```cypher
  MATCH (n) OPTIONAL MATCH (n)-[r]->(m) RETURN n, r, m;
  ```

- **Query B (Tìm kiểm soát giảm thiểu rủi ro):**
  ```cypher
  MATCH (k:KiemSoat)-[r:MITIGATES]->(rr:RuiRo {id: 'RR-001'})
  RETURN k.id, k.name, k.control_type, r.evidence_quote, r.verification_status;
  ```

- **Query C (Tìm sự kiện rủi ro đã phát sinh):**
  ```cypher
  MATCH (rr:RuiRo {id: 'RR-001'})-[r:OBSERVED_AS]->(sk:SuKienRuiRo)
  RETURN sk.id, sk.description, sk.occurred_at, sk.loss_amount_vnd;
  ```

- **Query D (Tìm chuỗi quan hệ đầy đủ: KiemSoat -> RuiRo -> SuKienRuiRo):**
  ```cypher
  MATCH path = (k:KiemSoat)-[:MITIGATES]->(rr:RuiRo)-[:OBSERVED_AS]->(sk:SuKienRuiRo)
  RETURN k.name AS kiem_soat, rr.name AS rui_ro, sk.description AS su_kien, sk.loss_amount_vnd AS ton_that;
  ```

- **Query E (Tìm rủi ro chưa có chốt kiểm soát - Unmitigated Risks):**
  ```cypher
  MATCH (rr:RuiRo)
  WHERE NOT ( (:KiemSoat)-[:MITIGATES]->(rr) )
  RETURN rr.id, rr.name, rr.category, rr.owner_unit_id;
  ```

- **Query F (Tìm các quan hệ chưa xác minh / PROPOSED):**
  ```cypher
  MATCH (s)-[r]->(t)
  WHERE coalesce(r.verification_status, 'PROPOSED') <> 'VERIFIED'
  RETURN s.id, type(r), t.id, r.confidence, r.verification_status;
  ```
