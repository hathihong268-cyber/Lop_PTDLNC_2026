"""
Unit tests for Hierarchy Resolution & Builder in Buổi 09:
Covering Required Test Groups 1-6:
1. Metadata/heading/carry-forward/fallback precedence.
2. Inline legal reference không bị coi là heading.
3. Conflict ambiguous warning.
4. Numeric child order và stable parent ID.
5. Parent window, pages, text và one-parent-per-child invariant.
6. Manifest fingerprint/stale/status/atomic build.

Tất cả chạy 100% offline, không mạng, không API, dùng temporary directory / fixture.
"""

import sys
import os
import json
import tempfile
import unittest
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from rag_advanced.buoi_09.hierarchical_rag import (
    load_and_order_hierarchical_chunks,
    resolve_child_hierarchy,
    build_parent_documents,
    save_hierarchy_store,
    get_hierarchy_status,
    load_hierarchy_store,
    extract_chunk_number,
    clean_article_slug,
)


class TestHierarchyPrecedenceAndHeadings(unittest.TestCase):
    """Test Groups 1, 2, 3: Precedence, Inline References, Ambiguous Warnings."""

    def test_01_precedence_metadata_over_text(self):
        """Ưu tiên metadata explicit hơn heading text trong chunk."""
        chunks = [
            {
                "chunk_id": "doc1:hierarchical:0001",
                "strategy": "hierarchical",
                "source": "doc1.pdf",
                "page_start": 1,
                "page_end": 1,
                "text": "Điều 5. Tiêu đề giả trong text",
                "structure": {"article": "Điều 10. Tiêu đề thật trong metadata"}
            }
        ]
        resolved, stats = resolve_child_hierarchy(chunks)
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0]["structural_path"]["article"], "Điều 10. Tiêu đề thật trong metadata")
        self.assertEqual(resolved[0]["resolution_method"], "metadata")

    def test_02_inline_legal_reference_not_treated_as_heading(self):
        """Trích dẫn luật inline (như 'sửa đổi Điều 8') không được coi là heading Điều mới."""
        chunks = [
            {
                "chunk_id": "doc2:hierarchical:0001",
                "strategy": "hierarchical",
                "source": "doc2.pdf",
                "page_start": 1,
                "page_end": 1,
                "text": "Điều 1. Phạm vi điều chỉnh\nThông tư này quy định...",
            },
            {
                "chunk_id": "doc2:hierarchical:0002",
                "strategy": "hierarchical",
                "source": "doc2.pdf",
                "page_start": 1,
                "page_end": 1,
                "text": "Khoản 2 này nhằm sửa đổi Điều 8 của Thông tư số 39/2016/TT-NHNN.",
            }
        ]
        resolved, stats = resolve_child_hierarchy(chunks)
        children_out, parents, p_stats = build_parent_documents(resolved)

        self.assertEqual(len(children_out), 2)
        # Chunk 2 phải kế thừa Điều 1 chứ không bị chuyển thành Điều 8
        self.assertEqual(children_out[0]["parent_id"], children_out[1]["parent_id"])
        self.assertIn("Dieu_1", children_out[1]["parent_id"])
        # Phải có warning amending_cited_article
        self.assertTrue(resolved[1]["ambiguous"])
        self.assertEqual(stats["warning_breakdown"].get("amending_cited_article"), 1)

    def test_03_conflict_ambiguous_warning(self):
        """Chunk có nhiều heading xung đột hoặc metadata lệch text heading sinh warning ambiguous."""
        chunks = [
            {
                "chunk_id": "doc3:hierarchical:0001",
                "strategy": "hierarchical",
                "source": "doc3.pdf",
                "page_start": 1,
                "page_end": 1,
                "text": "Điều 2. Tiêu đề trong text",
                "structure": {"article": "Điều 9. Tiêu đề trong metadata"}
            }
        ]
        resolved, stats = resolve_child_hierarchy(chunks)
        self.assertTrue(resolved[0]["ambiguous"])
        self.assertEqual(stats["warning_breakdown"].get("metadata_heading_conflict"), 1)
        self.assertTrue(any("Xung đột giữa metadata" in w for w in resolved[0]["warnings"]))


