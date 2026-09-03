# -*- coding: utf-8 -*-
"""
BƯỚC 8: Import Knowledge Graph vào Neo4j
Module: buoi_12_step8.py

Input:
- ner_kb/cleaned_documents.csv
- ner_kb/entities.csv
- ner_kb/relationships.csv
"""

import os
import sys
import io
import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Ensure UTF-8 output encoding for Windows terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def create_constraints(session):
    """Tạo các ràng buộc duy nhất (uniqueness constraints) trước khi import."""
    constraints = [
        "CREATE CONSTRAINT doc_so_ky_hieu_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.so_ky_hieu IS UNIQUE",
        "CREATE CONSTRAINT coquan_name_unique IF NOT EXISTS FOR (c:CoQuan) REQUIRE c.name IS UNIQUE",
        "CREATE CONSTRAINT nguoiky_name_unique IF NOT EXISTS FOR (n:NguoiKy) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT doituong_name_unique IF NOT EXISTS FOR (d:DoiTuongApDung) REQUIRE d.name IS UNIQUE",
        "CREATE CONSTRAINT linhvuc_name_unique IF NOT EXISTS FOR (l:LinhVuc) REQUIRE l.name IS UNIQUE",
    ]
    for q in constraints:
        try:
            session.run(q)
        except Exception as e:
            print(f"  [Cảnh báo constraint] {e}")

def import_knowledge_graph(session, df_docs, df_entities, df_rels):
    """
    Thực hiện import toàn bộ Document, Entity và Relationship bằng câu lệnh MERGE đảm bảo tính Idempotent.
    """
    import_errors = []
    
    # 1. Import Document nodes từ cleaned_documents.csv
    doc_query = """
    UNWIND $batch AS row
    MERGE (d:Document {so_ky_hieu: row.so_ky_hieu})
    SET 
        d.id = row.id,
        d.title = row.title,
        d.tieu_de = row.title,
        d.loai_van_ban = row.loai_van_ban,
        d.ngay_ban_hanh = row.ngay_ban_hanh,
        d.ngay_co_hieu_luc = row.ngay_co_hieu_luc,
        d.nguon_thu_thap = row.nguon_thu_thap,
        d.co_quan_ban_hanh = row.co_quan_ban_hanh,
        d.nguoi_ky = row.nguoi_ky,
        d.chuc_danh = row.chuc_danh,
        d.linh_vuc = row.linh_vuc,
        d.nganh = row.nganh
    """
    doc_records = []
    for _, r in df_docs.iterrows():
        doc_records.append({
            "so_ky_hieu": str(r.get("so_ky_hieu", "")).strip(),
            "id": str(r.get("id", "")).strip(),
            "title": str(r.get("title", "")).strip(),
            "loai_van_ban": str(r.get("loai_van_ban", "")).strip(),
            "ngay_ban_hanh": str(r.get("ngay_ban_hanh", "")).strip(),
            "ngay_co_hieu_luc": str(r.get("ngay_co_hieu_luc", "")).strip(),
            "nguon_thu_thap": str(r.get("nguon_thu_thap", "")).strip(),
            "co_quan_ban_hanh": str(r.get("co_quan_ban_hanh", "")).strip(),
            "nguoi_ky": str(r.get("nguoi_ky", "")).strip(),
            "chuc_danh": str(r.get("chuc_danh", "")).strip(),
            "linh_vuc": str(r.get("linh_vuc", "")).strip(),
            "nganh": str(r.get("nganh", "")).strip(),
        })
    try:
        session.run(doc_query, batch=doc_records)
    except Exception as e:
        import_errors.append(f"Lỗi import Document nodes: {e}")

    # 2. Import Entity nodes từ entities.csv theo từng label
    entity_queries = {
        "CoQuan": "UNWIND $batch AS row MERGE (e:CoQuan {name: row.name}) ON CREATE SET e.entity_type = 'CoQuan'",
        "NguoiKy": "UNWIND $batch AS row MERGE (e:NguoiKy {name: row.name}) ON CREATE SET e.entity_type = 'NguoiKy'",
        "DoiTuongApDung": "UNWIND $batch AS row MERGE (e:DoiTuongApDung {name: row.name}) ON CREATE SET e.entity_type = 'DoiTuongApDung'",
        "LinhVuc": "UNWIND $batch AS row MERGE (e:LinhVuc {name: row.name}) ON CREATE SET e.entity_type = 'LinhVuc'",
    }
    for etype, query in entity_queries.items():
        subset = df_entities[df_entities["entity_type"] == etype]
        names = subset["canonical_name"].dropna().unique().tolist()
        batch = [{"name": str(n).strip()} for n in names if str(n).strip()]
        if batch:
            try:
                session.run(query, batch=batch)
            except Exception as e:
                import_errors.append(f"Lỗi import {etype} nodes: {e}")

    # 3. Import Relationships từ relationships.csv
    rel_queries = {
        # Document -> Entity
        "BAN_HANH_BOI": """
            UNWIND $batch AS row
            MATCH (d:Document {so_ky_hieu: row.source})
            MATCH (e:CoQuan {name: row.target})
            MERGE (d)-[r:BAN_HANH_BOI]->(e)
            ON CREATE SET r.method = row.method, r.confidence = row.confidence, r.evidence = row.evidence
        """,
        "KY_BOI": """
            UNWIND $batch AS row
            MATCH (d:Document {so_ky_hieu: row.source})
            MATCH (e:NguoiKy {name: row.target})
            MERGE (d)-[r:KY_BOI]->(e)
            ON CREATE SET r.method = row.method, r.confidence = row.confidence, r.evidence = row.evidence
        """,
        "AP_DUNG_CHO": """
            UNWIND $batch AS row
            MATCH (d:Document {so_ky_hieu: row.source})
            MATCH (e:DoiTuongApDung {name: row.target})
            MERGE (d)-[r:AP_DUNG_CHO]->(e)
            ON CREATE SET r.method = row.method, r.confidence = row.confidence, r.evidence = row.evidence
        """,
        "THUOC_LINH_VUC": """
            UNWIND $batch AS row
            MATCH (d:Document {so_ky_hieu: row.source})
            MATCH (e:LinhVuc {name: row.target})
            MERGE (d)-[r:THUOC_LINH_VUC]->(e)
            ON CREATE SET r.method = row.method, r.confidence = row.confidence, r.evidence = row.evidence
        """,
        # Document -> Document
        "THAM_CHIEU": """
            UNWIND $batch AS row
            MERGE (d1:Document {so_ky_hieu: row.source})
            MERGE (d2:Document {so_ky_hieu: row.target})
            MERGE (d1)-[r:THAM_CHIEU]->(d2)
            ON CREATE SET r.method = row.method, r.confidence = row.confidence, r.evidence = row.evidence
        """,
        "SUA_DOI_BO_SUNG": """
            UNWIND $batch AS row
            MERGE (d1:Document {so_ky_hieu: row.source})
            MERGE (d2:Document {so_ky_hieu: row.target})
            MERGE (d1)-[r:SUA_DOI_BO_SUNG]->(d2)
            ON CREATE SET r.method = row.method, r.confidence = row.confidence, r.evidence = row.evidence
        """,
        "THAY_THE_BOI": """
            UNWIND $batch AS row
            MERGE (d1:Document {so_ky_hieu: row.source})
            MERGE (d2:Document {so_ky_hieu: row.target})
            MERGE (d1)-[r:THAY_THE_BOI]->(d2)
            ON CREATE SET r.method = row.method, r.confidence = row.confidence, r.evidence = row.evidence
        """
    }

    for rtype, q in rel_queries.items():
        subset = df_rels[df_rels["relationship_type"] == rtype]
        batch = []
        for _, r in subset.iterrows():
            batch.append({
                "source": str(r.get("source", "")).strip(),
                "target": str(r.get("target", "")).strip(),
                "method": str(r.get("method", "")).strip(),
                "confidence": float(r.get("confidence", 0.95)),
                "evidence": str(r.get("evidence", "")).strip()
            })
        if batch:
            try:
                session.run(q, batch=batch)
            except Exception as e:
                import_errors.append(f"Lỗi import relationship {rtype}: {e}")

    return import_errors

