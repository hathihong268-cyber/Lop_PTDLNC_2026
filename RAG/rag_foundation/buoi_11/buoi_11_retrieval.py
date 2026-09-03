"""
Module Bước 2: Truy vấn Vector và Mở rộng Đồ thị Đa bước (Multi-hop Graph Retrieval)
Bài thực hành 2 - Buổi 11: Multi-hop Graph RAG và Ứng dụng Hỏi Đáp (QA)

Chức năng:
1. Chuyển đổi câu hỏi của người dùng thành Vector nhúng (MSMARCO Vietnamese MiniLM).
2. Thực hiện Vector Search trong Neo4j (top-k Chunks phù hợp nhất).
3. Mở rộng đồ thị Đa bước (Multi-hop Traversal) theo N bước nhảy qua các liên kết:
   CAN_CU, THAY_THE, HOP_NHAT, SUA_DOI_BO_SUNG, VAN_BAN_BO_SUNG.
4. Trích xuất ngữ cảnh liên kết (Metadata, Đường dẫn quan hệ, và Chunks từ văn bản liên quan).
5. Định dạng Context hoàn chỉnh phục vụ cho việc tích hợp vào LLM (Bước 3).
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from dotenv import load_dotenv

import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel
from neo4j import GraphDatabase, Driver

# Cấu hình encoding trên Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Load cấu hình môi trường
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# Import module kết nối DB từ Bước 1
try:
    from buoi_11_db import get_neo4j_driver, get_db_config
except ImportError:
    from .buoi_11_db import get_neo4j_driver, get_db_config

# Cấu hình mặc định
DEFAULT_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5")
DEFAULT_EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))
DEFAULT_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")

# Danh sách các loại quan hệ liên kết văn bản pháp luật
DEFAULT_RELATIONSHIPS = [
    "CAN_CU",
    "THAY_THE",
    "HOP_NHAT",
    "SUA_DOI_BO_SUNG",
    "VAN_BAN_BO_SUNG"
]


# ==============================================================================
# 1. CLASS TẠO VECTOR NHÚNG TIẾNG VIỆT (MSMARCO DENSE EMBEDDINGS)
# ==============================================================================

class VietnameseEmbeddingModel:
    """
    Mô hình tạo Vector nhúng cho câu hỏi tiếng Việt sử dụng Transformer.
    Áp dụng Mean Pooling và chuẩn hóa L2 (L2 Normalization) để tính Cosine Similarity.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME, device: Optional[str] = None):
        self.device_str = device or ("cuda" if torch.cuda.is_available() else DEFAULT_DEVICE)
        self.device = torch.device(self.device_str)
        self.model_name = model_name

        print(f"[*] Đang tải mô hình nhúng '{model_name}' trên thiết bị: {self.device.type.upper()}...")
        start_time = time.time()
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()
        print(f"[+] Mô hình nhúng sẵn sàng ({time.time() - start_time:.2f}s). Chiều vector: {DEFAULT_EMBEDDING_DIM}")

    @staticmethod
    def _mean_pooling(model_output, attention_mask):
        """Tính Mean Pooling kết hợp Attention Mask."""
        token_embeddings = model_output[0]  # First element chứa token embeddings
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        return sum_embeddings / sum_mask

    def embed_query(self, query_text: str) -> List[float]:
        """
        Chuyển đổi 1 câu hỏi / câu truy vấn thành Vector nhúng đã chuẩn hóa L2.
        """
        if not query_text or not query_text.strip():
            return [0.0] * DEFAULT_EMBEDDING_DIM

        clean_query = query_text.strip()
        encoded_input = self.tokenizer(
            [clean_query],
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        ).to(self.device)

        with torch.no_grad():
            model_output = self.model(**encoded_input)
            sentence_embeddings = self._mean_pooling(model_output, encoded_input["attention_mask"])
            sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)

        return sentence_embeddings.cpu().squeeze(0).tolist()


# Singleton Instance của mô hình Embedding để tối ưu bộ nhớ
_EMBEDDING_MODEL_INSTANCE: Optional[VietnameseEmbeddingModel] = None


