"""
Script: hybrid_search.py
Buổi 14: Hybrid Search + Reranking + Mini Knowledge Graph
Nhiệm vụ: Chạy thử nghiệm Hybrid Search (BM25 + Dense + RRF Fusion)
và hiển thị bảng so sánh thứ hạng BM25 / Dense / Hybrid.
"""

import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Đảm bảo UTF-8 trên Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.hybrid_retriever import HybridRetriever


def print_hybrid_table(query: str, results: List[Dict[str, Any]], candidate_k: int):
    """In bảng kết quả Hybrid Search theo định dạng chuẩn."""
    print("\n" + "=" * 105)
    print(f"HYBRID RESULTS (Candidate-k: {candidate_k} | Top-{len(results)})")
    print(f"Câu hỏi: \"{query}\"")
    print("=" * 105)

    # In Header Bảng
    header = f"{'Rank':<5} | {'Chunk ID':<35} | {'BM25':<6} | {'Dense':<6} | {'RRF Score':<10} | {'Citation'}"
    print(header)
    print("-" * 105)

    for item in results:
        b_rank_str = str(item['bm25_rank']) if item['bm25_rank'] is not None else "-"
        d_rank_str = str(item['dense_rank']) if item['dense_rank'] is not None else "-"
        
        row_str = (
            f"{item['final_rank']:<5} | "
            f"{item['chunk_id']:<35} | "
            f"{b_rank_str:<6} | "
            f"{d_rank_str:<6} | "
            f"{item['rrf_score']:<10.6f} | "
            f"{item['citation']}"
        )
        print(row_str)

    print("-" * 105)
    print("\nCHI TIẾT NỘI DUNG TỪNG ỨNG VIÊN TOP-K:")
    for item in results:
        print(f"\n[Rank {item['final_rank']}] {item['citation']} (RRF: {item['rrf_score']:.6f} | BM25: #{item['bm25_rank']} | Dense: #{item['dense_rank']})")
        text_preview = item['text'].replace('\n', ' ')
        if len(text_preview) > 200:
            text_preview = text_preview[:200] + "..."
        print(f"  • Nội dung: {text_preview}")
    print("=" * 105 + "\n")


def run_hybrid(query: str, top_k: int = 5, candidate_k: int = 20, rrf_k: int = 60) -> List[Dict[str, Any]]:
    corpus_path = BASE_DIR / "data" / "processed" / "chunks_normalized.csv"
    if not corpus_path.exists():
        print(f"[ERROR] Không tìm thấy {corpus_path}. Hãy chạy `python scripts/prepare_corpus.py` trước.")
        sys.exit(1)

    hybrid = HybridRetriever(
        corpus_csv_path=corpus_path,
        cache_dir=BASE_DIR / "cache",
        rrf_k=rrf_k
    )

    results = hybrid.search(query, top_k=top_k, candidate_k=candidate_k)
    print_hybrid_table(query, results, candidate_k)
    return results


def main():
    parser = argparse.ArgumentParser(description="Chạy thử nghiệm Hybrid Search (BM25 + Dense + RRF)")
    parser.add_argument("--query", "--question", "-q", type=str, default="Theo Thông tư 01/2014/TT-NHNN thì trách nhiệm của người áp tải tiền mặt là gì?", help="Câu hỏi truy vấn")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Số lượng kết quả lấy ra (mặc định: 5)")
    parser.add_argument("--candidate-k", "-c", type=int, default=20, help="Số lượng ứng viên thu thập từ mỗi retriever (mặc định: 20)")
    parser.add_argument("--rrf-k", type=int, default=60, help="Hằng số làm mượt RRF k (mặc định: 60)")

    args = parser.parse_args()
    run_hybrid(args.query, args.top_k, args.candidate_k, args.rrf_k)


if __name__ == "__main__":
    main()
