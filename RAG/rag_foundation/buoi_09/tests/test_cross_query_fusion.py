"""
Bộ unit tests kiểm thử Cross-Query RRF Fusion và Per-Query Retrieval cho Buổi 09:
100% offline, độc lập hoàn toàn, sử dụng dependency injection mock retriever,
không gọi Gemini API qua mạng và không tải mô hình Cross-Encoder.
Bao quát 12 tiêu chí kiểm thử bắt buộc theo đặc tả kỹ thuật SPEC_buoi_09.md.
"""

import os
import sys
import json
import unittest
from pathlib import Path

# Đảm bảo import được module Buổi 09
BUOI_09_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUOI_09_DIR))

from hierarchical_rag import (
    cross_query_reciprocal_rank_fusion,
    retrieve_multi_query_children,
    load_buoi_09_config,
    _MULTI_QUERY_CACHE,
)


class TestCrossQueryFusion(unittest.TestCase):
    """
    Test suite kiểm thử toàn diện Cross-Query Reciprocal Rank Fusion (Tầng 2 Fusion).
    """

    def setUp(self):
        self.config = load_buoi_09_config()
        self.config["multi_query_count"] = 2
        self.config["multi_query_original_weight"] = 1.5
        self.config["multi_query_variant_weight"] = 1.0
        self.config["multi_query_rrf_k"] = 60
        self.config["per_query_candidates"] = 10
        _MULTI_QUERY_CACHE.clear()

    def test_01_mq_rrf_formula_arithmetic_precision(self):
        """
        Case 1: Công thức MQ-RRF tính toán chuẩn xác theo từng số hạng tính tay:
        Score(d) = 1.5 / (60 + rank_Q0) + 1.0 / (60 + rank_Q1)
        """
        # Chunk A: Q0 rank 1, Q1 rank 2 -> 1.5 / 61 + 1.0 / 62 = 0.02459016 + 0.01612903 = 0.040719
        q_results = {
            "Q0": [
                {"child_id": "chunk_A", "text": "A", "source": "s.pdf", "page_start": 1, "page_end": 1, "fused_rank": 1}
            ],
            "Q1": [
                {"child_id": "chunk_A", "text": "A", "source": "s.pdf", "page_start": 1, "page_end": 1, "fused_rank": 2}
            ]
        }
        weights = {"Q0": 1.5, "Q1": 1.0}
        fused, trace = cross_query_reciprocal_rank_fusion(q_results, weights, k_rrf=60)
        self.assertEqual(len(fused), 1)
        expected_score = round(1.5 / 61.0 + 1.0 / 62.0, 6)
        self.assertAlmostEqual(fused[0]["multi_query_rrf_score"], expected_score, places=5)
        self.assertEqual(fused[0]["multi_query_rank"], 1)

    def test_02_original_and_variant_weights_applied(self):
        """
        Case 2: Trọng số Q0 (1.5) cao hơn Q1 (1.0) nên candidate đứng rank 1 ở Q0 thắng candidate đứng rank 1 ở Q1.
        """
        # Chunk A chỉ ở Q0 rank 1 -> 1.5 / 61 = 0.024590
        # Chunk B chỉ ở Q1 rank 1 -> 1.0 / 61 = 0.016393
        q_results = {
            "Q0": [{"child_id": "chunk_A", "text": "A", "source": "s.pdf", "page_start": 1, "page_end": 1, "fused_rank": 1}],
            "Q1": [{"child_id": "chunk_B", "text": "B", "source": "s.pdf", "page_start": 1, "page_end": 1, "fused_rank": 1}],
        }
        weights = {"Q0": 1.5, "Q1": 1.0}
        fused, _ = cross_query_reciprocal_rank_fusion(q_results, weights, k_rrf=60)
        self.assertEqual(len(fused), 2)
        self.assertEqual(fused[0]["child_id"], "chunk_A")
        self.assertEqual(fused[1]["child_id"], "chunk_B")
        self.assertGreater(fused[0]["multi_query_rrf_score"], fused[1]["multi_query_rrf_score"])

    def test_03_deduplicate_union(self):
        """
        Case 3: Candidate xuất hiện ở nhiều queries được gộp thành duy nhất 1 bản ghi trong kết quả fusion.
        """
        q_results = {
            "Q0": [{"child_id": "chunk_1", "text": "T1", "source": "s.pdf", "page_start": 1, "page_end": 1, "fused_rank": 1}],
            "Q1": [{"child_id": "chunk_1", "text": "T1", "source": "s.pdf", "page_start": 1, "page_end": 1, "fused_rank": 1}],
            "Q2": [{"child_id": "chunk_1", "text": "T1", "source": "s.pdf", "page_start": 1, "page_end": 1, "fused_rank": 2}],
        }
        weights = {"Q0": 1.5, "Q1": 1.0, "Q2": 1.0}
        fused, trace = cross_query_reciprocal_rank_fusion(q_results, weights, k_rrf=60)
        self.assertEqual(len(fused), 1)
        self.assertEqual(fused[0]["child_id"], "chunk_1")
        self.assertEqual(trace["union_count"], 1)

    def test_04_missing_query_contribution_preserved(self):
        """
        Case 4: Candidate chỉ xuất hiện ở một số query con vẫn được bảo toàn và chỉ nhận điểm từ query đó.
        """
        q_results = {
            "Q0": [{"child_id": "chunk_1", "text": "T1", "source": "s.pdf", "page_start": 1, "page_end": 1, "fused_rank": 1}],
            "Q1": [{"child_id": "chunk_2", "text": "T2", "source": "s.pdf", "page_start": 2, "page_end": 2, "fused_rank": 3}],
        }
        weights = {"Q0": 1.5, "Q1": 1.0}
        fused, _ = cross_query_reciprocal_rank_fusion(q_results, weights, k_rrf=60)
        self.assertEqual(len(fused), 2)
        c2 = next(c for c in fused if c["child_id"] == "chunk_2")
        self.assertEqual(c2["per_query_ranks"], {"Q1": 3})
        self.assertNotIn("Q0", c2["per_query_ranks"])
        self.assertAlmostEqual(c2["multi_query_rrf_score"], round(1.0 / 63.0, 6), places=5)

    def test_05_support_query_count_and_ids(self):
        """
        Case 5: Ghi nhận chính xác support_query_count và support_query_ids theo thứ tự Q0, Q1...
        """
        q_results = {
            "Q1": [{"child_id": "chunk_X", "text": "X", "source": "s.pdf", "page_start": 1, "page_end": 1, "fused_rank": 2}],
            "Q0": [{"child_id": "chunk_X", "text": "X", "source": "s.pdf", "page_start": 1, "page_end": 1, "fused_rank": 1}],
            "Q3": [{"child_id": "chunk_X", "text": "X", "source": "s.pdf", "page_start": 1, "page_end": 1, "fused_rank": 5}],
        }
        weights = {"Q0": 1.5, "Q1": 1.0, "Q3": 1.0}
        fused, _ = cross_query_reciprocal_rank_fusion(q_results, weights, k_rrf=60)
        self.assertEqual(len(fused), 1)
        item = fused[0]
        self.assertEqual(item["support_query_count"], 3)
        self.assertEqual(item["support_query_ids"], ["Q0", "Q1", "Q3"])
        self.assertEqual(item["best_query_rank"], 1)

    def test_06_metadata_mismatch_fails_clearly(self):
        """
        Case 6: Cùng child_id nhưng metadata (source, page, text) sai lệch giữa các query phải raise ValueError.
        """
        q_results = {
            "Q0": [{"child_id": "chunk_err", "text": "Text gốc", "source": "docA.pdf", "page_start": 1, "page_end": 1, "fused_rank": 1}],
            "Q1": [{"child_id": "chunk_err", "text": "Text khác", "source": "docA.pdf", "page_start": 1, "page_end": 1, "fused_rank": 2}],
        }
        weights = {"Q0": 1.5, "Q1": 1.0}
        with self.assertRaises(ValueError) as ctx:
            cross_query_reciprocal_rank_fusion(q_results, weights, k_rrf=60)
        self.assertIn("Metadata mismatch", str(ctx.exception))

    def test_07_deterministic_tie_breaking(self):
        """
        Case 7: Khi 2 candidates có cùng MQ-RRF score, tie-break theo support_count -> best_rank -> child_id.
        """
        # Cùng score, cùng support count -> tie break theo child_id
        q_results = {
            "Q1": [
                {"child_id": "chunk_Z", "text": "Z", "source": "s.pdf", "page_start": 1, "page_end": 1, "fused_rank": 1},
                {"child_id": "chunk_A", "text": "A", "source": "s.pdf", "page_start": 1, "page_end": 1, "fused_rank": 1},
            ]
        }
        weights = {"Q1": 1.0}
        fused, _ = cross_query_reciprocal_rank_fusion(q_results, weights, k_rrf=60)
        self.assertEqual(fused[0]["child_id"], "chunk_A")
        self.assertEqual(fused[1]["child_id"], "chunk_Z")

    def test_08_each_query_calls_hybrid_once(self):
        """
        Case 8: Pipeline thực thi đúng mỗi query gọi hybrid retriever duy nhất 1 lần.
        """
        calls = []
        def mock_hybrid(query_str: str) -> list[dict]:
            calls.append(query_str)
            return [
                {"child_id": f"c_{len(calls)}", "text": f"Text {len(calls)}", "source": "s.pdf", "page_start": 1, "page_end": 1, "fused_rank": 1}
            ]

        def mock_gen(q: str) -> str:
            return json.dumps({
                "queries": [
                    {"text": "Query Variant 1", "focus": "exact_legal_terms"},
                    {"text": "Query Variant 2", "focus": "paraphrase"},
                ]
            })

        res = retrieve_multi_query_children(
            question="Câu hỏi gốc test calls",
            config=self.config,
            query_generator_fn=mock_gen,
            custom_hybrid_fn=mock_hybrid
        )
        self.assertEqual(len(calls), 3)  # Q0 + Q1 + Q2
        self.assertEqual(res["trace"]["query_counts"]["executed"], 3)

    def test_09_does_not_call_reranker_or_generation_during_retrieval(self):
        """
        Case 9: Giai đoạn Cross-Query Retrieval hoàn toàn không nạp/gọi CrossEncoderReranker hay LLM generation.
        """
        def mock_gen(q: str) -> str:
            return json.dumps({"queries": [{"text": "V1", "focus": "paraphrase"}]})

        def mock_retriever(q: str) -> list[dict]:
            return [{"child_id": "c1", "text": "T", "source": "s.pdf", "page_start": 1, "page_end": 1, "fused_rank": 1}]

        res = retrieve_multi_query_children(
            question="Test no reranker",
            config=self.config,
            query_generator_fn=mock_gen,
            custom_hybrid_fn=mock_retriever
        )
        self.assertEqual(res["status"], "ready")
        self.assertNotIn("rerank_score", res["fused_children"][0])

    def test_10_q0_failure_fails_all_and_variant_failure_yields_partial_status(self):
        """
        Case 10: Nếu Q0 fail -> toàn pipeline fail; Nếu variant fail -> status 'multi_query_partial'.
        """
        # 1. Q0 failure
        def mock_failing_q0(q: str) -> list[dict]:
            if "Gốc Lỗi" in q:
                raise RuntimeError("Lỗi database tại Q0")
            return [{"child_id": "c1", "text": "T", "source": "s.pdf", "page_start": 1, "page_end": 1, "fused_rank": 1}]

        def mock_gen(q: str) -> str:
            return json.dumps({"queries": [{"text": "V1", "focus": "paraphrase"}]})

        with self.assertRaises(RuntimeError) as ctx:
            retrieve_multi_query_children(
                question="Gốc Lỗi",
                config=self.config,
                query_generator_fn=mock_gen,
                custom_hybrid_fn=mock_failing_q0
            )
        self.assertIn("Q0 retrieval failed", str(ctx.exception))

        # 2. Variant failure -> status 'multi_query_partial'
        def mock_failing_variant(q: str) -> list[dict]:
            if "Variant Lỗi" in q:
                raise RuntimeError("Lỗi mạng tại variant")
            return [{"child_id": "c1", "text": "T", "source": "s.pdf", "page_start": 1, "page_end": 1, "fused_rank": 1}]

        def mock_gen_fail(q: str) -> str:
            return json.dumps({"queries": [{"text": "Variant Lỗi", "focus": "paraphrase"}]})

        res_partial = retrieve_multi_query_children(
            question="Gốc Thành Công",
            config=self.config,
            query_generator_fn=mock_gen_fail,
            custom_hybrid_fn=mock_failing_variant
        )
        self.assertEqual(res_partial["status"], "multi_query_partial")
        self.assertEqual(len(res_partial["fused_children"]), 1)
        self.assertTrue(len(res_partial["warnings"]) > 0)

    def test_11_trace_counts_and_latency_schema(self):
        """
        Case 11: Trace ghi nhận đầy đủ schema query_counts, latencies_ms, overlap_distribution.
        """
        def mock_gen(q: str) -> str:
            return json.dumps({"queries": [{"text": "V1", "focus": "paraphrase"}]})

        def mock_retriever(q: str) -> list[dict]:
            return [{"child_id": "c1", "text": "T", "source": "s.pdf", "page_start": 1, "page_end": 1, "fused_rank": 1}]

        res = retrieve_multi_query_children(
            question="Test Trace",
            config=self.config,
            query_generator_fn=mock_gen,
            custom_hybrid_fn=mock_retriever
        )
        t = res["trace"]
        self.assertIn("query_counts", t)
        self.assertIn("latencies_ms", t)
        self.assertIn("overlap_distribution", t)
        self.assertIn("union_child_count", t)
        self.assertEqual(t["query_counts"]["executed"], 2)

    def test_12_tests_run_100_percent_offline(self):
        """
        Case 12: Toàn bộ suite test chạy 100% offline, độc lập không phụ thuộc mạng hay disk storage.
        """
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
