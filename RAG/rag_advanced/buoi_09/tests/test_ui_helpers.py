"""
Unit tests for UI helper functions in rag_advanced/buoi_09/app.py.

Coverage:
- build_query_child_matrix        — Ma tran query-child (Q0..Qn x child chunks)
- build_mode_comparison_row       — Hang bang mode comparison cho 4 modes
- build_parent_tree_data          — Du lieu cay parent-child va rank movements
- format_citation                 — Format trich dan theo contract Buoi 09
- map_error_status                — Mapping loi than thien khong leak stack trace

Tat ca tests la thuan Python: khong can browser, khong goi API/model.
"""

import sys
import unittest
from pathlib import Path
import pandas as pd

# Them root workspace vao sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from rag_advanced.buoi_09.app import (
    build_query_child_matrix,
    build_mode_comparison_row,
    build_parent_tree_data,
    format_citation,
    map_error_status,
)


class TestBuildQueryChildMatrix(unittest.TestCase):
    """Kiem tra ma tran Query - Child."""

    def setUp(self):
        self.per_query_results = [
            {
                "query_id": "Q0",
                "candidates": [
                    {"child_id": "c1", "score": 0.9},
                    {"child_id": "c2", "score": 0.8},
                    {"child_id": "c3", "score": 0.7},
                ],
            },
            {
                "query_id": "Q1",
                "candidates": [
                    {"child_id": "c2", "score": 0.95},
                    {"child_id": "c4", "score": 0.85},
                ],
            },
            {
                "query_id": "Q2",
                "candidates": [
                    {"child_id": "c1", "score": 0.9},
                    {"child_id": "c2", "score": 0.88},
                ],
            },
        ]
        self.fused_children = [
            {
                "child_id": "c2",
                "cross_query_rrf_score": 0.0456,
                "support_query_ids": ["Q0", "Q1", "Q2"],
            },
            {
                "child_id": "c1",
                "cross_query_rrf_score": 0.0312,
                "support_query_ids": ["Q0", "Q2"],
            },
            {
                "child_id": "c4",
                "cross_query_rrf_score": 0.0150,
                "support_query_ids": ["Q1"],
            },
            {
                "child_id": "c3",
                "cross_query_rrf_score": 0.0120,
                "support_query_ids": ["Q0"],
            },
        ]

    def test_matrix_structure_and_columns(self):
        df = build_query_child_matrix(self.per_query_results, self.fused_children)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 4)
        expected_cols = ["Child ID", "MQ Rank", "Support Q#", "MQ-RRF Score", "Q0", "Q1", "Q2"]
        for col in expected_cols:
            self.assertIn(col, df.columns)

    def test_ranks_in_matrix(self):
        df = build_query_child_matrix(self.per_query_results, self.fused_children)
        # c2 la hang dau tien (MQ Rank 1)
        row_c2 = df[df["Child ID"] == "c2"].iloc[0]
        self.assertEqual(row_c2["Q0"], 2)  # c2 rank 2 in Q0
        self.assertEqual(row_c2["Q1"], 1)  # c2 rank 1 in Q1
        self.assertEqual(row_c2["Q2"], 2)  # c2 rank 2 in Q2
        self.assertEqual(row_c2["Support Q#"], 3)

        # c4 chi xuat hien trong Q1 (rank 2)
        row_c4 = df[df["Child ID"] == "c4"].iloc[0]
        self.assertTrue(pd.isna(row_c4["Q0"]) or row_c4["Q0"] is None)
        self.assertEqual(row_c4["Q1"], 2)
        self.assertTrue(pd.isna(row_c4["Q2"]) or row_c4["Q2"] is None)

    def test_empty_inputs(self):
        df = build_query_child_matrix([], [])
        self.assertTrue(df.empty)

        df_empty_fused = build_query_child_matrix(self.per_query_results, [])
        self.assertTrue(df_empty_fused.empty)


class TestBuildModeComparisonRow(unittest.TestCase):
    """Kiem tra tao row so sanh 4 modes."""

    def test_parent_mode_row(self):
        result = {
            "status": "answered",
            "parents": [
                {"parent_id": "p1", "source": "doc1.pdf", "text": "Parent 1 text 100 chars " * 5},
                {"parent_id": "p2", "source": "doc2.pdf", "text": "Parent 2 text 100 chars " * 5},
            ],
            "fused_children": [{"child_id": "c1"}, {"child_id": "c2"}, {"child_id": "c3"}],
            "trace": {
                "total_context_chars": 1000,
                "input_child_hit_count": 3,
                "context_expansion_factor": 3.33,
            },
            "latency_ms": 250.5,
            "generation_call_count": 1,
            "embedding_call_count": 3,
            "warnings": [],
        }
        row = build_mode_comparison_row("multi_parent", result)

        self.assertEqual(row["Mode"], "multi_parent")
        self.assertEqual(row["Status"], "answered")
        self.assertEqual(row["Unit Type"], "parent")
        self.assertEqual(row["Evidence IDs"], ["p1", "p2"])
        self.assertEqual(row["Evidence Count"], 2)
        self.assertEqual(row["Child Count"], 3)
        self.assertEqual(row["Parent Count"], 2)
        self.assertEqual(row["Context Chars"], 1000)
        self.assertEqual(row["Expansion Factor"], 3.33)
        self.assertEqual(row["Generation Calls"], 1)
        self.assertEqual(row["Embedding Calls"], 3)
        self.assertEqual(row["Latency (ms)"], 250.5)

    def test_flat_mode_row(self):
        result = {
            "status": "retrieval_only",
            "parents": [],
            "fused_children": [
                {"child_id": "c1", "source": "doc1.pdf", "text": "Chunk 1 content"},
                {"child_id": "c2", "source": "doc1.pdf", "text": "Chunk 2 content"},
            ],
            "latency_ms": 120.0,
            "generation_call_count": 0,
            "embedding_call_count": 1,
            "warnings": ["no_parent_expansion"],
        }
        row = build_mode_comparison_row("single_flat", result)

        self.assertEqual(row["Mode"], "single_flat")
        self.assertEqual(row["Unit Type"], "child")
        self.assertEqual(row["Evidence IDs"], ["c1", "c2"])
        self.assertEqual(row["Child Count"], 2)
        self.assertEqual(row["Parent Count"], 0)
        self.assertEqual(row["Expansion Factor"], 1.0)
        self.assertEqual(row["Unique Sources"], 1)
        self.assertIn("no_parent_expansion", row["Warnings"])


