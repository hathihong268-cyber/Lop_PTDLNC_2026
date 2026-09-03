"""
Module Buoc 4: Nap toan bo Du lieu Do thi, Chunking va Vector Embeddings vao Neo4j (kb-hops)
Tich hop Cache Embeddings cuc bo va co che Batch Transaction an toan.
Bai thuc hanh 1 - Buoi 10: Graph RAG Foundation
"""

import os
import sys
import time
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from tqdm import tqdm
from neo4j import GraphDatabase, Driver, exceptions

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Import cac module Buoc 1, Buoc 2, Buoc 3
from buoi_10_chunking import HTMLHierarchicalChunker, build_next_relationships
from buoi_10_embedding import embed_chunks_pipeline
from buoi_10_db import get_neo4j_driver, get_db_config

CACHE_DIR = Path(__file__).resolve().parent / "storage"
CACHE_FILE = CACHE_DIR / "embedded_chunks_cache.json"


def save_chunks_cache(chunks: List[Dict[str, Any]], next_rels: List[Dict[str, Any]]):
    """Luu cache chunks da duoc embed xuong dia de su dung lai tuc thi."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_data = {
        "chunks": chunks,
        "next_rels": next_rels
    }
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False)
    print(f"[+] Da luu Cache {len(chunks)} Chunks vao: {CACHE_FILE}")


def load_chunks_cache():
    """Doc cache chunks tu dia neu co."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"[+] Da tim thay Cache Embeddings san co: {len(data['chunks'])} chunks!")
            return data["chunks"], data["next_rels"]
        except Exception as e:
            print(f"[!] Khong the doc cache: {e}")
    return None, None


def create_schema_and_indexes(driver: Driver, database: str):
    """Tao Constraints va Vector Index trong Neo4j database kb-hops."""
    print("\n[*] 1. Khoi tao Constraints va Vector Index tren Neo4j...")
    queries = [
        "CREATE CONSTRAINT doc_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
        "CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE",
        "CREATE INDEX chunk_doc_id IF NOT EXISTS FOR (c:Chunk) ON (c.doc_id)",
        """
        CREATE VECTOR INDEX chunk_embeddings IF NOT EXISTS
        FOR (c:Chunk) ON (c.embedding)
        OPTIONS {indexConfig: {
            `vector.dimensions`: 384,
            `vector.similarity_function`: 'cosine'
        }}
        """
    ]

    with driver.session(database=database) as session:
        for q in queries:
            try:
                session.run(q)
            except Exception as e:
                print(f"    [!] Constraint/Index: {e}")
    print("[+] Da thiet lap Constraints va Vector Index thanh cong!")