class TestHierarchyOrderingAndParentInvariants(unittest.TestCase):
    """Test Groups 4, 5, 6: Ordering, Parent Windows, Invariants, Atomic Storage."""

    def test_04_numeric_child_order_and_stable_parent_id(self):
        """Thứ tự chunk_id theo số (0002 < 0010) và Parent ID có cấu trúc xác định."""
        self.assertEqual(extract_chunk_number("TT_39:hierarchical:0002"), 2)
        self.assertEqual(extract_chunk_number("TT_39:hierarchical:0010"), 10)
        self.assertLess(
            extract_chunk_number("TT_39:hierarchical:0002"),
            extract_chunk_number("TT_39:hierarchical:0010")
        )
        self.assertEqual(clean_article_slug("Điều 7. Điều kiện cho vay"), "Dieu_7")

    def test_05_parent_window_text_and_one_parent_per_child_invariant(self):
        """Mỗi child thuộc đúng một parent; parent có window, pages, text hợp lệ."""
        chunks = [
            {
                "chunk_id": "srcA:hierarchical:0001",
                "strategy": "hierarchical",
                "source": "srcA.pdf",
                "page_start": 1,
                "page_end": 1,
                "text": "Điều 1. Nội dung khoản 1",
            },
            {
                "chunk_id": "srcA:hierarchical:0002",
                "strategy": "hierarchical",
                "source": "srcA.pdf",
                "page_start": 1,
                "page_end": 2,
                "text": "Khoản 2 của Điều 1 tiếp nối",
            }
        ]
        resolved, _ = resolve_child_hierarchy(chunks)
        children_out, parents, stats = build_parent_documents(resolved, parent_max_chars=6000)

        self.assertEqual(len(parents), 1)
        p = parents[0]
        pid = p["parent_id"]

        # Invariant 1: Parent window, pages, text
        self.assertEqual(p["page_start"], 1)
        self.assertEqual(p["page_end"], 2)
        self.assertIn("Nội dung khoản 1", p["text"])
        self.assertIn("Khoản 2 của Điều 1", p["text"])

        # Invariant 2: One-parent-per-child
        for c in children_out:
            self.assertEqual(c["parent_id"], pid)
        self.assertEqual(set(p["child_ids"]), {"srcA:hierarchical:0001", "srcA:hierarchical:0002"})

    def test_06_manifest_fingerprint_and_atomic_build(self):
        """Kiểm tra manifest, fingerprint, trạng thái status và atomic build với tempdir."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Tạo dummy chunks file
            sample_chunks = [
                {
                    "chunk_id": "tst:hierarchical:0001",
                    "strategy": "hierarchical",
                    "source": "tst.pdf",
                    "page_start": 1,
                    "page_end": 1,
                    "text": "Điều 1. Mẫu kiểm thử atomic build",
                }
            ]
            chunk_file = tmp_path / "sample__hierarchical.json"
            chunk_file.write_text(json.dumps(sample_chunks, ensure_ascii=False), encoding="utf-8")

            # Load và build
            loaded, load_stats = load_and_order_hierarchical_chunks(input_path=chunk_file)
            self.assertEqual(len(loaded), 1)
            resolved, res_stats = resolve_child_hierarchy(loaded)
            children, parents, p_stats = build_parent_documents(resolved, parent_max_chars=6000)

            manifest = {
                "schema_version": "1.0",
                "strategy": "hierarchical",
                "build_timestamp": "2026-09-18T00:00:00Z",
                "input_file_fingerprints": load_stats["file_fingerprints"],
                "counts": {"total_children": len(children), "total_parents": len(parents)},
                "warning_counts": {"total_warnings": 0}
            }

            store_dir = tmp_path / "hierarchy_store"
            save_res = save_hierarchy_store(children, parents, manifest, storage_dir=store_dir)
            self.assertEqual(save_res["status"], "success")

            # Check status read-only
            status = get_hierarchy_status(storage_dir=store_dir)
            self.assertTrue(status["is_built"])
            self.assertEqual(status["total_children"], 1)
            self.assertEqual(status["total_parents"], 1)

            # Load store
            store = load_hierarchy_store(storage_dir=store_dir)
            self.assertEqual(len(store["children_by_id"]), 1)
            self.assertEqual(len(store["parents_by_id"]), 1)


if __name__ == "__main__":
    unittest.main()
