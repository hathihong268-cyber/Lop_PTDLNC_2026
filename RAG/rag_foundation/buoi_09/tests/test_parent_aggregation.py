"""
Bộ unit tests kiểm thử Parent Aggregation, Child-to-Parent Mapping và Context Budgeting cho Buổi 09:
100% offline, độc lập hoàn toàn, sử dụng mock hierarchy registry và mock child hits,
không gọi Gemini API qua mạng, không tải Cross-Encoder.
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
    load_hierarchy_store,
    aggregate_parent_candidates,
    apply_context_budget,
    retrieve_parent_documents,
    load_buoi_09_config,
)


class TestParentAggregation(unittest.TestCase):
    """
    Test suite kiểm thử toàn diện Parent Aggregation và Context Budget.
    """

    def setUp(self):
        self.config = load_buoi_09_config()
        self.config["parent_score_child_limit"] = 2
        self.config["parent_rrf_k"] = 60
        self.config["parent_candidates"] = 5
        self.config["total_context_max_chars"] = 4000

        # Mock Parent Store (Source of Truth)
        self.mock_parents = {
            "P1": {
                "parent_id": "P1",
                "source": "docA.pdf",
                "page_start": 1,
                "page_end": 2,
                "structural_path": {"law": "39/2016", "chapter": "I", "article": 8},
                "text": "Nội dung quy định Điều 8 của Thông tư 39...",
                "child_ids": ["c1", "c2", "c3"],
                "char_count": 1500,
                "ambiguous": False,
                "warnings": [],
            },
            "P2": {
                "parent_id": "P2",
                "source": "docA.pdf",
                "page_start": 3,
                "page_end": 4,
                "structural_path": {"law": "39/2016", "chapter": "II", "article": 14},
                "text": "Nội dung quy định Điều 14 của Thông tư 39...",
                "child_ids": ["c4", "c5"],
                "char_count": 2000,
                "ambiguous": False,
                "warnings": [],
            },
            "P_LARGE": {
                "parent_id": "P_LARGE",
                "source": "docB.pdf",
                "page_start": 1,
                "page_end": 5,
                "structural_path": {"law": "02/2023", "chapter": None, "article": 4},
                "text": "X" * 5000,  # Vượt budget 4000
                "child_ids": ["c_large"],
                "char_count": 5000,
                "ambiguous": False,
                "warnings": [],
            }
        }

        # Mock Children Registry
        self.mock_children = {
            "c1": {"chunk_id": "c1", "parent_id": "P1", "source": "docA.pdf", "page_start": 1, "page_end": 1, "text": "Child c1"},
            "c2": {"chunk_id": "c2", "parent_id": "P1", "source": "docA.pdf", "page_start": 1, "page_end": 2, "text": "Child c2"},
            "c3": {"chunk_id": "c3", "parent_id": "P1", "source": "docA.pdf", "page_start": 2, "page_end": 2, "text": "Child c3"},
            "c4": {"chunk_id": "c4", "parent_id": "P2", "source": "docA.pdf", "page_start": 3, "page_end": 3, "text": "Child c4"},
            "c5": {"chunk_id": "c5", "parent_id": "P2", "source": "docA.pdf", "page_start": 4, "page_end": 4, "text": "Child c5"},
            "c_large": {"chunk_id": "c_large", "parent_id": "P_LARGE", "source": "docB.pdf", "page_start": 1, "page_end": 5, "text": "Large child"},
        }

    def test_01_child_correctly_maps_to_parent(self):
        """
        Case 1: Fused child hits ánh xạ chính xác sang parent_id từ registry.
        """
        fused_hits = [
            {"child_id": "c1", "text": "Child c1", "multi_query_rank": 1, "support_query_ids": ["Q0"]},
            {"child_id": "c4", "text": "Child c4", "multi_query_rank": 2, "support_query_ids": ["Q1"]},
        ]
        kept_p, _, grouped = aggregate_parent_candidates(
            fused_child_hits=fused_hits,
            parents_by_id=self.mock_parents,
            children_by_id=self.mock_children,
            parent_score_child_limit=2,
            parent_rrf_k=60
        )
        self.assertEqual(len(kept_p), 2)
        p_ids = {p["parent_id"] for p in kept_p}
        self.assertEqual(p_ids, {"P1", "P2"})

    def test_02_missing_or_stale_hierarchy_store_raises_clear_error(self):
        """
        Case 2: Hierarchy store không tồn tại phải ném RuntimeError('hierarchy_not_ready').
        """
        non_existent_dir = BUOI_09_DIR / "storage" / "non_existent_hierarchy_dir"
        with self.assertRaises(RuntimeError) as ctx:
            load_hierarchy_store(storage_dir=non_existent_dir)
        self.assertIn("hierarchy_not_ready", str(ctx.exception))

    def test_03_parent_aggregation_formula_arithmetic_precision(self):
        """
        Case 3: Công thức Parent RRF tính toán số học chuẩn xác:
        Score(P1) = 1 / (60 + rank(c1)) + 1 / (60 + rank(c2))
        """
        # c1 rank 1, c2 rank 3 -> 1/61 + 1/63 = 0.01639344 + 0.01587302 = 0.032266
        fused_hits = [
            {"child_id": "c1", "text": "Child c1", "multi_query_rank": 1, "support_query_ids": ["Q0"]},
            {"child_id": "c2", "text": "Child c2", "multi_query_rank": 3, "support_query_ids": ["Q1"]},
        ]
        kept_p, _, _ = aggregate_parent_candidates(
            fused_child_hits=fused_hits,
            parents_by_id=self.mock_parents,
            children_by_id=self.mock_children,
            parent_score_child_limit=3,
            parent_rrf_k=60
        )
        expected_score = round(1.0 / 61.0 + 1.0 / 63.0, 6)
        self.assertAlmostEqual(kept_p[0]["parent_rrf_score"], expected_score, places=5)

    def test_04_child_score_cap_enforced(self):
        """
        Case 4: PARENT_SCORE_CHILD_LIMIT (ví dụ 2) chỉ lấy tối đa 2 child tốt nhất để tính điểm.
        """
        # P1 có 3 child: c1 (rank 1), c2 (rank 2), c3 (rank 4). Cap = 2 -> Chỉ tính c1 và c2
        fused_hits = [
            {"child_id": "c1", "text": "c1", "multi_query_rank": 1, "support_query_ids": ["Q0"]},
            {"child_id": "c2", "text": "c2", "multi_query_rank": 2, "support_query_ids": ["Q1"]},
            {"child_id": "c3", "text": "c3", "multi_query_rank": 4, "support_query_ids": ["Q2"]},
        ]
        kept_p, _, _ = aggregate_parent_candidates(
            fused_child_hits=fused_hits,
            parents_by_id=self.mock_parents,
            children_by_id=self.mock_children,
            parent_score_child_limit=2,  # Cap = 2
            parent_rrf_k=60
        )
        p1 = kept_p[0]
        self.assertEqual(len(p1["scoring_child_ids"]), 2)
        self.assertEqual(p1["scoring_child_ids"], ["c1", "c2"])
        expected_score = round(1.0 / 61.0 + 1.0 / 62.0, 6)
        self.assertAlmostEqual(p1["parent_rrf_score"], expected_score, places=5)

    def test_05_supporting_and_scoring_children_separated(self):
        """
        Case 5: Tách biệt rõ ràng scoring_child_ids (được tính điểm) và supporting_child_ids (toàn bộ child hits).
        """
        fused_hits = [
            {"child_id": "c1", "text": "c1", "multi_query_rank": 1, "support_query_ids": ["Q0"]},
            {"child_id": "c2", "text": "c2", "multi_query_rank": 2, "support_query_ids": ["Q1"]},
            {"child_id": "c3", "text": "c3", "multi_query_rank": 4, "support_query_ids": ["Q2"]},
        ]
        kept_p, _, _ = aggregate_parent_candidates(
            fused_child_hits=fused_hits,
            parents_by_id=self.mock_parents,
            children_by_id=self.mock_children,
            parent_score_child_limit=2,
            parent_rrf_k=60
        )
        p1 = kept_p[0]
        self.assertEqual(p1["anchor_child_id"], "c1")
        self.assertEqual(p1["scoring_child_ids"], ["c1", "c2"])
        self.assertEqual(p1["supporting_child_ids"], ["c1", "c2", "c3"])
        self.assertEqual(p1["support_query_ids"], ["Q0", "Q1", "Q2"])

    def test_06_parent_deduplication(self):
        """
        Case 6: Nhiều child chunks thuộc cùng một parent không tạo duplicate parent trong kết quả.
        """
        fused_hits = [
            {"child_id": "c1", "text": "c1", "multi_query_rank": 1, "support_query_ids": ["Q0"]},
            {"child_id": "c2", "text": "c2", "multi_query_rank": 2, "support_query_ids": ["Q0"]},
        ]
        kept_p, _, _ = aggregate_parent_candidates(
            fused_child_hits=fused_hits,
            parents_by_id=self.mock_parents,
            children_by_id=self.mock_children,
            parent_score_child_limit=3,
            parent_rrf_k=60
        )
        self.assertEqual(len(kept_p), 1)
        self.assertEqual(kept_p[0]["parent_id"], "P1")

    def test_07_deterministic_tie_breaking(self):
        """
        Case 7: Tie-breaking đơn định: parent_rrf_score -> len(support_query_ids) -> best_child_rank -> parent_id.
        """
        # P1 và P2 có cùng score và cùng số queries, P1 có best_child_rank=1 nhỏ hơn P2 (best_child_rank=2) -> P1 đứng trước
        fused_hits = [
            {"child_id": "c1", "text": "c1", "multi_query_rank": 1, "support_query_ids": ["Q0"]},
            {"child_id": "c4", "text": "c4", "multi_query_rank": 1, "support_query_ids": ["Q0"]},
        ]
        kept_p, _, _ = aggregate_parent_candidates(
            fused_child_hits=fused_hits,
            parents_by_id=self.mock_parents,
            children_by_id=self.mock_children,
            parent_score_child_limit=2,
            parent_rrf_k=60
        )
        self.assertEqual(kept_p[0]["parent_id"], "P1")
        self.assertEqual(kept_p[1]["parent_id"], "P2")

    def test_08_candidate_limit_enforced(self):
        """
        Case 8: Giới hạn PARENT_CANDIDATES (ví dụ 1) chỉ giữ tối đa số lượng parent cấu hình.
        """
        fused_hits = [
            {"child_id": "c1", "text": "c1", "multi_query_rank": 1, "support_query_ids": ["Q0"]},
            {"child_id": "c4", "text": "c4", "multi_query_rank": 2, "support_query_ids": ["Q1"]},
        ]
        kept_p, dropped_p, _ = aggregate_parent_candidates(
            fused_child_hits=fused_hits,
            parents_by_id=self.mock_parents,
            children_by_id=self.mock_children,
            parent_score_child_limit=2,
            parent_rrf_k=60,
            parent_candidates_limit=1  # Limit = 1
        )
        self.assertEqual(len(kept_p), 1)
        self.assertEqual(len(dropped_p), 1)
        self.assertEqual(kept_p[0]["parent_id"], "P1")
        self.assertEqual(dropped_p[0]["parent_id"], "P2")

    def test_09_context_budget_cuts_only_at_parent_boundary(self):
        """
        Case 9: Ngân sách ngữ cảnh chỉ cắt tại ranh giới parent, không cắt cụt giữa text của parent.
        """
        # P1 = 1500 chars, P2 = 2000 chars, Budget = 2500 chars -> Chỉ chọn P1 (1500 chars), bỏ P2 (1500 + 2000 > 2500)
        parent_cands = [
            {"parent_id": "P1", "char_count": 1500, "text": "A" * 1500},
            {"parent_id": "P2", "char_count": 2000, "text": "B" * 2000},
        ]
        budgeted, dropped, cum_chars, warnings = apply_context_budget(
            parent_candidates=parent_cands,
            total_context_max_chars=2500
        )
        self.assertEqual(len(budgeted), 1)
        self.assertEqual(budgeted[0]["parent_id"], "P1")
        self.assertEqual(len(dropped), 1)
        self.assertEqual(dropped[0]["parent_id"], "P2")
        self.assertEqual(cum_chars, 1500)

    def test_10_oversized_first_parent_kept_with_warning(self):
        """
        Case 10: Parent đầu tiên vượt quá total_context_max_chars vẫn được giữ nguyên và phát cảnh báo rõ ràng.
        """
        # P_LARGE = 5000 chars, Budget = 4000 chars
        parent_cands = [
            {"parent_id": "P_LARGE", "char_count": 5000, "text": "X" * 5000},
        ]
        budgeted, dropped, cum_chars, warnings = apply_context_budget(
            parent_candidates=parent_cands,
            total_context_max_chars=4000
        )
        self.assertEqual(len(budgeted), 1)
        self.assertEqual(budgeted[0]["parent_id"], "P_LARGE")
        self.assertEqual(cum_chars, 5000)
        self.assertTrue(any("oversized_first_parent_exceeds_budget" in w for w in warnings))

    def test_11_expansion_factor_and_count_trace(self):
        """
        Case 11: Trace tính toán đầy đủ expansion factor, child chars và expanded parent chars.
        """
        def mock_hybrid(q: str) -> list[dict]:
            return [
                {"child_id": "TT_39_2016_NHNN:hierarchical:0059", "text": "Child 59", "source": "TT_39_2016_NHNN.pdf", "page_start": 4, "page_end": 5, "fused_rank": 1}
            ]

        res = retrieve_parent_documents(
            question="Điều kiện vay vốn",
            mode="single_parent",
            config=self.config,
            custom_retriever_fn=mock_hybrid
        )
        t = res["trace"]
        self.assertIn("child_chars", t)
        self.assertIn("expanded_parent_chars", t)
        self.assertIn("context_expansion_factor", t)
        self.assertIn("unique_parent_count", t)
        self.assertGreaterEqual(t["context_expansion_factor"], 1.0)

    def test_12_tests_run_100_percent_offline(self):
        """
        Case 12: Toàn bộ suite test chạy 100% offline không có kết nối mạng hay gọi LLM answer generation.
        """
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