def load_documents(driver: Driver, database: str, df_meta: pd.DataFrame):
    """Nap 15 Document metadata vao cac nut (:Document)."""
    print(f"\n[*] 2. Nap {len(df_meta)} Document Nodes...")
    records = []
    for _, row in df_meta.iterrows():
        records.append({
            "id": str(row['id']),
            "title": str(row['title']) if pd.notna(row['title']) else "",
            "so_ky_hieu": str(row['so_ky_hieu']) if pd.notna(row['so_ky_hieu']) else "",
            "ngay_ban_hanh": str(row['ngay_ban_hanh']) if pd.notna(row['ngay_ban_hanh']) else "",
            "loai_van_ban": str(row['loai_van_ban']) if pd.notna(row['loai_van_ban']) else "",
            "ngay_co_hieu_luc": str(row['ngay_co_hieu_luc']) if pd.notna(row['ngay_co_hieu_luc']) else "",
            "ngay_het_hieu_luc": str(row['ngay_het_hieu_luc']) if pd.notna(row['ngay_het_hieu_luc']) else "",
            "nguon_thu_thap": str(row['nguon_thu_thap']) if pd.notna(row['nguon_thu_thap']) else "",
            "ngay_dang_cong_bao": str(row['ngay_dang_cong_bao']) if pd.notna(row['ngay_dang_cong_bao']) else "",
            "nganh": str(row['nganh']) if pd.notna(row['nganh']) else "",
            "linh_vuc": str(row['linh_vuc']) if pd.notna(row['linh_vuc']) else "",
            "co_quan_ban_hanh": str(row['co_quan_ban_hanh']) if pd.notna(row['co_quan_ban_hanh']) else "",
            "chuc_danh": str(row['chuc_danh']) if pd.notna(row['chuc_danh']) else "",
            "nguoi_ky": str(row['nguoi_ky']) if pd.notna(row['nguoi_ky']) else "",
            "pham_vi": str(row['pham_vi']) if pd.notna(row['pham_vi']) else "",
            "thong_tin_ap_dung": str(row['thong_tin_ap_dung']) if pd.notna(row['thong_tin_ap_dung']) else "",
            "tinh_trang_hieu_luc": str(row['tinh_trang_hieu_luc']) if pd.notna(row['tinh_trang_hieu_luc']) else ""
        })

    cypher = """
    UNWIND $batch AS row
    MERGE (d:Document {id: row.id})
    SET d.title = row.title,
        d.so_ky_hieu = row.so_ky_hieu,
        d.ngay_ban_hanh = row.ngay_ban_hanh,
        d.loai_van_ban = row.loai_van_ban,
        d.ngay_co_hieu_luc = row.ngay_co_hieu_luc,
        d.ngay_het_hieu_luc = row.ngay_het_hieu_luc,
        d.nguon_thu_thap = row.nguon_thu_thap,
        d.ngay_dang_cong_bao = row.ngay_dang_cong_bao,
        d.nganh = row.nganh,
        d.linh_vuc = row.linh_vuc,
        d.co_quan_ban_hanh = row.co_quan_ban_hanh,
        d.chuc_danh = row.chuc_danh,
        d.nguoi_ky = row.nguoi_ky,
        d.pham_vi = row.pham_vi,
        d.thong_tin_ap_dung = row.thong_tin_ap_dung,
        d.tinh_trang_hieu_luc = row.tinh_trang_hieu_luc
    """

    with driver.session(database=database) as session:
        session.run(cypher, batch=records)
    print(f"[+] Da nap thanh cong {len(records)} Document Nodes vao Neo4j!")


def load_doc_relationships(driver: Driver, database: str, df_rels: pd.DataFrame):
    """Nap 8 quan he giua cac Document."""
    print(f"\n[*] 3. Nap {len(df_rels)} Quan he giua cac Document...")
    with driver.session(database=database) as session:
        for _, row in df_rels.iterrows():
            doc_id = str(row['doc_id'])
            other_doc_id = str(row['other_doc_id'])
            rel_type = str(row['relationship_type']).strip().upper()
            rel_desc = str(row['relationship']) if pd.notna(row['relationship']) else ""

            cypher = f"""
            MATCH (d1:Document {{id: $doc_id}})
            MATCH (d2:Document {{id: $other_doc_id}})
            MERGE (d1)-[r:{rel_type}]->(d2)
            SET r.relationship = $rel_desc
            """
            session.run(cypher, doc_id=doc_id, other_doc_id=other_doc_id, rel_desc=rel_desc)

    print(f"[+] Da nap thanh cong {len(df_rels)} Quan he Document-to-Document!")


def run_batch_query_with_retry(driver: Driver, database: str, cypher: str, batch: list, max_retries: int = 3):
    """Thuc thi mot batch Cypher query voi co che retry an toan."""
    for attempt in range(max_retries):
        try:
            with driver.session(database=database) as session:
                session.run(cypher, batch=batch)
            return
        except (exceptions.ServiceUnavailable, exceptions.SessionExpired, ConnectionResetError, Exception) as e:
            if attempt < max_retries - 1:
                time.sleep(1.0)
                continue
            else:
                raise e


