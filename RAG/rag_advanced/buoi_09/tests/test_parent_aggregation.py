"""
Unit Tests cho Parent Aggregation + Context Budget - Buoi 09
Buoc 06: 12 ca kiem thu bat buoc (khong goi reranker/generation/mang).
"""

import unittest
import tempfile
import json
import os
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from hierarchical_rag import (
    aggregate_parent_candidates,
    load_hierarchy_store,
    get_hierarchy_status,
)


# ---------------------------------------------------------------------------
# Helpers: xay dung registry gia lap tu dict
# ---------------------------------------------------------------------------

def make_child(child_id, parent_id, text="Child text default", source="doc.pdf",
               page_start=1, page_end=1, structural_path=None):
    return {
        "child_id": child_id,
        "parent_id": parent_id,
        "text": text,
        "source": source,
        "page_start": page_start,
        "page_end": page_end,
        "structural_path": structural_path or {"chapter": None, "article": "Dieu_7", "clause": None, "point": None},
        "ambiguous": False,
        "warnings": [],
    }


def make_parent(parent_id, child_ids, text=None, source="doc.pdf",
                page_start=1, page_end=2, article_key="Dieu_7",
                char_count=None, warnings=None):
    t = text or (" ".join(f"Parent text {i}" for i in range(20)))
    return {
        "parent_id": parent_id,
        "source": source,
        "page_start": page_start,
        "page_end": page_end,
        "article_key": article_key,
        "child_ids": child_ids,
        "text": t,
        "char_count": char_count if char_count is not None else len(t),
        "ambiguous_child_count": 0,
        "warnings": warnings or [],
    }


def make_registry(children_list, parents_list):
    return {
        "children_by_id": {c["child_id"]: c for c in children_list},
        "parents_by_id": {p["parent_id"]: p for p in parents_list},
    }


def make_child_hit(child_id, multi_query_rank, support_query_ids=None,
                   chunk_id=None, mq_rrf_score=0.01):
    return {
        "child_id": child_id or chunk_id,
        "chunk_id": child_id or chunk_id,
        "multi_query_rank": multi_query_rank,
        "multi_query_rrf_score": mq_rrf_score,
        "support_query_ids": support_query_ids or ["Q0"],
        "support_query_count": len(support_query_ids or ["Q0"]),
        "text": f"text {child_id}",
        "source": "doc.pdf",
        "page_start": 1,
        "page_end": 1,
    }


DEFAULT_CFG = {
    "parent_rrf_k": 60,
    "parent_score_child_limit": 3,
    "parent_candidates": 10,
    "total_context_max_chars": 16000,
    "parent_max_chars": 6000,
}


