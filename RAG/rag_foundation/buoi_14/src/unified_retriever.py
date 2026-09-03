"""
Module: unified_retriever.py
Buổi 14: Hybrid Search + Reranking + Mini Knowledge Graph
Nhiệm vụ: Cung cấp hàm retrieval thống nhất `retrieve(question, method, top_k)`
hỗ trợ cả 4 phương pháp: bm25, dense, hybrid, hybrid_rerank.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional

from src.bm25_retriever import BM25Retriever
from src.dense_retriever import DenseRetriever
from src.hybrid_retriever import HybridRetriever
from src.reranker import CrossEncoderReranker

BASE_DIR = Path(__file__).resolve().parent.parent

# Cache các instance của Retriever để tránh khởi tạo lại nhiều lần
_GLOBAL_COMPONENTS = {
    "bm25": None,
    "dense": None,
    "hybrid": None,
    "reranker": None
}


def get_or_create_components() -> Dict[str, Any]:
    """Khởi tạo và tái sử dụng các thành phần retrieval."""
    corpus_path = BASE_DIR / "data" / "processed" / "chunks_normalized.csv"
    cache_dir = BASE_DIR / "cache"

    if _GLOBAL_COMPONENTS["bm25"] is None:
        _GLOBAL_COMPONENTS["bm25"] = BM25Retriever(corpus_path)

    if _GLOBAL_COMPONENTS["dense"] is None:
        _GLOBAL_COMPONENTS["dense"] = DenseRetriever(corpus_path, cache_dir)

    if _GLOBAL_COMPONENTS["hybrid"] is None:
        _GLOBAL_COMPONENTS["hybrid"] = HybridRetriever(
            bm25_retriever=_GLOBAL_COMPONENTS["bm25"],
            dense_retriever=_GLOBAL_COMPONENTS["dense"],
            corpus_csv_path=corpus_path,
            cache_dir=cache_dir
        )

    if _GLOBAL_COMPONENTS["reranker"] is None:
        _GLOBAL_COMPONENTS["reranker"] = CrossEncoderReranker()

    return _GLOBAL_COMPONENTS


def retrieve(
    question: str,
    method: str = "hybrid_rerank",
    top_k: int = 5,
    candidate_k: int = 20
) -> List[Dict[str, Any]]:
    """
    Hàm truy xuất dữ liệu thống nhất cho toàn bộ hệ thống RAG.

    Tham số:
    - question: Câu hỏi truy vấn
    - method: Phương pháp truy xuất ('bm25', 'dense', 'hybrid', 'hybrid_rerank')
    - top_k: Số lượng kết quả cuối cùng cần lấy ra
    - candidate_k: Số lượng ứng viên từ Hybrid trước khi Rerank (mặc định 20)

    Schema đầu ra chuẩn cho mỗi kết quả:
    - rank: Thứ hạng cuối cùng (1, 2, ...)
    - chunk_id: Mã định danh duy nhất của chunk
    - document_id: ID văn bản gốc
    - text: Nội dung văn bản
    - score: Điểm số chính theo phương pháp được chọn
    - citation: Chuỗi trích dẫn chuẩn [Tên văn bản | Điều | chunk_id]
    - retrieval_method: Tên phương pháp
    - hybrid_score: (Chỉ có ở hybrid / hybrid_rerank) Điểm RRF
    - rerank_score: (Chỉ có ở hybrid_rerank) Điểm Sigmoid từ Cross-Encoder
    """
    if not question or not question.strip():
        raise ValueError("Câu hỏi question không được để trống.")

    valid_methods = ["bm25", "dense", "hybrid", "hybrid_rerank"]
    method_lower = method.lower().strip()
    if method_lower not in valid_methods:
        raise ValueError(f"Phương pháp không hợp lệ: '{method}'. Phải thuộc {valid_methods}")

    components = get_or_create_components()
    results: List[Dict[str, Any]] = []

    # 1. BM25-only
    if method_lower == "bm25":
        raw_res = components["bm25"].search(question, top_k=top_k)
        for r in raw_res:
            results.append({
                "rank": r["rank"],
                "chunk_id": r["chunk_id"],
                "document_id": r["document_id"],
                "text": r["text"],
                "score": r["retrieval_score"],
                "citation": r["citation"],
                "retrieval_method": "bm25"
            })

    # 2. Dense-only
    elif method_lower == "dense":
        raw_res = components["dense"].search(question, top_k=top_k)
        for r in raw_res:
            results.append({
                "rank": r["rank"],
                "chunk_id": r["chunk_id"],
                "document_id": r["document_id"],
                "text": r["text"],
                "score": r["retrieval_score"],
                "citation": r["citation"],
                "retrieval_method": "dense"
            })

    # 3. Hybrid Search (RRF)
    elif method_lower == "hybrid":
        raw_res = components["hybrid"].search(question, top_k=top_k, candidate_k=candidate_k)
        for r in raw_res:
            results.append({
                "rank": r["final_rank"],
                "chunk_id": r["chunk_id"],
                "document_id": r["document_id"],
                "text": r["text"],
                "score": r["rrf_score"],
                "citation": r["citation"],
                "retrieval_method": "hybrid",
                "hybrid_score": r["rrf_score"],
                "bm25_rank": r["bm25_rank"],
                "dense_rank": r["dense_rank"]
            })

    # 4. Hybrid + Cross-Encoder Reranking
    elif method_lower == "hybrid_rerank":
        candidates = components["hybrid"].search(question, top_k=candidate_k, candidate_k=candidate_k)
        reranked = components["reranker"].rerank(question, candidates, top_k=top_k)
        for r in reranked:
            results.append({
                "rank": r["final_rank"],
                "chunk_id": r["chunk_id"],
                "document_id": r["document_id"],
                "text": r["text"],
                "score": r["rerank_score"],
                "citation": r["citation"],
                "retrieval_method": "hybrid_rerank",
                "hybrid_rank": r.get("hybrid_rank"),
                "hybrid_score": r.get("hybrid_score"),
                "rerank_score": r.get("rerank_score"),
                "rank_shift": r.get("rank_shift", 0)
            })

    return results
