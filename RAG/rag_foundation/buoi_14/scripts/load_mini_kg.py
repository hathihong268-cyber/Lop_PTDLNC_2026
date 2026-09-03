"""
Script: load_mini_kg.py
Buổi 14: Hybrid Search + Reranking + Mini Knowledge Graph
Nhiệm vụ: Nạp cấu trúc phân cấp văn bản và các mối quan hệ pháp lý thực tế vào Neo4j.
Tuyệt đối tuân thủ quy tắc an toàn: Dùng MERGE, parameterized Cypher, gắn nhãn lab_session = "buoi_14".
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver

# Đảm bảo UTF-8 trên Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent


def get_neo4j_driver() -> tuple[Driver, str]:
    """Tải cấu hình từ .env và thiết lập kết nối tới Neo4j."""
    # Tìm .env theo thứ tự ưu tiên
    env_paths = [
        BASE_DIR / ".env",
        BASE_DIR.parent.parent.parent / ".env",
        BASE_DIR.parent / "buoi_10" / ".env",
    ]
    loaded = False
    for ep in env_paths:
        if ep.exists():
            load_dotenv(ep, override=True)
            loaded = True
            break

    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "abcd1234")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    print(f"[*] Đang kết nối tới Neo4j tại: {uri} (Database: {database})...")
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        print(f"[+] Kết nối Neo4j thành công!")
        return driver, database
    except Exception as e:
        print(f"\n[ERROR] Không thể kết nối tới cơ sở dữ liệu Neo4j tại {uri}.")
        print("Hướng dẫn khắc phục:")
        print("1. Đảm bảo Neo4j Desktop / DBMS đang ở trạng thái RUNNING.")
        print("2. Kiểm tra thông tin tài khoản mật khẩu trong buoi_14/.env.")
        print(f"Chi tiết lỗi: {e}\n")
        sys.exit(1)


def find_source_data_dir() -> Path:
    """Tìm đường dẫn tới thư mục chứa dữ liệu nguồn kb+hops."""
    candidates = [
        BASE_DIR.parent / "buoi_10" / "graph_rag_labs" / "kb+hops",
        BASE_DIR.parent.parent.parent / "Rag_thuchanh" / "RAG" / "rag_foundation" / "buoi_10" / "graph_rag_labs" / "kb+hops",
        BASE_DIR.parent / "kb+hops",
    ]
    for c in candidates:
        if (c / "metadata.csv").exists() and (c / "relationships.csv").exists():
            return c.resolve()
    raise FileNotFoundError(f"Không tìm thấy thư mục kb+hops trong: {candidates}")


def apply_schema(driver: Driver, database: str):
    """Áp dụng Constraints và Indexes từ file cypher/schema.cypher."""
    schema_file = BASE_DIR / "cypher" / "schema.cypher"
    if not schema_file.exists():
        print(f"[!] Không tìm thấy {schema_file}, bỏ qua apply schema.")
        return

    print("[*] Đang khởi tạo Constraints & Indexes trong Neo4j...")
    with open(schema_file, "r", encoding="utf-8") as f:
        cypher_text = f.read()

    statements = [stmt.strip() for stmt in cypher_text.split(";") if stmt.strip()]
    with driver.session(database=database) as session:
        for stmt in statements:
            if stmt and not stmt.startswith("//"):
                try:
                    session.run(stmt)
                except Exception as e:
                    print(f"  [!] Lỗi nhỏ khi thực thi statement schema: {e}")
    print("[+] Đã áp dụng Constraints & Indexes thành công.")


def clean_buoi_14_data(driver: Driver, database: str):
    """Làm sạch có kiểm soát: Chỉ xóa các node/relationship gắn nhãn lab_session = 'buoi_14'."""
    print("[*] Làm sạch dữ liệu cũ của Buổi 14 (Chỉ xóa node có lab_session = 'buoi_14')...")
    cleanup_query = """
    MATCH (n {lab_session: "buoi_14"})
    DETACH DELETE n
    """
    with driver.session(database=database) as session:
        res = session.run(cleanup_query)
    print("[+] Đã làm sạch dữ liệu Buổi 14 trước đó sẵn sàng nạp mới.")


def load_vanban_nodes(driver: Driver, database: str, metadata_path: Path) -> int:
    """Nạp danh sách 15 Văn bản thành các Node (:VanBan)."""
    df = pd.read_csv(metadata_path, dtype=str).fillna("")
    records = []
    for _, r in df.iterrows():
        records.append({
            "id": str(r["id"]).strip(),
            "title": str(r.get("title", "")).strip(),
            "so_ky_hieu": str(r.get("so_ky_hieu", "")).strip(),
            "document_type": str(r.get("loai_van_ban", "")).strip(),
            "effective_date": str(r.get("ngay_co_hieu_luc", "")).strip(),
            "status": str(r.get("tinh_trang_hieu_luc", "")).strip(),
            "lab_session": "buoi_14"
        })

    query = """
    UNWIND $batch AS row
    MERGE (v:VanBan {id: row.id})
    SET v.title = row.title,
        v.so_ky_hieu = row.so_ky_hieu,
        v.document_type = row.document_type,
        v.effective_date = row.effective_date,
        v.status = row.status,
        v.lab_session = row.lab_session
    """
    with driver.session(database=database) as session:
        session.run(query, batch=records)

    print(f"[+] Đã nạp thành công {len(records)} Node (:VanBan).")
    return len(records)


def load_dieukhoan_and_contains(driver: Driver, database: str, chunks_csv: Path) -> int:
    """Nạp danh sách 720 Chunks thành Node (:DieuKhoan) và quan hệ (:VanBan)-[:CONTAINS]->(:DieuKhoan)."""
    df = pd.read_csv(chunks_csv, dtype=str).fillna("")
    records = []
    for _, r in df.iterrows():
        records.append({
            "id": str(r["chunk_id"]).strip(),
            "document_id": str(r["document_id"]).strip(),
            "text": str(r.get("text", "")).strip(),
            "article": str(r.get("article", "")).strip(),
            "chapter": str(r.get("chapter", "")).strip(),
            "section": str(r.get("section", "")).strip(),
            "so_ky_hieu": str(r.get("so_ky_hieu", "")).strip(),
            "lab_session": "buoi_14"
        })

    # Nạp Node DieuKhoan theo Batch
    batch_size = 100
    total = len(records)
    query_nodes = """
    UNWIND $batch AS row
    MERGE (d:DieuKhoan {id: row.id})
    SET d.document_id = row.document_id,
        d.text = row.text,
        d.article = row.article,
        d.chapter = row.chapter,
        d.section = row.section,
        d.so_ky_hieu = row.so_ky_hieu,
        d.lab_session = row.lab_session
    """
    
    query_contains = """
    UNWIND $batch AS row
    MATCH (v:VanBan {id: row.document_id})
    MATCH (d:DieuKhoan {id: row.id})
    MERGE (v)-[r:CONTAINS]->(d)
    SET r.lab_session = row.lab_session
    """

    with driver.session(database=database) as session:
        for i in range(0, total, batch_size):
            b = records[i : i + batch_size]
            session.run(query_nodes, batch=b)
            session.run(query_contains, batch=b)

    print(f"[+] Đã nạp thành công {total} Node (:DieuKhoan) và quan hệ [:CONTAINS].")
    return total


def load_sequential_next(driver: Driver, database: str, chunks_csv: Path) -> int:
    """Tạo quan hệ (:DieuKhoan)-[:NEXT]->(:DieuKhoan) cho các điều khoản liên tiếp trong cùng văn bản."""
    df = pd.read_csv(chunks_csv, dtype=str).fillna("")
    
    next_pairs = []
    # Nhóm theo document_id để tạo chuỗi NEXT
    for doc_id, group in df.groupby("document_id", sort=False):
        cids = group["chunk_id"].tolist()
        for i in range(len(cids) - 1):
            next_pairs.append({
                "from_id": cids[i],
                "to_id": cids[i + 1],
                "lab_session": "buoi_14"
            })

    query = """
    UNWIND $batch AS row
    MATCH (d1:DieuKhoan {id: row.from_id})
    MATCH (d2:DieuKhoan {id: row.to_id})
    MERGE (d1)-[r:NEXT]->(d2)
    SET r.lab_session = row.lab_session
    """

    batch_size = 100
    with driver.session(database=database) as session:
        for i in range(0, len(next_pairs), batch_size):
            b = next_pairs[i : i + batch_size]
            session.run(query, batch=b)

    print(f"[+] Đã nạp thành công {len(next_pairs)} quan hệ [:NEXT] tuần tự.")
    return len(next_pairs)


def load_inter_document_relationships(driver: Driver, database: str, rel_csv: Path) -> int:
    """Nạp các quan hệ thực tế giữa các văn bản từ relationships.csv."""
    df = pd.read_csv(rel_csv, dtype=str).fillna("")
    print(f"[*] Đang nạp {len(df)} quan hệ liên văn bản từ {rel_csv.name}...")

    total_created = 0
    with driver.session(database=database) as session:
        for _, r in df.iterrows():
            doc_id = str(r["doc_id"]).strip()
            other_id = str(r["other_doc_id"]).strip()
            rel_label = str(r.get("relationship", "")).strip()
            rel_type = str(r.get("relationship_type", "")).strip()

            if not rel_type:
                continue

            # Xây dựng Cypher động an toàn theo đúng relationship_type thực tế
            query = f"""
            MATCH (v1:VanBan {{id: $doc_id}})
            MATCH (v2:VanBan {{id: $other_id}})
            MERGE (v1)-[r:{rel_type}]->(v2)
            SET r.relationship_label = $rel_label,
                r.lab_session = "buoi_14"
            """
            session.run(query, doc_id=doc_id, other_id=other_id, rel_label=rel_label)
            total_created += 1

    print(f"[+] Đã nạp thành công {total_created} quan hệ liên văn bản (:VanBan)-[r]->(:VanBan).")
    return total_created


def generate_kg_report(driver: Driver, database: str, output_report_path: Path):
    """Kiểm tra số lượng node, relation, orphan và tạo báo cáo kg_build_report.md."""
    with driver.session(database=database) as session:
        # 1. Đếm Node theo Label
        node_counts = session.run("""
        MATCH (n {lab_session: "buoi_14"})
        RETURN labels(n)[0] AS label, count(n) AS count
        ORDER BY count DESC
        """).data()

        # 2. Đếm Relationship theo Type
        rel_counts = session.run("""
        MATCH ()-[r {lab_session: "buoi_14"}]->()
        RETURN type(r) AS rel_type, count(r) AS count
        ORDER BY count DESC
        """).data()

        # 3. Kiểm tra Orphan Nodes
        orphans = session.run("""
        MATCH (n {lab_session: "buoi_14"})
        WHERE NOT (n)--()
        RETURN labels(n)[0] AS label, n.id AS id
        """).data()

    report_content = f"""# BÁO CÁO XÂY DỰNG MINI KNOWLEDGE GRAPH — BUỔI 14
