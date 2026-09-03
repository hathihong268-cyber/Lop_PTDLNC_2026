"""
Module Đánh giá Hiệu năng Retrieval & Ranking (Evaluation Suite) cho Buổi 08:
Hỗ trợ tính toán định lượng các chỉ số: Hit@K, MRR@K, Recall@K, nDCG@K cùng thống kê latency (mean, p50).
Hoạt động độc lập, thuần túy đánh giá tầng Retrieval/Ranking và HOÀN TOÀN KHÔNG gọi LLM generation.
"""

import os
import sys
import json
import time
import math
import statistics
import datetime
import argparse
from pathlib import Path
from typing import Any, Callable

# Đảm bảo import được module Buổi 08
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from advanced_rag import (
    load_advanced_config,
    build_bm25_retriever,
    retrieve_semantic_candidates,
    retrieve_hybrid_candidates,
    retrieve_and_rerank_candidates,
    CrossEncoderReranker,
    ALLOWED_STRATEGIES,
    DEFAULT_INPUT_DIR,
    CHROMA_STORAGE_DIR,
    HF_STORAGE_DIR,
)
from rag import load_chunks

EVAL_DIR = BASE_DIR / "eval"
DEFAULT_QUESTIONS_FILE = EVAL_DIR / "questions.json"
REPORTS_DIR = BASE_DIR / "reports"


def hit_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """
    Tính Hit@K: Trả về 1.0 nếu có ít nhất 1 chunk đúng nằm trong top-K, ngược lại 0.0.
    """
    if k <= 0 or not relevant_ids or not retrieved_ids:
        return 0.0
    top_k_ids = retrieved_ids[:k]
    return 1.0 if any(cid in relevant_ids for cid in top_k_ids) else 0.0


def reciprocal_rank_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """
    Tính MRR@K (Mean Reciprocal Rank): 1 / rank của chunk đúng đầu tiên trong top-K.
    """
    if k <= 0 or not relevant_ids or not retrieved_ids:
        return 0.0
    for rank, cid in enumerate(retrieved_ids[:k], start=1):
        if cid in relevant_ids:
            return 1.0 / rank
    return 0.0


def precision_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """
    Tính Precision@K: Tỷ lệ chunk đúng trong số K chunk được truy xuất.
    """
    if k <= 0 or not retrieved_ids:
        return 0.0
    top_k_ids = retrieved_ids[:k]
    hits = sum(1 for cid in top_k_ids if cid in relevant_ids)
    return hits / k


def recall_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """
    Tính Recall@K: Tỷ lệ chunk đúng được truy xuất trên tổng số chunk đúng trong ground truth.
    """
    if k <= 0 or not relevant_ids or not retrieved_ids:
        return 0.0
    top_k_ids = retrieved_ids[:k]
    hits = sum(1 for cid in top_k_ids if cid in relevant_ids)
    return hits / len(relevant_ids)


def dcg_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """
    Tính Discounted Cumulative Gain (DCG@K) với binary relevance (rel = 1 nếu đúng, 0 nếu sai).
    DCG@K = sum_{i=1}^K (rel_i / log2(i + 1))
    """
    if k <= 0 or not relevant_ids or not retrieved_ids:
        return 0.0
    dcg = 0.0
    for rank, cid in enumerate(retrieved_ids[:k], start=1):
        rel = 1.0 if cid in relevant_ids else 0.0
        if rel > 0:
            dcg += rel / math.log2(rank + 1.0)
    return dcg


def ndcg_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """
    Tính Normalized Discounted Cumulative Gain (nDCG@K):
    nDCG@K = DCG@K / IDCG@K (với IDCG là DCG lý tưởng khi toàn bộ relevant chunks nằm ở đầu danh sách).
    """
    if k <= 0 or not relevant_ids or not retrieved_ids:
        return 0.0

    actual_dcg = dcg_at_k(retrieved_ids, relevant_ids, k)
    if actual_dcg == 0.0:
        return 0.0

    # IDCG@K: tối đa min(k, len(relevant_ids)) tài liệu đúng ở các vị trí đầu tiên
    ideal_count = min(k, len(relevant_ids))
    idcg = sum(1.0 / math.log2(rank + 1.0) for rank in range(1, ideal_count + 1))

    if idcg <= 0.0:
        return 0.0

    return actual_dcg / idcg


