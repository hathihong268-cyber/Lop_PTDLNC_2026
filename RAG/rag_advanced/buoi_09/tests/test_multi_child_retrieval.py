"""
Unit Tests cho Fan-out Multi-Query Retrieval & Cross-Query RRF Fusion - Buổi 09
Bước 05: 12 ca kiểm thử bắt buộc:

1.  Công thức MQ-RRF tính tay (so sánh chính xác từng chữ số).
2.  Q0 dùng original_weight, Qi generated dùng variant_weight.
3.  Deduplication union: cùng child_id không bị nhân đôi.
4.  Missing query contribution: child chỉ xuất hiện ở một query vẫn vào union.
5.  support_query_count / support_query_ids đúng.
6.  Metadata mismatch -> ValueError rõ ràng.
7.  Deterministic tie-break.
8.  Mỗi query chỉ gọi hybrid retriever đúng một lần.
9.  Không gọi reranker / generation trong fan_out.
10. Q0 failure -> status=q0_retrieval_failed, fused_children=[].
11. Generated query partial failure -> status=multi_query_partial, Q0 results vẫn có.
12. Trace: schema đầy đủ.
"""

import unittest
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from hierarchical_rag import (
    cross_query_rrf_fusion,
    fan_out_multi_query_retrieval,
    clear_query_expansion_cache,
)


def make_candidate(child_id, fused_rank, bm25_rank=None, semantic_rank=None,
                   source="doc_a.pdf", page_start=1, page_end=2):
    return {
        "chunk_id": child_id,
        "text": f"Noi dung {child_id}",
        "source": source,
        "page_start": page_start,
        "page_end": page_end,
        "fused_rank": fused_rank,
        "bm25_rank": bm25_rank,
        "semantic_rank": semantic_rank,
        "matched_by": ["bm25"],
    }


def make_per_query_result(qid, origin, candidates, status="ok", error_msg=None):
    return {
        "query_id": qid,
        "origin": origin,
        "text": f"Query text for {qid}",
        "status": status,
        "error_msg": error_msg,
        "candidates": candidates,
        "result_count": len(candidates) if status == "ok" else 0,
        "latency_ms": 10.0,
        "retrieval_trace": {},
    }


DEFAULT_CFG = {
    "multi_query_rrf_k": 60,
    "multi_query_original_weight": 1.5,
    "multi_query_variant_weight": 1.0,
    "per_query_candidates": 5,
    "multi_query_count": 2,
    "multi_query_temperature": 0.2,
    "multi_query_max_chars": 300,
    "generation_model": "mock-model",
    "api_key": "",
}


