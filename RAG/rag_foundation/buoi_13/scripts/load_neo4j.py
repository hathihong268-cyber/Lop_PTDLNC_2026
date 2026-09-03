#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/load_neo4j.py
Nạp dữ liệu từ outputs/entities.csv và outputs/relations.csv vào Neo4j Knowledge Graph.

Tuân thủ:
- Sử dụng Parameterized Cypher 100%
- Dùng MERGE để chạy lại an toàn (Idempotent)
- Đọc cấu hình bảo mật từ .env (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE)
- Báo lỗi và hướng dẫn chi tiết nếu Neo4j chưa khởi động
"""

import csv
import os
import sys
from pathlib import Path

# Đảm bảo in Unicode tiếng Việt mượt mà trên Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def load_env_file():
    """Đọc file .env nếu có, kết hợp với biến môi trường hệ thống."""
    # Tìm file .env trong các thư mục khả dĩ
    env_paths = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent / ".env",
        Path.cwd() / "Rag_thuchanh" / "RAG" / "rag_foundation" / "buoi_13" / ".env",
        Path(__file__).resolve().parent.parent / "Rag_thuchanh" / "RAG" / "rag_foundation" / "buoi_13" / ".env",
    ]
    for ep in env_paths:
        if ep.exists():
            try:
                with open(ep, mode="r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass
            break


def find_outputs_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent / "outputs",
        Path.cwd() / "outputs",
        Path.cwd() / "Rag_thuchanh" / "RAG" / "rag_foundation" / "buoi_13" / "outputs",
        Path(__file__).resolve().parent.parent / "Rag_thuchanh" / "RAG" / "rag_foundation" / "buoi_13" / "outputs",
    ]
    for p in candidates:
        if (p / "entities.csv").exists() and (p / "relations.csv").exists():
            return p
    raise FileNotFoundError("Không tìm thấy outputs/entities.csv và outputs/relations.csv! Hãy chạy build_entities.py trước.")


def read_csv(file_path: Path):
    with open(file_path, mode="r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    load_env_file()

    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    print("=" * 80)
    print("BƯỚC 6: NẠP DỮ LIỆU WIKI RISK GRAPH VÀO NEO4J")
    print(f"Neo4j URI:      {uri}")
    print(f"Neo4j User:     {user}")
    print(f"Neo4j Database: {database}")
    print("=" * 80)

    if not password or password == "your_password_here":
        print("\n[HƯỚNG DẪN CẤU HÌNH NEO4J]")
        print("1. Chưa tìm thấy mật khẩu hợp lệ trong file .env!")
        print("2. Hãy tạo hoặc chỉnh sửa file .env với thông tin kết nối thực tế:")
        print("   NEO4J_URI=bolt://localhost:7687")
        print("   NEO4J_USER=neo4j")
        print("   NEO4J_PASSWORD=<mat_khau_cua_ban>")
        print("   NEO4J_DATABASE=neo4j")
        print("3. Nếu bạn đang dùng Neo4j Desktop hoặc Docker:")
        print("   docker run -d --name neo4j-lab -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password123 neo4j:5-community")
        print("=" * 80)
        sys.exit(0)

    try:
        from neo4j import GraphDatabase, exceptions
    except ImportError:
        print("\n[LỖI THIẾU THƯ VIỆN]")
        print("Chưa cài đặt thư viện 'neo4j'. Vui lòng chạy lệnh:")
        print("   pip install neo4j")
        print("=" * 80)
        sys.exit(1)

    # Thử kết nối tới Neo4j
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session(database=database) as session:
            session.run("RETURN 1 AS test").single()
        print("\n[KẾT NỐI THÀNH CÔNG] Đã kết nối thành công tới Neo4j Instance!")
    except Exception as e:
        print("\n[CẢNH BÁO: KHÔNG THỂ KẾT NỐI TỚI NEO4J]")
        print(f"Chi tiết lỗi kết nối: {e}")
        print("\nHướng dẫn khắc phục:")
        print("1. Kiểm tra dịch vụ Neo4j đã được khởi động (Active) hay chưa.")
        print("2. Đảm bảo cổng 7687 (Bolt) và 7474 (HTTP) không bị chặn.")
        print("3. Kiểm tra lại user/password trong file .env.")
        print("4. Toàn bộ dữ liệu Wiki Markdown và báo cáo CSV trước đó vẫn an toàn tuyệt đối.")
        print("=" * 80)
        sys.exit(0)

    # Đọc dữ liệu từ outputs/
    outputs_dir = find_outputs_dir()
    entities = read_csv(outputs_dir / "entities.csv")
    relations = read_csv(outputs_dir / "relations.csv")

    # Phân loại entities
    risks = [e for e in entities if e["type"] == "RuiRo"]
    controls = [e for e in entities if e["type"] == "KiemSoat"]
    events = [e for e in entities if e["type"] == "SuKienRuiRo"]

    mitigates_rels = [r for r in relations if r["relationship_type"] == "MITIGATES"]
    observed_rels = [r for r in relations if r["relationship_type"] == "OBSERVED_AS"]

    with driver.session(database=database) as session:
        # 1. Tạo Ràng buộc duy nhất (Constraints)
        print("\n1. Khởi tạo Schema & Unique Constraints...")
        session.run("CREATE CONSTRAINT rui_ro_id_unique IF NOT EXISTS FOR (r:RuiRo) REQUIRE r.id IS UNIQUE;")
        session.run("CREATE CONSTRAINT kiem_soat_id_unique IF NOT EXISTS FOR (k:KiemSoat) REQUIRE k.id IS UNIQUE;")
        session.run("CREATE CONSTRAINT su_kien_rui_ro_id_unique IF NOT EXISTS FOR (s:SuKienRuiRo) REQUIRE s.id IS UNIQUE;")
        print("   -> Đã tạo Constraints cho (:RuiRo), (:KiemSoat), (:SuKienRuiRo)")

        # 2. Nạp Nodes RuiRo
        print(f"\n2. Đang nạp {len(risks)} nodes :RuiRo...")
        cypher_risks = """
        UNWIND $batch AS row
        MERGE (r:RuiRo {id: row.id})
        SET r.name = row.name,
            r.category = row.category,
            r.description = row.description,
            r.cause = row.cause,
            r.event = row.event,
            r.impact = row.impact,
            r.inherent_level = row.inherent_level,
            r.residual_level = row.residual_level,
            r.owner_unit_id = row.owner_unit_id,
            r.data_origin = row.data_origin,
            r.verification_status = row.verification_status
        """
        session.run(cypher_risks, batch=risks)
        print(f"   -> Đã MERGE thành công {len(risks)} nodes :RuiRo")

        # 3. Nạp Nodes KiemSoat
        print(f"\n3. Đang nạp {len(controls)} nodes :KiemSoat...")
        cypher_controls = """
        UNWIND $batch AS row
        MERGE (k:KiemSoat {id: row.id})
        SET k.name = row.name,
            k.description = row.description,
            k.control_type = row.control_type,
            k.frequency = row.frequency,
            k.owner_role_id = row.owner_role_id,
            k.effectiveness = row.effectiveness,
            k.data_origin = row.data_origin,
            k.verification_status = row.verification_status
        """
        session.run(cypher_controls, batch=controls)
        print(f"   -> Đã MERGE thành công {len(controls)} nodes :KiemSoat")

        # 4. Nạp Nodes SuKienRuiRo
        print(f"\n4. Đang nạp {len(events)} nodes :SuKienRuiRo...")
        # Parse numeric loss amount
        for ev in events:
            try:
                ev["loss_amount_vnd"] = float(ev["loss_amount_vnd"]) if ev["loss_amount_vnd"] else 0.0
            except ValueError:
                ev["loss_amount_vnd"] = 0.0

        cypher_events = """
        UNWIND $batch AS row
        MERGE (s:SuKienRuiRo {id: row.id})
        SET s.name = row.name,
            s.description = row.description,
            s.risk_id = row.risk_id,
            s.occurred_at = row.occurred_at,
            s.discovered_at = row.discovered_at,
            s.severity = row.severity,
            s.loss_amount_vnd = row.loss_amount_vnd,
            s.data_origin = row.data_origin,
            s.verification_status = row.verification_status
        """
        session.run(cypher_events, batch=events)
        print(f"   -> Đã MERGE thành công {len(events)} nodes :SuKienRuiRo")

        # 5. Nạp Edges MITIGATES: (:KiemSoat)-[:MITIGATES]->(:RuiRo)
        print(f"\n5. Đang nạp {len(mitigates_rels)} edges [:MITIGATES]...")
        for mr in mitigates_rels:
            mr["confidence"] = float(mr.get("confidence", 1.0))

        cypher_mitigates = """
        UNWIND $batch AS row
        MATCH (k:KiemSoat {id: row.source_id})
        MATCH (r:RuiRo {id: row.target_id})
        MERGE (k)-[rel:MITIGATES]->(r)
        SET rel.source = row.source,
            rel.evidence_quote = row.evidence_quote,
            rel.confidence = row.confidence,
            rel.verification_status = row.verification_status,
            rel.data_origin = row.data_origin
        """
        session.run(cypher_mitigates, batch=mitigates_rels)
        print(f"   -> Đã MERGE thành công {len(mitigates_rels)} edges [:MITIGATES]")

        # 6. Nạp Edges OBSERVED_AS: (:RuiRo)-[:OBSERVED_AS]->(:SuKienRuiRo)
        print(f"\n6. Đang nạp {len(observed_rels)} edges [:OBSERVED_AS]...")
        for obr in observed_rels:
            obr["confidence"] = float(obr.get("confidence", 1.0))

        cypher_observed = """
        UNWIND $batch AS row
        MATCH (r:RuiRo {id: row.source_id})
        MATCH (s:SuKienRuiRo {id: row.target_id})
        MERGE (r)-[rel:OBSERVED_AS]->(s)
        SET rel.source = row.source,
            rel.evidence_quote = row.evidence_quote,
            rel.confidence = row.confidence,
            rel.verification_status = row.verification_status,
            rel.data_origin = row.data_origin
        """
        session.run(cypher_observed, batch=observed_rels)
        print(f"   -> Đã MERGE thành công {len(observed_rels)} edges [:OBSERVED_AS]")

        # 7. Thống kê kết quả trên database
        node_count = session.run("MATCH (n) RETURN count(n) AS total").single()["total"]
        rel_count = session.run("MATCH ()-[r]->() RETURN count(r) AS total").single()["total"]

        print("\n--- BÁO CÁO NẠP NEO4J THÀNH CÔNG ---")
        print(f"- Tổng số Node trong database:      {node_count}")
        print(f"- Tổng số Quan hệ trong database:  {rel_count}")

    driver.close()
    print("\n" + "=" * 80)
    print("HOÀN TẤT NẠP NEO4J BƯỚC 6")
    print("=" * 80)


if __name__ == "__main__":
    main()
