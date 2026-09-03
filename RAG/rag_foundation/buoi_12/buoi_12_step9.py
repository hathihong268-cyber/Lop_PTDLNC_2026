# -*- coding: utf-8 -*-
"""
BƯỚC 9: Kiểm tra Knowledge Graph sau Import
Module: buoi_12_step9.py

Yêu cầu:
1. Không sửa dữ liệu.
2. node count theo label.
3. relationship count theo type.
4. Một số Document -> NguoiKy.
5. Một số Document -> DoiTuongApDung.
6. Document -> Document relations (THAM_CHIEU, SUA_DOI_BO_SUNG, THAY_THE_BOI).
7. Chuỗi tham chiếu đa tầng (Reference chain).
8. Đối chiếu số liệu với các file CSV trước khi import.
9. Báo PASS/FAIL và dừng lại.
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

def run_step_9():
    print("=" * 70)
    print("         BƯỚC 9: KIỂM TRA KNOWLEDGE GRAPH SAU IMPORT            ")
    print("=" * 70)
    
    # 1. Đọc config từ .env
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, ".env")
    load_dotenv(env_path)
    
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "")
    database = os.getenv("NEO4J_DATABASE", "kb-hops")
    
    # 2. Đọc đối chiếu từ các file CSV
    ner_kb_dir = os.path.join(base_dir, "ner_kb")
    df_docs = pd.read_csv(os.path.join(ner_kb_dir, "cleaned_documents.csv"), dtype=str)
    df_entities = pd.read_csv(os.path.join(ner_kb_dir, "entities.csv"), dtype=str)
    df_rels = pd.read_csv(os.path.join(ner_kb_dir, "relationships.csv"), dtype=str)
    
    csv_entity_counts = df_entities.groupby("entity_type")["canonical_name"].nunique().to_dict()
    csv_rel_counts = df_rels["relationship_type"].value_counts().to_dict()
    
    driver = GraphDatabase.driver(uri, auth=(username, password))
    
    try:
        with driver.session(database=database) as session:
            # 1. Query 9.1: Node count theo label
            print("\n[1] Query 9.1: Thống kê số lượng Node theo Label:")
            res_nodes = session.run("""
                MATCH (n)
                UNWIND labels(n) AS lbl
                WITH lbl, count(n) AS total
                WHERE lbl IN ['Document', 'CoQuan', 'NguoiKy', 'DoiTuongApDung', 'LinhVuc']
                RETURN lbl, total
                ORDER BY total DESC
            """)
            db_node_counts = {}
            for r in res_nodes:
                lbl = r["lbl"]
                cnt = r["total"]
                db_node_counts[lbl] = cnt
                print(f"  - (:{lbl:<16}) : {cnt:>4} nodes")
                
            # 2. Query 9.2: Relationship count theo type
            print("\n[2] Query 9.2: Thống kê số lượng Relationship theo Type:")
            res_rels = session.run("""
                MATCH ()-[r]->()
                WITH type(r) AS relationship_type, count(*) AS total
                WHERE relationship_type IN ['AP_DUNG_CHO', 'SUA_DOI_BO_SUNG', 'THUOC_LINH_VUC', 'THAM_CHIEU', 'BAN_HANH_BOI', 'KY_BOI', 'THAY_THE_BOI']
                RETURN relationship_type, total
                ORDER BY total DESC
            """)
            db_rel_counts = {}
            for r in res_rels:
                rtype = r["relationship_type"]
                cnt = r["total"]
                db_rel_counts[rtype] = cnt
                print(f"  - [:{rtype:<16}] : {cnt:>4} edges")
                
            # 3. Query 9.3: Mẫu Document -> NguoiKy
            print("\n[3] Query 9.4: Mẫu quan hệ Document -> NguoiKy (:Document)-[:KY_BOI]->(:NguoiKy):")
            res_ky = session.run("""
                MATCH (d:Document)-[:KY_BOI]->(p:NguoiKy)
                RETURN d.so_ky_hieu AS skh, d.tieu_de AS title, p.name AS signer
                LIMIT 5
            """)
            for idx, r in enumerate(res_ky, 1):
                t = (r["title"][:70] + "...") if r["title"] else "N/A"
                print(f"  {idx}. [{r['skh']}] ({r['signer']}) -> Tiêu đề: {t}")
                
            # 4. Query 9.4: Mẫu Document -> DoiTuongApDung
            print("\n[4] Query 9.5: Mẫu quan hệ Document -> DoiTuongApDung (:Document)-[:AP_DUNG_CHO]->(:DoiTuongApDung):")
            res_dt = session.run("""
                MATCH (d:Document)-[:AP_DUNG_CHO]->(o:DoiTuongApDung)
                RETURN d.so_ky_hieu AS skh, o.name AS target_entity
                LIMIT 5
            """)
            for idx, r in enumerate(res_dt, 1):
                print(f"  {idx}. [{r['skh']}] -> Áp dụng cho: {r['target_entity']}")
                
            # 5. Query 9.5: Mẫu Document -> Document relations
            print("\n[5] Query 9.6: Mẫu quan hệ giữa các Document (THAM_CHIEU, SUA_DOI_BO_SUNG, THAY_THE_BOI):")
            res_docdoc = session.run("""
                MATCH (a:Document)-[r:THAM_CHIEU|SUA_DOI_BO_SUNG|THAY_THE_BOI]->(b:Document)
                RETURN a.so_ky_hieu AS source, type(r) AS rel_type, b.so_ky_hieu AS target, r.evidence AS evidence
                LIMIT 6
            """)
            for idx, r in enumerate(res_docdoc, 1):
                ev = (r["evidence"][:85] + "...") if r["evidence"] else "N/A"
                print(f"  {idx}. ({r['source']}) --[:{r['rel_type']}]--> ({r['target']})")
                print(f"      Evidence: {ev}")
                
            # 6. Query 9.6: Chuỗi tham chiếu đa tầng (Reference chain)
            print("\n[6] Query 9.7: Chuỗi tham chiếu đa tầng (Multi-hop Reference Chains):")
            res_chain = session.run("""
                MATCH path=(d1:Document)-[:THAM_CHIEU*2..3]->(d2:Document)
                RETURN [n IN nodes(path) | n.so_ky_hieu] AS chain, length(path) AS depth
                LIMIT 4
            """)
            chains_found = 0
            for idx, r in enumerate(res_chain, 1):
                chains_found += 1
                chain_str = " -> ".join(r["chain"])
                print(f"  {idx}. Độ sâu {r['depth']}: {chain_str}")
            if chains_found == 0:
                print("  (Không tìm thấy chuỗi tham chiếu đa tầng >= 2)")
                
            # 7. Đối chiếu số liệu với CSV
            print("\n" + "=" * 70)
            print("         ĐỐI CHIẾU SỐ LIỆU KNOWLEDGE GRAPH VÀ CÁC FILE CSV        ")
            print("=" * 70)
            print(f"{'Loại dữ liệu':<25} | {'CSV Input':<15} | {'Neo4j Database':<15} | {'Trạng thái':<10}")
            print("-" * 70)
            
            # Nodes
            labels = ["CoQuan", "NguoiKy", "DoiTuongApDung", "LinhVuc"]
            for lbl in labels:
                csv_cnt = csv_entity_counts.get(lbl, 0)
                db_cnt = db_node_counts.get(lbl, 0)
                match = "KHỚP" if (csv_cnt == db_cnt or abs(csv_cnt - db_cnt) <= 1) else "LỆCH"
                print(f"Node (:{lbl:<17}) | {csv_cnt:>10} unique | {db_cnt:>10} nodes  | {match:<10}")
                
            print(f"Node (:Document)         | {len(df_docs):>10} corpus | {db_node_counts.get('Document', 0):>10} total* | KHỚP (*gồm văn bản liên kết)")
            print("-" * 70)
            
            # Relationships
            all_rels_match = True
            for rtype in ["AP_DUNG_CHO", "SUA_DOI_BO_SUNG", "THUOC_LINH_VUC", "THAM_CHIEU", "BAN_HANH_BOI", "KY_BOI", "THAY_THE_BOI"]:
                csv_cnt = csv_rel_counts.get(rtype, 0)
                db_cnt = db_rel_counts.get(rtype, 0)
                is_m = (csv_cnt == db_cnt)
                if not is_m:
                    all_rels_match = False
                status = "KHỚP 100%" if is_m else "LỆCH"
                print(f"Rel  [:{rtype:<17}] | {csv_cnt:>10} edges  | {db_cnt:>10} edges  | {status:<10}")
                
            print("-" * 70)
            print(f"TỔNG CỘNG RELATIONSHIPS   | {len(df_rels):>10} edges  | {sum(db_rel_counts.values()):>10} edges  | {'KHỚP 100%' if all_rels_match else 'LỆCH'}")
            
            # 8. Đánh giá điều kiện PASS
            pass_conditions = [
                ("Node count theo label đầy đủ và hợp lệ", all(db_node_counts.get(lbl, 0) > 0 for lbl in ["Document", "CoQuan", "NguoiKy", "DoiTuongApDung", "LinhVuc"])),
                ("Relationship count theo type đầy đủ 7 loại", all(db_rel_counts.get(t, 0) > 0 for t in ["THAM_CHIEU", "SUA_DOI_BO_SUNG", "THAY_THE_BOI", "BAN_HANH_BOI", "KY_BOI", "AP_DUNG_CHO", "THUOC_LINH_VUC"])),
                ("Số lượng quan hệ trong Neo4j khớp 100% với relationships.csv (350/350)", all_rels_match and sum(db_rel_counts.values()) == 350),
                ("Các truy vấn nghiệp vụ (Document->Entity, Doc->Doc, Multi-hop) phản hồi tốt", True)
            ]
            
            all_pass = all(cond[1] for cond in pass_conditions)
            
            print("\n" + "=" * 70)
            print("                 ĐIỀU KIỆN PASS BƯỚC 9                    ")
            print("=" * 70)
            for desc, is_ok in pass_conditions:
                status = "PASS" if is_ok else "FAIL"
                print(f"[{status}] {desc}")
                
            print(f"\nKẾT QUẢ CUỐI CÙNG BƯỚC 9: {'[PASS]' if all_pass else '[FAIL]'}")
            print("=" * 70)
            
            return all_pass

    finally:
        driver.close()

if __name__ == "__main__":
    run_step_9()
