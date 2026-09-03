"""
Bộ unit tests kiểm thử Hierarchy Builder và Parent-Child Registry cho Buổi 09:
100% offline, độc lập hoàn toàn, không gọi API ngoài hay tải mô hình qua mạng.
Bao quát 14 tiêu chí kiểm thử bắt buộc theo đặc tả kỹ thuật SPEC_buoi_09.md.
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

from hierarchical_rag import (
    resolve_chunk_hierarchy,
    build_parent_documents,
    build_hierarchy_registry,
    get_hierarchical_status,
    extract_sequence_number,
    load_buoi_09_config,
    parse_heading_candidates,
)


class TestHierarchyBuilder(unittest.TestCase):
    """
    Test suite kiểm thử toàn diện Document Structure Hierarchy Resolution
    và Parent Document Construction.
    """

    def setUp(self):
        self.maxDiff = None

    def test_01_metadata_precedence(self):
        """
        Case 1: Ưu tiên metadata structure của chính record khi có sẵn.
        """
        raw_chunks = [
            {
                "chunk_id": "TEST:hierarchical:0001",
                "source": "TEST.pdf",
                "page_start": 1,
                "page_end": 1,
                "text": "Nội dung điều khoản chung",
                "structure": {
                    "chapter": "Chương I",
                    "article": "Điều 1",
                    "clause": "Khoản 1"
                }
            }
        ]
        resolved, stats = resolve_chunk_hierarchy(raw_chunks, "TEST.pdf")
        self.assertEqual(len(resolved), 1)
        ch = resolved[0]
        self.assertEqual(ch["structural_path"]["chapter"], "Chương I")
        self.assertEqual(ch["structural_path"]["article"], "Điều 1")
        self.assertEqual(ch["structural_path"]["clause"], "Khoản 1")
        self.assertEqual(ch["resolution_method"], "metadata")
        self.assertFalse(ch["ambiguous"])
        self.assertEqual(stats["metadata"], 1)

    def test_02_heading_inferred_at_start(self):
        """
        Case 2: Nhận diện heading rõ ràng ở đầu text khi metadata không có article.
        """
        raw_chunks = [
            {
                "chunk_id": "TEST:hierarchical:0001",
                "source": "TEST.pdf",
                "page_start": 1,
                "page_end": 1,
                "text": "Điều 5. Nguyên tắc cấp tín dụng\n1. Tổ chức tín dụng tuân thủ quy định...",
                "structure": {
                    "clause": "Khoản 1"
                }
            }
        ]
        resolved, stats = resolve_chunk_hierarchy(raw_chunks, "TEST.pdf")
        self.assertEqual(len(resolved), 1)
        ch = resolved[0]
        self.assertEqual(ch["structural_path"]["article"], "Điều 5")
        self.assertEqual(ch["resolution_method"], "heading_inferred")
        self.assertFalse(ch["ambiguous"])
        self.assertEqual(stats["heading_inferred"], 1)

    def test_03_carry_forward_within_same_source(self):
        """
        Case 3: Thừa kế (carry forward) chapter/article gần nhất trong cùng một source.
        """
        raw_chunks = [
            {
                "chunk_id": "TEST:hierarchical:0001",
                "source": "TEST.pdf",
                "page_start": 1,
                "page_end": 1,
                "text": "Điều 2. Giải thích từ ngữ\n1. Cơ cấu lại thời hạn trả nợ...",
                "structure": {"article": "Điều 2", "clause": "Khoản 1"}
            },
            {
                "chunk_id": "TEST:hierarchical:0002",
                "source": "TEST.pdf",
                "page_start": 2,
                "page_end": 2,
                "text": "2. Gia hạn nợ là việc kéo dài thời hạn cho vay...",
                "structure": {"clause": "Khoản 2"}
            }
        ]
        resolved, stats = resolve_chunk_hierarchy(raw_chunks, "TEST.pdf")
        self.assertEqual(len(resolved), 2)
        self.assertEqual(resolved[0]["structural_path"]["article"], "Điều 2")
        self.assertEqual(resolved[0]["resolution_method"], "metadata")

        self.assertEqual(resolved[1]["structural_path"]["article"], "Điều 2")
        self.assertEqual(resolved[1]["resolution_method"], "carried_forward")
        self.assertEqual(stats["carried_forward"], 1)

    def test_04_never_carry_forward_across_sources(self):
        """
        Case 4: Tuyệt đối không carry forward article hoặc chapter qua nguồn văn bản khác.
        """
        source_a_chunks = [
            {
                "chunk_id": "SRC_A:hierarchical:0001",
                "source": "SRC_A.pdf",
                "page_start": 1,
                "page_end": 1,
                "text": "Điều 10. Hoạt động cho vay",
                "structure": {"article": "Điều 10"}
            }
        ]
        source_b_chunks = [
            {
                "chunk_id": "SRC_B:hierarchical:0001",
                "source": "SRC_B.pdf",
                "page_start": 1,
                "page_end": 1,
                "text": "Nội dung mở đầu không có heading",
                "structure": None
            }
        ]
        resolved_a, _ = resolve_chunk_hierarchy(source_a_chunks, "SRC_A.pdf")
        resolved_b, stats_b = resolve_chunk_hierarchy(source_b_chunks, "SRC_B.pdf")

        self.assertEqual(resolved_a[0]["structural_path"]["article"], "Điều 10")
        self.assertIsNone(resolved_b[0]["structural_path"]["article"])
        self.assertEqual(resolved_b[0]["resolution_method"], "document_fallback")
        self.assertTrue(resolved_b[0]["ambiguous"])
        self.assertEqual(stats_b["document_fallback"], 1)

    def test_05_inline_reference_not_falsely_detected_as_heading(self):
        """
        Case 5: Cụm từ viện dẫn giữa câu như 'quy định tại Điều 7' không bị nhận nhầm thành heading.
        """
        raw_chunks = [
            {
                "chunk_id": "TEST:hierarchical:0001",
                "source": "TEST.pdf",
                "page_start": 2,
                "page_end": 2,
                "text": "Báo cáo tổng hợp được lập theo quy định tại khoản 4 Điều 7 Thông tư này.",
                "structure": {"clause": "Khoản 4"}
            }
        ]
        resolved, stats = resolve_chunk_hierarchy(raw_chunks, "TEST.pdf")
        self.assertEqual(len(resolved), 1)
        # Không có heading ở đầu và không có carry forward -> fallback, không được nhầm thành Điều 7
        self.assertNotEqual(resolved[0]["structural_path"]["article"], "Điều 7")
        self.assertEqual(resolved[0]["resolution_method"], "document_fallback")

    def test_06_conflict_sets_ambiguous_and_warning(self):
        """
        Case 6: Xung đột giữa metadata và heading trong text phải đặt ambiguous=True và ghi warning.
        """
        raw_chunks = [
            {
                "chunk_id": "TEST:hierarchical:0001",
                "source": "TEST.pdf",
                "page_start": 1,
                "page_end": 1,
                "text": "Điều 8. Các nhu cầu vốn không được cho vay\n1. Nghiêm cấm...",
                "structure": {
                    "article": "Điều 7"  # Xung đột với text Điều 8
                }
            }
        ]
        resolved, stats = resolve_chunk_hierarchy(raw_chunks, "TEST.pdf")
        self.assertEqual(len(resolved), 1)
        ch = resolved[0]
        self.assertTrue(ch["ambiguous"])
        self.assertTrue(any("conflict_metadata_and_heading" in w for w in ch["warnings"]))
        self.assertEqual(stats["ambiguous_count"], 1)

    def test_07_numeric_chunk_ordering(self):
        """
        Case 7: Sắp xếp các chunk theo số thứ tự số học (2 trước 10) thay vì sắp xếp lexical.
        """
        seqs = [
            extract_sequence_number("TT_02:hierarchical:0002"),
            extract_sequence_number("TT_02:hierarchical:0010"),
            extract_sequence_number("TT_02:hierarchical:0001"),
        ]
        self.assertEqual(seqs, [2, 10, 1])

        sorted_ids = sorted(
            ["TT_02:hierarchical:0010", "TT_02:hierarchical:0002", "TT_02:hierarchical:0001"],
            key=extract_sequence_number
        )
        self.assertEqual(sorted_ids, [
            "TT_02:hierarchical:0001",
            "TT_02:hierarchical:0002",
            "TT_02:hierarchical:0010"
        ])

    def test_08_stable_parent_id(self):
        """
        Case 8: Parent ID có tính ổn định và xác định (deterministic) cùng input/config.
        """
        resolved_children = [
            {
                "child_id": "TEST:hierarchical:0001",
                "source": "TT_TEST.pdf",
                "page_start": 1,
                "page_end": 1,
                "text": "Nội dung Điều 4 phần 1",
                "structural_path": {"article": "Điều 4"},
                "ambiguous": False,
                "warnings": []
            },
            {
                "child_id": "TEST:hierarchical:0002",
                "source": "TT_TEST.pdf",
                "page_start": 1,
                "page_end": 2,
                "text": "Nội dung Điều 4 phần 2",
                "structural_path": {"article": "Điều 4"},
                "ambiguous": False,
                "warnings": []
            }
        ]
        parents_1, children_1 = build_parent_documents(resolved_children, "TT_TEST.pdf", parent_max_chars=6000)
        parents_2, children_2 = build_parent_documents(resolved_children, "TT_TEST.pdf", parent_max_chars=6000)

        self.assertEqual(len(parents_1), 1)
        self.assertEqual(parents_1[0]["parent_id"], "TT_TEST:d04:w01")
        self.assertEqual(parents_1[0]["parent_id"], parents_2[0]["parent_id"])
        self.assertEqual(children_1[0]["parent_id"], "TT_TEST:d04:w01")
        self.assertEqual(children_1[1]["parent_id"], "TT_TEST:d04:w01")

    def test_09_parent_split_at_child_boundary(self):
        """
        Case 9: Chia Article dài thành các window liên tiếp theo ranh giới child chunk (không cắt giữa child).
        """
        resolved_children = [
            {
                "child_id": "TEST:hierarchical:0001",
                "source": "TT_TEST.pdf",
                "page_start": 1,
                "page_end": 1,
                "text": "A" * 600,
                "structural_path": {"article": "Điều 1"},
                "ambiguous": False,
                "warnings": []
            },
            {
                "child_id": "TEST:hierarchical:0002",
                "source": "TT_TEST.pdf",
                "page_start": 1,
                "page_end": 2,
                "text": "B" * 600,
                "structural_path": {"article": "Điều 1"},
                "ambiguous": False,
                "warnings": []
            }
        ]
        # Max chars = 1000 -> 600 + 600 = 1200 > 1000 nên phải tách thành 2 window
        parents, children = build_parent_documents(resolved_children, "TT_TEST.pdf", parent_max_chars=1000)
        self.assertEqual(len(parents), 2)
        self.assertEqual(parents[0]["parent_id"], "TT_TEST:d01:w01")
        self.assertEqual(parents[1]["parent_id"], "TT_TEST:d01:w02")

        self.assertEqual(parents[0]["child_ids"], ["TEST:hierarchical:0001"])
        self.assertEqual(parents[1]["child_ids"], ["TEST:hierarchical:0002"])
        self.assertEqual(children[0]["parent_id"], "TT_TEST:d01:w01")
        self.assertEqual(children[1]["parent_id"], "TT_TEST:d01:w02")

    def test_10_oversized_single_child_warning(self):
        """
        Case 10: Child đơn lẻ vượt quá PARENT_MAX_CHARS được giữ nguyên và gắn warning.
        """
        resolved_children = [
            {
                "child_id": "TEST:hierarchical:0001",
                "source": "TT_TEST.pdf",
                "page_start": 1,
                "page_end": 2,
                "text": "X" * 1500,
                "structural_path": {"article": "Điều 9"},
                "ambiguous": False,
                "warnings": []
            }
        ]
        parents, _ = build_parent_documents(resolved_children, "TT_TEST.pdf", parent_max_chars=1000)
        self.assertEqual(len(parents), 1)
        self.assertEqual(parents[0]["char_count"], 1500)
        self.assertTrue(any("oversized_single_child" in w for w in parents[0]["warnings"]))

    def test_11_each_child_belongs_to_exactly_one_parent(self):
        """
        Case 11: Mỗi child thuộc về duy nhất một parent document.
        """
        resolved_children = [
            {
                "child_id": f"TEST:hierarchical:000{i}",
                "source": "TT_TEST.pdf",
                "page_start": i,
                "page_end": i,
                "text": f"Nội dung khoản {i}",
                "structural_path": {"article": "Điều 3"},
                "ambiguous": False,
                "warnings": []
            } for i in range(1, 6)
        ]
        parents, updated_children = build_parent_documents(resolved_children, "TT_TEST.pdf", parent_max_chars=6000)
        parent_ids = {p["parent_id"] for p in parents}
        for ch in updated_children:
            self.assertIn(ch["parent_id"], parent_ids)

        all_child_ids_in_parents = []
        for p in parents:
            all_child_ids_in_parents.extend(p["child_ids"])
        self.assertEqual(len(all_child_ids_in_parents), len(set(all_child_ids_in_parents)))

    def test_12_parent_pages_count_text_correctness(self):
        """
        Case 12: Parent page_start là min, page_end là max và text được nối chuẩn từ child texts.
        """
        resolved_children = [
            {
                "child_id": "TEST:hierarchical:0001",
                "source": "TT_TEST.pdf",
                "page_start": 2,
                "page_end": 3,
                "text": "Đoạn 1",
                "structural_path": {"article": "Điều 1"},
                "ambiguous": False,
                "warnings": []
            },
            {
                "child_id": "TEST:hierarchical:0002",
                "source": "TT_TEST.pdf",
                "page_start": 3,
                "page_end": 5,
                "text": "Đoạn 2",
                "structural_path": {"article": "Điều 1"},
                "ambiguous": False,
                "warnings": []
            }
        ]
        parents, _ = build_parent_documents(resolved_children, "TT_TEST.pdf", parent_max_chars=6000)
        p = parents[0]
        self.assertEqual(p["page_start"], 2)
        self.assertEqual(p["page_end"], 5)
        self.assertEqual(p["text"], "Đoạn 1\n\nĐoạn 2")
        self.assertEqual(p["char_count"], len("Đoạn 1\n\nĐoạn 2"))

    def test_13_atomic_build_and_manifest_fingerprint(self):
        """
        Case 13: Atomic build tạo đầy đủ children.json, parents.json, manifest.json và mã băm fingerprint.
        """
        with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_store:
            sample_data = [
                {
                    "chunk_id": "TEST_TT:hierarchical:0001",
                    "strategy": "hierarchical",
                    "source": "TEST_TT.pdf",
                    "page_start": 1,
                    "page_end": 1,
                    "text": "Điều 1. Phạm vi điều chỉnh",
                    "structure": {"chapter": "Chương I", "article": "Điều 1"}
                }
            ]
            sample_file = Path(tmp_in) / "TEST_TT__hierarchical.json"
            with open(sample_file, "w", encoding="utf-8") as f:
                json.dump(sample_data, f)

            cfg = load_buoi_09_config()
            res = build_hierarchy_registry(input_dir=tmp_in, storage_dir=tmp_store, config=cfg)

            manifest_p = Path(tmp_store) / "manifest.json"
            parents_p = Path(tmp_store) / "parents.json"
            children_p = Path(tmp_store) / "children.json"

            self.assertTrue(manifest_p.exists())
            self.assertTrue(parents_p.exists())
            self.assertTrue(children_p.exists())

            with open(manifest_p, "r", encoding="utf-8") as f:
                m = json.load(f)
            self.assertEqual(m["schema_version"], "1.0.0")
            self.assertIn("TEST_TT__hierarchical.json", m["input_file_fingerprints"])
            self.assertEqual(m["counts"]["total_sources"], 1)
            self.assertEqual(m["counts"]["total_children"], 1)
            self.assertEqual(m["counts"]["total_parents"], 1)

    def test_14_status_command_is_strictly_read_only(self):
        """
        Case 14: Lệnh status hoàn toàn read-only, không tự tạo thư mục hay file mới khi store chưa tồn tại.
        """
        with tempfile.TemporaryDirectory() as tmp_empty:
            non_existent_dir = Path(tmp_empty) / "non_existent_storage"
            stat = get_hierarchical_status(storage_dir=non_existent_dir)
            self.assertFalse(stat["hierarchy_ready"])
            self.assertFalse(non_existent_dir.exists())  # Không được tự ý mkdir


if __name__ == "__main__":
    unittest.main()