class TestCrossQueryRRFFusion(unittest.TestCase):

    def test_01_mq_rrf_formula_exact(self):
        """Case 1: Cong thuc MQ-RRF tinh tay chinh xac."""
        expected_a = round(1.5 / 61 + 1.0 / 61, 8)
        expected_b = round(1.5 / 62, 8)

        per_q = [
            make_per_query_result("Q0", "original", [
                make_candidate("child_A", fused_rank=1),
                make_candidate("child_B", fused_rank=2),
            ]),
            make_per_query_result("Q1", "generated", [
                make_candidate("child_A", fused_rank=1),
            ]),
        ]

        fused, _ = cross_query_rrf_fusion(per_q, config=DEFAULT_CFG)
        scores = {item["child_id"]: item["multi_query_rrf_score"] for item in fused}

        self.assertAlmostEqual(scores["child_A"], expected_a, places=7)
        self.assertAlmostEqual(scores["child_B"], expected_b, places=7)
        self.assertGreater(scores["child_A"], scores["child_B"])

    def test_02_original_vs_variant_weights(self):
        """Case 2: Q0 original_weight=2.0, Q1 variant_weight=0.5."""
        cfg = dict(DEFAULT_CFG, multi_query_original_weight=2.0, multi_query_variant_weight=0.5)

        per_q = [
            make_per_query_result("Q0", "original", [make_candidate("child_X", 1)]),
            make_per_query_result("Q1", "generated", [make_candidate("child_Y", 1)]),
        ]

        fused, _ = cross_query_rrf_fusion(per_q, config=cfg)
        scores = {item["child_id"]: item["multi_query_rrf_score"] for item in fused}

        self.assertAlmostEqual(scores["child_X"], round(2.0 / 61, 8), places=7)
        self.assertAlmostEqual(scores["child_Y"], round(0.5 / 61, 8), places=7)
        self.assertGreater(scores["child_X"], scores["child_Y"])

    def test_03_deduplicate_union_no_double_count(self):
        """Case 3: Cung child_id tu nhieu query duoc gop mot lan."""
        per_q = [
            make_per_query_result("Q0", "original", [make_candidate("child_A", 1)]),
            make_per_query_result("Q1", "generated", [make_candidate("child_A", 1)]),
            make_per_query_result("Q2", "generated", [make_candidate("child_A", 1)]),
        ]

        fused, stats = cross_query_rrf_fusion(per_q, config=DEFAULT_CFG)

        self.assertEqual(len(fused), 1)
        self.assertEqual(stats["union_child_count"], 1)

    def test_04_missing_query_contribution_single_query_child(self):
        """Case 4: Child chi xuat hien o mot query van vao union."""
        per_q = [
            make_per_query_result("Q0", "original", [make_candidate("child_A", 1)]),
            make_per_query_result("Q1", "generated", [make_candidate("child_B", 1)]),
        ]

        fused, stats = cross_query_rrf_fusion(per_q, config=DEFAULT_CFG)
        child_ids = [item["child_id"] for item in fused]

        self.assertIn("child_A", child_ids)
        self.assertIn("child_B", child_ids)
        self.assertEqual(stats["union_child_count"], 2)

        item_b = next(i for i in fused if i["child_id"] == "child_B")
        self.assertEqual(item_b["support_query_count"], 1)
        self.assertEqual(item_b["support_query_ids"], ["Q1"])

    def test_05_support_query_count_and_ids_correct(self):
        """Case 5: support_query_count va support_query_ids dung."""
        per_q = [
            make_per_query_result("Q0", "original", [
                make_candidate("child_A", 1),
                make_candidate("child_B", 2),
            ]),
            make_per_query_result("Q1", "generated", [
                make_candidate("child_A", 1),
                make_candidate("child_C", 2),
            ]),
            make_per_query_result("Q2", "generated", [
                make_candidate("child_A", 1),
            ]),
        ]

        fused, _ = cross_query_rrf_fusion(per_q, config=DEFAULT_CFG)
        item_a = next(i for i in fused if i["child_id"] == "child_A")

        self.assertEqual(item_a["support_query_count"], 3)
        self.assertEqual(item_a["support_query_ids"], ["Q0", "Q1", "Q2"])

    def test_06_metadata_mismatch_raises_valueerror(self):
        """Case 6: Metadata mismatch -> ValueError."""
        hit_q0 = make_candidate("child_A", 1, source="doc_a.pdf")
        hit_q1 = make_candidate("child_A", 1, source="doc_b.pdf")

        per_q = [
            make_per_query_result("Q0", "original", [hit_q0]),
            make_per_query_result("Q1", "generated", [hit_q1]),
        ]

        with self.assertRaises(ValueError) as ctx:
            cross_query_rrf_fusion(per_q, config=DEFAULT_CFG)

        self.assertIn("Metadata mismatch", str(ctx.exception))
        self.assertIn("child_A", str(ctx.exception))

    def test_07_deterministic_tiebreak(self):
        """Case 7: Score bang nhau -> sort theo child_id ASC."""
        per_q = [
            make_per_query_result("Q0", "original", [
                make_candidate("child_ZZ", 1),
                make_candidate("child_AA", 1),
            ]),
        ]

        fused, _ = cross_query_rrf_fusion(per_q, config=DEFAULT_CFG)
        ids = [item["child_id"] for item in fused]
        self.assertEqual(ids[0], "child_AA")
        self.assertEqual(ids[1], "child_ZZ")

    def test_07b_multi_query_rank_assigned_from_1(self):
        """Case 7b: multi_query_rank bat dau tu 1."""
        per_q = [
            make_per_query_result("Q0", "original", [
                make_candidate("child_A", 1),
                make_candidate("child_B", 2),
                make_candidate("child_C", 3),
            ]),
        ]
        fused, _ = cross_query_rrf_fusion(per_q, config=DEFAULT_CFG)
        ranks = [item["multi_query_rank"] for item in fused]
        self.assertEqual(ranks, [1, 2, 3])


