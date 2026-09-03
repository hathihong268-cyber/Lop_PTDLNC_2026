"""
Module Đánh giá Hiệu năng RAG Toàn Diện cho Buổi 09:
Thực hiện so sánh đối chuẩn 4 chế độ (single_flat, multi_flat, single_parent, multi_parent)
ở tầng Retrieval-Only (KHÔNG gọi answer generation).

Tính toán các chỉ số:
- Child Recall@K
- Parent Recall@K
- MRR@K (Mean Reciprocal Rank)
- nDCG@K (Normalized Discounted Cumulative Gain với binary relevance)
- Unique relevant parents/sources retrieved
- Ngữ cảnh: Context chars & Context expansion factor
- Thời gian: Mean Latency (ms) & P50 Latency (ms)
- Ngân sách: Query-generation calls (0 calls) & Embedding calls
Lưu trữ báo cáo nguyên tử (atomic) tại reports/eval_report_<timestamp>.json và reports/latest_report.json.
"""

import os
import sys
import json
import math
import time
import statistics
import datetime
from pathlib import Path
from typing import Any, Callable

# Thư mục gốc Buổi 09
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from hierarchical_rag import (
    load_buoi_09_config,
    load_hierarchy_store,
    query_hierarchical_rag,
    MODES,
    HIERARCHY_STORAGE_DIR,
)

QUESTIONS_FILE = BASE_DIR / "eval" / "questions.json"
REPORTS_DIR = BASE_DIR / "reports"