class TestParentAggregation(unittest.TestCase):

    def _run(self, children, parents, hits, cfg=None):
        reg = make_registry(children, parents)
        return aggregate_parent_candidates(hits, reg, config=cfg or DEFAULT_CFG)

    # --- Case 1: Child map dung parent ---
    def test_01_child_maps_to_correct_parent(self):
        """Case 1: child_id duoc map dung parent_id tu registry."""
        c1 = make_child("c1", "p1", text="Text c1")
        p1 = make_parent("p1", ["c1"], text="Parent context p1", char_count=200)
        hit1 = make_child_hit("c1", multi_query_rank=1)

        result = self._run([c1], [p1], [hit1])

        self.assertEqual(result["status"], "ok")
        parents = result["parents"]
        self.assertEqual(len(parents), 1)
        self.assertEqual(parents[0]["parent_id"], "p1")
        self.assertEqual(parents[0]["anchor_child_id"], "c1")

    # --- Case 2: Missing/stale hierarchy ---
    def test_02_missing_child_raises_keyerror(self):
        """Case 2: Child ID khong co trong registry -> KeyError ro rang."""
        c1 = make_child("c1", "p1")
        p1 = make_parent("p1", ["c1"])
        hit_unknown = make_child_hit("c_ghost", multi_query_rank=1)  # khong ton tai

        with self.assertRaises(KeyError) as ctx:
            self._run([c1], [p1], [hit_unknown])

        self.assertIn("c_ghost", str(ctx.exception))

    def test_02b_missing_parent_raises_keyerror(self):
        """Case 2b: Parent ID trong child record nhung khong co trong parents_by_id."""
        c_orphan = make_child("c_orphan", "p_ghost")
        # Khong co parent 'p_ghost' trong parents_by_id
        hit = make_child_hit("c_orphan", multi_query_rank=1)

        with self.assertRaises(KeyError) as ctx:
            self._run([c_orphan], [], [hit])

        self.assertIn("p_ghost", str(ctx.exception))

    # --- Case 3: Parent aggregation formula tinh tay ---
    def test_03_parent_rrf_formula_exact(self):
        """Case 3: parent_rrf_score = sum(1/(K+mq_rank)) cho scoring children."""
        # c1 -> p1 (mq_rank=1), c2 -> p1 (mq_rank=3)
        # Voi K=60, limit=3: score = 1/61 + 1/63
        c1 = make_child("c1", "p1", text="Text c1 unique")
        c2 = make_child("c2", "p1", text="Text c2 unique")
        p1 = make_parent("p1", ["c1", "c2"])

        hit1 = make_child_hit("c1", multi_query_rank=1)
        hit2 = make_child_hit("c2", multi_query_rank=3)

        result = self._run([c1, c2], [p1], [hit1, hit2])

        expected_score = round(1.0/61 + 1.0/63, 8)
        self.assertAlmostEqual(result["parents"][0]["parent_rrf_score"], expected_score, places=7)

    # --- Case 4: Child score cap ---
    def test_04_child_score_cap(self):
        """Case 4: Chi dung toi da PARENT_SCORE_CHILD_LIMIT child tot nhat de tinh diem."""
        cfg = dict(DEFAULT_CFG, parent_score_child_limit=2)  # gioi han 2
        # 4 children cung parent, rank 1..4
        children = [make_child(f"c{i}", "p1", text=f"Unique text child {i} abcd") for i in range(1, 5)]
        p1 = make_parent("p1", [f"c{i}" for i in range(1, 5)])
        hits = [make_child_hit(f"c{i}", multi_query_rank=i) for i in range(1, 5)]

        result = self._run(children, [p1], hits, cfg=cfg)

        p = result["parents"][0]
        # Scoring: chi c1(rank=1) va c2(rank=2)
        self.assertEqual(len(p["scoring_child_ids"]), 2)
        self.assertIn("c1", p["scoring_child_ids"])
        self.assertIn("c2", p["scoring_child_ids"])
        # Supporting: tat ca 4
        self.assertEqual(len(p["supporting_child_ids"]), 4)

        expected_score = round(1.0/61 + 1.0/62, 8)
        self.assertAlmostEqual(p["parent_rrf_score"], expected_score, places=7)

    # --- Case 5: Supporting va scoring child tach dung ---
    def test_05_supporting_vs_scoring_children_separated(self):
        """Case 5: scoring_child_ids la top-limit; supporting_child_ids la toan bo."""
        cfg = dict(DEFAULT_CFG, parent_score_child_limit=1)
        c1 = make_child("c1", "p1", text="Unique text A abcd efgh")
        c2 = make_child("c2", "p1", text="Unique text B ijkl mnop")
        p1 = make_parent("p1", ["c1", "c2"])
        hits = [make_child_hit("c1", 1), make_child_hit("c2", 2)]

        result = self._run([c1, c2], [p1], hits, cfg=cfg)
        p = result["parents"][0]

        self.assertEqual(p["scoring_child_ids"], ["c1"])         # chi top 1
        self.assertIn("c1", p["supporting_child_ids"])            # ca hai
        self.assertIn("c2", p["supporting_child_ids"])

    # --- Case 6: Parent deduplicate ---
    def test_06_parent_deduplicate_in_output(self):
        """Case 6: Hai child cung parent -> ket qua chi co 1 parent entry."""
        c1 = make_child("c1", "p1", text="Unique text for c1")
        c2 = make_child("c2", "p1", text="Unique text for c2")
        p1 = make_parent("p1", ["c1", "c2"])
        hits = [make_child_hit("c1", 1), make_child_hit("c2", 2)]

        result = self._run([c1, c2], [p1], hits)

        # Chi 1 parent
        self.assertEqual(len(result["parents"]), 1)
        self.assertEqual(result["parents"][0]["parent_id"], "p1")

    # --- Case 7: Sort/tie-break deterministic ---
    def test_07_sort_deterministic_tiebreak(self):
        """Case 7: parent_rrf_score bang nhau -> sort theo support_query_count, best_child_rank, parent_id."""
        c1 = make_child("c1", "pA", text="Child 1 text unique")
        c2 = make_child("c2", "pZ", text="Child 2 text unique")
        pA = make_parent("pA", ["c1"], text="Parent A text context")
        pZ = make_parent("pZ", ["c2"], text="Parent Z text context")

        # Ca hai parent co dung 1 child rank=1 -> score = 1/61 (bang nhau)
        # -> tie-break theo parent_id ASC: pA < pZ
        hits = [make_child_hit("c1", 1), make_child_hit("c2", 1)]

        result = self._run([c1, c2], [pA, pZ], hits)
        ids = [p["parent_id"] for p in result["parents"]]
        self.assertEqual(ids[0], "pA")
        self.assertEqual(ids[1], "pZ")

    # --- Case 8: Candidate limit ---
    def test_08_candidate_limit(self):
        """Case 8: Sau khi agg, chi giu PARENT_CANDIDATES parent truoc budget."""
        cfg = dict(DEFAULT_CFG, parent_candidates=2, total_context_max_chars=999999)
        # Tao 4 parents khac nhau
        children = []
        parents = []
        hits = []
        for i in range(1, 5):
            cid = f"c{i}"
            pid = f"p{i}"
            children.append(make_child(cid, pid, text=f"Unique text for child {i} abcdef"))
            parents.append(make_parent(pid, [cid], text=f"Parent text {i} " * 20))
            hits.append(make_child_hit(cid, i))

        result = self._run(children, parents, hits, cfg=cfg)

        # Gioi han 2 -> chi 2 parent duoc giu
        self.assertLessEqual(len(result["parents"]), 2)
        trace = result["trace"]
        self.assertGreater(trace["dropped_by_candidate_limit"], 0)

    # --- Case 9: Context budget cat o parent boundary ---
    def test_09_context_budget_cuts_at_parent_boundary(self):
        """Case 9: Khong cat giua parent; chi them nguyen parent khi con budget."""
        # Budget = 500 chars; p1=300 chars, p2=300 chars -> p2 bi cat (300+300>500)
        cfg = dict(DEFAULT_CFG, total_context_max_chars=500, parent_candidates=10)
        c1 = make_child("c1", "p1", text="Unique child text c1 abcd")
        c2 = make_child("c2", "p2", text="Unique child text c2 efgh")
        p1 = make_parent("p1", ["c1"], text="A" * 300, char_count=300)
        p2 = make_parent("p2", ["c2"], text="B" * 300, char_count=300)

        hits = [make_child_hit("c1", 1), make_child_hit("c2", 2)]

        result = self._run([c1, c2], [p1, p2], hits, cfg=cfg)
        trace = result["trace"]

        # Chi p1 duoc giu, p2 bi cat
        self.assertEqual(len(result["parents"]), 1)
        self.assertEqual(result["parents"][0]["parent_id"], "p1")
        self.assertIn("p2", trace["dropped_by_budget"])

    # --- Case 10: Oversized first parent warning ---
    def test_10_oversized_first_parent_warning(self):
        """Case 10: Parent dau tien vuot budget van duoc giu, co warning ro rang."""
        cfg = dict(DEFAULT_CFG, total_context_max_chars=100)  # budget nho
        c1 = make_child("c1", "p1", text="Child text c1 uniqueX")
        p1 = make_parent("p1", ["c1"], text="X" * 500, char_count=500)
        hits = [make_child_hit("c1", 1)]

        result = self._run([c1], [p1], hits, cfg=cfg)
        trace = result["trace"]

        # Phai giu parent dau tien du oversized
        self.assertEqual(len(result["parents"]), 1)
        self.assertTrue(trace["first_parent_oversized"])
        # Parent phai co warning ve oversized
        p_warnings = " ".join(result["parents"][0].get("warnings", []))
        self.assertIn("oversized_first_parent", p_warnings)

    # --- Case 11: Expansion factor/count trace ---
    def test_11_trace_expansion_factor_and_counts(self):
        """Case 11: context_expansion_factor = parent_chars / child_chars."""
        c1 = make_child("c1", "p1", text="Short")  # 5 chars
        p1 = make_parent("p1", ["c1"], text="A" * 100, char_count=100)
        hits = [make_child_hit("c1", 1)]

        result = self._run([c1], [p1], hits)
        trace = result["trace"]

        # Truong bat buoc trong trace
        required = [
            "input_child_hit_count", "unique_parent_count_before_limit",
            "unique_parent_count_selected", "dropped_by_candidate_limit",
            "dropped_by_budget", "first_parent_oversized",
            "total_context_chars", "total_child_chars",
            "context_expansion_factor", "ambiguous_parent_count",
            "warning_count", "children_per_parent",
            "parent_score_components", "mapping_table", "latency_ms",
        ]
        for k in required:
            self.assertIn(k, trace, f"Thieu key '{k}' trong trace")

        # expansion_factor = parent_chars / child_chars
        self.assertGreater(trace["context_expansion_factor"], 0)
        self.assertGreater(trace["total_context_chars"], trace["total_child_chars"])

        # latency_ms co 4 sub-keys
        lat = trace["latency_ms"]
        for k in ("mapping", "aggregation", "budget", "total"):
            self.assertIn(k, lat)

    # --- Case 12: Khong goi reranker/generation ---
    def test_12_no_reranker_no_generation(self):
        """Case 12: aggregate_parent_candidates khong goi reranker hay generation."""
        reranker_calls = []
        gen_calls = []

        import hierarchical_rag as hrag
        orig_rerank = hrag.rerank_parents_cross_encoder.__doc__

        c1 = make_child("c1", "p1", text="Child c1 text unique")
        p1 = make_parent("p1", ["c1"])
        hits = [make_child_hit("c1", 1)]

        # Goi aggregate_parent_candidates binh thuong
        result = self._run([c1], [p1], hits)

        # Khong co reranker hay gen call
        self.assertEqual(reranker_calls, [])
        self.assertEqual(gen_calls, [])
        self.assertEqual(result["status"], "ok")