def get_embedding_model() -> VietnameseEmbeddingModel:
    """Lấy hoặc khởi tạo đối tượng Singleton VietnameseEmbeddingModel."""
    global _EMBEDDING_MODEL_INSTANCE
    if _EMBEDDING_MODEL_INSTANCE is None:
        _EMBEDDING_MODEL_INSTANCE = VietnameseEmbeddingModel()
    return _EMBEDDING_MODEL_INSTANCE


# ==============================================================================
# 2. VECTOR SEARCH TRONG NEO4J (TÌM TOP-K CHUNKS PHÙ HỢP NHẤT - HOP 0)
# ==============================================================================

def vector_search_chunks(
    driver: Driver,
    database: str,
    query_vector: List[float],
    top_k: int = 3,
    score_threshold: float = 0.0
) -> List[Dict[str, Any]]:
    """
    Truy vấn Vector Index 'chunk_embeddings' trong Neo4j để tìm top-k Chunks phù hợp nhất.
    Đồng thời liên kết tới Node Document cha thông qua quan hệ [:PART_OF].

    Args:
        driver: Neo4j Driver instance.
        database: Tên database (ví dụ: 'kb-hops').
        query_vector: Vector nhúng của câu hỏi (384 float).
        top_k: Số lượng Chunk cần lấy (mặc định: 3).
        score_threshold: Điểm tương đồng tối thiểu (mặc định: 0.0).

    Returns:
        Danh sách các Dict chứa thông tin Chunk và Document cha.
    """
    cypher_query = """
    CALL db.index.vector.queryNodes('chunk_embeddings', $top_k, $query_vector)
    YIELD node AS chunk, score
    WHERE score >= $score_threshold
    OPTIONAL MATCH (chunk)-[:PART_OF]->(doc:Document)
    RETURN 
        chunk.id AS chunk_id,
        chunk.text AS text,
        chunk.heading AS heading,
        chunk.level AS level,
        chunk.seq_order AS seq_order,
        score,
        doc.id AS doc_id,
        doc.title AS doc_title,
        doc.so_ky_hieu AS doc_so_ky_hieu,
        doc.loai_van_ban AS doc_loai_van_ban,
        doc.co_quan_ban_hanh AS doc_co_quan_ban_hanh,
        doc.ngay_ban_hanh AS doc_ngay_ban_hanh,
        doc.tinh_trang_hieu_luc AS doc_tinh_trang_hieu_luc
    ORDER BY score DESC
    """

    results = []
    with driver.session(database=database) as session:
        records = session.run(
            cypher_query,
            top_k=top_k,
            query_vector=query_vector,
            score_threshold=score_threshold
        )
        for r in records:
            results.append({
                "chunk_id": r["chunk_id"],
                "text": r["text"],
                "heading": r["heading"],
                "level": r["level"],
                "seq_order": r["seq_order"],
                "score": float(r["score"]),
                "doc_id": r["doc_id"] or "",
                "doc_title": r["doc_title"] or "",
                "doc_so_ky_hieu": r["doc_so_ky_hieu"] or "",
                "doc_loai_van_ban": r["doc_loai_van_ban"] or "",
                "doc_co_quan_ban_hanh": r["doc_co_quan_ban_hanh"] or "",
                "doc_ngay_ban_hanh": r["doc_ngay_ban_hanh"] or "",
                "doc_tinh_trang_hieu_luc": r["doc_tinh_trang_hieu_luc"] or "",
                "hop_level": 0,
                "retrieval_type": "DIRECT_VECTOR"
            })

    return results


# ==============================================================================
# 3. MỞ RỘNG ĐA BƯỚC (MULTI-HOP GRAPH TRAVERSAL: HOP 1 -> N)
# ==============================================================================