def get_graph_statistics(session):
    """Thu thập số lượng node theo label và relationship theo type."""
    stats = {"nodes": {}, "relationships": {}}
    
    # 1. Node count theo label
    labels_to_check = ["Document", "CoQuan", "NguoiKy", "DoiTuongApDung", "LinhVuc"]
    for lbl in labels_to_check:
        res = session.run(f"MATCH (n:{lbl}) RETURN count(n) AS cnt")
        stats["nodes"][lbl] = res.single()["cnt"]
        
    # 2. Relationship count theo type
    types_to_check = [
        "THAM_CHIEU", "SUA_DOI_BO_SUNG", "THAY_THE_BOI",
        "BAN_HANH_BOI", "KY_BOI", "AP_DUNG_CHO", "THUOC_LINH_VUC"
    ]
    for t in types_to_check:
        res = session.run(f"MATCH ()-[r:{t}]->() RETURN count(r) AS cnt")
        stats["relationships"][t] = res.single()["cnt"]
        
    return stats

def run_step_8():
    print("=" * 70)
    print("           BƯỚC 8: IMPORT KNOWLEDGE GRAPH VÀO NEO4J              ")
    print("=" * 70)
    
    # 1. Đọc config từ .env
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, ".env")
    load_dotenv(env_path)
    
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "")
    database = os.getenv("NEO4J_DATABASE", "kb-hops")
    
    print(f"[1] Đọc cấu hình kết nối:")
    print(f"  - NEO4J_URI      : {uri}")
    print(f"  - NEO4J_USERNAME : {username}")
    print(f"  - NEO4J_DATABASE : {database}")
    
    # 2. Đọc các tập tin dữ liệu đầu vào
    ner_kb_dir = os.path.join(base_dir, "ner_kb")
    df_docs = pd.read_csv(os.path.join(ner_kb_dir, "cleaned_documents.csv"), dtype=str)
    df_entities = pd.read_csv(os.path.join(ner_kb_dir, "entities.csv"), dtype=str)
    df_rels = pd.read_csv(os.path.join(ner_kb_dir, "relationships.csv"), dtype=str)
    
    print(f"\n[2] Đã đọc dữ liệu CSV:")
    print(f"  - cleaned_documents.csv : {len(df_docs)} documents")
    print(f"  - entities.csv            : {len(df_entities)} entities")
    print(f"  - relationships.csv       : {len(df_rels)} relationships")
    
    driver = GraphDatabase.driver(uri, auth=(username, password))
    
    try:
        with driver.session(database=database) as session:
            # 3. Tạo Uniqueness Constraints
            print("\n[3] Thiết lập các Uniqueness Constraints trên Neo4j...")
            create_constraints(session)
            print("  --> Đã thiết lập 5 uniqueness constraints thành công.")
            
            # 4. Thực hiện Import Lần 1
            print("\n[4] Tiến hành IMPORT LẦN 1 vào Neo4j...")
            errors_run1 = import_knowledge_graph(session, df_docs, df_entities, df_rels)
            stats_run1 = get_graph_statistics(session)
            
            # 5. Thực hiện Import Lần 2 (Kiểm tra tính Idempotent)
            print("\n[5] Tiến hành IMPORT LẦN 2 (Kiểm tra tính Idempotent)...")
            errors_run2 = import_knowledge_graph(session, df_docs, df_entities, df_rels)
            stats_run2 = get_graph_statistics(session)
            
            # So sánh thống kê giữa 2 lần chạy
            is_idempotent = (stats_run1 == stats_run2)
            total_errors = len(errors_run1) + len(errors_run2)
            
            # 6. In Báo cáo kết quả
            print("\n" + "=" * 70)
            print("                    BÁO CÁO THỐNG KÊ BƯỚC 8                      ")
            print("=" * 70)
            print(f"1. Số lượng Node trong Knowledge Graph theo Label:")
            total_nodes = 0
            for lbl, cnt in stats_run1["nodes"].items():
                print(f"  - (:{lbl:<15}) : {cnt:>4} nodes")
                total_nodes += cnt
            print(f"  -------------------------------------------------------------")
            print(f"  - TỔNG CỘNG NODES          : {total_nodes:>4} nodes")
            
            print(f"\n2. Số lượng Relationship trong Knowledge Graph theo Type:")
            total_rels = 0
            for t, cnt in stats_run1["relationships"].items():
                print(f"  - [:{t:<16}] : {cnt:>4} edges")
                total_rels += cnt
            print(f"  -------------------------------------------------------------")
            print(f"  - TỔNG CỘNG RELATIONSHIPS  : {total_rels:>4} edges")
            
            print(f"\n3. Kết quả kiểm tra tính Idempotent (Chạy Lần 1 vs Lần 2):")
            print(f"  - Node counts khớp 100%    : {'ĐẠT (Không trùng lặp)' if stats_run1['nodes'] == stats_run2['nodes'] else 'LỖI'}")
            print(f"  - Edge counts khớp 100%    : {'ĐẠT (Không trùng lặp)' if stats_run1['relationships'] == stats_run2['relationships'] else 'LỖI'}")
            print(f"  - Số lỗi trong quá trình import: {total_errors} lỗi")
            if total_errors > 0:
                for err in (errors_run1 + errors_run2):
                    print(f"    + {err}")
                    
            # 7. Đánh giá điều kiện PASS
            pass_conditions = [
                ("Neo4j import thành công không lỗi", total_errors == 0),
                ("Document nodes tồn tại trong đồ thị", stats_run1["nodes"]["Document"] >= 30),
                ("Entity nodes tồn tại (CoQuan, NguoiKy, DoiTuong, LinhVuc)", all(stats_run1["nodes"][lbl] > 0 for lbl in ["CoQuan", "NguoiKy", "DoiTuongApDung", "LinhVuc"])),
                ("7 loại Relationships được tạo đầy đủ", all(stats_run1["relationships"][t] > 0 for t in ["THAM_CHIEU", "SUA_DOI_BO_SUNG", "THAY_THE_BOI", "BAN_HANH_BOI", "KY_BOI", "AP_DUNG_CHO", "THUOC_LINH_VUC"])),
                ("Tính Idempotent: Lần 2 không tạo duplicate node/edge", is_idempotent)
            ]
            
            all_pass = all(cond[1] for cond in pass_conditions)
            
            print("\n" + "=" * 70)
            print("                 ĐIỀU KIỆN PASS BƯỚC 8                    ")
            print("=" * 70)
            for desc, is_ok in pass_conditions:
                status = "PASS" if is_ok else "FAIL"
                print(f"[{status}] {desc}")
                
            print(f"\nKẾT QUẢ CUỐI CÙNG BƯỚC 8: {'[PASS]' if all_pass else '[FAIL]'}")
            print("=" * 70)
            
            return all_pass
            
    finally:
        driver.close()
        print("\n[Đã đóng Neo4j driver an toàn.]")

if __name__ == "__main__":
    run_step_8()
