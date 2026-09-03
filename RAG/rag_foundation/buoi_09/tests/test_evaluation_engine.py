"""
Bộ unit tests kiểm thử Evaluation Engine cho Buổi 09:
100% offline, độc lập hoàn toàn, sử dụng mock retriever và mock questions,
không gọi Gemini API qua mạng, không tải Hugging Face model thật.
"""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path

# Đảm bảo import được module Buổi 09
BUOI_09_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUOI_09_DIR))

from evaluate import (
    calculate_mrr_at_k,
    calculate_recall_at_k,
    calculate_ndcg_at_k,
    evaluate_single_mode,
    run_full_evaluation,
)


class TestEvaluationEngine(unittest.TestCase):
    """
    Test suite kiểm thử các công thức và quy trình đánh giá của Buổi 09.
    """

    def test_01_mrr_at_k_calculation(self):
        """
        Case 1: Tính toán MRR@K chính xác: Hit đầu tiên ở rank 2 -> MRR = 0.5.
        """
        gold = {"doc_gold_1"}
        ranked = ["doc_irrelevant", "doc_gold_1", "doc_other"]
        mrr = calculate_mrr_at_k(ranked, gold, k=3)
        self.assertEqual(mrr, 0.5)

    def test_02_recall_at_k_calculation(self):
        """
        Case 2: Tính toán Recall@K chính xác: 2 gold IDs, tìm thấy 1 trong top 2 -> Recall = 0.5.
        """
        gold = {"doc_1", "doc_2"}
        ranked = ["doc_1", "doc_3"]
        recall = calculate_recall_at_k(ranked, gold, k=2)
        self.assertEqual(recall, 0.5)

    def test_03_ndcg_at_k_calculation(self):
        """
        Case 3: Tính toán nDCG@K với binary relevance: Perfect ranking -> nDCG = 1.0.
        """
        gold = {"doc_1", "doc_2"}
        ranked = ["doc_1", "doc_2", "doc_3"]
        ndcg = calculate_ndcg_at_k(ranked, gold, k=3)
        self.assertAlmostEqual(ndcg, 1.0, places=4)

    def test_04_evaluate_single_mode_offline(self):
        """
        Case 4: Chạy evaluate_single_mode hoàn toàn offline qua mock injection.
        """
        mock_questions = [
            {
                "question_id": "Q01",
                "question": "Điều kiện vay vốn?",
                "relevant_child_ids": ["TT_39_2016_NHNN:hierarchical:0059"],
                "relevant_parent_ids": ["TT_39_2016_NHNN:d08:w01"]
            }
        ]

        def mock_hybrid(q: str) -> list[dict]:
            return [{
                "child_id": "TT_39_2016_NHNN:hierarchical:0059",
                "text": "Child text",
                "source": "TT_39_2016_NHNN.pdf",
                "page_start": 4,
                "page_end": 5,
                "fused_rank": 1
            }]

        def mock_score(q: str, texts: list[str]) -> list[float]:
            return [2.0 for _ in texts]

        res = evaluate_single_mode(
            mode="single_parent",
            questions=mock_questions,
            custom_hybrid_fn=mock_hybrid,
            score_fn=mock_score
        )
        self.assertEqual(res["mode"], "single_parent")
        self.assertIn("mean_parent_recall_at_k", res)
        self.assertEqual(res["generation_calls_per_query"], 0)

    def test_05_atomic_report_generation(self):
        """
        Case 5: Báo cáo evaluation được ghi nguyên tử (atomic) và cập nhật latest_report.json.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_p = Path(tmp_dir)
            q_file = tmp_p / "test_questions.json"
            rep_dir = tmp_p / "reports"

            mock_q = [
                {
                    "question_id": "Q_TEST",
                    "question": "Test question?",
                    "relevant_child_ids": ["TT_39_2016_NHNN:hierarchical:0059"],
                    "relevant_parent_ids": ["TT_39_2016_NHNN:d08:w01"]
                }
            ]
            with open(q_file, "w", encoding="utf-8") as f:
                json.dump(mock_q, f)

            def mock_hybrid(q: str) -> list[dict]:
                return [{
                    "child_id": "TT_39_2016_NHNN:hierarchical:0059",
                    "text": "Child text",
                    "source": "TT_39_2016_NHNN.pdf",
                    "page_start": 4,
                    "page_end": 5,
                    "fused_rank": 1
                }]

            def mock_score(q: str, texts: list[str]) -> list[float]:
                return [2.0 for _ in texts]

            report = run_full_evaluation(
                questions_file=q_file,
                reports_dir=rep_dir,
                custom_hybrid_fn=mock_hybrid,
                score_fn=mock_score
            )
            self.assertIn("modes", report)
            self.assertTrue((rep_dir / "latest_report.json").exists())


if __name__ == "__main__":
    unittest.main()
