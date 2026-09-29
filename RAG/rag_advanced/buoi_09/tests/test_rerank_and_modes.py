"""
Unit tests for Reranking and 4 Modes in Buổi 09:
Covering Required Test Groups 19-23:
19. Rerank Q0 + parent.
20. Bốn mode routing (single_flat, multi_flat, single_parent, multi_parent).
21. Gate/status/no silent fallback.
22. Citation parent + anchor child.
23. API call budget và compare không generation.

Tất cả chạy 100% offline, không mạng, không API, dùng mock/fakes qua Dependency Injection.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from rag_advanced.buoi_09.hierarchical_rag import (
    rerank_parents_cross_encoder,
    query_hierarchical_rag,
)


class MockCrossEncoder:
    def __init__(self, scores):
        self.scores = scores
        self.last_pairs = []

    def predict(self, pairs):
        self.last_pairs = pairs
        return self.scores[:len(pairs)]


def fake_retriever(query_text, top_n=10, config=None):
    return {
        "status": "ok",
        "candidates": [
            {
                "child_id": "doc1:hierarchical:0001",
                "source": "doc1.pdf",
                "page_start": 1,
                "page_end": 1,
                "text": "Nội dung Điều 1 khoản 1 về lãi suất",
                "score": 0.85,
                "rank": 1,
            },
            {
                "child_id": "doc1:hierarchical:0002",
                "source": "doc1.pdf",
                "page_start": 1,
                "page_end": 2,
                "text": "Nội dung Điều 1 khoản 2 về điều kiện",
                "score": 0.75,
                "rank": 2,
            }
        ],
        "trace": {"retrieval_ms": 1.0}
    }


def fake_generator(q, count=3, temp=0.2, model="mock"):
    return {
        "queries": [
            {"text": "Q1 paraphrase: " + q, "focus": "paraphrase"},
            {"text": "Q2 legal focus: " + q, "focus": "exact_legal_terms"},
        ]
    }


class TestRerankAndModes(unittest.TestCase):

    def setUp(self):
        self.mock_store = {
            "children_by_id": {
                "doc1:hierarchical:0001": {
                    "child_id": "doc1:hierarchical:0001",
                    "parent_id": "doc1.pdf::Dieu_1::w01",
                    "source": "doc1.pdf",
                    "page_start": 1,
                    "page_end": 1,
                    "text": "Nội dung Điều 1 khoản 1 về lãi suất",
                },
                "doc1:hierarchical:0002": {
                    "child_id": "doc1:hierarchical:0002",
                    "parent_id": "doc1.pdf::Dieu_1::w01",
                    "source": "doc1.pdf",
                    "page_start": 1,
                    "page_end": 2,
                    "text": "Nội dung Điều 1 khoản 2 về điều kiện",
                }
            },
            "parents_by_id": {
                "doc1.pdf::Dieu_1::w01": {
                    "parent_id": "doc1.pdf::Dieu_1::w01",
                    "source": "doc1.pdf",
                    "title": "Điều 1. Phạm vi điều chỉnh",
                    "page_start": 1,
                    "page_end": 2,
                    "text": "Điều 1. Phạm vi điều chỉnh toàn văn...",
                    "child_ids": ["doc1:hierarchical:0001", "doc1:hierarchical:0002"],
                    "char_count": 300,
                }
            }
        }

    def test_19_rerank_q0_with_parents(self):
        """Test 19: Rerank sử dụng Q0 kết hợp với text của parent."""
        parents = [
            {"parent_id": "p1", "text": "Văn bản về cho vay vốn", "title": "Điều 1"},
            {"parent_id": "p2", "text": "Văn bản về lãi suất tối đa", "title": "Điều 2"},
        ]
        # p2 đạt điểm cao hơn p1
        mock_reranker = MockCrossEncoder(scores=[0.35, 0.92])
        reranked = rerank_parents_cross_encoder("Lãi suất cho vay ngắn hạn", parents, reranker_instance=mock_reranker, min_score=0.5)

        self.assertEqual(len(reranked), 2)
        # p2 đứng đầu vì 0.92 > 0.35
        self.assertEqual(reranked[0]["parent_id"], "p2")
        self.assertEqual(reranked[0]["rerank_rank"], 1)
        self.assertEqual(reranked[0]["rerank_score"], 0.92)
        self.assertTrue(reranked[0]["accepted"])

        self.assertEqual(reranked[1]["parent_id"], "p1")
        self.assertEqual(reranked[1]["rerank_rank"], 2)
        self.assertFalse(reranked[1]["accepted"])

        # Kiểm tra pairs truyền vào là (Q0, parent.text)
        expected_pairs = [
            ["Lãi suất cho vay ngắn hạn", "Văn bản về cho vay vốn"],
            ["Lãi suất cho vay ngắn hạn", "Văn bản về lãi suất tối đa"],
        ]
        self.assertEqual(mock_reranker.last_pairs, expected_pairs)

    def test_20_four_mode_routing(self):
        """Test 20: Kiểm tra định tuyến chính xác cho 4 chế độ truy xuất."""
        modes = ["single_flat", "multi_flat", "single_parent", "multi_parent"]
        for m in modes:
            res = query_hierarchical_rag(
                question="Điều kiện vay vốn",
                mode=m,
                retrieval_only=True,
                per_query_retriever=fake_retriever,
                generator_fn=fake_generator,
                reranker_instance=MockCrossEncoder(scores=[0.88]),
                store=self.mock_store,
            )
            self.assertEqual(res["status"], "retrieval_only")
            self.assertEqual(res["mode"], m)
            if "parent" in m:
                self.assertGreaterEqual(len(res["parents"]), 1)
                self.assertEqual(res["evidence"][0]["parent_id"], "doc1.pdf::Dieu_1::w01")
            else:
                self.assertEqual(len(res["parents"]), 0)
                self.assertIn("child_id", res["evidence"][0])

    def test_21_gate_status_no_silent_fallback(self):
        """Test 21: Báo lỗi/status rõ ràng, không silent fallback sinh kết quả giả."""
        # Trường hợp không có evidence
        def empty_retriever(q, top_n=10, config=None):
            return {"status": "ok", "candidates": [], "trace": {}}

        res = query_hierarchical_rag(
            question="Câu hỏi ngoài phạm vi",
            mode="multi_parent",
            retrieval_only=False,
            per_query_retriever=empty_retriever,
            generator_fn=fake_generator,
            store=self.mock_store,
        )
        self.assertEqual(res["status"], "insufficient_evidence")
        self.assertIn("Không tìm thấy đủ thông tin", res["answer"])
        self.assertEqual(res["generation_call_count"], 0)

        # Trường hợp Q0 retrieval thất bại
        def fail_q0_retriever(q, top_n=10, config=None):
            raise RuntimeError("Database connection down")

        res_fail = query_hierarchical_rag(
            question="Câu hỏi lỗi",
            mode="single_flat",
            retrieval_only=True,
            per_query_retriever=fail_q0_retriever,
        )
        self.assertEqual(res_fail["status"], "q0_retrieval_failed")

    def test_22_citation_parent_and_anchor_child(self):
        """Test 22: Trích dẫn Parent Documents gồm title, pages và các anchor child chunks."""
        res = query_hierarchical_rag(
            question="Quy định phạm vi điều chỉnh",
            mode="single_parent",
            retrieval_only=False,
            per_query_retriever=fake_retriever,
            reranker_instance=MockCrossEncoder(scores=[0.85]),
            store=self.mock_store,
            custom_generation_fn=lambda prompt: "Căn cứ theo quy định [E1], Thông tư áp dụng cho TCTD.",
        )
        self.assertEqual(res["status"], "answered")
        self.assertEqual(len(res["citations"]), 1)
        cit = res["citations"][0]
        self.assertEqual(cit["label"], "[E1]")
        self.assertIn("Điều 1. Phạm vi điều chỉnh", cit["display"])
        self.assertIn("doc1:hierarchical:0001", cit["display"])

    def test_23_api_call_budget_and_compare_no_generation(self):
        """Test 23: Chế độ retrieval_only tuyệt đối không gọi Answer Generation."""
        gen_mock = MagicMock(return_value="Answer")
        res_cmp = query_hierarchical_rag(
            question="So sánh 4 mode",
            mode="multi_parent",
            retrieval_only=True,
            per_query_retriever=fake_retriever,
            generator_fn=fake_generator,
            reranker_instance=MockCrossEncoder(scores=[0.9]),
            store=self.mock_store,
            custom_generation_fn=gen_mock,
        )
        # retrieval_only -> gen_mock KHÔNG được gọi
        gen_mock.assert_not_called()
        self.assertEqual(res_cmp["generation_call_count"], 0)
        self.assertEqual(res_cmp["answer"], "")


if __name__ == "__main__":
    unittest.main()
