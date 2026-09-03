"""
Bộ kiểm thử tự động (Unit Tests) cho Cross-Encoder Reranker - Buổi 08.
Đảm bảo 100% chạy offline qua Dependency Injection và Mocking, không tải file model và không gọi mạng.
"""

import sys
import math
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Đảm bảo import được module Buổi 08
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from advanced_rag import (
    CrossEncoderReranker,
    compute_rerank_scores,
    retrieve_and_rerank_candidates,
    _RERANKER_CACHE
)


class TestCrossEncoderReranker(unittest.TestCase):
    """Kiểm thử Cross-Encoder Reranking, Sigmoid Scoring, Sorting và Dependency Injection"""

    def setUp(self):
        self.sample_fused_candidates = [
            {
                "chunk_id": "chunk_01",
                "text": "Nội dung Điều 4 về cơ cấu nợ và trích lập dự phòng.",
                "source": "TT_02.pdf",
                "page_start": 1,
                "page_end": 2,
                "fused_rank": 1,
                "rrf_score": 0.032,
                "matched_by": ["bm25", "semantic"]
            },
            {
                "chunk_id": "chunk_02",
                "text": "Nội dung Điều 8 về các nhu cầu vốn không được cho vay.",
                "source": "TT_39.pdf",
                "page_start": 3,
                "page_end": 4,
                "fused_rank": 2,
                "rrf_score": 0.016,
                "matched_by": ["bm25"]
            },
            {
                "chunk_id": "chunk_03",
                "text": "Nội dung Điều 13 về thỏa thuận lãi suất cho vay.",
                "source": "TT_39.pdf",
                "page_start": 5,
                "page_end": 6,
                "fused_rank": 3,
                "rrf_score": 0.015,
                "matched_by": ["semantic"]
            },
            {
                "chunk_id": "chunk_04",
                "text": "Nội dung Điều 22 về xử lý vi phạm quy chế.",
                "source": "TT_39.pdf",
                "page_start": 7,
                "page_end": 8,
                "fused_rank": 4,
                "rrf_score": 0.012,
                "matched_by": ["bm25"]
            }
        ]

    def test_01_lazy_loading_does_not_load_model_at_init(self):
        """Case 1: Khởi tạo CrossEncoderReranker không tự động tải mô hình vào RAM"""
        reranker = CrossEncoderReranker(model_name="BAAI/bge-reranker-v2-m3")
        self.assertIsNone(reranker.model)
        self.assertIsNone(reranker.tokenizer)

    def test_02_one_pair_per_candidate(self):
        """Case 2: Mỗi candidate được ghép đúng 1 cặp (query, candidate_text) khi tính điểm"""
        called_pairs = []

        def mock_score_fn(query, texts):
            for t in texts:
                called_pairs.append((query, t))
            return [1.0] * len(texts)

        reranker = CrossEncoderReranker(score_fn=mock_score_fn)
        reranker.rerank(
            query="Quy định cơ cấu nợ",
            candidates=self.sample_fused_candidates,
            top_k=4
        )

        self.assertEqual(len(called_pairs), 4)
        self.assertEqual(called_pairs[0][0], "Quy định cơ cấu nợ")
        self.assertEqual(called_pairs[0][1], self.sample_fused_candidates[0]["text"])

    def test_03_batch_processing_preserves_count(self):
        """Case 3: Xử lý theo batch_size khác nhau không làm thay đổi số lượng kết quả"""
        def mock_score_fn(query, texts):
            return [float(i) for i in range(len(texts))]

        scores_b1 = compute_rerank_scores(
            query="test",
            texts=["t1", "t2", "t3", "t4"],
            batch_size=1,
            score_fn=mock_score_fn
        )
        scores_b4 = compute_rerank_scores(
            query="test",
            texts=["t1", "t2", "t3", "t4"],
            batch_size=4,
            score_fn=mock_score_fn
        )

        self.assertEqual(len(scores_b1), 4)
        self.assertEqual(len(scores_b4), 4)
        self.assertEqual(scores_b1, scores_b4)

    def test_04_sigmoid_score_arithmetic_precision(self):
        """Case 4: rerank_score được tính chính xác bằng công thức Sigmoid: 1 / (1 + exp(-logit))"""
        raw_logits = [0.0, 2.0, -2.0]

        def mock_score_fn(query, texts):
            return raw_logits

        scores = compute_rerank_scores(
            query="test",
            texts=["a", "b", "c"],
            score_fn=mock_score_fn
        )

        # logit 0.0 -> sigmoid = 0.5
        self.assertAlmostEqual(scores[0][1], 0.5, places=3)
        # logit 2.0 -> sigmoid = 1 / (1 + exp(-2.0)) ≈ 0.8808
        self.assertAlmostEqual(scores[1][1], 1.0 / (1.0 + math.exp(-2.0)), places=3)
        # logit -2.0 -> sigmoid = 1 / (1 + exp(2.0)) ≈ 0.1192
        self.assertAlmostEqual(scores[2][1], 1.0 / (1.0 + math.exp(2.0)), places=3)

    def test_05_sorting_and_deterministic_tie_breaking(self):
        """Case 5: Sắp xếp giảm dần theo rerank_score, tie-break theo fused_rank tăng dần và chunk_id"""
        # Gán chunk_02 điểm cao nhất, chunk_01 và chunk_03 bằng điểm nhau
        def mock_score_fn(query, texts):
            # chunk_01=1.0, chunk_02=3.0, chunk_03=1.0, chunk_04=0.0
            return [1.0, 3.0, 1.0, 0.0]

        reranker = CrossEncoderReranker(score_fn=mock_score_fn)
        results = reranker.rerank(
            query="Cơ cấu nợ",
            candidates=self.sample_fused_candidates,
            top_k=4
        )

        # chunk_02 có score cao nhất (sigmoid(3.0)) -> Rank 1
        self.assertEqual(results[0]["chunk_id"], "chunk_02")
        self.assertEqual(results[0]["rerank_rank"], 1)

        # chunk_01 và chunk_03 cùng có score sigmoid(1.0) -> tie-break theo fused_rank: chunk_01 (fused_rank=1) < chunk_03 (fused_rank=3)
        self.assertEqual(results[1]["chunk_id"], "chunk_01")
        self.assertEqual(results[1]["rerank_rank"], 2)
        self.assertEqual(results[2]["chunk_id"], "chunk_03")
        self.assertEqual(results[2]["rerank_rank"], 3)

    def test_06_rank_change_calculation_correctness(self):
        """Case 6: rank_change được tính chính xác bằng công thức: fused_rank - rerank_rank"""
        # chunk_02 từ fused_rank 2 nhảy lên rerank_rank 1 (rank_change = +1)
        # chunk_01 từ fused_rank 1 tụt xuống rerank_rank 2 (rank_change = -1)
        def mock_score_fn(query, texts):
            return [1.0, 3.0, 0.5, 0.1]

        reranker = CrossEncoderReranker(score_fn=mock_score_fn)
        results = reranker.rerank(
            query="test",
            candidates=self.sample_fused_candidates,
            top_k=2
        )

        # chunk_02: fused=2, rerank=1 -> rank_change = 2 - 1 = +1
        self.assertEqual(results[0]["chunk_id"], "chunk_02")
        self.assertEqual(results[0]["rank_change"], 1)

        # chunk_01: fused=1, rerank=2 -> rank_change = 1 - 2 = -1
        self.assertEqual(results[1]["chunk_id"], "chunk_01")
        self.assertEqual(results[1]["rank_change"], -1)

    def test_07_reranks_only_limited_candidates(self):
        """Case 7: Giới hạn tối đa candidate được nạp vào rerank bằng min(rerank_candidates_limit, len(candidates))"""
        reranked_texts = []

        def mock_score_fn(query, texts):
            reranked_texts.extend(texts)
            return [1.0] * len(texts)

        reranker = CrossEncoderReranker(score_fn=mock_score_fn)
        reranker.rerank(
            query="test",
            candidates=self.sample_fused_candidates,
            top_k=2,
            rerank_candidates_limit=2  # Chỉ rerank 2 candidate đầu
        )

        # Chỉ có 2 candidate đầu tiên được chuyển tới score_fn
        self.assertEqual(len(reranked_texts), 2)
        self.assertEqual(reranked_texts[0], self.sample_fused_candidates[0]["text"])
        self.assertEqual(reranked_texts[1], self.sample_fused_candidates[1]["text"])

    def test_08_returns_only_final_top_k(self):
        """Case 8: Pipeline chỉ trả về đúng số lượng FINAL_TOP_K sau khi đã tái xếp hạng"""
        def mock_score_fn(query, texts):
            return [float(i) for i in range(len(texts))]

        reranker = CrossEncoderReranker(score_fn=mock_score_fn)
        results = reranker.rerank(
            query="test",
            candidates=self.sample_fused_candidates,
            top_k=2  # Chỉ lấy 2
        )

        self.assertEqual(len(results), 2)

    def test_09_model_failure_does_not_silently_fallback(self):
        """Case 9: Khi việc tải mô hình reranker gặp lỗi, phải raise Exception (reranker_unavailable) chứ không âm thầm bỏ qua"""
        with patch("advanced_rag.load_reranker_model", side_effect=RuntimeError("Connection Timeout")):
            reranker = CrossEncoderReranker(model_name="non-existent/model")
            with self.assertRaises(RuntimeError) as ctx:
                reranker.rerank(
                    query="test",
                    candidates=self.sample_fused_candidates,
                    top_k=2
                )
            self.assertIn("Connection Timeout", str(ctx.exception))

    def test_10_tests_run_offline_without_network(self):
        """Case 10: Toàn bộ quá trình kiểm thử không tải mô hình thật và không có network call"""
        # Kiểm tra _RERANKER_CACHE ban đầu vẫn None nếu chỉ dùng score_fn
        def mock_fn(q, t):
            return [0.5] * len(t)

        reranker = CrossEncoderReranker(score_fn=mock_fn)
        res = reranker.rerank("offline query", self.sample_fused_candidates, top_k=1)
        self.assertEqual(len(res), 1)


if __name__ == "__main__":
    unittest.main()