class TestBuildParentTreeData(unittest.TestCase):
    """Kiem tra du lieu cay parent-child va rank movements."""

    def test_tree_construction_with_rerank_movement(self):
        parents = [
            {
                "parent_id": "doc1::dieu_5",
                "source": "doc1.pdf",
                "structural_path": {"chapter": "Chuong I", "article": "Dieu 5"},
                "page_start": 3,
                "page_end": 4,
                "parent_rank": 3,
                "rerank_rank": 1,
                "parent_rrf_score": 0.035,
                "rerank_score": 0.89,
                "supporting_child_ids": ["c1", "c2"],
                "accepted": True,
                "ambiguous": False,
                "text": "Noi dung Dieu 5...",
            },
            {
                "parent_id": "doc1::dieu_2",
                "source": "doc1.pdf",
                "structural_path": {"chapter": "Chuong I", "article": "Dieu 2"},
                "page_start": 1,
                "page_end": 2,
                "parent_rank": 1,
                "rerank_rank": 2,
                "parent_rrf_score": 0.048,
                "rerank_score": 0.72,
                "supporting_child_ids": ["c3"],
                "accepted": True,
                "ambiguous": True,
                "text": "Noi dung Dieu 2...",
            }
        ]
        children_by_id = {
            "c1": {"text": "Doan 1 cua dieu 5"},
            "c2": {"text": "Doan 2 cua dieu 5"},
            "c3": {"text": "Doan 1 cua dieu 2"},
        }

        tree = build_parent_tree_data(parents, children_by_id)
        self.assertEqual(len(tree), 2)

        # Kiem tra parent 1: rank truoc 3, rerank 1 => rank_change = 3 - 1 = +2
        p1 = tree[0]
        self.assertEqual(p1["parent_id"], "doc1::dieu_5")
        self.assertEqual(p1["parent_rank"], 3)
        self.assertEqual(p1["rerank_rank"], 1)
        self.assertEqual(p1["rank_change"], 2)
        self.assertEqual(p1["article"], "Dieu 5")
        self.assertEqual(len(p1["supporting_children"]), 2)
        self.assertEqual(p1["supporting_children"][0]["anchor_snippet"], "Doan 1 cua dieu 5")
        self.assertFalse(p1["ambiguous"])

        # Kiem tra parent 2: rank truoc 1, rerank 2 => rank_change = 1 - 2 = -1
        p2 = tree[1]
        self.assertEqual(p2["parent_rank"], 1)
        self.assertEqual(p2["rerank_rank"], 2)
        self.assertEqual(p2["rank_change"], -1)
        self.assertTrue(p2["ambiguous"])


class TestFormatCitation(unittest.TestCase):
    """Kiem tra dinh dang trich dan theo dung contract."""

    def test_format_citation_standard(self):
        parent = {
            "parent_id": "TT39_2016::Dieu_2",
            "source": "TT39_2016.pdf",
            "title": "Dieu 2: Pham vi dieu chinh",
            "page_start": 2,
            "page_end": 3,
            "supporting_child_ids": ["c1", "c2"],
        }
        res = format_citation(parent, 1)
        self.assertEqual(res["label"], "[E1]")
        self.assertIn("[Nguon: TT39_2016.pdf, Dieu 2: Pham vi dieu chinh, tr. 2-3", res["citation"])
        self.assertIn("cac chunks kich hoat: c1, c2", res["citation"])

    def test_format_citation_many_children(self):
        parent = {
            "parent_id": "doc::art_1",
            "source": "doc.pdf",
            "title": "Dieu 1",
            "page_start": 1,
            "page_end": 1,
            "supporting_child_ids": ["c1", "c2", "c3", "c4", "c5", "c6"],
        }
        res = format_citation(parent, 2)
        self.assertEqual(res["label"], "[E2]")
        self.assertIn("c1, c2, c3, c4, ... (+2)", res["citation"])


class TestMapErrorStatus(unittest.TestCase):
    """Kiem tra mapping loi khong leak stack trace va co huong dan ro rang."""

    def test_known_statuses(self):
        for status in [
            "hierarchy_not_ready",
            "collection_not_ready",
            "query_generation_unavailable",
            "multi_query_partial",
            "reranker_unavailable",
            "insufficient_evidence",
            "generation_error",
        ]:
            info = map_error_status(status)
            self.assertIn("icon", info)
            self.assertIn("title", info)
            self.assertIn("guidance", info)
            self.assertIn("severity", info)
            self.assertGreater(len(info["guidance"]), 0, f"Status {status} missing guidance")
            # Khong leak stack trace
            self.assertNotIn("Traceback", info["guidance"])
            self.assertNotIn("File \"", info["guidance"])

    def test_unknown_status(self):
        info = map_error_status("some_random_status")
        self.assertEqual(info["title"], "some_random_status")
        self.assertEqual(info["severity"], "info")


if __name__ == "__main__":
    unittest.main()
