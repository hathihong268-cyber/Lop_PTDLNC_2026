"""
Module: secure_retriever.py
Buổi 15: Cài đặt Kiểm soát Truy cập dựa trên Vai trò (RBAC) ở mức Dữ liệu & Retrieval Pipeline
Nhiệm vụ: Cung cấp Secure Retrieval Pipeline (BM25, Dense, Hybrid RRF, Cross-Encoder Reranker, Graph Hints)
đảm bảo 100% kết quả và ứng viên đều được lọc quyền truy cập dựa trên `user_roles`.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
import pandas as pd
import numpy as np

# Đảm bảo UTF-8 trên Windows console
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.config import (
    CHUNKS_SECURE_PATH,
    CACHE_DIR,
    VALID_ROLES,
    ROLE_ADMIN,
    ROLE_HR_MANAGER,
    ROLE_RISK_OFFICER,
    ROLE_EMPLOYEE,
    ROLE_GUEST,
    validate_roles,
    get_neo4j_driver,
    get_neo4j_config,
)
from src.citation import format_citation
from src.bm25_retriever import BM25Retriever, tokenize_vietnamese_legal
from src.dense_retriever import DenseRetriever
from src.reranker import CrossEncoderReranker


def parse_roles_list(raw: Any) -> List[str]:
    """Chuyển đổi allowed_roles thành List[str] an toàn."""
    if isinstance(raw, list):
        return [str(r).strip() for r in raw]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(r).strip() for r in parsed]
        except Exception:
            pass
        cleaned = raw.strip("[]'\" ").split(",")
        return [r.strip().strip("'\"") for r in cleaned if r.strip().strip("'\"")]
    return [ROLE_GUEST]


def check_access_permission(chunk_roles: List[str], user_roles: List[str]) -> Tuple[bool, List[str]]:
    """
    Kiểm tra xem người dùng có quyền truy cập chunk này hay không.
    Trả về (is_allowed, matched_roles).
    """
    if ROLE_ADMIN in user_roles:
        return True, [ROLE_ADMIN]
    
    chunk_roles_set = set(chunk_roles)
    matched = [r for r in user_roles if r in chunk_roles_set]
    return len(matched) > 0, matched


class SecureRetriever:
    """
    Hệ thống Secure Retrieval Pipeline tích hợp RBAC:
    - Pre-filtering / Post-filtering trên BM25 & Dense Search
    - Secure Hybrid Fusion (chỉ tính RRF trên các ứng viên hợp lệ)
    - Secure Neural Reranking (chỉ xếp hạng ứng viên được phép xem)
    - Secure Graph Hints (truy vấn Cypher có WHERE any(...))
    """

    def __init__(
        self,
        corpus_csv_path: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        rrf_k: int = 60
    ):
        self.corpus_csv_path = Path(corpus_csv_path) if corpus_csv_path else CHUNKS_SECURE_PATH
        self.cache_dir = Path(cache_dir) if cache_dir else CACHE_DIR
        self.rrf_k = rrf_k

        if not self.corpus_csv_path.exists():
            raise FileNotFoundError(f"Không tìm thấy file corpus bảo mật: {self.corpus_csv_path}")

        # Đọc dữ liệu corpus bảo mật
        self.df = pd.read_csv(self.corpus_csv_path, dtype=str).fillna("")
        self.chunks: List[Dict[str, Any]] = self.df.to_dict(orient="records")
        
        # Parse sẵn allowed_roles cho từng chunk trong bộ nhớ để lọc nhanh
        self.chunk_roles_cache: List[List[str]] = [
            parse_roles_list(c.get("allowed_roles", "[]")) for c in self.chunks
        ]

        # Khởi tạo BM25 & Dense & Reranker
        print("[*] Khởi tạo các thành phần Secure Retrieval Pipeline...")
        self.bm25_component = BM25Retriever(self.corpus_csv_path)
        self.dense_component = DenseRetriever(self.corpus_csv_path, self.cache_dir)
        self.reranker_component = CrossEncoderReranker()
        print("[+] Secure Retrieval Pipeline đã sẵn sàng.")

    def search_bm25_secure(
        self,
        query: str,
        user_roles: List[str],
        top_k: int = 5
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Tìm kiếm BM25 kèm lọc quyền truy cập:
        Chỉ trả về các chunk mà người dùng có quyền xem.
        """
        tokenized_query = tokenize_vietnamese_legal(query)
        if not tokenized_query:
            return [], 0

        scores = self.bm25_component.bm25.get_scores(tokenized_query)
        # Sắp xếp toàn bộ theo thứ tự điểm giảm dần
        sorted_indices = np.argsort(scores)[::-1]

        results = []
        filtered_out_count = 0

        for idx in sorted_indices:
            chunk_allowed_roles = self.chunk_roles_cache[idx]
            has_permission, matched_roles = check_access_permission(chunk_allowed_roles, user_roles)

            if not has_permission:
                filtered_out_count += 1
                continue

            row = self.chunks[idx]
            score = float(scores[idx])

            results.append({
                "rank": len(results) + 1,
                "chunk_id": row["chunk_id"],
                "document_id": row["document_id"],
                "text": row["text"],
                "score": round(score, 4),
                "retrieval_score": round(score, 4),
                "retrieval_method": "bm25",
                "citation": format_citation(row),
                "allowed_roles": chunk_allowed_roles,
                "matched_roles": matched_roles,
            })

            if len(results) >= top_k:
                break

        return results, filtered_out_count

    def search_dense_secure(
        self,
        query: str,
        user_roles: List[str],
        top_k: int = 5
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Tìm kiếm Dense Vector Embedding kèm lọc quyền truy cập:
        Tính tương đồng Cosine và lọc bỏ các chunk bị cấm trước khi trả về top_k.
        """
        query_vec = self.dense_component.embed_query(query)
        scores = np.dot(self.dense_component.doc_embeddings, query_vec)
        sorted_indices = np.argsort(scores)[::-1]

        results = []
        filtered_out_count = 0

        for idx in sorted_indices:
            chunk_allowed_roles = self.chunk_roles_cache[idx]
            has_permission, matched_roles = check_access_permission(chunk_allowed_roles, user_roles)

            if not has_permission:
                filtered_out_count += 1
                continue

            row = self.chunks[idx]
            score = float(scores[idx])

            results.append({
                "rank": len(results) + 1,
                "chunk_id": row["chunk_id"],
                "document_id": row["document_id"],
                "text": row["text"],
                "score": round(score, 4),
                "retrieval_score": round(score, 4),
                "retrieval_method": "dense",
                "citation": format_citation(row),
                "allowed_roles": chunk_allowed_roles,
                "matched_roles": matched_roles,
            })

            if len(results) >= top_k:
                break

        return results, filtered_out_count

    def search_hybrid_secure(
        self,
        query: str,
        user_roles: List[str],
        top_k: int = 5,
        candidate_k: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Tìm kiếm Hybrid (BM25 + Dense) an toàn:
        1. Lấy candidate_k từ BM25 an toàn (đã lọc quyền)
        2. Lấy candidate_k từ Dense an toàn (đã lọc quyền)
        3. Kết hợp bằng RRF
        4. Trả về top_k kết quả hoàn toàn sạch về bảo mật
        """
        bm25_candidates, bm25_filtered = self.search_bm25_secure(query, user_roles, top_k=candidate_k)
        dense_candidates, dense_filtered = self.search_dense_secure(query, user_roles, top_k=candidate_k)

        fused_map: Dict[str, Dict[str, Any]] = {}

        for item in bm25_candidates:
            cid = item["chunk_id"]
            rank = item["rank"]
            rrf_val = 1.0 / (self.rrf_k + rank)

            if cid not in fused_map:
                fused_map[cid] = {
                    "chunk_id": cid,
                    "document_id": item["document_id"],
                    "bm25_rank": rank,
                    "dense_rank": None,
                    "bm25_score": item["retrieval_score"],
                    "dense_score": None,
                    "rrf_score": rrf_val,
                    "text": item["text"],
                    "citation": item["citation"],
                    "allowed_roles": item["allowed_roles"],
                    "matched_roles": item["matched_roles"],
                }
            else:
                fused_map[cid]["bm25_rank"] = rank
                fused_map[cid]["bm25_score"] = item["retrieval_score"]
                fused_map[cid]["rrf_score"] += rrf_val

        for item in dense_candidates:
            cid = item["chunk_id"]
            rank = item["rank"]
            rrf_val = 1.0 / (self.rrf_k + rank)

            if cid not in fused_map:
                fused_map[cid] = {
                    "chunk_id": cid,
                    "document_id": item["document_id"],
                    "bm25_rank": None,
                    "dense_rank": rank,
                    "bm25_score": None,
                    "dense_score": item["retrieval_score"],
                    "rrf_score": rrf_val,
                    "text": item["text"],
                    "citation": item["citation"],
                    "allowed_roles": item["allowed_roles"],
                    "matched_roles": item["matched_roles"],
                }
            else:
                fused_map[cid]["dense_rank"] = rank
                fused_map[cid]["dense_score"] = item["retrieval_score"]
                fused_map[cid]["rrf_score"] += rrf_val

        sorted_candidates = sorted(fused_map.values(), key=lambda x: x["rrf_score"], reverse=True)

        final_results = []
        for idx, item in enumerate(sorted_candidates[:top_k], 1):
            final_results.append({
                "rank": idx,
                "final_rank": idx,
                "chunk_id": item["chunk_id"],
                "document_id": item["document_id"],
                "bm25_rank": item["bm25_rank"],
                "dense_rank": item["dense_rank"],
                "score": round(item["rrf_score"], 6),
                "rrf_score": round(item["rrf_score"], 6),
                "hybrid_score": round(item["rrf_score"], 6),
                "text": item["text"],
                "citation": item["citation"],
                "retrieval_method": "hybrid",
                "allowed_roles": item["allowed_roles"],
                "matched_roles": item["matched_roles"],
                "bm25_score": item["bm25_score"],
                "dense_score": item["dense_score"],
            })

        total_filtered = bm25_filtered + dense_filtered
        return final_results, total_filtered

    def search_hybrid_rerank_secure(
        self,
        query: str,
        user_roles: List[str],
        top_k: int = 5,
        candidate_k: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Tìm kiếm Hybrid + Reranker an toàn:
        Chỉ đưa các ứng viên đã vượt qua bảo mật sang Cross-Encoder Reranker.
        """
        candidates, filtered_count = self.search_hybrid_secure(
            query=query,
            user_roles=user_roles,
            top_k=candidate_k,
            candidate_k=candidate_k
        )

        if not candidates:
            return [], filtered_count

        reranked = self.reranker_component.rerank(query, candidates, top_k=top_k)

        final_results = []
        for r in reranked:
            final_results.append({
                "rank": r["final_rank"],
                "chunk_id": r["chunk_id"],
                "document_id": r["document_id"],
                "text": r["text"],
                "score": r["rerank_score"],
                "rerank_score": r["rerank_score"],
                "hybrid_score": r.get("hybrid_score"),
                "hybrid_rank": r.get("hybrid_rank"),
                "citation": r["citation"],
                "retrieval_method": "hybrid_rerank",
                "allowed_roles": r.get("allowed_roles", []),
                "matched_roles": r.get("matched_roles", []),
                "rank_shift": r.get("rank_shift", 0),
            })

        return final_results, filtered_count

    def get_secure_graph_hints(
        self,
        retrieved_results: List[Dict[str, Any]],
        user_roles: List[str]
    ) -> Dict[str, Any]:
        """
        Truy vấn Graph Hints từ Neo4j có tích hợp mệnh đề bảo mật:
        WHERE any(role IN node.allowed_roles WHERE role IN $user_roles)
        """
        hints = {
            "connected": False,
            "document_relations": [],
            "adjacent_chunks": [],
            "error_message": None
        }

        if not retrieved_results:
            return hints

        try:
            driver, database = get_neo4j_driver()
            driver.verify_connectivity()
        except Exception as e:
            hints["error_message"] = f"Neo4j không khả dụng ({e}). Bỏ qua Graph Hints."
            return hints

        hints["connected"] = True
        doc_ids = list({r["document_id"] for r in retrieved_results if "document_id" in r})
        chunk_ids = list({r["chunk_id"] for r in retrieved_results if "chunk_id" in r})

        try:
            with driver.session(database=database) as session:
                # 1. Document to Document Relations có lọc quyền
                q_doc_rel = """
                MATCH (v1:VanBan)-[r]->(v2:VanBan)
                WHERE (v1.id IN $doc_ids OR v2.id IN $doc_ids)
                  AND ($is_admin OR any(role IN v1.allowed_roles WHERE role IN $user_roles))
                  AND ($is_admin OR any(role IN v2.allowed_roles WHERE role IN $user_roles))
                RETURN v1.id AS src_id, v1.so_ky_hieu AS src_doc, v1.allowed_roles AS src_roles,
                       type(r) AS rel_type, r.relationship_label AS rel_label,
                       v2.id AS dst_id, v2.so_ky_hieu AS dst_doc, v2.allowed_roles AS dst_roles
                LIMIT 10
                """
                is_admin = ROLE_ADMIN in user_roles
                doc_res = session.run(q_doc_rel, doc_ids=doc_ids, user_roles=user_roles, is_admin=is_admin).data()
                for d in doc_res:
                    rel_label_str = f" ({d['rel_label']})" if d.get('rel_label') else ""
                    hints["document_relations"].append(
                        f"[{d['src_doc']}] --[:{d['rel_type']}{rel_label_str}]--> [{d['dst_doc']}]"
                    )

                # 2. Adjacent NEXT Chunks có lọc quyền
                q_next = """
                MATCH (d1:DieuKhoan)-[:NEXT]->(d2:DieuKhoan)
                WHERE (d1.id IN $chunk_ids OR d2.id IN $chunk_ids)
                  AND ($is_admin OR any(role IN d1.allowed_roles WHERE role IN $user_roles))
                  AND ($is_admin OR any(role IN d2.allowed_roles WHERE role IN $user_roles))
                RETURN d1.id AS from_chunk, d1.article AS from_art,
                       d2.id AS to_chunk, d2.article AS to_art
                LIMIT 5
                """
                next_res = session.run(q_next, chunk_ids=chunk_ids, user_roles=user_roles, is_admin=is_admin).data()
                for n in next_res:
                    f_art = n['from_art'].split('.')[0] if '.' in n['from_art'] else n['from_art']
                    t_art = n['to_art'].split('.')[0] if '.' in n['to_art'] else n['to_art']
                    hints["adjacent_chunks"].append(
                        f"({n['from_chunk']} [{f_art}]) --[:NEXT]--> ({n['to_chunk']} [{t_art}])"
                    )
        finally:
            driver.close()

        return hints


# ==============================================================================
# SINGLETON INSTANCE & UNIFIED SECURE RETRIEVE FUNCTION
# ==============================================================================
_GLOBAL_SECURE_RETRIEVER: Optional[SecureRetriever] = None


def get_or_create_secure_retriever() -> SecureRetriever:
    """Khởi tạo và tái sử dụng SecureRetriever instance."""
    global _GLOBAL_SECURE_RETRIEVER
    if _GLOBAL_SECURE_RETRIEVER is None:
        _GLOBAL_SECURE_RETRIEVER = SecureRetriever()
    return _GLOBAL_SECURE_RETRIEVER


def secure_retrieve(
    query: str,
    user_roles: List[str],
    method: str = "hybrid_rerank",
    top_k: int = 5,
    candidate_k: int = 20,
    include_graph_hints: bool = True
) -> Dict[str, Any]:
    """
    Hàm truy xuất an toàn thống nhất (Unified Secure Retrieve).

    Tham số:
    - query: Câu hỏi truy vấn
    - user_roles: Danh sách vai trò của người dùng (ví dụ: ["Guest"], ["HR_Manager"], ["Admin"])
    - method: Phương pháp tìm kiếm ('bm25', 'dense', 'hybrid', 'hybrid_rerank')
    - top_k: Số kết quả cần trả về (mặc định: 5)
    - candidate_k: Số ứng viên thu thập trước khi rerank (mặc định: 20)
    - include_graph_hints: Trích xuất gợi ý đồ thị an toàn từ Neo4j

    Trả về:
    - Dict chứa 'results', 'user_roles', 'method', 'filtered_out_count', 'graph_hints'
    """
    if not query or not query.strip():
        raise ValueError("Câu hỏi query không được để trống.")

    clean_user_roles = validate_roles(user_roles)
    retriever = get_or_create_secure_retriever()

    method_lower = method.lower().strip()
    valid_methods = ["bm25", "dense", "hybrid", "hybrid_rerank"]
    if method_lower not in valid_methods:
        raise ValueError(f"Phương pháp không hợp lệ: '{method}'. Phải thuộc {valid_methods}")

    start_time = time.time()

    if method_lower == "bm25":
        results, filtered_count = retriever.search_bm25_secure(query, clean_user_roles, top_k=top_k)
    elif method_lower == "dense":
        results, filtered_count = retriever.search_dense_secure(query, clean_user_roles, top_k=top_k)
    elif method_lower == "hybrid":
        results, filtered_count = retriever.search_hybrid_secure(
            query, clean_user_roles, top_k=top_k, candidate_k=candidate_k
        )
    elif method_lower == "hybrid_rerank":
        results, filtered_count = retriever.search_hybrid_rerank_secure(
            query, clean_user_roles, top_k=top_k, candidate_k=candidate_k
        )

    graph_hints = None
    if include_graph_hints:
        graph_hints = retriever.get_secure_graph_hints(results, clean_user_roles)

    elapsed_ms = (time.time() - start_time) * 1000

    return {
        "query": query,
        "user_roles": clean_user_roles,
        "method": method_lower,
        "top_k": top_k,
        "results_count": len(results),
        "filtered_out_count": filtered_count,
        "elapsed_ms": round(elapsed_ms, 2),
        "results": results,
        "graph_hints": graph_hints
    }


if __name__ == "__main__":
    print("=" * 70)
    print("DEMO KIỂM THỬ BỘ TÌM KIẾM AN TOÀN (SECURE RETRIEVER)")
    print("=" * 70)

    test_queries = [
        # Query 1: Câu hỏi về Nhân sự (Chỉ HR & Admin có quyền)
        ("Tiêu chuẩn bổ nhiệm chức danh thủ kho tiền, thủ quỹ", "HR Query"),
        # Query 2: Câu hỏi về Rủi ro & Vận chuyển tiền (Risk, Employee, Admin)
        ("Quy trình áp tải và vận chuyển tiền mặt trong ngành Ngân hàng", "Risk Query"),
        # Query 3: Câu hỏi về Phạm vi áp dụng chung (Tất cả vai trò kể cả Guest)
        ("Phạm vi và đối tượng áp dụng Luật kinh doanh bảo hiểm", "Public Query"),
    ]

    roles_to_test = [
        ("Guest", [ROLE_GUEST]),
        ("HR_Manager", [ROLE_HR_MANAGER]),
        ("Risk_Officer", [ROLE_RISK_OFFICER]),
        ("Admin", [ROLE_ADMIN]),
    ]

    for q, q_type in test_queries:
        print("\n" + "=" * 70)
        print(f"QUERY: '{q}' [{q_type}]")
        print("=" * 70)
        
        for role_name, r_list in roles_to_test:
            out = secure_retrieve(q, user_roles=r_list, method="hybrid_rerank", top_k=3, include_graph_hints=False)
            print(f"\n[Role: {role_name:<12}] -> Trả về {len(out['results'])} kết quả (Đã lọc bỏ {out['filtered_out_count']} chunks cấm):")
            for item in out["results"]:
                print(f"   Rank {item['rank']}: [{item['chunk_id']}] Score: {item['score']} | Allowed: {item['allowed_roles']}")