def expand_multihop_graph(
    driver: Driver,
    database: str,
    seed_doc_ids: List[str],
    num_hops: int = 1,
    rel_types: Optional[List[str]] = None,
    chunks_per_hop_doc: int = 2,
    query_vector: Optional[List[float]] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Thực hiện duyệt đồ thị Đa bước (Multi-hop Traversal) từ danh sách tài liệu gốc (Seed Docs).

    Args:
        driver: Neo4j Driver instance.
        database: Tên database ('kb-hops').
        seed_doc_ids: Danh sách ID của các tài liệu tìm thấy từ bước Vector search.
        num_hops: Số bước nhảy (N hops, ví dụ: 1 hoặc 2. Nếu = 0 thì không duyệt).
        rel_types: Danh sách quan hệ cần duyệt (mặc định: CAN_CU, THAY_THE, HOP_NHAT, SUA_DOI_BO_SUNG, VAN_BAN_BO_SUNG).
        chunks_per_hop_doc: Số lượng Chunk trích xuất từ mỗi tài liệu liên quan được tìm thấy.
        query_vector: Vector câu hỏi (nếu có) để xếp hạng Chunk trong tài liệu liên quan.

    Returns:
        Tuple gồm:
        - traversal_paths: Danh sách các đường đi quan hệ chi tiết giữa các tài liệu.
        - related_documents: Danh sách các Document liên quan được mở rộng qua N-hops.
        - hop_chunks: Danh sách các Chunk ngữ cảnh được lấy từ các Document liên quan.
    """
    if num_hops <= 0 or not seed_doc_ids:
        return [], [], []

    allowed_rels = rel_types or DEFAULT_RELATIONSHIPS
    rel_pattern = ":" + "|".join(allowed_rels)

    # 1. Cypher Query duyệt N-hops giữa các Document
    # Lưu ý: Duyệt vô hướng/hai chiều (undirected) để bắt cả văn bản thay thế lẫn bị thay thế,
    # sau đó lưu trữ rõ hướng gốc từ startNode -> endNode trong từng liên kết.
    multihop_cypher = f"""
    UNWIND $seed_doc_ids AS s_id
    MATCH (seed:Document {{id: s_id}})
    MATCH path = (seed)-[r{rel_pattern}*1..{int(num_hops)}]-(target:Document)
    WHERE seed.id <> target.id
    WITH seed, target, relationships(path) AS rel_list, nodes(path) AS node_list, length(path) AS hop_dist
    RETURN DISTINCT
        seed.id AS seed_id,
        seed.so_ky_hieu AS seed_so_ky_hieu,
        seed.title AS seed_title,
        target.id AS target_id,
        target.title AS target_title,
        target.so_ky_hieu AS target_so_ky_hieu,
        target.loai_van_ban AS target_loai_van_ban,
        target.co_quan_ban_hanh AS target_co_quan_ban_hanh,
        target.ngay_ban_hanh AS target_ngay_ban_hanh,
        target.tinh_trang_hieu_luc AS target_tinh_trang_hieu_luc,
        hop_dist,
        [rel IN rel_list | {{
            type: type(rel),
            relationship: rel.relationship,
            from_id: startNode(rel).id,
            from_so: startNode(rel).so_ky_hieu,
            to_id: endNode(rel).id,
            to_so: endNode(rel).so_ky_hieu
        }}] AS path_rels
    ORDER BY hop_dist ASC, target_so_ky_hieu ASC
    """

    traversal_paths = []
    related_docs_map = {}

    with driver.session(database=database) as session:
        records = session.run(multihop_cypher, seed_doc_ids=seed_doc_ids)
        for r in records:
            t_id = r["target_id"]
            hop_dist = int(r["hop_dist"])

            # Lưu lại đường dẫn duyệt
            traversal_paths.append({
                "seed_id": r["seed_id"],
                "seed_so_ky_hieu": r["seed_so_ky_hieu"],
                "seed_title": r["seed_title"],
                "target_id": t_id,
                "target_so_ky_hieu": r["target_so_ky_hieu"],
                "target_title": r["target_title"],
                "hop_distance": hop_dist,
                "relationships": r["path_rels"]
            })

            # Gom nhóm Document liên quan (chọn khoảng cách hop nhỏ nhất nếu trùng)
            if t_id not in related_docs_map or hop_dist < related_docs_map[t_id]["hop_distance"]:
                related_docs_map[t_id] = {
                    "doc_id": t_id,
                    "doc_title": r["target_title"] or "",
                    "doc_so_ky_hieu": r["target_so_ky_hieu"] or "",
                    "doc_loai_van_ban": r["target_loai_van_ban"] or "",
                    "doc_co_quan_ban_hanh": r["target_co_quan_ban_hanh"] or "",
                    "doc_ngay_ban_hanh": r["target_ngay_ban_hanh"] or "",
                    "doc_tinh_trang_hieu_luc": r["target_tinh_trang_hieu_luc"] or "",
                    "hop_distance": hop_dist
                }

    related_documents = list(related_docs_map.values())
    if not related_documents:
        return traversal_paths, [], []

    # 2. Thu thập các Chunks tiêu biểu từ các Document liên quan được mở rộng
    hop_chunks = []
    with driver.session(database=database) as session:
        for doc in related_documents:
            t_id = doc["doc_id"]
            hop_dist = doc["hop_distance"]

            # Lấy các chunk hàng đầu (ưu tiên theo cosine score nếu có query_vector)
            if query_vector is not None:
                # Tìm chunk của tài liệu này có độ liên quan cao nhất với câu hỏi
                chunk_query = """
                MATCH (c:Chunk)-[:PART_OF]->(d:Document {id: $doc_id})
                WHERE c.embedding IS NOT NULL
                WITH c, d, vector.similarity.cosine(c.embedding, $query_vector) AS score
                RETURN 
                    c.id AS chunk_id,
                    c.text AS text,
                    c.heading AS heading,
                    c.level AS level,
                    c.seq_order AS seq_order,
                    score
                ORDER BY score DESC
                LIMIT $limit
                """
                try:
                    c_records = session.run(
                        chunk_query,
                        doc_id=t_id,
                        query_vector=query_vector,
                        limit=chunks_per_hop_doc
                    )
                    c_list = list(c_records)
                except Exception:
                    c_list = []
            else:
                c_list = []

            # Nếu không tìm được qua vector hoặc không có query_vector, lấy theo thứ tự cấu trúc (seq_order)
            if not c_list:
                fallback_query = """
                MATCH (c:Chunk)-[:PART_OF]->(d:Document {id: $doc_id})
                RETURN 
                    c.id AS chunk_id,
                    c.text AS text,
                    c.heading AS heading,
                    c.level AS level,
                    c.seq_order AS seq_order,
                    1.0 AS score
                ORDER BY c.seq_order ASC
                LIMIT $limit
                """
                c_records = session.run(
                    fallback_query,
                    doc_id=t_id,
                    limit=chunks_per_hop_doc
                )
                c_list = list(c_records)

            for cr in c_list:
                hop_chunks.append({
                    "chunk_id": cr["chunk_id"],
                    "text": cr["text"],
                    "heading": cr["heading"],
                    "level": cr["level"],
                    "seq_order": cr["seq_order"],
                    "score": float(cr["score"]) if cr["score"] is not None else 0.0,
                    "doc_id": doc["doc_id"],
                    "doc_title": doc["doc_title"],
                    "doc_so_ky_hieu": doc["doc_so_ky_hieu"],
                    "doc_loai_van_ban": doc["doc_loai_van_ban"],
                    "doc_co_quan_ban_hanh": doc["doc_co_quan_ban_hanh"],
                    "doc_ngay_ban_hanh": doc["doc_ngay_ban_hanh"],
                    "doc_tinh_trang_hieu_luc": doc["doc_tinh_trang_hieu_luc"],
                    "hop_level": hop_dist,
                    "retrieval_type": f"MULTI_HOP_{hop_dist}"
                })

    return traversal_paths, related_documents, hop_chunks


# ==============================================================================
# 4. HÀM TÌM KIẾM NGỮ CẢNH GRAPH RAG TỔNG HỢP (SEARCH CONTEXT PIPELINE)
# ==============================================================================

def search_graph_rag_context(
    query: str,
    top_k: int = 3,
    num_hops: int = 1,
    rel_types: Optional[List[str]] = None,
    chunks_per_hop_doc: int = 2,
    score_threshold: float = 0.0,
    driver: Optional[Driver] = None,
    database: Optional[str] = None
) -> Dict[str, Any]:
    """
    Hàm tìm kiếm ngữ cảnh Graph RAG Đa bước hoàn chỉnh:
    1. Nhúng câu hỏi thành vector bằng mô hình tiếng Việt MSMARCO.
    2. Thực hiện Vector Search trong Neo4j để tìm top-k Chunks (Hop 0).
    3. Mở rộng đồ thị N-hops từ các Document gốc để tìm tài liệu liên kết và Chunks liên quan.
    4. Tổng hợp và đóng gói dữ liệu phục vụ Prompt LLM.

    Args:
        query: Câu hỏi cần tra cứu của người dùng.
        top_k: Số lượng phân đoạn văn bản tìm kiếm vector trực tiếp (mặc định: 3).
        num_hops: Số bước nhảy đồ thị đa bước (0: chỉ vector; 1: 1 hop; 2: 2 hops...).
        rel_types: Danh sách các mối quan hệ cho phép duyệt (None = tất cả quan hệ chuẩn).
        chunks_per_hop_doc: Số chunk lấy từ mỗi tài liệu liên quan trong multi-hop.
        score_threshold: Ngưỡng điểm Cosine tối thiểu.
        driver: Neo4j Driver (nếu không truyền sẽ tự tạo và đóng).
        database: Tên database (mặc định lấy từ cấu hình .env: 'kb-hops').

    Returns:
        Dict chứa đầy đủ thông tin: query, initial_chunks, traversal_paths,
        related_documents, hop_chunks, all_chunks, formatted_context.
    """
    cfg = get_db_config()
    db_name = database or cfg["database"]
    own_driver = False

    if driver is None:
        driver = get_neo4j_driver()
        own_driver = True

    try:
        # Bước 2.1: Chuyển đổi câu hỏi thành Vector nhúng
        embedder = get_embedding_model()
        t0 = time.time()
        query_vector = embedder.embed_query(query)
        embed_time = time.time() - t0

        # Bước 2.2: Vector Search trong Neo4j (Hop 0)
        t1 = time.time()
        initial_chunks = vector_search_chunks(
            driver=driver,
            database=db_name,
            query_vector=query_vector,
            top_k=top_k,
            score_threshold=score_threshold
        )
        search_time = time.time() - t1

        # Lấy danh sách ID các Document hạt nhân (Seed Documents)
        seed_doc_ids = []
        for c in initial_chunks:
            if c["doc_id"] and c["doc_id"] not in seed_doc_ids:
                seed_doc_ids.append(c["doc_id"])

        # Bước 2.3: Mở rộng Đa bước (Multi-hop Expansion: Hop 1 -> N)
        t2 = time.time()
        traversal_paths, related_documents, hop_chunks = expand_multihop_graph(
            driver=driver,
            database=db_name,
            seed_doc_ids=seed_doc_ids,
            num_hops=num_hops,
            rel_types=rel_types,
            chunks_per_hop_doc=chunks_per_hop_doc,
            query_vector=query_vector
        )
        hop_time = time.time() - t2

        # Tổng hợp tất cả chunks (trực tiếp + đa bước)
        all_chunks = initial_chunks + hop_chunks

        # Tạo chuỗi Context chuẩn hóa cho Prompt LLM
        formatted_context = format_graph_context_for_prompt({
            "query": query,
            "initial_chunks": initial_chunks,
            "seed_doc_ids": seed_doc_ids,
            "traversal_paths": traversal_paths,
            "related_documents": related_documents,
            "hop_chunks": hop_chunks,
            "num_hops": num_hops
        })

        return {
            "query": query,
            "query_vector": query_vector,
            "num_hops": num_hops,
            "top_k": top_k,
            "seed_doc_ids": seed_doc_ids,
            "initial_chunks": initial_chunks,
            "traversal_paths": traversal_paths,
            "related_documents": related_documents,
            "hop_chunks": hop_chunks,
            "all_chunks": all_chunks,
            "formatted_context": formatted_context,
            "metrics": {
                "embed_time_s": embed_time,
                "vector_search_time_s": search_time,
                "multihop_expansion_time_s": hop_time,
                "total_time_s": embed_time + search_time + hop_time,
                "num_initial_chunks": len(initial_chunks),
                "num_traversal_paths": len(traversal_paths),
                "num_related_docs": len(related_documents),
                "num_hop_chunks": len(hop_chunks),
                "num_total_chunks": len(all_chunks)
            }
        }

    finally:
        if own_driver and driver:
            driver.close()


# ==============================================================================
# 5. ĐỊNH DẠNG NGỮ CẢNH (FORMAT GRAPH CONTEXT CHO LLM PROMPT)
# ==============================================================================

def format_graph_context_for_prompt(retrieval_data: Dict[str, Any]) -> str:
    """
    Đóng gói toàn bộ kết quả tìm kiếm Vector trực tiếp và Mở rộng Đồ thị Đa bước
    thành văn bản ngữ cảnh rõ ràng, có cấu trúc để nạp vào LLM Prompt.
    """
    initial_chunks = retrieval_data.get("initial_chunks", [])
    traversal_paths = retrieval_data.get("traversal_paths", [])
    related_documents = retrieval_data.get("related_documents", [])
    hop_chunks = retrieval_data.get("hop_chunks", [])
    num_hops = retrieval_data.get("num_hops", 0)

    context_lines = []
    context_lines.append("=== THÔNG TIN NGỮ CẢNH TỪ HỆ THỐNG GRAPH RAG ===")

    # 1. Phần phân đoạn văn bản trực tiếp (Hop 0)
    context_lines.append(f"\n--- 1. CÁC ĐOẠN VĂN BẢN KHỚP TRỰC TIẾP (VECTOR SEARCH - {len(initial_chunks)} Chunks) ---")
    if not initial_chunks:
        context_lines.append("[Không tìm thấy phân đoạn văn bản khớp trực tiếp]")
    else:
        for idx, c in enumerate(initial_chunks, 1):
            doc_info = f"Văn bản: {c['doc_so_ky_hieu']} - {c['doc_title']}"
            if c['doc_co_quan_ban_hanh']:
                doc_info += f" | Cơ quan ban hành: {c['doc_co_quan_ban_hanh']}"
            if c['doc_tinh_trang_hieu_luc']:
                doc_info += f" | Tình trạng: {c['doc_tinh_trang_hieu_luc']}"

            context_lines.append(f"\n[Đoạn {idx}] (Độ tương đồng: {c['score']:.4f})")
            context_lines.append(f"• Nguồn: {doc_info}")
            context_lines.append(f"• Tiêu đề mục: {c['heading']}")
            context_lines.append(f"• Nội dung: {c['text']}")

    # 2. Phần đường dẫn liên kết đồ thị (Graph Traversal Paths)
    if num_hops > 0:
        context_lines.append(f"\n--- 2. CÁC MỐI QUAN HỆ LIÊN KẾT ĐỒ THỊ (GRAPH TRAVERSAL - {num_hops} Hops) ---")
        if not traversal_paths:
            context_lines.append(f"[Không có mối quan hệ liên kết nào được tìm thấy trong bán kính {num_hops} bước nhảy]")
        else:
            for idx, path in enumerate(traversal_paths, 1):
                rels_str = []
                for rel in path["relationships"]:
                    r_type = rel["type"]
                    r_desc = f" ({rel['relationship']})" if rel.get("relationship") else ""
                    from_so = rel.get("from_so") or rel.get("from_id")
                    to_so = rel.get("to_so") or rel.get("to_id")
                    rels_str.append(f"[{from_so}] --[:{r_type}{r_desc}]--> [{to_so}]")

                path_repr = " -> ".join(rels_str)
                context_lines.append(f"• [Liên kết {idx} - Khoảng cách {path['hop_distance']} hop]: {path_repr}")
                context_lines.append(f"  + Văn bản liên quan đích: {path['target_so_ky_hieu']} - {path['target_title']}")

        # 3. Phần thông tin và phân đoạn từ tài liệu liên quan (Hop 1..N)
        context_lines.append(f"\n--- 3. NỘI DUNG TỪ CÁC VĂN BẢN LIÊN QUAN ĐA BƯỚC (MULTI-HOP CONTEXT) ---")
        if not related_documents:
            context_lines.append("[Không có tài liệu liên quan đa bước nào]")
        else:
            for idx, doc in enumerate(related_documents, 1):
                context_lines.append(f"\n[Văn bản liên quan {idx}] Số hiệu: {doc['doc_so_ky_hieu']} (Cách {doc['hop_distance']} hop)")
                context_lines.append(f"• Tiêu đề: {doc['doc_title']}")
                context_lines.append(f"• Cơ quan ban hành: {doc['doc_co_quan_ban_hanh']} | Tình trạng: {doc['doc_tinh_trang_hieu_luc']}")

                # Lấy các chunk thuộc văn bản này
                doc_chunks = [ch for ch in hop_chunks if ch["doc_id"] == doc["doc_id"]]
                if doc_chunks:
                    context_lines.append("• Các đoạn trích dẫn quan trọng:")
                    for c_idx, ch in enumerate(doc_chunks, 1):
                        context_lines.append(f"  ({c_idx}) [{ch['heading']}]: {ch['text']}")
                else:
                    context_lines.append("• (Chưa có trích đoạn chi tiết)")

    context_lines.append("\n=== HẾT THÔNG TIN NGỮ CẢNH ===")
    return "\n".join(context_lines)


# ==============================================================================
# 6. DEMO CLI VÀ KIỂM THỬ TRUY VẤN ĐA BƯỚC
# ==============================================================================

def print_search_results(res: Dict[str, Any]):
    """Hiển thị kết quả tìm kiếm trực quan trên terminal."""
    print("\n" + "=" * 90)
    print(f" CÂU HỎI TRUY VẤN: \"{res['query']}\"")
    print(f" CẤU HÌNH       : Top-k = {res['top_k']} | Số bước nhảy (Num hops) = {res['num_hops']}")
    print("=" * 90)

    m = res["metrics"]
    print(f"⏱️ THỜI GIAN THỰC THI:")
    print(f"  • Tạo Embedding Vector : {m['embed_time_s']:.3f}s")
    print(f"  • Vector Search        : {m['vector_search_time_s']:.3f}s (Tìm thấy {m['num_initial_chunks']} Chunks)")
    print(f"  • Multi-hop Expansion  : {m['multihop_expansion_time_s']:.3f}s ({m['num_traversal_paths']} liên kết, {m['num_related_docs']} docs, {m['num_hop_chunks']} hop chunks)")
    print(f"  • TỔNG THỜI GIAN       : {m['total_time_s']:.3f}s")

    print("\n" + "-" * 90)
    print(f"1. PHÂN ĐOẠN KHỚP TRỰC TIẾP (DIRECT VECTOR SEARCH - HOP 0):")
    print("-" * 90)
    for i, c in enumerate(res["initial_chunks"], 1):
        print(f"  [{i}] Score: {c['score']:.4f} | Văn bản: {c['doc_so_ky_hieu']} ({c['doc_id']})")
        print(f"      Tiêu đề: {c['doc_title'][:80]}...")
        print(f"      Mục    : {c['heading']}")
        print(f"      Nội dung: {c['text'][:150]}...\n")

    if res["num_hops"] > 0:
        print("-" * 90)
        print(f"2. CÁC ĐƯỜNG DẪN QUAN HỆ ĐA BƯỚC (GRAPH TRAVERSAL PATHS - {res['num_hops']} HOPS):")
        print("-" * 90)
        if not res["traversal_paths"]:
            print("  (Không tìm thấy liên kết đồ thị nào từ các tài liệu khớp ban đầu)")
        for i, p in enumerate(res["traversal_paths"], 1):
            rels_info = []
            for r in p["relationships"]:
                rels_info.append(f"{r.get('from_so') or r.get('from_id')} -[:{r['type']} ({r.get('relationship','')})]-> {r.get('to_so') or r.get('to_id')}")
            print(f"  ({i}) [Hop {p['hop_distance']}] {' -> '.join(rels_info)}")
            print(f"      => Đích: {p['target_so_ky_hieu']} - {p['target_title'][:70]}...")

        print("\n" + "-" * 90)
        print(f"3. NỘI DUNG TỪ TÀI LIỆU LIÊN QUAN (MULTI-HOP CONTEXT CHUNKS):")
        print("-" * 90)
        if not res["hop_chunks"]:
            print("  (Không có chunk nào từ tài liệu liên quan)")
        for i, hc in enumerate(res["hop_chunks"], 1):
            print(f"  [{i}] (Hop {hc['hop_level']}) Văn bản: {hc['doc_so_ky_hieu']} | Score: {hc['score']:.4f}")
            print(f"      Mục    : {hc['heading']}")
            print(f"      Nội dung: {hc['text'][:150]}...\n")

    print("=" * 90)


if __name__ == "__main__":
    print("=" * 90)
    print(" BƯỚC 2: KIỂM THỬ TRUY VẤN VECTOR VÀ MỐI QUAN HỆ ĐA BƯỚC (MULTI-HOP GRAPH RAG)")
    print("=" * 90)

    # 5 câu hỏi kiểm thử chuẩn theo đề bài Buổi 11 Bước 4
    test_queries = [
        ("Nghị định 46/2023/NĐ-CP thay thế cho nghị định nào, và nghị định bị thay thế đó có nội dung gì nổi bật về kinh doanh bảo hiểm?", 1),
        ("Văn bản hợp nhất số 52/VBHN-NHNN được hợp nhất từ văn bản nào, và quy định về hồ sơ, thủ tục cấp giấy phép lần đầu của ngân hàng thương mại gồm những tài liệu gì?", 1),
        ("Thông tư số 01/2025/TT-NHNN quy định về cấp giấy phép quỹ tín dụng nhân dân được sửa đổi, bổ sung bởi văn bản nào, và những nội dung sửa đổi bổ sung chính là gì?", 1),
        ("Thông tư số 41/2016/TT-NHNN về tỷ lệ an toàn vốn của ngân hàng căn cứ vào luật nào, và luật đó quy định chức năng nhiệm vụ của cơ quan nào?", 1),
        ("Hoạt động giao nhận, vận chuyển tiền mặt và tài sản quý của Ngân hàng Nhà nước được điều chỉnh bởi Thông tư nào, và Thông tư đó có được sửa đổi bổ sung bởi văn bản nào không?", 1),
    ]

    print("\nChọn chế độ chạy:")
    print("1. Chạy thử 1 câu hỏi mẫu (Nghị định 46/2023/NĐ-CP thay thế...)")
    print("2. Chạy toàn bộ 5 câu hỏi kiểm thử")
    print("3. Nhập câu hỏi tùy chỉnh từ bàn phím")

    # Mặc định chạy câu hỏi 1 làm mẫu minh họa
    sample_q, sample_hops = test_queries[0]
    print(f"\n[*] Đang thực hiện tìm kiếm câu hỏi mẫu:")
    print(f"    Câu hỏi: {sample_q}")
    print(f"    Số bước nhảy (hops): {sample_hops}")

    try:
        results = search_graph_rag_context(query=sample_q, top_k=3, num_hops=sample_hops)
        print_search_results(results)
    except Exception as e:
        print(f"\n[!] Lỗi khi thực thi tìm kiếm: {e}")
        print("    Vui lòng kiểm tra lại kết nối Neo4j (bật Neo4j Desktop và database kb-hops)!")