def load_eval_questions(file_path: Path = QUESTIONS_FILE) -> list[dict]:
    """
    Nạp danh sách câu hỏi đánh giá kèm nhãn liên quan (ground truth relevance).
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file câu hỏi benchmark: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_mrr_at_k(ranked_ids: list[str], gold_ids: set[str], k: int = 5) -> float:
    """
    Tính Mean Reciprocal Rank tại k: 1 / rank của relevant hit đầu tiên.
    """
    if not gold_ids:
        return 1.0 if not ranked_ids else 0.0
    for rank, doc_id in enumerate(ranked_ids[:k], start=1):
        if doc_id in gold_ids:
            return 1.0 / rank
    return 0.0


def calculate_recall_at_k(retrieved_ids: list[str], gold_ids: set[str], k: int = 5) -> float:
    """
    Tính Recall@k: Tỷ lệ các gold IDs được tìm thấy trong top k.
    """
    if not gold_ids:
        return 1.0 if not retrieved_ids else 0.0
    top_set = set(retrieved_ids[:k])
    intersect = top_set.intersection(gold_ids)
    return len(intersect) / len(gold_ids)


def calculate_ndcg_at_k(ranked_ids: list[str], gold_ids: set[str], k: int = 5) -> float:
    """
    Tính Normalized Discounted Cumulative Gain tại k (với binary relevance: 1 nếu thuộc gold_ids).
    """
    if not gold_ids:
        return 1.0 if not ranked_ids else 0.0

    dcg = 0.0
    for rank, doc_id in enumerate(ranked_ids[:k], start=1):
        if doc_id in gold_ids:
            dcg += 1.0 / math.log2(rank + 1)

    ideal_hits = min(len(gold_ids), k)
    if ideal_hits == 0:
        return 0.0

    idcg = sum(1.0 / math.log2(r + 1) for r in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0


def evaluate_single_mode(
    mode: str,
    questions: list[dict],
    config: dict = None,
    children_by_id: dict = None,
    custom_hybrid_fn: Callable[[str], list[dict]] = None,
    query_generator_fn: Callable[[str], str] = None,
    score_fn: Callable[[str, list[str]], list[float]] = None
) -> dict[str, Any]:
    """
    Đánh giá một chế độ RAG trên toàn bộ tập câu hỏi:
    - Chạy ở tầng Retrieval-Only (KHÔNG gọi answer generation).
    - Tính toán chi tiết các metric cho từng câu hỏi và tổng hợp toàn mode.
    """
    if config is None:
        config = load_buoi_09_config()

    k_eval = config.get("final_parent_top_k", 3)
    per_question_results = []

    child_recalls = []
    parent_recalls = []
    mrrs = []
    ndcgs = []
    latencies = []
    context_chars_list = []
    expansion_factors = []

    for q_item in questions:
        qid = q_item["question_id"]
        q_text = q_item["question"]
        q_type = q_item.get("question_type", "exact")
        gold_child_ids = set(q_item.get("relevant_child_ids", []))
        gold_parent_ids = set(q_item.get("relevant_parent_ids", []))

        t0 = time.perf_counter()

        # Thực thi truy xuất qua query_hierarchical_rag với mock answer generator
        res = query_hierarchical_rag(
            question=q_text,
            mode=mode,
            strategy="hierarchical",
            config=config,
            score_fn=score_fn,
            query_generator_fn=query_generator_fn,
            custom_hybrid_fn=custom_hybrid_fn,
            answer_generator_fn=lambda q, ev: "MOCK_EVAL_NO_GEN"
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        accepted_ev = res.get("accepted_evidence", [])
        is_parent_mode = "parent" in mode

        # Trích xuất danh sách ID được truy xuất
        if is_parent_mode:
            ranked_parent_ids = [p["parent_id"] for p in accepted_ev if "parent_id" in p]
            # Trích xuất toàn bộ supporting children của các parent được chấp nhận
            all_retrieved_children = []
            for p in accepted_ev:
                all_retrieved_children.extend(p.get("supporting_child_ids", []))
            ranked_child_ids = list(dict.fromkeys(all_retrieved_children))
        else:
            ranked_child_ids = [c.get("child_id") or c.get("chunk_id") for c in accepted_ev if c.get("child_id") or c.get("chunk_id")]
            # Map children sang parent_ids qua registry
            mapped_parents = []
            if children_by_id:
                for cid in ranked_child_ids:
                    if cid in children_by_id:
                        p_id = children_by_id[cid].get("parent_id")
                        if p_id and p_id not in mapped_parents:
                            mapped_parents.append(p_id)
            ranked_parent_ids = mapped_parents

        # Tính toán các chỉ số
        p_recall = calculate_recall_at_k(ranked_parent_ids, gold_parent_ids, k=k_eval)
        c_recall = calculate_recall_at_k(ranked_child_ids, gold_child_ids, k=k_eval)
        
        # MRR và nDCG dựa trên đơn vị của mode
        eval_ids = ranked_parent_ids if is_parent_mode else ranked_child_ids
        eval_golds = gold_parent_ids if is_parent_mode else gold_child_ids
        mrr = calculate_mrr_at_k(eval_ids, eval_golds, k=k_eval)
        ndcg = calculate_ndcg_at_k(eval_ids, eval_golds, k=k_eval)

        # Tính tổng số ký tự ngữ cảnh
        ctx_chars = sum(len(e.get("text", "")) for e in accepted_ev)
        child_chars = sum(len(c.get("text", "")) for c in res.get("child_hits", []))
        exp_factor = round(ctx_chars / max(child_chars, 1), 2) if is_parent_mode else 1.0

        child_recalls.append(c_recall)
        parent_recalls.append(p_recall)
        mrrs.append(mrr)
        ndcgs.append(ndcg)
        latencies.append(elapsed_ms)
        context_chars_list.append(ctx_chars)
        expansion_factors.append(exp_factor)

        per_question_results.append({
            "question_id": qid,
            "question": q_text,
            "question_type": q_type,
            "status": res["status"],
            "retrieved_parents": ranked_parent_ids,
            "retrieved_children_count": len(ranked_child_ids),
            "parent_recall_at_k": round(p_recall, 4),
            "child_recall_at_k": round(c_recall, 4),
            "mrr_at_k": round(mrr, 4),
            "ndcg_at_k": round(ndcg, 4),
            "context_chars": ctx_chars,
            "latency_ms": elapsed_ms,
            "warnings": res.get("warnings", [])
        })

    # Tổng hợp chỉ số
    summary = {
        "mode": mode,
        "mean_parent_recall_at_k": round(statistics.mean(parent_recalls), 4) if parent_recalls else 0.0,
        "mean_child_recall_at_k": round(statistics.mean(child_recalls), 4) if child_recalls else 0.0,
        "mean_mrr_at_k": round(statistics.mean(mrrs), 4) if mrrs else 0.0,
        "mean_ndcg_at_k": round(statistics.mean(ndcgs), 4) if ndcgs else 0.0,
        "mean_context_chars": round(statistics.mean(context_chars_list), 1) if context_chars_list else 0,
        "mean_expansion_factor": round(statistics.mean(expansion_factors), 2) if expansion_factors else 1.0,
        "mean_latency_ms": round(statistics.mean(latencies), 2) if latencies else 0.0,
        "p50_latency_ms": round(statistics.median(latencies), 2) if latencies else 0.0,
        "generation_calls_per_query": 0,  # Benchmark retrieval không gọi Gemini Generation
        "embedding_calls_per_query": 4 if "multi" in mode else 1,
        "per_question_results": per_question_results
    }

    return summary


def run_full_evaluation(
    questions_file: Path = QUESTIONS_FILE,
    reports_dir: Path = REPORTS_DIR,
    custom_hybrid_fn: Callable = None,
    query_generator_fn: Callable = None,
    score_fn: Callable = None
) -> dict[str, Any]:
    """
    Chạy đánh giá toàn diện trên cả 4 chế độ:
    - Lưu báo cáo nguyên tử (atomic) tại reports/eval_report_<timestamp>.json.
    - Cập nhật reports/latest_report.json.
    """
    config = load_buoi_09_config()
    questions = load_eval_questions(questions_file)

    reports_dir.mkdir(parents=True, exist_ok=True)

    # Nạp Hierarchy Registry để mapping
    children_by_id = {}
    try:
        _, children_by_id, manifest_data = load_hierarchy_store(storage_dir=HIERARCHY_STORAGE_DIR)
    except Exception:
        pass

    timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")

    mode_summaries = {}
    for m in ["single_flat", "multi_flat", "single_parent", "multi_parent"]:
        mode_summaries[m] = evaluate_single_mode(
            mode=m,
            questions=questions,
            config=config,
            children_by_id=children_by_id,
            custom_hybrid_fn=custom_hybrid_fn,
            query_generator_fn=query_generator_fn,
            score_fn=score_fn
        )

    full_report = {
        "timestamp_utc": timestamp_str,
        "environment": {
            "strategy": "hierarchical",
            "embedding_model": config["embedding_model"],
            "generation_model": config["generation_model"],
            "reranker_model": config["reranker_model"],
            "rerank_min_score": config["rerank_min_score"],
            "final_parent_top_k": config["final_parent_top_k"],
            "total_context_max_chars": config["total_context_max_chars"],
            "multi_query_count": config["multi_query_count"]
        },
        "questions_count": len(questions),
        "needs_human_review_disclaimer": (
            "CẢNH BÁO KỸ THUẬT: Tập nhãn đánh giá được gắn cờ 'needs_human_review=True'. "
            "Các chỉ số phản ánh sự so sánh tương đối giữa các chiến lược truy xuất và "
            "không được sử dụng để tuyên bố một chế độ nào chiến thắng tuyệt đối nếu thiếu ground truth chuẩn hóa."
        ),
        "modes": mode_summaries
    }

    # Ghi file nguyên tử (atomic write qua file tạm)
    report_file = reports_dir / f"eval_report_{timestamp_str}.json"
    temp_report = reports_dir / f".eval_report_{timestamp_str}.tmp"
    with open(temp_report, "w", encoding="utf-8") as f:
        json.dump(full_report, f, ensure_ascii=False, indent=2)
    temp_report.replace(report_file)

    # Cập nhật latest_report.json
    latest_file = reports_dir / "latest_report.json"
    temp_latest = reports_dir / ".latest_report.tmp"
    with open(temp_latest, "w", encoding="utf-8") as f:
        json.dump(full_report, f, ensure_ascii=False, indent=2)
    temp_latest.replace(latest_file)

    return full_report


def main():
    print("=========================================================================================")
    print("CHƯƠNG TRÌNH ĐÁNH GIÁ VÀ ĐỐI CHUẨN HIỆU NĂNG RAG (Buổi 09 Evaluator)")
    print("=========================================================================================")
    try:
        report = run_full_evaluation()
        print(f"Thời điểm đánh giá (UTC) : {report['timestamp_utc']}")
        print(f"Số lượng câu hỏi benchmark: {report['questions_count']}")
        print("-" * 105)
        print(f"{'Chế độ (Mode)':<16} | {'Parent Recall@K':<16} | {'Child Recall@K':<16} | {'MRR@K':<8} | {'nDCG@K':<8} | {'Latency P50':<12} | {'Context Chars':<14}")
        print("-" * 105)
        for m_name, m_data in report["modes"].items():
            print(f"{m_name:<16} | {m_data['mean_parent_recall_at_k']:<16.2%} | {m_data['mean_child_recall_at_k']:<16.2%} | {m_data['mean_mrr_at_k']:<8.4f} | {m_data['mean_ndcg_at_k']:<8.4f} | {m_data['p50_latency_ms']:<9.1f} ms | {m_data['mean_context_chars']:<14.1f}")
        print("-" * 105)
        print("LƯU Ý: Đánh giá hoàn toàn ở tầng Retrieval & Reranking; KHÔNG gọi Gemini Generation API.")
        print(f"Báo cáo đã được lưu trữ tại: reports/latest_report.json")
    except Exception as e:
        print(f"LỖI EVALUATION: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
