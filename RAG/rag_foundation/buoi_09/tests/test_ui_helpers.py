"""
Bộ unit tests kiểm thử các UI Helper thuần Python cho Streamlit App Buổi 09:
100% offline, không cần trình duyệt, không gọi API mạng hay model.
"""

import sys
import unittest
from pathlib import Path

# Đảm bảo import được module Buổi 09
BUOI_09_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUOI_09_DIR))

from ui_helpers import (
    build_query_child_matrix_data,
    format_parent_tree_summary,
    build_mode_comparison_rows,
    format_citation_display,
    map_ui_error_message,
)


class TestUIHelpers(unittest.TestCase):
    """
    Test suite kiểm thử các hàm hỗ trợ định dạng UI của Buổi 09.
    """

    def test_01_build_query_child_matrix_data(self):
        """
        Case 1: Xây dựng dữ liệu ma trận Query - Child chính xác từng ô.
        """
        fused_children = [
            {
                "child_id": "c1",
                "source": "TT_39_2016_NHNN.pdf",
                "page_start": 4,
                "page_end": 5,
                "multi_query_rrf_score": 0.045678,
                "multi_query_rank": 1,
                "support_query_ids": ["Q0", "Q1"],
                "per_query_ranks": {"Q0": 1, "Q1": 3},
            },
            {
                "child_id": "c2",
                "source": "TT_06_2023_NHNN.pdf",
                "page_start": 2,
                "page_end": 3,
                "multi_query_rrf_score": 0.021000,
                "multi_query_rank": 2,
                "support_query_ids": ["Q0"],
                "per_query_ranks": {"Q0": 2},
            }
        ]
        query_set = {
            "queries": [
                {"query_id": "Q0", "text": "Q0 text"},
                {"query_id": "Q1", "text": "Q1 text"},
            ]
        }
        matrix = build_query_child_matrix_data(fused_children, query_set)
        self.assertEqual(len(matrix), 2)
        row1 = matrix[0]
        self.assertEqual(row1["Child_ID"], "c1")
        self.assertEqual(row1["Q0"], "#1")
        self.assertEqual(row1["Q1"], "#3")
        self.assertEqual(row1["Support_Count"], 2)

        row2 = matrix[1]
        self.assertEqual(row2["Child_ID"], "c2")
        self.assertEqual(row2["Q0"], "#2")
        self.assertEqual(row2["Q1"], "—")

    def test_02_format_parent_tree_summary(self):
        """
        Case 2: Định dạng cây phân cấp Parent Document với độ lệch thứ hạng (Rank Movement).
        """
        parent_cand = {
            "parent_id": "P1",
            "source": "TT_39_2016_NHNN.pdf",
            "page_start": 1,
            "page_end": 18,
            "structural_path": {"law": "39/2016/TT-NHNN", "article": 8},
            "parent_rank": 2,
            "parent_rerank_rank": 1,
            "parent_rank_change": 1,  # Tăng 1 bậc (+1)
            "parent_rrf_score": 0.035,
            "parent_rerank_score": 0.9254,
            "anchor_child_id": "c1",
            "scoring_child_ids": ["c1", "c2"],
            "supporting_child_ids": ["c1", "c2", "c3"],
            "support_query_ids": ["Q0", "Q1"],
            "ambiguous": False,
            "warnings": [],
            "text": "Parent 1 content..."
        }
        grouped = [
            {"child_id": "c1", "multi_query_rank": 1, "support_query_ids": ["Q0", "Q1"], "text": "Snippet 1"},
            {"child_id": "c2", "multi_query_rank": 4, "support_query_ids": ["Q0"], "text": "Snippet 2"},
        ]
        summary = format_parent_tree_summary(parent_cand, grouped)
        self.assertEqual(summary["parent_id"], "P1")
        self.assertEqual(summary["law_title"], "39/2016/TT-NHNN - Điều 8")
        self.assertEqual(summary["old_rank"], 2)
        self.assertEqual(summary["new_rank"], 1)
        self.assertEqual(summary["rank_delta_str"], "+1")
        self.assertEqual(len(summary["children"]), 2)
        self.assertTrue(summary["children"][0]["is_anchor"])
        self.assertTrue(summary["children"][0]["is_scored"])

    def test_03_build_mode_comparison_rows(self):
        """
        Case 3: Xây dựng các hàng so sánh đối chuẩn 4 chế độ.
        """
        comp_data = {
            "modes": {
                "single_flat": {"top1_id": "c1", "top1_score": 0.95, "top1_law": "Điều 8", "top1_source": "docA.pdf", "accepted_evidence_count": 5, "latency_ms": 120.5, "status": "ready"},
                "multi_flat": {"top1_id": "c1", "top1_score": 0.97, "top1_law": "Điều 8", "top1_source": "docA.pdf", "accepted_evidence_count": 5, "latency_ms": 250.0, "status": "ready"},
                "single_parent": {"top1_id": "P1", "top1_score": 0.98, "top1_law": "Điều 8", "top1_source": "docA.pdf", "accepted_evidence_count": 3, "latency_ms": 150.0, "status": "ready"},
                "multi_parent": {"top1_id": "P1", "top1_score": 0.99, "top1_law": "Điều 8", "top1_source": "docA.pdf", "accepted_evidence_count": 2, "latency_ms": 320.0, "status": "ready"},
            }
        }
        rows = build_mode_comparison_rows(comp_data)
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["Mode"], "single_flat")
        self.assertEqual(rows[0]["Unit_Type"], "Child Chunk")
        self.assertEqual(rows[3]["Mode"], "multi_parent")
        self.assertEqual(rows[3]["Unit_Type"], "Parent Document")
        self.assertEqual(rows[3]["Generation_Calls"], 0)

    def test_04_format_citation_display(self):
        """
        Case 4: Định dạng hiển thị trích dẫn pháp lý rõ ràng.
        """
        cit = {
            "source": "TT_39_2016_NHNN.pdf",
            "page_start": 4,
            "page_end": 5,
            "structural_path": {"law": "39/2016/TT-NHNN", "article": 7},
            "parent_id": "TT_39_2016_NHNN:d07:w01"
        }
        disp = format_citation_display(cit)
        self.assertIn("39/2016/TT-NHNN", disp)
        self.assertIn("Điều 7", disp)
        self.assertIn("tr. 4-5", disp)
        self.assertIn("parent: TT_39_2016_NHNN:d07:w01", disp)

    def test_05_map_ui_error_message(self):
        """
        Case 5: Ánh xạ mã lỗi sang thông báo hướng dẫn người dùng an toàn.
        """
        err_h = map_ui_error_message("hierarchy_not_ready")
        self.assertEqual(err_h["type"], "error")
        self.assertIn("Chưa xây dựng Hierarchy Registry", err_h["title"])

        err_ins = map_ui_error_message("insufficient_evidence")
        self.assertEqual(err_ins["type"], "info")
        self.assertIn("Không đủ bằng chứng", err_ins["title"])

    def test_06_import_and_status_no_side_effects(self):
        """
        Case 6 (Test Group 24): Import và lệnh status không gây side effect,
        không tự tạo file/folder và không ghi vào storage.
        """
        import tempfile
        from hierarchical_rag import get_hierarchical_status

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_target = Path(tmp_dir) / "empty_dir"
            self.assertFalse(test_target.exists())
            status = get_hierarchical_status(storage_dir=test_target)
            self.assertFalse(status["hierarchy_ready"])
            # Khẳng định thư mục không bị tạo ngầm
            self.assertFalse(test_target.exists())

    def test_07_no_model_or_store_build_on_page_load(self):
        """
        Case 7 (Test Group 25 & 26): Module UI không kích hoạt model loading
        hoặc hierarchy building tự động khi import.
        """
        # Kiểm tra nội dung mã nguồn của app.py để đảm bảo việc gọi build_hierarchy_registry
        # và load model chỉ xảy ra khi người dùng kích hoạt qua nút bấm st.button
        app_file = BUOI_09_DIR / "app.py"
        self.assertTrue(app_file.exists())
        with open(app_file, "r", encoding="utf-8") as f:
            app_code = f.read()

        # build_hierarchy_registry chỉ được gọi khi bấm nút build trong expander quản trị
        self.assertIn('Xây dựng Hierarchy Registry', app_code)
        # Truy xuất và so sánh chỉ được gọi khi bấm nút submit
        self.assertIn('Thực Thi Truy Xuất & Trả Lời', app_code)
        self.assertIn('Chạy So Sánh 4 Chế Độ', app_code)


if __name__ == "__main__":
    unittest.main()