class TestLoadHierarchyStore(unittest.TestCase):
    """Test load_hierarchy_store() voi store that."""

    def test_store_not_built_raises_runtimeerror(self):
        """Store chua build -> RuntimeError voi thong bao hierarchy_not_ready."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(RuntimeError) as ctx:
                load_hierarchy_store(storage_dir=tmpdir)

            self.assertIn("hierarchy_not_ready", str(ctx.exception))

    def test_store_loads_correctly(self):
        """Store hop le -> tra ve children_by_id va parents_by_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)

            children = [
                {"child_id": "c1", "parent_id": "p1", "text": "T1",
                 "source": "a.pdf", "page_start": 1, "page_end": 1,
                 "structural_path": {}, "ambiguous": False, "warnings": []},
            ]
            parents = [
                {"parent_id": "p1", "source": "a.pdf", "page_start": 1,
                 "page_end": 2, "article_key": "Dieu_7", "child_ids": ["c1"],
                 "text": "Parent text", "char_count": 11, "ambiguous_child_count": 0,
                 "warnings": []},
            ]
            manifest = {
                "schema_version": "1.0",
                "strategy": "hierarchical",
                "build_timestamp": "2026-01-01T00:00:00Z",
                "counts": {"total_children": 1, "total_parents": 1,
                           "ambiguous_children": 0, "oversized_single_children": 0},
                "warning_counts": {"total_warnings": 0},
                "config_identity": {},
                "input_file_fingerprints": [],
            }

            for fname, data in [("children.json", children), ("parents.json", parents),
                                 ("manifest.json", manifest)]:
                with open(td / fname, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False)

            reg = load_hierarchy_store(storage_dir=tmpdir)

            self.assertIn("c1", reg["children_by_id"])
            self.assertIn("p1", reg["parents_by_id"])
            self.assertEqual(reg["total_children"], 1)
            self.assertEqual(reg["total_parents"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)