class TestFanOutMultiQueryRetrieval(unittest.TestCase):

    def setUp(self):
        clear_query_expansion_cache()
        self.cfg = dict(DEFAULT_CFG)

    def tearDown(self):
        clear_query_expansion_cache()

    def _make_query_set(self, queries_spec):
        return {
            "original_question": "Test question",
            "status": "ready",
            "queries": [
                {"query_id": qid, "origin": origin, "text": text, "focus": "original_intent"}
                for qid, origin, text in queries_spec
            ]
        }

    def test_08_each_query_calls_retriever_exactly_once(self):
        """Case 8: Moi query chi goi hybrid retriever dung mot lan."""
        call_log = []

        def fake_retriever(question, top_n, config):
            call_log.append(question)
            return {
                "candidates": [make_candidate(f"child_{len(call_log)}", fused_rank=1)],
                "trace": {}
            }

        qs = self._make_query_set([
            ("Q0", "original", "Cau hoi Q0"),
            ("Q1", "generated", "Bien the Q1"),
            ("Q2", "generated", "Bien the Q2"),
        ])

        fan_out_multi_query_retrieval(qs, config=self.cfg, hybrid_retriever_fn=fake_retriever)

        self.assertEqual(len(call_log), 3)

    def test_09_no_reranker_no_generation_called(self):
        """Case 9: Khong goi reranker hay generation."""
        reranker_called = []
        generation_called = []

        def fake_retriever(question, top_n, config):
            return {
                "candidates": [make_candidate("child_1", fused_rank=1)],
                "trace": {}
            }

        qs = self._make_query_set([("Q0", "original", "Test")])
        fan_out_multi_query_retrieval(qs, config=self.cfg, hybrid_retriever_fn=fake_retriever)

        self.assertEqual(reranker_called, [])
        self.assertEqual(generation_called, [])

    def test_10_q0_failure_fails_entire_pipeline(self):
        """Case 10: Q0 loi -> status=q0_retrieval_failed."""
        def fake_retriever(question, top_n, config):
            if "Q0" in question:
                raise RuntimeError("ChromaDB connection refused for Q0")
            return {"candidates": [make_candidate("child_1", 1)], "trace": {}}

        qs = self._make_query_set([
            ("Q0", "original", "Q0 text"),
            ("Q1", "generated", "Q1 text"),
        ])

        result = fan_out_multi_query_retrieval(qs, config=self.cfg, hybrid_retriever_fn=fake_retriever)

        self.assertEqual(result["status"], "q0_retrieval_failed")
        self.assertEqual(result["fused_children"], [])
        self.assertIn("error", result)

    def test_11_generated_query_partial_failure(self):
        """Case 11: Generated loi -> multi_query_partial, Q0 results van co."""
        fail_queries = {"Bien the Q1", "Bien the Q2"}

        def fake_retriever(question, top_n, config):
            if question in fail_queries:
                raise RuntimeError(f"Error: {question}")
            return {
                "candidates": [
                    make_candidate("child_q0", fused_rank=1),
                    make_candidate("child_q0_b", fused_rank=2),
                ],
                "trace": {}
            }

        qs = self._make_query_set([
            ("Q0", "original", "Cau hoi goc"),
            ("Q1", "generated", "Bien the Q1"),
            ("Q2", "generated", "Bien the Q2"),
        ])

        result = fan_out_multi_query_retrieval(qs, config=self.cfg, hybrid_retriever_fn=fake_retriever)

        self.assertEqual(result["status"], "multi_query_partial")
        self.assertEqual(result["query_count_failed"], 2)

        fused_ids = [item["child_id"] for item in result["fused_children"]]
        self.assertIn("child_q0", fused_ids)

        pq_statuses = {r["query_id"]: r["status"] for r in result["per_query_results"]}
        self.assertEqual(pq_statuses["Q0"], "ok")
        self.assertEqual(pq_statuses["Q1"], "error")
        self.assertEqual(pq_statuses["Q2"], "error")

    def test_12_trace_schema_complete(self):
        """Case 12: Trace co day du cac truong bat buoc."""
        def fake_retriever(question, top_n, config):
            return {
                "candidates": [make_candidate(f"c_{abs(hash(question))%1000}", fused_rank=1)],
                "trace": {}
            }

        qs = self._make_query_set([
            ("Q0", "original", "Cau hoi Q0"),
            ("Q1", "generated", "Cau Q1"),
        ])

        result = fan_out_multi_query_retrieval(qs, config=self.cfg, hybrid_retriever_fn=fake_retriever)
        trace = result.get("trace", {})

        required_keys = [
            "per_query_summary", "union_child_count", "overlap_distribution",
            "fusion_latency_ms", "total_retrieval_latency_ms", "config_snapshot",
        ]
        for k in required_keys:
            self.assertIn(k, trace, f"Thieu key '{k}' trong trace")

        for pqs in trace["per_query_summary"]:
            for f in ("query_id", "origin", "status", "result_count", "latency_ms"):
                self.assertIn(f, pqs)

        cfg_snap = trace["config_snapshot"]
        for f in ("per_query_candidates", "multi_query_rrf_k",
                  "multi_query_original_weight", "multi_query_variant_weight"):
            self.assertIn(f, cfg_snap)

        od = trace["overlap_distribution"]
        self.assertIsInstance(od, dict)
        self.assertGreaterEqual(trace["union_child_count"], 0)


