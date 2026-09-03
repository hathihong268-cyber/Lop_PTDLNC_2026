"""
Bộ kiểm thử tự động (Unit Tests) cho Evaluation Metrics Suite - Buổi 08.
Đảm bảo 100% chạy offline, tính toán số học chính xác từng công thức Hit@K, MRR@K, Recall@K, nDCG@K.
"""

import sys
import math
import json
import tempfile
import unittest
from pathlib import Path

# Đảm bảo import được module Buổi 08
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from evaluate import (
    hit_at_k,
    reciprocal_rank_at_k,
    precision_at_k,
    recall_at_k,
    dcg_at_k,
    ndcg_at_k,
    evaluate_retrieval_system
)


class TestEvaluationMetrics(unittest.TestCase):
    """Kiểm thử độ chính xác số học của các độ đo đánh giá Retrieval & Ranking"""

    def test_01_hit_at_k_arithmetic_precision(self):
        """Case 1: Hit@K tính toán chuẩn xác với ranking nhỏ tính tay được"""
        retrieved = ["chunk_01", "chunk_02", "chunk_03", "chunk_04"]
        relevant = {"chunk_02"}

        self.assertEqual(hit_at_k(retrieved, relevant, k=1), 0.0)  # chunk_01 không khớp
        self.assertEqual(hit_at_k(retrieved, relevant, k=2), 1.0)  # chunk_02 khớp tại rank 2
        self.assertEqual(hit_at_k(retrieved, relevant, k=4), 1.0)
        self.assertEqual(hit_at_k(retrieved, {"chunk_99"}, k=4), 0.0)  # Không có trong top-k

    def test_02_reciprocal_rank_at_k_precision(self):
        """Case 2: MRR@K tính đúng 1 / rank của relevant document đầu tiên"""
        retrieved = ["chunk_01", "chunk_02", "chunk_03"]

        # Relevant chunk tại rank 1 -> MRR = 1/1 = 1.0
        self.assertEqual(reciprocal_rank_at_k(retrieved, {"chunk_01"}, k=3), 1.0)

        # Relevant chunk tại rank 2 -> MRR = 1/2 = 0.5
        self.assertEqual(reciprocal_rank_at_k(retrieved, {"chunk_02"}, k=1), 0.0)
        self.assertEqual(reciprocal_rank_at_k(retrieved, {"chunk_02"}, k=2), 0.5)

        # Relevant chunk tại rank 3 -> MRR = 1/3 ≈ 0.3333
        self.assertAlmostEqual(reciprocal_rank_at_k(retrieved, {"chunk_03"}, k=3), 1.0 / 3.0, places=4)

    def test_03_precision_and_recall_at_k_precision(self):
        """Case 3: Precision@K và Recall@K tính đúng tỷ lệ trên ground truth"""
        retrieved = ["c1", "c_bad", "c2", "c_bad2"]
        relevant = {"c1", "c2"}  # Tổng cộng 2 tài liệu đúng

        # Tại K=1: 1 hit / 1 retrieved = 1.0 precision, 1 hit / 2 relevant = 0.5 recall
        self.assertEqual(precision_at_k(retrieved, relevant, k=1), 1.0)
        self.assertEqual(recall_at_k(retrieved, relevant, k=1), 0.5)

        # Tại K=2: 1 hit / 2 retrieved = 0.5 precision, 1 hit / 2 relevant = 0.5 recall
        self.assertEqual(precision_at_k(retrieved, relevant, k=2), 0.5)
        self.assertEqual(recall_at_k(retrieved, relevant, k=2), 0.5)

        # Tại K=3: 2 hits / 3 retrieved = 2/3 precision, 2 hits / 2 relevant = 1.0 recall
        self.assertAlmostEqual(precision_at_k(retrieved, relevant, k=3), 2.0 / 3.0, places=4)
        self.assertEqual(recall_at_k(retrieved, relevant, k=3), 1.0)

    def test_04_dcg_and_ndcg_at_k_precision(self):
        """Case 4: nDCG@K tính đúng với binary relevance và chiết khấu logarit cơ số 2"""
        # Trường hợp lý tưởng: tài liệu đúng đứng đầu danh sách
        retrieved_ideal = ["c1", "c2", "c_bad"]
        relevant = {"c1", "c2"}
        self.assertEqual(ndcg_at_k(retrieved_ideal, relevant, k=1), 1.0)
        self.assertEqual(ndcg_at_k(retrieved_ideal, relevant, k=2), 1.0)

        # Trường hợp đảo vị trí: tài liệu sai đứng đầu danh sách -> ["c_bad", "c1", "c2"]
        retrieved_suboptimal = ["c_bad", "c1", "c2"]
        # K=1: không có hit nào -> nDCG@1 = 0.0
        self.assertEqual(ndcg_at_k(retrieved_suboptimal, relevant, k=1), 0.0)

        # K=2: DCG@2 = 0 + 1 / log2(2 + 1) = 1 / log2(3) ≈ 0.63093
        # IDCG@2 = 1 / log2(1 + 1) + 1 / log2(2 + 1) = 1 + 1 / log2(3) ≈ 1.63093
        # nDCG@2 = 0.63093 / 1.63093 ≈ 0.38685
        expected_ndcg_2 = (1.0 / math.log2(3.0)) / (1.0 + 1.0 / math.log2(3.0))
        self.assertAlmostEqual(ndcg_at_k(retrieved_suboptimal, relevant, k=2), expected_ndcg_2, places=4)

    def test_05_evaluate_retrieval_system_with_synthetic_fixture(self):
        """Case 5: evaluate_retrieval_system chạy hoàn chỉnh trên synthetic fixture, cảnh báo unreviewed và lưu report"""
        # Tạo file questions tạm thời có gắn cờ needs_human_review
        synthetic_questions = [
            {
                "id": "q1",
                "question": "Điều 4 cơ cấu lại nợ",
                "relevant_chunk_ids": ["c1"],
                "needs_human_review": True
            },
            {
                "id": "q2",
                "question": "Nhu cầu vốn không được cho vay",
                "relevant_chunk_ids": ["c2"],
                "needs_human_review": False
            }
        ]

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".json") as tf:
            json.dump(synthetic_questions, tf, ensure_ascii=False)
            temp_q_file = Path(tf.name)

        def mock_retriever_fn(q, mode, k):
            if "cơ cấu" in q:
                return ["c1", "c2"]
            return ["c2", "c1"]

        config = {
            "embedding_model": "gemini-embedding-2",
            "embedding_dim": 128,
            "reranker_model": "BAAI/bge-reranker-v2-m3",
            "rrf_k": 60,
            "rrf_bm25_weight": 1.0,
            "rrf_semantic_weight": 1.0,
        }

        report = evaluate_retrieval_system(
            questions_file=temp_q_file,
            strategy="hierarchical",
            modes=["mock_mode"],
            k_list=[1, 2],
            config=config,
            custom_retriever_fn=mock_retriever_fn
        )

        # Báo cáo phải ghi nhận cảnh báo needs_human_review
        self.assertEqual(report["unreviewed_questions"], 1)
        self.assertGreater(len(report["warnings"]), 0)
        self.assertIn("needs_human_review=true", report["warnings"][0])

        # Điểm Hit@1 và Recall@1 phải bằng 1.0
        mock_summary = report["metrics_summary"]["mock_mode"]
        self.assertEqual(mock_summary["mean_hit@1"], 1.0)
        self.assertEqual(mock_summary["mean_recall@1"], 1.0)
        self.assertEqual(mock_summary["mean_ndcg@1"], 1.0)

        # Dọn dẹp file tạm
        try:
            temp_q_file.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
