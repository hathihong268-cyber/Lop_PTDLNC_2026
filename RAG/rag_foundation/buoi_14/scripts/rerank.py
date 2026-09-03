"""
Script: rerank.py
Buổi 14: Hybrid Search + Reranking + Mini Knowledge Graph
Nhiệm vụ: Thực thi Pipeline đầy đủ (Query -> Hybrid candidate_k -> Reranker -> Top-k)
và hiển thị bảng so sánh BEFORE RERANK vs AFTER RERANK.
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
from src.reranker import CrossEncoderReranker


def print_comparison_tables(query: str, before_results: List[Dict[str, Any]], after_results: List[Dict[str, Any]]):
    """In bảng so sánh trực quan thứ bậc trước và sau Reranking."""
    print("\n" + "=" * 115)
    print(f"PIPELINE SO SÁNH THỨ HẠNG TRƯỚC VÀ SAU RERANKING")
    print(f"Câu hỏi: \"{query}\"")
    print("=" * 115)

    # 1. Bảng BEFORE RERANK
    print("\n" + "-" * 115)
    print("📋 BEFORE RERANK (Hybrid Search Top-k)")
    print("-" * 115)
    header_before = f"{'Rank':<5} | {'Chunk ID':<35} | {'BM25':<6} | {'Dense':<6} | {'RRF Score':<10} | {'Citation'}"
    print(header_before)
    print("-" * 115)
    for item in before_results:
        b_str = str(item['bm25_rank']) if item['bm25_rank'] is not None else "-"
        d_str = str(item['dense_rank']) if item['dense_rank'] is not None else "-"
        print(f"{item['final_rank']:<5} | {item['chunk_id']:<35} | {b_str:<6} | {d_str:<6} | {item['rrf_score']:<10.6f} | {item['citation']}")

    # 2. Bảng AFTER RERANK
    print("\n" + "-" * 115)
    print("🎯 AFTER RERANK (Cross-Encoder BAAI/bge-reranker-base Top-k)")
    print("-" * 115)
    header_after = f"{'Final':<5} | {'Chunk ID':<35} | {'Hybrid':<8} | {'Shift':<7} | {'Rerank Score':<13} | {'Citation'}"
    print(header_after)
    print("-" * 115)
    for item in after_results:
        shift_val = item['rank_shift']
        shift_str = f"+{shift_val}" if shift_val > 0 else (f"{shift_val}" if shift_val < 0 else "=")
        h_str = f"#{item['hybrid_rank']}"
        print(f"{item['final_rank']:<5} | {item['chunk_id']:<35} | {h_str:<8} | {shift_str:<7} | {item['rerank_score']:<13.4f} | {item['citation']}")

    print("-" * 115)
    print("\nCHI TIẾT NỘI DUNG TỪNG ỨNG VIÊN TOP-K SAU RERANK:")
    for item in after_results:
        shift_val = item['rank_shift']
        shift_tag = f"(Dịch chuyển: +{shift_val})" if shift_val > 0 else (f"(Dịch chuyển: {shift_val})" if shift_val < 0 else "(Giữ nguyên)")
        print(f"\n[Rank {item['final_rank']}] {item['citation']} | Rerank Score: {item['rerank_score']:.4f} {shift_tag}")
        text_preview = item['text'].replace('\n', ' ')
        if len(text_preview) > 200:
            text_preview = text_preview[:200] + "..."
        print(f"  • Nội dung: {text_preview}")
    print("=" * 115 + "\n")


def run_reranking_pipeline(query: str, candidate_k: int = 20, top_k: int = 5):
    corpus_path = BASE_DIR / "data" / "processed" / "chunks_normalized.csv"
    if not corpus_path.exists():
        print(f"[ERROR] Không tìm thấy {corpus_path}. Hãy chạy `python scripts/prepare_corpus.py` trước.")
        sys.exit(1)

    # 1. Khởi tạo Hybrid Retriever
    hybrid = HybridRetriever(
        corpus_csv_path=corpus_path,
        cache_dir=BASE_DIR / "cache"
    )

    # 2. Thu thập candidate_k từ Hybrid Search
    print(f"[*] Thu thập {candidate_k} ứng viên từ Hybrid Search cho query: \"{query}\"...")
    candidates = hybrid.search(query, top_k=candidate_k, candidate_k=candidate_k)

    # 3. Khởi tạo Reranker và chấm điểm lại
    reranker = CrossEncoderReranker()
    reranked_top_k = reranker.rerank(query, candidates, top_k=top_k)

    # 4. Hiển thị Before vs After
    before_top_k = candidates[:top_k]
    print_comparison_tables(query, before_top_k, reranked_top_k)

    return reranked_top_k


def main():
    parser = argparse.ArgumentParser(description="Chạy Pipeline Hybrid Search + Cross-Encoder Reranking")
    parser.add_argument("--query", "--question", "-q", type=str, default="Theo Thông tư 01/2014/TT-NHNN thì trách nhiệm của người áp tải tiền mặt là gì?", help="Câu hỏi truy vấn")
    parser.add_argument("--candidate-k", "-c", type=int, default=20, help="Số lượng ứng viên từ Hybrid Search (mặc định: 20)")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Số lượng kết quả lấy ra sau Reranking (mặc định: 5)")

    args = parser.parse_args()
    run_reranking_pipeline(args.query, args.candidate_k, args.top_k)


if __name__ == "__main__":
    main()