def evaluate_retrieval_system(
    questions_file: Path | str = DEFAULT_QUESTIONS_FILE,
    strategy: str = "hierarchical",
    modes: list[str] = None,
    k_list: list[int] = [1, 3, 5],
    config: dict = None,
    custom_chunks: list[dict] = None,
    custom_retriever_fn: Callable[[str, str, int], list[str]] = None,
    storage_path: Path = CHROMA_STORAGE_DIR
) -> dict[str, Any]:
    """
    Thực thi quy trình đánh giá định lượng retrieval/ranking trên bộ câu hỏi chuẩn:
    - Không gọi LLM generation.
    - Cùng một corpus, câu hỏi và top-k cho mọi mode.
    - Tính toán: Recall@K, MRR@K, nDCG@K, Hit@K, Latency Mean & P50.
    - Nếu questions còn cờ 'needs_human_review=true', report tự động ghi nhận cảnh báo.
    """
    if config is None:
        config = load_advanced_config()

    if modes is None:
        modes = ["bm25", "semantic", "hybrid", "hybrid_rerank"]

    q_path = Path(questions_file)
    if not q_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file câu hỏi benchmark: {q_path}")

    with open(q_path, "r", encoding="utf-8") as f:
        questions_data = json.load(f)

    if not questions_data:
        raise ValueError("File câu hỏi benchmark rỗng (0 items).")

    # Kiểm tra cảnh báo human review
    unreviewed_count = sum(1 for q in questions_data if q.get("needs_human_review", False))
    has_human_review_warning = unreviewed_count > 0

    warnings = []
    if has_human_review_warning:
        warnings.append(
            f"Bộ câu hỏi benchmark có {unreviewed_count}/{len(questions_data)} câu hỏi đang mang cờ 'needs_human_review=true'. "
            "Kết quả đánh giá chỉ mang tính sơ bộ và KHÔNG tuyên bố mode chiến thắng chính thức cho đến khi được chuyên gia thẩm định."
        )

    # Nạp chunks và BM25 retriever nếu không dùng custom retriever function
    cached_chunks = None
    bm25_retriever = None
    if custom_retriever_fn is None:
        if custom_chunks is None:
            cached_chunks, _ = load_chunks(DEFAULT_INPUT_DIR, strategy=strategy)
        else:
            cached_chunks = custom_chunks
        bm25_retriever = build_bm25_retriever(cached_chunks)

    max_k = max(k_list)
    results_by_mode = {m: {"latencies": [], "per_query": []} for m in modes}

    for q_idx, q_item in enumerate(questions_data, start=1):
        q_text = q_item["question"]
        relevant_ids = set(q_item.get("relevant_chunk_ids", []))

        for mode in modes:
            t0 = time.perf_counter()
            retrieved_ids = []
            err_msg = None

            try:
                if custom_retriever_fn is not None:
                    retrieved_ids = custom_retriever_fn(q_text, mode, max_k)
                else:
                    if mode == "bm25":
                        res = bm25_retriever.search(query=q_text, top_k=max_k)
                        retrieved_ids = [r["chunk_id"] for r in res]
                    elif mode == "semantic":
                        res = retrieve_semantic_candidates(
                            question=q_text,
                            strategy=strategy,
                            candidate_k=max_k,
                            config=config,
                            storage_path=storage_path
                        )
                        retrieved_ids = [r["chunk_id"] for r in res]
                    elif mode == "hybrid":
                        res = retrieve_hybrid_candidates(
                            question=q_text,
                            strategy=strategy,
                            config=config,
                            chunks=cached_chunks,
                            storage_path=storage_path,
                            custom_retriever=bm25_retriever
                        )
                        retrieved_ids = [r["chunk_id"] for r in res["candidates"][:max_k]]
                    elif mode == "hybrid_rerank":
                        cfg_run = dict(config)
                        cfg_run["final_top_k"] = max_k
                        res = retrieve_and_rerank_candidates(
                            question=q_text,
                            strategy=strategy,
                            config=cfg_run,
                            chunks=cached_chunks,
                            storage_path=storage_path,
                            custom_retriever=bm25_retriever
                        )
                        retrieved_ids = [r["chunk_id"] for r in res["candidates"]]
            except Exception as e:
                err_msg = str(e)
                retrieved_ids = []

            lat_ms = round((time.perf_counter() - t0) * 1000, 2)
            results_by_mode[mode]["latencies"].append(lat_ms)

            query_metrics = {
                "question_id": q_item.get("id", f"q_{q_idx}"),
                "question": q_text,
                "error": err_msg,
                "latency_ms": lat_ms,
                "retrieved_count": len(retrieved_ids),
            }

            for k in k_list:
                query_metrics[f"hit@{k}"] = hit_at_k(retrieved_ids, relevant_ids, k)
                query_metrics[f"mrr@{k}"] = round(reciprocal_rank_at_k(retrieved_ids, relevant_ids, k), 4)
                query_metrics[f"recall@{k}"] = round(recall_at_k(retrieved_ids, relevant_ids, k), 4)
                query_metrics[f"ndcg@{k}"] = round(ndcg_at_k(retrieved_ids, relevant_ids, k), 4)

            results_by_mode[mode]["per_query"].append(query_metrics)

    # Tính toán chỉ số trung bình (Aggregated Metrics)
    aggregated_metrics = {}
    for mode in modes:
        mode_queries = results_by_mode[mode]["per_query"]
        lats = results_by_mode[mode]["latencies"]
        n_queries = len(mode_queries)

        mode_agg = {
            "query_count": n_queries,
            "error_count": sum(1 for q in mode_queries if q["error"] is not None),
            "latency_mean_ms": round(statistics.mean(lats), 2) if lats else 0.0,
            "latency_p50_ms": round(statistics.median(lats), 2) if lats else 0.0,
        }

        for k in k_list:
            mode_agg[f"mean_hit@{k}"] = round(sum(q[f"hit@{k}"] for q in mode_queries) / n_queries, 4)
            mode_agg[f"mean_mrr@{k}"] = round(sum(q[f"mrr@{k}"] for q in mode_queries) / n_queries, 4)
            mode_agg[f"mean_recall@{k}"] = round(sum(q[f"recall@{k}"] for q in mode_queries) / n_queries, 4)
            mode_agg[f"mean_ndcg@{k}"] = round(sum(q[f"ndcg@{k}"] for q in mode_queries) / n_queries, 4)

        aggregated_metrics[mode] = mode_agg

    report = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "strategy": strategy,
        "eval_questions_file": str(q_path),
        "total_questions": len(questions_data),
        "unreviewed_questions": unreviewed_count,
        "k_list": k_list,
        "modes": modes,
        "config": {
            "embedding_model": config["embedding_model"],
            "embedding_dim": config["embedding_dim"],
            "reranker_model": config["reranker_model"],
            "rrf_k": config["rrf_k"],
            "rrf_bm25_weight": config["rrf_bm25_weight"],
            "rrf_semantic_weight": config["rrf_semantic_weight"],
        },
        "warnings": warnings,
        "metrics_summary": aggregated_metrics,
        "detailed_results": results_by_mode,
    }

    # Lưu báo cáo vào reports/ nếu thư mục tồn tại
    try:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_filename = f"eval_report_{strategy}_{int(time.time())}.json"
        report_path = REPORTS_DIR / report_filename
        with open(report_path, "w", encoding="utf-8") as rf:
            json.dump(report, rf, ensure_ascii=False, indent=2)
        report["saved_report_file"] = str(report_path)
    except Exception as save_err:
        warnings.append(f"Không thể lưu file báo cáo JSON: {save_err}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Advanced RAG Buổi 08 - Evaluation Benchmark Suite")
    parser.add_argument(
        "--strategy",
        type=str,
        default="hierarchical",
        choices=sorted(list(ALLOWED_STRATEGIES)),
        help="Strategy chia chunk cần đánh giá (mặc định: hierarchical)",
    )
    parser.add_argument(
        "--questions-file",
        type=str,
        default=str(DEFAULT_QUESTIONS_FILE),
        help="Đường dẫn file JSON câu hỏi benchmark",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Giá trị K cho Recall@K, MRR@K, nDCG@K (mặc định: 5)",
    )

    args = parser.parse_args()

    try:
        print(f"=== KHỞI ĐỘNG ĐÁNH GIÁ RETRIEVAL & RANKING (Strategy: {args.strategy}, K={args.k}) ===")
        report = evaluate_retrieval_system(
            questions_file=args.questions_file,
            strategy=args.strategy,
            k_list=[1, 3, args.k]
        )

        print("\n" + "=" * 90)
        print("TỔNG HỢP CHỈ SỐ RETRIEVAL THEO TỪNG CHẾ ĐỘ:")
        print("=" * 90)
        print(f"{'Chế độ (Mode)':<16} | {'Recall@' + str(args.k):<10} | {'MRR@' + str(args.k):<10} | {'nDCG@' + str(args.k):<10} | {'Hit@' + str(args.k):<8} | {'Lat. Mean':<10} | {'Lat. P50':<8}")
        print("-" * 90)

        for mode, m in report["metrics_summary"].items():
            r_k = f"{m.get(f'mean_recall@{args.k}', 0):.4f}"
            m_k = f"{m.get(f'mean_mrr@{args.k}', 0):.4f}"
            n_k = f"{m.get(f'mean_ndcg@{args.k}', 0):.4f}"
            h_k = f"{m.get(f'mean_hit@{args.k}', 0):.4f}"
            lat_mean = f"{m.get('latency_mean_ms', 0):.1f} ms"
            lat_p50 = f"{m.get('latency_p50_ms', 0):.1f} ms"
            print(f"{mode:<16} | {r_k:<10} | {m_k:<10} | {n_k:<10} | {h_k:<8} | {lat_mean:<10} | {lat_p50:<8}")

        print("-" * 90)

        if report["warnings"]:
            print("\n⚠️ CẢNH BÁO QUAN TRỌNG TỪ ĐÁNH GIÁ BENCHMARK:")
            for w in report["warnings"]:
                print(f"  [!] {w}")

        if "saved_report_file" in report:
            print(f"\n✅ Đã lưu file báo cáo chi tiết: {report['saved_report_file']}")

    except Exception as e:
        print(f"\n❌ LỖI ĐÁNH GIÁ: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