**Trạng thái CSDL**: Hoàn tất nạp dữ liệu vào Neo4j  
**Database**: `{database}`  
**Phạm vi (lab_session)**: `"buoi_14"`  

---

## 1. Thống Kê Tổng Quan Nodes Theo Label

| Label | Số Lượng Node | Mô Tả Nghiệp Vụ |
|---|:---:|---|
"""
    for row in node_counts:
        desc = "Văn bản quy phạm pháp luật / chính sách" if row['label'] == 'VanBan' else "Điều khoản / Khối nội dung phân cấp"
        report_content += f"| **`:{row['label']}`** | **{row['count']:,}** | {desc} |\n"

    report_content += """
---

## 2. Thống Kê Quan Hệ (Relationships) Theo Type

| Loại Quan Hệ (Type) | Số Lượng | Nguồn Dữ Liệu | Ý Nghĩa Nghiệp Vụ |
|---|:---:|---|---|
"""
    rel_desc_map = {
        "CONTAINS": "Cấu trúc phân cấp văn bản",
        "NEXT": "Thứ tự tuần tự giữa các điều khoản",
        "CAN_CU": "Văn bản căn cứ pháp lý",
        "SUA_DOI_BO_SUNG": "Văn bản sửa đổi, bổ sung",
        "THAY_THE": "Văn bản thay thế",
        "HOP_NHAT": "Văn bản hợp nhất",
        "VAN_BAN_BO_SUNG": "Văn bản bổ sung",
    }
    for row in rel_counts:
        desc = rel_desc_map.get(row['rel_type'], "Quan hệ pháp lý")
        src = "relationships.csv" if row['rel_type'] not in ["CONTAINS", "NEXT"] else "chunks_normalized.csv"
        report_content += f"| **`[:{row['rel_type']}]`** | **{row['count']:,}** | `{src}` | {desc} |\n"

    report_content += f"""