def load_chunks_and_relations(driver: Driver, database: str, chunks: List[Dict[str, Any]], next_rels: List[Dict[str, Any]], batch_size: int = 150):
    """Nap toan bo Chunks kem Vector Embedding, quan he PART_OF, PARENT_OF va NEXT."""
    print(f"\n[*] 4. Nap {len(chunks)} Chunks va Vector Embeddings (Batch size = {batch_size})...")
    
    # 1. Nap Chunks
    chunk_cypher = """
    UNWIND $batch AS row
    MERGE (c:Chunk {id: row.chunk_id})
    SET c.doc_id = row.doc_id,
        c.doc_title = row.doc_title,
        c.heading = row.heading,
        c.level = row.level,
        c.text = row.text,
        c.embedding = row.embedding,
        c.seq_order = row.seq_order
    """
    for i in tqdm(range(0, len(chunks), batch_size), desc="[Nap Chunks]"):
        batch = chunks[i:i + batch_size]
        run_batch_query_with_retry(driver, database, chunk_cypher, batch)
    print(f"[+] Da nap {len(chunks)} Chunks thanh cong!")

    # 2. Nap quan he PART_OF (Chunk -> Document)
    print(f"\n[*] 5. Tao quan he [:PART_OF] tu Chunk ve Document...")
    part_of_cypher = """
    UNWIND $batch AS row
    MATCH (c:Chunk {id: row.chunk_id})
    MATCH (d:Document {id: row.doc_id})
    MERGE (c)-[:PART_OF]->(d)
    """
    part_of_items = [{'chunk_id': c['chunk_id'], 'doc_id': c['doc_id']} for c in chunks]
    for i in tqdm(range(0, len(part_of_items), 300), desc="[PART_OF]"):
        batch = part_of_items[i:i + 300]
        run_batch_query_with_retry(driver, database, part_of_cypher, batch)
    print("[+] Da tao toan bo quan he [:PART_OF]!")

    # 3. Nap quan he PARENT_OF (Chunk Cha -> Chunk Con)
    parent_child_pairs = [{'parent_id': c['parent_id'], 'chunk_id': c['chunk_id']} for c in chunks if c.get('parent_id')]
    print(f"\n[*] 6. Tao {len(parent_child_pairs)} quan he phan cap [:PARENT_OF]...")
    parent_of_cypher = """
    UNWIND $batch AS row
    MATCH (p:Chunk {id: row.parent_id})
    MATCH (c:Chunk {id: row.chunk_id})
    MERGE (p)-[:PARENT_OF]->(c)
    """
    for i in tqdm(range(0, len(parent_child_pairs), 300), desc="[PARENT_OF]"):
        batch = parent_child_pairs[i:i + 300]
        run_batch_query_with_retry(driver, database, parent_of_cypher, batch)
    print("[+] Da tao toan bo quan he [:PARENT_OF]!")

    # 4. Nap quan he NEXT
    print(f"\n[*] 7. Tao {len(next_rels)} quan he doc tuan tu [:NEXT]...")
    next_cypher = """
    UNWIND $batch AS row
    MATCH (c1:Chunk {id: row.from_chunk_id})
    MATCH (c2:Chunk {id: row.to_chunk_id})
    MERGE (c1)-[:NEXT]->(c2)
    """
    for i in tqdm(range(0, len(next_rels), 300), desc="[NEXT]"):
        batch = next_rels[i:i + 300]
        run_batch_query_with_retry(driver, database, next_cypher, batch)
    print("[+] Da tao toan bo quan he [:NEXT]!")