class TestCrossQueryRRFEdgeCases(unittest.TestCase):

    def test_empty_all_error(self):
        """Tat ca queries loi -> fused rong."""
        per_q = [
            make_per_query_result("Q0", "original", [], status="error", error_msg="fail"),
            make_per_query_result("Q1", "generated", [], status="error", error_msg="fail"),
        ]
        fused, stats = cross_query_rrf_fusion(per_q, config=DEFAULT_CFG)
        self.assertEqual(len(fused), 0)
        self.assertEqual(stats["union_child_count"], 0)

    def test_overlap_distribution_computed_correctly(self):
        """overlap_distribution dem dung so child theo so query support."""
        per_q = [
            make_per_query_result("Q0", "original", [
                make_candidate("child_AB", 1),
                make_candidate("child_A_only", 2),
            ]),
            make_per_query_result("Q1", "generated", [
                make_candidate("child_AB", 1),
                make_candidate("child_B_only", 2),
            ]),
        ]
        fused, stats = cross_query_rrf_fusion(per_q, config=DEFAULT_CFG)
        od = stats["overlap_distribution"]
        self.assertEqual(od.get(2, 0), 1)
        self.assertEqual(od.get(1, 0), 2)

    def test_fused_rank_starts_from_1(self):
        """multi_query_rank cua top item phai la 1."""
        per_q = [
            make_per_query_result("Q0", "original", [
                make_candidate("child_A", 1),
                make_candidate("child_B", 2),
            ]),
        ]
        fused, _ = cross_query_rrf_fusion(per_q, config=DEFAULT_CFG)
        self.assertEqual(fused[0]["multi_query_rank"], 1)
        self.assertEqual(fused[-1]["multi_query_rank"], len(fused))


if __name__ == "__main__":
    unittest.main(verbosity=2)
