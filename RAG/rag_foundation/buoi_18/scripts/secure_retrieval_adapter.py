"""
Module: secure_retrieval_adapter.py
Vị trí: buoi_17/scripts/secure_retrieval_adapter.py
Mục đích: Adapter tái sử dụng SecureRetriever của Buổi 14, chuẩn hóa output đúng cấu hình yêu cầu của Buổi 17.
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

# Thêm đường dẫn buoi_14 vào sys.path để import trực tiếp module Buổi 14
CURRENT_DIR = Path(__file__).resolve().parent
BUOI_17_DIR = CURRENT_DIR.parent
PROJECT_ROOT = BUOI_17_DIR.parent
BUOI_14_DIR = PROJECT_ROOT / "buoi_14"

if str(BUOI_14_DIR) not in sys.path:
    sys.path.insert(0, str(BUOI_14_DIR))

try:
    from src.secure_retriever import SecureRetriever, get_or_create_secure_retriever, secure_retrieve
    from src.config import validate_roles
except ImportError as e:
    raise ImportError(f"Không thể import SecureRetriever từ Buổi 14 ({BUOI_14_DIR}): {e}")


class SecureRetrievalAdapter:
    """
    Adapter wrap SecureRetriever từ Buổi 14.
    Không viết lại retriever mới, chỉ gọi retriever gốc và chuẩn hóa schema kết quả.
    """

    def __init__(self, corpus_csv_path: Optional[Path] = None):
        if corpus_csv_path is None:
            # Mặc định sử dụng dữ liệu chunks_secure.csv từ Buổi 14
            corpus_csv_path = BUOI_14_DIR / "data" / "processed" / "chunks_secure.csv"
        
        self.retriever = SecureRetriever(corpus_csv_path=corpus_csv_path)
        # Bảng tra cứu metadata theo chunk_id để bổ sung title và article nếu thiếu
        self.chunk_meta_map: Dict[str, Dict[str, Any]] = {
            c["chunk_id"]: c for c in self.retriever.chunks
        }

    def retrieve(
        self,
        query: str,
        user_roles: List[str],
        method: str = "hybrid_rerank",
        top_k: int = 5,
        candidate_k: int = 20,
        include_graph_hints: bool = False
    ) -> Dict[str, Any]:
        """
        Thực hiện truy xuất an toàn và chuẩn hóa kết quả đầu ra.
        
        Output schema của từng result item:
        - rank (int)
        - chunk_id (str)
        - document_id (str)
        - title (str)
        - article (str)
        - citation (str)
        - allowed_roles (List[str])
        - access_decision (str) -> "ALLOWED"
        - retrieval_method (str)
        """
        raw_output = secure_retrieve(
            query=query,
            user_roles=user_roles,
            method=method,
            top_k=top_k,
            candidate_k=candidate_k,
            include_graph_hints=include_graph_hints
        )

        normalized_results = []
        for idx, item in enumerate(raw_output.get("results", []), 1):
            cid = item.get("chunk_id", "")
            meta = self.chunk_meta_map.get(cid, {})

            normalized_item = {
                "rank": item.get("rank", idx),
                "chunk_id": cid,
                "document_id": item.get("document_id", meta.get("document_id", "")),
                "title": meta.get("title", ""),
                "article": meta.get("article", ""),
                "citation": item.get("citation", ""),
                "allowed_roles": item.get("allowed_roles", meta.get("allowed_roles", [])),
                "access_decision": "ALLOWED",  # Mọi chunk trả về đều đã vượt qua bộ lọc RBAC
                "retrieval_method": item.get("retrieval_method", method),
                "score": item.get("score", 0.0),
                "text": item.get("text", meta.get("text", "")),
                "matched_roles": item.get("matched_roles", [])
            }
            normalized_results.append(normalized_item)

        return {
            "query": raw_output.get("query", query),
            "user_roles": raw_output.get("user_roles", user_roles),
            "method": raw_output.get("method", method),
            "top_k": raw_output.get("top_k", top_k),
            "results_count": len(normalized_results),
            "filtered_out_count": raw_output.get("filtered_out_count", 0),
            "elapsed_ms": raw_output.get("elapsed_ms", 0.0),
            "results": normalized_results,
            "graph_hints": raw_output.get("graph_hints", None)
        }


def get_adapted_secure_retriever() -> SecureRetrievalAdapter:
    """Tạo hoặc sử dụng adapter singleton."""
    return SecureRetrievalAdapter()


if __name__ == "__main__":
    print("=" * 70)
    print("DEMO SECURE RETRIEVAL ADAPTER (BUỔI 17)")
    print("=" * 70)
    adapter = get_adapted_secure_retriever()
    res = adapter.retrieve(
        query="Tiêu chuẩn bổ nhiệm chức danh thủ kho tiền, thủ quỹ",
        user_roles=["HR_Manager"],
        method="hybrid_rerank",
        top_k=3
    )
    print(f"Query: {res['query']}")
    print(f"User Roles: {res['user_roles']}")
    print(f"Results Count: {res['results_count']} (Filtered out: {res['filtered_out_count']})")
    for r in res["results"]:
        print(f"\n[Rank {r['rank']}] Chunk ID: {r['chunk_id']} | Doc ID: {r['document_id']}")
        print(f"  Title: {r['title'][:60]}...")
        print(f"  Article: {r['article']}")
        print(f"  Citation: {r['citation']}")
        print(f"  Allowed Roles: {r['allowed_roles']}")
        print(f"  Access Decision: {r['access_decision']}")
        print(f"  Retrieval Method: {r['retrieval_method']}")