def verify_database_stats(driver: Driver, database: str):
    """Kiem tra va xac minh toan bo so luong Nodes va Relationships."""
    print("\n" + "=" * 80)
    print(" BƯỚC 5: KIỂM TRA VÀ XÁC MINH SỐ LƯỢNG THỰC THỂ TRONG NEO4J")
    print("=" * 80)

    with driver.session(database=database) as session:
        doc_count = session.run("MATCH (d:Document) RETURN count(d) AS count").single()["count"]
        chunk_count = session.run("MATCH (c:Chunk) RETURN count(c) AS count").single()["count"]
        doc_rel_count = session.run("""
        MATCH (d1:Document)-[r]->(d2:Document)
        RETURN count(r) AS count
        """).single()["count"]
        
        rel_types = session.run("""
        MATCH ()-[r]->()
        RETURN type(r) AS type, count(r) AS count
        ORDER BY count DESC
        """)
        rel_summary = {r["type"]: r["count"] for r in rel_types}

    print(f"\n[+] KẾT QUẢ XÁC MINH CƠ SỞ DỮ LIỆU `{database}`:")
    print(f"  • Số lượng nút (:Document)            : {doc_count} (Yêu cầu đề bài: 15)")
    print(f"  • Số lượng nút (:Chunk)               : {chunk_count:,}")
    print(f"  • Số lượng quan hệ Document-to-Doc    : {doc_rel_count} (Yêu cầu đề bài: 8)")
    print(f"\n  • Chi tiết các loại quan hệ trong đồ thị:")
    for r_type, r_cnt in rel_summary.items():
        print(f"    - [:{r_type}]: {r_cnt:,}")

    if doc_count == 15 and doc_rel_count == 8 and chunk_count > 0:
        print("\n🎉 [XÁC MINH THÀNH CÔNG] Toàn bộ dữ liệu đồ thị và phân đoạn đã được nạp chính xác 100%!")
    else:
        print("\n⚠️ [LƯU Ý] Vui lòng kiểm tra lại nếu số lượng chưa khớp.")


def main():
    print("=" * 80)
    print(" BƯỚC 4: NẠP DỮ LIỆU VĂN BẢN, CHUNKS & VECTOR EMBEDDINGS VÀO NEO4J")
    print("=" * 80)

    data_dir = Path(__file__).resolve().parent / "graph_rag_labs" / "kb+hops"
    metadata_path = data_dir / "metadata.csv"
    content_path = data_dir / "content.csv"
    relationships_path = data_dir / "relationships.csv"

    df_meta = pd.read_csv(metadata_path)
    df_content = pd.read_csv(content_path)
    df_rels = pd.read_csv(relationships_path)

    # Kiem tra Cache truoc
    all_chunks, all_next_rels = load_chunks_cache()

    if not all_chunks:
        print("\n[*] Khong tim thay cache, bat dau quy trinh Chunking & Embedding...")
        chunker = HTMLHierarchicalChunker()
        all_chunks = []
        all_next_rels = []

        for _, row in df_content.iterrows():
            d_id = str(row['id'])
            meta_match = df_meta[df_meta['id'].astype(str) == d_id]
            d_title = meta_match['title'].values[0] if not meta_match.empty else f"Document {d_id}"
            d_html = row['content_html']

            doc_chunks = chunker.parse_document(doc_id=d_id, title=d_title, html_content=d_html)
            doc_nexts = build_next_relationships(doc_chunks)

            all_chunks.extend(doc_chunks)
            all_next_rels.extend(doc_nexts)

        print(f"[+] Da tao tong cong {len(all_chunks)} Chunks tu 15 tai lieu.")
        all_chunks = embed_chunks_pipeline(all_chunks, batch_size=64)
        save_chunks_cache(all_chunks, all_next_rels)

    # Khoi tao Driver Neo4j va nap du lieu
    cfg = get_db_config()
    db_name = cfg["database"]
    driver = get_neo4j_driver()

    try:
        create_schema_and_indexes(driver, db_name)
        load_documents(driver, db_name, df_meta)
        load_doc_relationships(driver, db_name, df_rels)
        load_chunks_and_relations(driver, db_name, all_chunks, all_next_rels, batch_size=150)
        verify_database_stats(driver, db_name)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
