"""
Script: compare_retrieval.py
Buổi 14: Hybrid Search + Reranking + Mini Knowledge Graph
Nhiệm vụ: Chạy Benchmark đánh giá định lượng so sánh 4 cấu hình Retrieval:
1. BM25-only
2. Dense-only
3. Hybrid (RRF)
4. Hybrid + Cross-Encoder Rerank

Tính toán các chỉ số: Hit@1, Hit@3, Hit@5 và MRR (Mean Reciprocal Rank).
Xuất kết quả chi tiết ra: buoi_14/outputs/retrieval_comparison.csv
"""

import sys
import os
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

# Đảm bảo UTF-8 trên Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.bm25_retriever import BM25Retriever
from src.dense_retriever import DenseRetriever
from src.hybrid_retriever import HybridRetriever
from src.reranker import CrossEncoderReranker


def evaluate_pipeline(
    questions_csv: Path,
    corpus_csv: Path,
    cache_dir: Path,
    output_csv: Path,
    candidate_k: int = 20,
    top_k: int = 5
) -> pd.DataFrame:
    print("=" * 85)
    print("CHẠY BENCHMARK ĐÁNH GIÁ 4 CẤU HÌNH RETRIEVAL — BUỔI 14")
    print("=" * 85)

    if not questions_csv.exists():
        raise FileNotFoundError(f"Không tìm thấy file câu hỏi đánh giá tại: {questions_csv}")
    if not corpus_csv.exists():
        raise FileNotFoundError(f"Không tìm thấy file corpus tại: {corpus_csv}")

    # Đọc bộ câu hỏi
    q_df = pd.read_csv(questions_csv)
    print(f"[*] Đã tải {len(q_df)} câu hỏi đánh giá từ: {questions_csv}")

    # Khởi tạo các Retriever
    print("[*] Đang khởi tạo BM25Retriever...")
    bm25 = BM25Retriever(corpus_csv)

    print("[*] Đang khởi tạo DenseRetriever...")
    dense = DenseRetriever(corpus_csv, cache_dir)

    print("[*] Đang khởi tạo HybridRetriever...")
    hybrid = HybridRetriever(bm25, dense, corpus_csv, cache_dir)

    print("[*] Đang khởi tạo CrossEncoderReranker...")
    reranker = CrossEncoderReranker()

    methods = ["bm25", "dense", "hybrid", "hybrid_rerank"]
    detailed_rows = []

    for _, q_row in q_df.iterrows():
        qid = q_row["question_id"]
        q_text = q_row["question"]
        expected_cid = str(q_row["expected_chunk_id"]).strip()
        q_type = q_row["query_type"]

        print(f"\n[>] Đánh giá [{qid}] ({q_type}): \"{q_text}\"")
        print(f"    Expected Gold Chunk: {expected_cid}")

        # 1. BM25
        bm25_res = bm25.search(q_text, top_k=top_k)

        # 2. Dense
        dense_res = dense.search(q_text, top_k=top_k)

        # 3. Hybrid
        hybrid_candidates = hybrid.search(q_text, top_k=candidate_k, candidate_k=candidate_k)
        hybrid_res = hybrid_candidates[:top_k]

        # 4. Hybrid + Rerank
        rerank_res = reranker.rerank(q_text, hybrid_candidates, top_k=top_k)

        res_dict = {
            "bm25": bm25_res,
            "dense": dense_res,
            "hybrid": hybrid_res,
            "hybrid_rerank": rerank_res
        }

        for m in methods:
            results = res_dict[m]
            found_rank = None
            for idx, r in enumerate(results, 1):
                if r["chunk_id"] == expected_cid:
                    found_rank = idx
                    break

            hit_1 = 1 if found_rank == 1 else 0
            hit_3 = 1 if (found_rank is not None and found_rank <= 3) else 0
            hit_5 = 1 if (found_rank is not None and found_rank <= 5) else 0
            rr = (1.0 / found_rank) if found_rank is not None else 0.0

            top1 = results[0] if results else {}
            top1_cid = top1.get("chunk_id", "")
            top1_cit = top1.get("citation", "")
            top1_score = top1.get("retrieval_score", top1.get("rerank_score", top1.get("rrf_score", 0.0)))

            detailed_rows.append({
                "question_id": qid,
                "query_type": q_type,
                "question": q_text,
                "expected_chunk_id": expected_cid,
                "method": m,
                "found_rank": found_rank if found_rank is not None else "-",
                "hit@1": hit_1,
                "hit@3": hit_3,
                "hit@5": hit_5,
                "reciprocal_rank": round(rr, 4),
                "top1_chunk_id": top1_cid,
                "top1_citation": top1_cit,
                "top1_score": top1_score
            })

            rank_disp = f"Rank #{found_rank}" if found_rank else "Miss (Not in Top-5)"
            print(f"      • {m:<14}: {rank_disp} (Top-1: {top1_cid})")

    # Lưu file CSV so sánh chi tiết
    det_df = pd.DataFrame(detailed_rows)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    det_df.to_csv(output_csv, index=False, encoding="utf-8")
    print(f"\n[+] Đã lưu kết quả chi tiết vào: {output_csv}")

    # ==============================================================================
    # TÍNH TOÁN BẢNG TỔNG KẾT METRICS
    # ==============================================================================
    print("\n" + "=" * 85)
    print("BẢNG TỔNG KẾT ĐÁNH GIÁ METRICS (Overall & By Query Type)")
    print("=" * 85)

    summary_list = []
    for m in methods:
        sub = det_df[det_df["method"] == m]
        hit1_avg = sub["hit@1"].mean() * 100
        hit3_avg = sub["hit@3"].mean() * 100
        hit5_avg = sub["hit@5"].mean() * 100
        mrr_val = sub["reciprocal_rank"].mean()
        summary_list.append({
            "Method": m,
            "Hit@1 (%)": f"{hit1_avg:.1f}%",
            "Hit@3 (%)": f"{hit3_avg:.1f}%",
            "Hit@5 (%)": f"{hit5_avg:.1f}%",
            "MRR": f"{mrr_val:.4f}"
        })

    sum_df = pd.DataFrame(summary_list)
    print(sum_df.to_string(index=False))

    # In theo nhóm query_type
    print("\n" + "-" * 85)
    print("CHI TIẾT THEO TỪNG NHÓM TRUY VẤN (Hit@1 / Hit@5 / MRR):")
    print("-" * 85)
    
    types = q_df["query_type"].unique()
    type_summary = []
    for t in types:
        for m in methods:
            sub = det_df[(det_df["query_type"] == t) & (det_df["method"] == m)]
            h1 = sub["hit@1"].mean() * 100
            h5 = sub["hit@5"].mean() * 100
            mrr = sub["reciprocal_rank"].mean()
            type_summary.append({
                "Query Type": t,
                "Method": m,
                "Hit@1": f"{h1:.0f}%",
                "Hit@5": f"{h5:.0f}%",
                "MRR": f"{mrr:.4f}"
            })
    t_df = pd.DataFrame(type_summary)
    print(t_df.to_string(index=False))
    print("=" * 85 + "\n")

    return det_df


def main():
    parser = argparse.ArgumentParser(description="Chạy Benchmark so sánh 4 cấu hình Retrieval")
    parser.add_argument("--candidate-k", "-c", type=int, default=20, help="Số lượng candidate cho Hybrid và Rerank (mặc định: 20)")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Số lượng top_k đánh giá (mặc định: 5)")

    args = parser.parse_args()

    questions_csv = BASE_DIR / "data" / "eval" / "questions.csv"
    corpus_csv = BASE_DIR / "data" / "processed" / "chunks_normalized.csv"
    cache_dir = BASE_DIR / "cache"
    output_csv = BASE_DIR / "outputs" / "retrieval_comparison.csv"

    evaluate_pipeline(
        questions_csv=questions_csv,
        corpus_csv=corpus_csv,
        cache_dir=cache_dir,
        output_csv=output_csv,
        candidate_k=args.candidate_k,
        top_k=args.top_k
    )


if __name__ == "__main__":
    main()
