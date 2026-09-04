"""
Module Evaluate - Buoi 08: Benchmark Retrieval Metrics cho Advanced RAG Pipeline.

Chuc nang:
1. Doc bo cau hoi danh gia tu `eval/questions.json` (co relevant_chunk_ids).
2. Chay thu nghiem tren mot hoac nhieu retrieval mode: bm25, semantic, hybrid, hybrid_rerank.
3. Do luong cac chi so IR:
   - Recall@K   : Phan tram relevant docs duoc tim thay trong top-K
   - MRR@K      : Mean Reciprocal Rank
   - nDCG@K     : Normalized Discounted Cumulative Gain (binary relevance)
   - Latency    : mean va p50 (ms) cua tung mode
4. Xuat bao cao JSON trong `reports/` voi timestamp, config va model identity.

Quy tac:
- Khong goi generation.
- Neu needs_human_review=true -> bao cao co WARNING, khong tuyen bo mode thang.
- Loi tung query -> ghi ro FAIL, khong bo am tham.
- Command offline (synthetic fixture) chay duoc trong test.

Command real (nguoi dung chu dong):
    <PYTHON> rag_foundation/buoi_08/evaluate.py --strategy hierarchical --k 5

Command offline mock (test):
    evaluate_retrieval_system(questions_file=..., custom_retriever_fn=..., ...)
"""

from pathlib import Path
import os
import sys
import json
import math
import time
import statistics
import argparse
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Set

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
EVAL_FILE = (BASE_DIR / "eval" / "questions.json").resolve()
REPORTS_DIR = (BASE_DIR / "reports").resolve()


# ============================================================================
# 1. METRIC FUNCTIONS
# ============================================================================

def hit_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    Hit@K = 1.0 neu it nhat mot relevant doc nam trong top-K, nguoc lai = 0.0.

    Vi du tinh tay:
        retrieved = ["c1", "c2", "c3"], relevant = {"c2"}, k=2
        top_2 = ["c1", "c2"] -> co c2 -> Hit@2 = 1.0
        k=1 -> top_1 = ["c1"] -> khong co c2 -> Hit@1 = 0.0
    """
    if k <= 0:
        return 0.0
    return 1.0 if any(doc_id in relevant for doc_id in retrieved[:k]) else 0.0


def reciprocal_rank_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    Reciprocal Rank@K = 1 / rank_of_first_relevant trong top-K.

    Vi du tinh tay:
        retrieved = ["c1", "c2", "c3"], relevant = {"c2"}, k=3
        c2 o vi tri rank=2 -> RR = 1/2 = 0.5
        k=1 -> top_1 = ["c1"] -> khong co c2 -> RR@1 = 0.0
        relevant = {"c1"} -> c1 o rank=1 -> RR = 1.0
    """
    for rank, doc_id in enumerate(retrieved[:k], start=1):
        if doc_id in relevant:
            return 1.0 / rank
    return 0.0


def precision_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    Precision@K = |hits in top-K| / K.

    Vi du tinh tay:
        retrieved = ["c1", "bad", "c2"], relevant = {"c1", "c2"}, k=2
        top_2 hits = {c1} -> P@2 = 1/2 = 0.5
        k=3 hits = {c1, c2} -> P@3 = 2/3 ~ 0.667
    """
    if k <= 0:
        return 0.0
    hits = sum(1 for doc_id in retrieved[:k] if doc_id in relevant)
    return hits / k


def recall_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    Recall@K = |hits in top-K| / |relevant|.

    Vi du tinh tay:
        retrieved = ["c1", "bad", "c2"], relevant = {"c1", "c2"}, k=1
        top_1 hits = {c1} -> Recall@1 = 1/2 = 0.5
        k=3 hits = {c1, c2} -> Recall@3 = 2/2 = 1.0
    """
    if not relevant or k <= 0:
        return 0.0
    hits = sum(1 for doc_id in retrieved[:k] if doc_id in relevant)
    return hits / len(relevant)


def dcg_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    DCG@K voi binary relevance = sum(rel_i / log2(i+1)), i=1..K.

    Vi du tinh tay (log co so 2):
        retrieved = ["bad", "c1", "c2"], relevant = {"c1", "c2"}, k=3
        i=1: rel=0 -> 0
        i=2: rel=1 -> 1/log2(3) ~ 0.631
        i=3: rel=1 -> 1/log2(4) = 0.5
        DCG@3 ~ 1.131
    """
    dcg = 0.0
    for i, doc_id in enumerate(retrieved[:k], start=1):
        if doc_id in relevant:
            dcg += 1.0 / math.log2(i + 1)
    return dcg


def ndcg_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    nDCG@K = DCG@K / IDCG@K, IDCG la DCG ly tuong (relevant docs len dau).

    Vi du tinh tay:
        retrieved = ["bad", "c1", "c2"], relevant = {"c1", "c2"}, k=2
        DCG@2 = 0 + 1/log2(3) ~ 0.631
        IDCG@2 = 1/log2(2) + 1/log2(3) = 1.0 + 0.631 ~ 1.631
        nDCG@2 = 0.631 / 1.631 ~ 0.387
    """
    actual_dcg = dcg_at_k(retrieved, relevant, k)
    n_relevant_in_top_k = min(len(relevant), k)
    ideal_retrieved = list(relevant)[:n_relevant_in_top_k] + ["__pad__"] * (k - n_relevant_in_top_k)
    ideal_dcg = dcg_at_k(ideal_retrieved, relevant, k)
    if ideal_dcg == 0.0:
        return 0.0
    return actual_dcg / ideal_dcg