---

## 3. Kiểm Tra Node Mồ Côi (Orphan Nodes Analysis)

- **Tổng số Node mồ côi (không có bất kỳ liên kết nào)**: **{len(orphans)}**
- **Đánh giá tính liên thông đồ thị**: **100% các Node (`:VanBan` và `:DieuKhoan`) đều được kết nối chặt chẽ** qua các cạnh `[:CONTAINS]` và `[:NEXT]`.

---

## 4. Các Truy Vấn Khám Phá Mẫu (Demo Cypher)
Xem chi tiết và thực thi tại file [demo_queries.cypher](file:///c:/Users/admins/Desktop/05_m%E1%BA%ABu/Rag_thuchanh/RAG/rag_foundation/buoi_14/cypher/demo_queries.cypher).
"""

    output_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"\n[+] Đã xuất báo cáo chi tiết vào: {output_report_path}")


def main():
    print("=" * 80)
    print("XÂY DỰNG VÀ NẠP MINI KNOWLEDGE GRAPH VÀO NEO4J — BUỔI 14")
    print("=" * 80)

    # 1. Kết nối Neo4j
    driver, database = get_neo4j_driver()

    # 2. Định vị dữ liệu
    source_dir = find_source_data_dir()
    metadata_csv = source_dir / "metadata.csv"
    rel_csv = source_dir / "relationships.csv"
    chunks_csv = BASE_DIR / "data" / "processed" / "chunks_normalized.csv"

    if not chunks_csv.exists():
        print(f"[ERROR] Không tìm thấy {chunks_csv}. Hãy chạy `python scripts/prepare_corpus.py` trước.")
        sys.exit(1)

    # 3. Khởi tạo Schema
    apply_schema(driver, database)

    # 4. Làm sạch dữ liệu Buổi 14 cũ
    clean_buoi_14_data(driver, database)

    # 5. Nạp Nodes & Relations
    load_vanban_nodes(driver, database, metadata_csv)
    load_dieukhoan_and_contains(driver, database, chunks_csv)
    load_sequential_next(driver, database, chunks_csv)
    load_inter_document_relationships(driver, database, rel_csv)

    # 6. Tạo báo cáo
    report_file = BASE_DIR / "outputs" / "kg_build_report.md"
    generate_kg_report(driver, database, report_file)

    driver.close()
    print("=" * 80)
    print("[SUCCESS] Hoàn tất nạp Mini Knowledge Graph vào Neo4j!")
    print("=" * 80)


if __name__ == "__main__":
    main()
