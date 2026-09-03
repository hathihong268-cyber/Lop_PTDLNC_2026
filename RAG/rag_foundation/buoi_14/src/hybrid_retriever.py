"""
Module: hybrid_retriever.py
Buổi 14: Hybrid Search + Reranking + Mini Knowledge Graph
Nhiệm vụ: Bộ truy xuất Hybrid kết hợp Lexical (BM25) và Semantic (Dense Embedding)
sử dụng thuật toán Reciprocal Rank Fusion (RRF).
"""

from pathlib import Path
from typing import List, Dict, Any, Optional

from src.bm25_retriever import BM25Retriever
from src.dense_retriever import DenseRetriever
from src.citation import format_citation


class HybridRetriever:
    """
    Bộ truy xuất Hybrid Search kết hợp BM25 và Dense Retriever bằng RRF.
    """

    def __init__(
        self,
        bm25_retriever: Optional[BM25Retriever] = None,
        dense_retriever: Optional[DenseRetriever] = None,
        corpus_csv_path: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        rrf_k: int = 60
    ):
        base_dir = Path(__file__).resolve().parent.parent
        if corpus_csv_path is None:
            corpus_csv_path = base_dir / "data" / "processed" / "chunks_normalized.csv"
        if cache_dir is None:
            cache_dir = base_dir / "cache"

        self.corpus_csv_path = Path(corpus_csv_path)
        self.cache_dir = Path(cache_dir)
        self.rrf_k = rrf_k

        # Tái sử dụng hoặc khởi tạo retriever
        self.bm25 = bm25_retriever if bm25_retriever is not None else BM25Retriever(self.corpus_csv_path)
        self.dense = dense_retriever if dense_retriever is not None else DenseRetriever(self.corpus_csv_path, self.cache_dir)

    def search(self, query: str, top_k: int = 5, candidate_k: int = 20) -> List[Dict[str, Any]]:
        """
        Thực thi Hybrid Search:
        1. Lấy candidate_k từ BM25
        2. Lấy candidate_k từ Dense
        3. Hợp nhất bằng Reciprocal Rank Fusion (RRF)
        4. Trả về top_k theo schema chuẩn
        """
        # 1 & 2. Thu thập ứng viên
        bm25_candidates = self.bm25.search(query, top_k=candidate_k)
        dense_candidates = self.dense.search(query, top_k=candidate_k)

        # 3. Fusion theo chunk_id bằng RRF
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
                    "citation": item["citation"]
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
                    "citation": item["citation"]
                }
            else:
                fused_map[cid]["dense_rank"] = rank
                fused_map[cid]["dense_score"] = item["retrieval_score"]
                fused_map[cid]["rrf_score"] += rrf_val

        # 4. Sắp xếp giảm dần theo điểm RRF Score
        sorted_candidates = sorted(fused_map.values(), key=lambda x: x["rrf_score"], reverse=True)

        # 5. Cắt lấy top_k và gán final_rank
        final_results = []
        for idx, item in enumerate(sorted_candidates[:top_k], 1):
            final_results.append({
                "final_rank": idx,
                "chunk_id": item["chunk_id"],
                "document_id": item["document_id"],
                "bm25_rank": item["bm25_rank"],
                "dense_rank": item["dense_rank"],
                "rrf_score": round(item["rrf_score"], 6),
                "text": item["text"],
                "citation": item["citation"],
                "bm25_score": item["bm25_score"],
                "dense_score": item["dense_score"]
            })

        return final_results