# ============================================================================
# 2. LOAD EVAL QUESTIONS
# ============================================================================

def load_eval_questions(eval_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Nap danh sach cau hoi benchmark tu file JSON.
    Moi cau hoi can co: id/query_id, question, relevant_chunk_ids.
    """
    path = eval_path or EVAL_FILE
    if not path.exists():
        raise FileNotFoundError(f"Khong tim thay file cau hoi benchmark: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


# ============================================================================
# 3. CORE EVALUATION ENGINE
# ============================================================================

def evaluate_retrieval_system(
    questions_file: Optional[Path] = None,
    strategy: str = "hierarchical",
    modes: Optional[List[str]] = None,
    k_list: Optional[List[int]] = None,
    config: Optional[Dict[str, Any]] = None,
    custom_retriever_fn: Optional[Callable] = None,
    save_report: bool = False,
    report_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Chay evaluation retrieval tren toan bo bo cau hoi.

    Args:
        questions_file: Duong dan file JSON cau hoi.
        strategy: Chunking strategy.
        modes: Danh sach retrieval mode can so sanh.
        k_list: Danh sach K de tinh metric (e.g. [1, 3, 5]).
        config: Config dict.
        custom_retriever_fn: Mock retriever fn(question, mode, k) -> List[str] chunk_ids.
            Khi None -> goi real retrieval.
        save_report: Co luu bao cao JSON ra reports/ hay khong.
        report_dir: Thu muc luu bao cao.

    Returns:
        report dict gom:
            - config, metrics_summary, per_query_results
            - warnings, unreviewed_questions, needs_human_review
            - latency_stats, saved_report_path
    """
    questions = load_eval_questions(questions_file)
    if not modes:
        modes = ["bm25", "semantic", "hybrid", "hybrid_rerank"]
    if not k_list:
        k_list = [1, 3, 5]
    if not config:
        config = {}

    max_k = max(k_list)
    run_timestamp = datetime.now().isoformat()

    unreviewed = [q for q in questions if q.get("needs_human_review", False)]
    warnings_list: List[str] = []
    if unreviewed:
        warnings_list.append(
            f"[WARNING] needs_human_review=true: {len(unreviewed)}/{len(questions)} cau hoi "
            f"chua co gold labels duoc xac nhan. "
            f"Khong tuyen bo mode chien thang chinh thuc dua tren bao cao nay."
        )

    def get_qid(q: Dict) -> str:
        return q.get("query_id") or q.get("id") or "UNKNOWN"

    per_query_results: Dict[str, List[Dict]] = {}
    metrics_summary: Dict[str, Dict] = {}
    latency_stats: Dict[str, Dict] = {}

    for mode in modes:
        mode_results = []
        latencies_ms: List[float] = []

        for q in questions:
            qid = get_qid(q)
            question_text = q.get("question", "")
            relevant_ids: Set[str] = set(q.get("relevant_chunk_ids", []))

            row: Dict[str, Any] = {
                "query_id": qid,
                "question": question_text,
                "relevant_chunk_ids": list(relevant_ids),
                "needs_human_review": q.get("needs_human_review", False),
                "scope": q.get("scope", "in_scope"),
            }

            try:
                t_start = time.perf_counter()

                if custom_retriever_fn is not None:
                    retrieved_ids = custom_retriever_fn(question_text, mode, max_k)
                else:
                    retrieved_ids = _real_retrieval(question_text, mode, max_k, strategy, config)

                t_end = time.perf_counter()
                latency = (t_end - t_start) * 1000.0
                latencies_ms.append(latency)
                row["latency_ms"] = round(latency, 2)

                for k in k_list:
                    row[f"hit@{k}"] = hit_at_k(retrieved_ids, relevant_ids, k)
                    row[f"recall@{k}"] = recall_at_k(retrieved_ids, relevant_ids, k)
                    row[f"ndcg@{k}"] = round(ndcg_at_k(retrieved_ids, relevant_ids, k), 6)
                    row[f"mrr@{k}"] = round(reciprocal_rank_at_k(retrieved_ids, relevant_ids, k), 6)

                row["retrieved_ids"] = retrieved_ids[:max_k]
                row["error"] = None

            except Exception as exc:
                row["error"] = f"FAIL [{type(exc).__name__}]: {str(exc)}"
                row["latency_ms"] = None
                for k in k_list:
                    row[f"hit@{k}"] = None
                    row[f"recall@{k}"] = None
                    row[f"ndcg@{k}"] = None
                    row[f"mrr@{k}"] = None
                print(f"[EVAL ERROR] mode={mode} query_id={qid}: {exc}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)

            mode_results.append(row)

        per_query_results[mode] = mode_results

        valid_rows = [r for r in mode_results if r.get("error") is None]
        n_valid = len(valid_rows)
        n_failed = len(mode_results) - n_valid

        summary: Dict[str, Any] = {
            "n_queries": len(mode_results),
            "n_valid": n_valid,
            "n_failed": n_failed,
        }

        for k in k_list:
            for metric in ["hit", "recall", "ndcg", "mrr"]:
                vals = [r.get(f"{metric}@{k}") for r in valid_rows if r.get(f"{metric}@{k}") is not None]
                summary[f"mean_{metric}@{k}"] = round(sum(vals) / len(vals), 6) if vals else None

        if latencies_ms:
            summary["mean_latency_ms"] = round(statistics.mean(latencies_ms), 2)
            summary["p50_latency_ms"] = round(statistics.median(latencies_ms), 2)
        else:
            summary["mean_latency_ms"] = None
            summary["p50_latency_ms"] = None

        metrics_summary[mode] = summary
        latency_stats[mode] = {
            "mean_ms": summary["mean_latency_ms"],
            "p50_ms": summary["p50_latency_ms"],
        }

    has_unreviewed = len(unreviewed) > 0
    report: Dict[str, Any] = {
        "run_timestamp": run_timestamp,
        "config": {
            "strategy": strategy,
            "modes": modes,
            "k_list": k_list,
            "embedding_model": config.get("embedding_model", "UNKNOWN"),
            "embedding_dim": config.get("embedding_dim", "UNKNOWN"),
            "reranker_model": config.get("reranker_model", "UNKNOWN"),
            "rrf_k": config.get("rrf_k", "UNKNOWN"),
            "rrf_bm25_weight": config.get("rrf_bm25_weight", "UNKNOWN"),
            "rrf_semantic_weight": config.get("rrf_semantic_weight", "UNKNOWN"),
        },
        "metrics_summary": metrics_summary,
        "per_query_results": per_query_results,
        "latency_stats": latency_stats,
        "warnings": warnings_list,
        "unreviewed_questions": len(unreviewed),
        "needs_human_review": has_unreviewed,
        "saved_report_path": None,
    }

    if has_unreviewed:
        report["winner_note"] = (
            "KHONG tuyen bo mode chien thang chinh thuc vi co cau hoi can xac nhan "
            "gold labels thu cong (needs_human_review=true). "
            "Dung ket qua nay de dinh huong, khong lam bang chung cuoi cung."
        )

    if save_report:
        out_dir = report_dir or REPORTS_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = out_dir / f"eval_{strategy}_{ts_str}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        report["saved_report_path"] = str(report_path)
        print(f"[EVAL] Bao cao da luu: {report_path}")

    return report


def _real_retrieval(
    question: str,
    mode: str,
    k: int,
    strategy: str,
    config: Dict[str, Any],
) -> List[str]:
    """
    Goi real retrieval tu advanced_rag, tra ve danh sach chunk_id theo thu tu rank.
    Chi duoc dung khi nguoi dung chu dong goi evaluate.py, khong goi generation.
    """
    from advanced_rag import (
        build_bm25_retriever,
        retrieve_semantic_candidates,
        retrieve_hybrid_candidates,
        CrossEncoderReranker,
    )
    from rag import load_chunks as rag_load_chunks, DEFAULT_INPUT_DIR, DEFAULT_CHROMA_DIR

    storage_path = config.get("storage_path", DEFAULT_CHROMA_DIR)
    input_dir = config.get("input_dir", DEFAULT_INPUT_DIR)

    chunks = rag_load_chunks(input_dir, strategy)
    if not chunks:
        raise ValueError(f"Corpus trong cho strategy={strategy}")

    if mode == "bm25":
        retriever = build_bm25_retriever(chunks)
        results = retriever.search(question, top_k=k)
        return [r["chunk_id"] for r in results]

    elif mode == "semantic":
        results = retrieve_semantic_candidates(
            question=question,
            strategy=strategy,
            candidate_k=k,
            config=config,
            storage_path=Path(storage_path),
        )
        return [r["chunk_id"] for r in results]

    elif mode in ("hybrid", "hybrid_rerank"):
        result = retrieve_hybrid_candidates(
            question=question,
            strategy=strategy,
            config=config,
            chunks=chunks,
            storage_path=Path(storage_path),
        )
        fused = result.get("candidates", [])
        if mode == "hybrid_rerank":
            reranker = CrossEncoderReranker(
                model_name=config.get("reranker_model", "BAAI/bge-reranker-v2-m3")
            )
            reranked = reranker.rerank(question, fused, top_k=k)
            return [r["chunk_id"] for r in reranked]
        else:
            return [r["chunk_id"] for r in fused[:k]]
    else:
        raise ValueError(
            f"Mode khong hop le: '{mode}'. Dung: bm25, semantic, hybrid, hybrid_rerank."
        )


# ============================================================================
# 4. CLI ENTRY POINT
# ============================================================================

def _print_summary(report: Dict[str, Any]) -> None:
    """In tom tat bao cao ra stdout."""
    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)
    print(f"Timestamp : {report['run_timestamp']}")
    cfg = report.get("config", {})
    print(f"Strategy  : {cfg.get('strategy', 'N/A')}")
    print(f"Modes     : {cfg.get('modes', [])}")
    print(f"K         : {cfg.get('k_list', [])}")
    print(f"Embedding : {cfg.get('embedding_model', 'N/A')}")
    print(f"Reranker  : {cfg.get('reranker_model', 'N/A')}")

    if report.get("warnings"):
        print("\n[CANH BAO]:")
        for w in report["warnings"]:
            print(f"   {w}")

    print("\nMetrics Summary:")
    header_parts = ["Mode".ljust(20)]
    for k in cfg.get("k_list", [5]):
        header_parts.append(f"Recall@{k}".rjust(10))
        header_parts.append(f"MRR@{k}".rjust(8))
        header_parts.append(f"nDCG@{k}".rjust(8))
    header_parts.append("P50(ms)".rjust(10))
    print("  " + "".join(header_parts))
    print("  " + "-" * (sum(len(p) for p in header_parts) + 2))

    for mode, summary in report.get("metrics_summary", {}).items():
        row_parts = [mode.ljust(20)]
        for k in cfg.get("k_list", [5]):
            r = summary.get(f"mean_recall@{k}")
            m = summary.get(f"mean_mrr@{k}")
            n = summary.get(f"mean_ndcg@{k}")
            row_parts.append((f"{r:.4f}" if r is not None else "N/A").rjust(10))
            row_parts.append((f"{m:.4f}" if m is not None else "N/A").rjust(8))
            row_parts.append((f"{n:.4f}" if n is not None else "N/A").rjust(8))
        p50 = summary.get("p50_latency_ms")
        row_parts.append((f"{p50:.1f}ms" if p50 is not None else "N/A").rjust(10))
        print("  " + "".join(row_parts))
        n_failed = summary.get("n_failed", 0)
        if n_failed > 0:
            print(f"    [WARN] {n_failed} queries FAILED cho mode={mode}")

    if report.get("needs_human_review"):
        print(f"\n[NOTE] {report['unreviewed_questions']} cau hoi chua xac nhan gold labels.")
        print("   -> Khong tuyen bo mode chien thang chinh thuc.")

    if report.get("saved_report_path"):
        print(f"\n[SAVED] Bao cao: {report['saved_report_path']}")
    print("=" * 70)


def main():
    """CLI chinh cho evaluate.py."""
    parser = argparse.ArgumentParser(
        description="Evaluate retrieval modes cho Advanced RAG - Buoi 08.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--strategy", default="hierarchical",
        choices=["hierarchical", "flat", "recursive", "semantic"],
        help="Chunking strategy (default: hierarchical)"
    )
    parser.add_argument(
        "--modes", nargs="+", default=["bm25", "semantic", "hybrid", "hybrid_rerank"],
        help="Danh sach retrieval mode"
    )
    parser.add_argument(
        "--k", nargs="+", type=int, default=[1, 3, 5],
        help="Danh sach K de tinh metric (default: 1 3 5)"
    )
    parser.add_argument(
        "--questions", type=str, default=None,
        help="Duong dan file questions.json"
    )
    parser.add_argument(
        "--save", action="store_true",
        help="Luu bao cao JSON vao reports/"
    )

    args = parser.parse_args()

    try:
        from advanced_rag import load_advanced_config
        config = load_advanced_config()
    except Exception:
        config = {}

    questions_file = Path(args.questions) if args.questions else None

    print(f"[EVAL] Bat dau evaluation...")
    print(f"[EVAL] Strategy: {args.strategy}, Modes: {args.modes}, K: {args.k}")

    report = evaluate_retrieval_system(
        questions_file=questions_file,
        strategy=args.strategy,
        modes=args.modes,
        k_list=args.k,
        config=config,
        save_report=args.save,
    )

    _print_summary(report)


if __name__ == "__main__":
    main()
