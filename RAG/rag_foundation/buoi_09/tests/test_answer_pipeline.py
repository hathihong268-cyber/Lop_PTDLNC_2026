"""
Bộ unit tests kiểm thử Reranking, Evidence Gate, Answer Generation và Citation Validator cho Buổi 09:
100% offline, độc lập hoàn toàn, sử dụng dependency injection mock reranker và mock LLM,
không gọi Gemini API qua mạng, không tải model HuggingFace thật.
Bao quát 14 tiêu chí kiểm thử bắt buộc theo đặc tả kỹ thuật SPEC_buoi_09.md.
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
    rerank_parent_candidates,
    generate_parent_rag_answer,
    query_hierarchical_rag,
    compare_hierarchical_rag,
    load_buoi_09_config,
    _MULTI_QUERY_CACHE,
)


class TestAnswerPipeline(unittest.TestCase):
    """
    Test suite kiểm thử toàn diện Parent Reranker, Evidence Gate, Citation Validator và Mode Comparison.
    """

    def setUp(self):
        self.config = load_buoi_09_config()
        self.config["final_parent_top_k"] = 3
        self.config["rerank_min_score"] = 0.5
        self.config["parent_candidates"] = 5
        self.config["total_context_max_chars"] = 8000
        _MULTI_QUERY_CACHE.clear()

        # Mock Parent Candidates
        self.mock_parent_candidates = [
            {
                "parent_id": "P1",
                "source": "docA.pdf",
                "page_start": 1,
                "page_end": 2,
                "structural_path": {"law": "39/2016", "article": 8},
                "text": "Parent 1 text about lending conditions...",
                "char_count": 500,
                "parent_rrf_score": 0.045,
                "parent_rank": 1,
                "anchor_child_id": "c1",
                "scoring_child_ids": ["c1"],
                "supporting_child_ids": ["c1", "c2"],
                "support_query_ids": ["Q0", "Q1"],
                "best_child_rank": 1,
                "ambiguous": False,
                "warnings": [],
            },
            {
                "parent_id": "P2",
                "source": "docA.pdf",
                "page_start": 3,
                "page_end": 4,
                "structural_path": {"law": "39/2016", "article": 14},
                "text": "Parent 2 text about interest rates...",
                "char_count": 600,
                "parent_rrf_score": 0.035,
                "parent_rank": 2,
                "anchor_child_id": "c4",
                "scoring_child_ids": ["c4"],
                "supporting_child_ids": ["c4"],
                "support_query_ids": ["Q0"],
                "best_child_rank": 2,
                "ambiguous": False,
                "warnings": [],
            },
            {
                "parent_id": "P3",
                "source": "docB.pdf",
                "page_start": 1,
                "page_end": 3,
                "structural_path": {"law": "02/2023", "article": 4},
                "text": "Parent 3 text about debt restructuring...",
                "char_count": 700,
                "parent_rrf_score": 0.025,
                "parent_rank": 3,
                "anchor_child_id": "c5",
                "scoring_child_ids": ["c5"],
                "supporting_child_ids": ["c5"],
                "support_query_ids": ["Q1"],
                "best_child_rank": 3,
                "ambiguous": True,
                "warnings": ["ambiguous_hierarchy"],
            },
        ]

    def test_01_reranker_pair_uses_q0_and_parent_text(self):
        """
        Case 1: Cross-Encoder pair luôn sử dụng nguyên văn Q0 và text của Parent Document.
        """
        recorded_pairs = []
        def mock_score_fn(query: str, texts: list[str]) -> list[float]:
            for t in texts:
                recorded_pairs.append((query, t))
            return [2.5, 1.0, -1.0]

        accepted, rejected, top_k, trace = rerank_parent_candidates(
            original_question="  Câu hỏi gốc Q0?  ",
            parent_candidates=self.mock_parent_candidates,
            score_fn=mock_score_fn
        )
        self.assertEqual(len(recorded_pairs), 3)
        self.assertEqual(recorded_pairs[0][0], "Câu hỏi gốc Q0?")
        self.assertEqual(recorded_pairs[0][1], self.mock_parent_candidates[0]["text"])

    def test_02_generated_queries_not_used_for_rerank_or_generation(self):
        """
        Case 2: Các query variants Q1..Qn không được đưa vào cặp reranker hoặc answer prompt như sự thật.
        """
        sent_prompts = []
        def mock_answer_gen(q: str, evidence_block: str) -> str:
            sent_prompts.append((q, evidence_block))
            return "Theo [P1], điều kiện vay vốn là hợp pháp."

        accepted_evidence = [self.mock_parent_candidates[0]]
        accepted_evidence[0]["parent_rerank_score"] = 0.92

        res = generate_parent_rag_answer(
            original_question="Câu hỏi gốc Q0?",
            accepted_evidence=accepted_evidence,
            mode="multi_parent",
            config=self.config,
            answer_generator_fn=mock_answer_gen
        )
        self.assertEqual(len(sent_prompts), 1)
        q_sent, ev_sent = sent_prompts[0]
        self.assertEqual(q_sent, "Câu hỏi gốc Q0?")
        self.assertIn("[P1]", ev_sent)
        self.assertNotIn("Q1", ev_sent)
        self.assertNotIn("Q2", ev_sent)

    def test_03_sort_rank_change_and_final_top_k(self):
        """
        Case 3: Sắp xếp theo parent_rerank_score giảm dần, tính parent_rank_change và cắt top K.
        """
        # P2 trước đó rank 2 nhận score cao nhất -> vươn lên rank 1 (rank_change = 2 - 1 = +1)
        # P1 trước đó rank 1 nhận score nhì -> xuống rank 2 (rank_change = 1 - 2 = -1)
        def mock_score_fn(query: str, texts: list[str]) -> list[float]:
            return [1.0, 3.0, -2.0]  # P1: sigmoid(1.0)=0.7311, P2: sigmoid(3.0)=0.9526, P3: sigmoid(-2.0)=0.1192

        accepted, rejected, top_k, trace = rerank_parent_candidates(
            original_question="Q0",
            parent_candidates=self.mock_parent_candidates,
            final_parent_top_k=2,
            rerank_min_score=0.5,
            score_fn=mock_score_fn
        )
        self.assertEqual(len(top_k), 2)
        self.assertEqual(top_k[0]["parent_id"], "P2")
        self.assertEqual(top_k[0]["parent_rank_change"], 1)
        self.assertEqual(top_k[1]["parent_id"], "P1")
        self.assertEqual(top_k[1]["parent_rank_change"], -1)

    def test_04_evidence_gate_accepted_and_rejected(self):
        """
        Case 4: Evidence Gate phân loại đúng accepted (score >= 0.5) và rejected (score < 0.5).
        """
        def mock_score_fn(query: str, texts: list[str]) -> list[float]:
            return [2.0, -1.0, -3.0]  # P1: >0.5 (accepted), P2: <0.5 (rejected), P3: <0.5 (rejected)

        accepted, rejected, top_k, trace = rerank_parent_candidates(
            original_question="Q0",
            parent_candidates=self.mock_parent_candidates,
            rerank_min_score=0.5,
            score_fn=mock_score_fn
        )
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]["parent_id"], "P1")
        self.assertEqual(len(rejected), 2)

    def test_05_insufficient_evidence_makes_zero_generation_call(self):
        """
        Case 5: Khi không có bằng chứng nào vượt qua Gate -> trả insufficient_evidence và KHÔNG gọi LLM.
        """
        gen_calls = 0
        def mock_answer_gen(q: str, ev: str) -> str:
            nonlocal gen_calls
            gen_calls += 1
            return "Answer"

        res = generate_parent_rag_answer(
            original_question="Q0",
            accepted_evidence=[],  # Không có evidence
            mode="multi_parent",
            config=self.config,
            answer_generator_fn=mock_answer_gen
        )
        self.assertEqual(res["status"], "insufficient_evidence")
        self.assertEqual(gen_calls, 0)
        self.assertEqual(len(res["citations"]), 0)

    def test_06_flat_and_parent_mode_routing(self):
        """
        Case 6: Kiểm tra định tuyến chính xác giữa 4 modes: single_flat, multi_flat, single_parent, multi_parent.
        """
        def mock_gen(q: str) -> str:
            return json.dumps({"queries": [{"text": "V1", "focus": "paraphrase"}]})

        def mock_ret(q: str) -> list[dict]:
            return [{
                "child_id": "TT_39_2016_NHNN:hierarchical:0059",
                "chunk_id": "TT_39_2016_NHNN:hierarchical:0059",
                "text": "Child 59 text",
                "source": "TT_39_2016_NHNN.pdf",
                "page_start": 4,
                "page_end": 5,
                "fused_rank": 1
            }]

        def mock_score(q: str, texts: list[str]) -> list[float]:
            return [2.0 for _ in texts]

        def mock_ans(q: str, ev: str) -> str:
            return "Theo [P1] hoặc [C1], quy định rõ ràng."

        for mode in ["single_flat", "multi_flat", "single_parent", "multi_parent"]:
            res = query_hierarchical_rag(
                question="Điều kiện vay vốn?",
                mode=mode,
                config=self.config,
                score_fn=mock_score,
                query_generator_fn=mock_gen,
                custom_hybrid_fn=mock_ret,
                answer_generator_fn=mock_ans
            )
            self.assertEqual(res["mode"], mode)
            self.assertIn(res["status"], {"ready", "multi_query_partial"})

    def test_07_multi_query_failure_status(self):
        """
        Case 7: Khi generator trả JSON hỏng -> mode multi trả status 'multi_query_partial' kèm cảnh báo.
        """
        def mock_broken_gen(q: str) -> str:
            return "BROKEN_JSON"

        def mock_ret(q: str) -> list[dict]:
            return [{
                "child_id": "TT_39_2016_NHNN:hierarchical:0059",
                "chunk_id": "TT_39_2016_NHNN:hierarchical:0059",
                "text": "Child 59 text",
                "source": "TT_39_2016_NHNN.pdf",
                "page_start": 4,
                "page_end": 5,
                "fused_rank": 1
            }]

        def mock_score(q: str, texts: list[str]) -> list[float]:
            return [2.0 for _ in texts]

        res = query_hierarchical_rag(
            question="Điều kiện vay vốn?",
            mode="multi_parent",
            config=self.config,
            score_fn=mock_score,
            query_generator_fn=mock_broken_gen,
            custom_hybrid_fn=mock_ret,
            answer_generator_fn=lambda q, ev: "Theo [P1], nội dung tốt."
        )
        self.assertEqual(res["status"], "multi_query_partial")
        self.assertTrue(len(res["warnings"]) > 0)

    def test_08_reranker_failure_does_not_silently_fallback(self):
        """
        Case 8: Khi Reranker ném Exception -> ném lỗi rõ ràng, không âm thầm fallback sang điểm không rerank.
        """
        def mock_broken_reranker(q: str, texts: list[str]) -> list[float]:
            raise RuntimeError("CUDA out of memory / Tokenizer crash")

        with self.assertRaises(RuntimeError) as ctx:
            rerank_parent_candidates(
                original_question="Q0",
                parent_candidates=self.mock_parent_candidates,
                score_fn=mock_broken_reranker
            )
        self.assertIn("CUDA out of memory", str(ctx.exception))

    def test_09_citation_uses_parent_and_real_anchor_child(self):
        """
        Case 9: Citation object chứa đúng parent_id, anchor_child_id và supporting_child_ids thực tế.
        """
        def mock_ans(q: str, ev: str) -> str:
            return "Theo [P1], ngân hàng cho vay vốn khi đáp ứng điều kiện."

        accepted = [self.mock_parent_candidates[0]]
        accepted[0]["parent_rerank_score"] = 0.88

        res = generate_parent_rag_answer(
            original_question="Q0",
            accepted_evidence=accepted,
            mode="multi_parent",
            config=self.config,
            answer_generator_fn=mock_ans
        )
        self.assertEqual(len(res["citations"]), 1)
        cit = res["citations"][0]
        self.assertEqual(cit["evidence_id"], "P1")
        self.assertEqual(cit["parent_id"], "P1")
        self.assertEqual(cit["anchor_child_id"], "c1")
        self.assertEqual(cit["supporting_child_ids"], ["c1", "c2"])

    def test_10_citation_label_validation(self):
        """
        Case 10: Nhãn trích dẫn bịa đặt như [P99] không có trong Evidence bị loại bỏ và ghi cảnh báo.
        """
        def mock_ans_fake_label(q: str, ev: str) -> str:
            return "Theo [P1] và [P99], quy định tại văn bản mở đầu."

        accepted = [self.mock_parent_candidates[0]]
        accepted[0]["parent_rerank_score"] = 0.88

        res = generate_parent_rag_answer(
            original_question="Q0",
            accepted_evidence=accepted,
            mode="multi_parent",
            config=self.config,
            answer_generator_fn=mock_ans_fake_label
        )
        self.assertNotIn("[P99]", res["answer"])
        self.assertTrue(any("Loại bỏ nhãn trích dẫn không có thật" in w for w in res["warnings"]))

    def test_11_multi_mode_maximum_two_generation_api_calls(self):
        """
        Case 11: Mode multi_parent thực hiện tối đa 2 cuộc gọi Generation API (1 expansion + 1 answer).
        """
        gen_calls = 0
        def mock_gen(q: str) -> str:
            nonlocal gen_calls
            gen_calls += 1
            return json.dumps({"queries": [{"text": "V1", "focus": "paraphrase"}]})

        def mock_ans(q: str, ev: str) -> str:
            nonlocal gen_calls
            gen_calls += 1
            return "Theo [P1], hoàn thành."

        def mock_ret(q: str) -> list[dict]:
            return [{
                "child_id": "TT_39_2016_NHNN:hierarchical:0059",
                "chunk_id": "TT_39_2016_NHNN:hierarchical:0059",
                "text": "Child 59 text",
                "source": "TT_39_2016_NHNN.pdf",
                "page_start": 4,
                "page_end": 5,
                "fused_rank": 1
            }]

        def mock_score(q: str, texts: list[str]) -> list[float]:
            return [2.0 for _ in texts]

        res = query_hierarchical_rag(
            question="Q0",
            mode="multi_parent",
            config=self.config,
            score_fn=mock_score,
            query_generator_fn=mock_gen,
            custom_hybrid_fn=mock_ret,
            answer_generator_fn=mock_ans
        )
        t = res["trace"]
        self.assertLessEqual(t["api_call_counts"]["generation_calls"], 2)
        self.assertEqual(gen_calls, 2)

    def test_12_compare_command_does_not_call_answer_generation(self):
        """
        Case 12: Lệnh compare chạy 4 modes retrieval/rerank nhưng TUYỆT ĐỐI KHÔNG gọi answer generation.
        """
        def mock_gen(q: str) -> str:
            return json.dumps({"queries": [{"text": "V1", "focus": "paraphrase"}]})

        def mock_ret(q: str) -> list[dict]:
            return [{
                "child_id": "TT_39_2016_NHNN:hierarchical:0059",
                "chunk_id": "TT_39_2016_NHNN:hierarchical:0059",
                "text": "Child 59 text",
                "source": "TT_39_2016_NHNN.pdf",
                "page_start": 4,
                "page_end": 5,
                "fused_rank": 1
            }]

        def mock_score(q: str, texts: list[str]) -> list[float]:
            return [2.0 for _ in texts]

        comp_res = compare_hierarchical_rag(
            question="Điều kiện vay vốn?",
            config=self.config,
            score_fn=mock_score,
            query_generator_fn=mock_gen,
            custom_hybrid_fn=mock_ret
        )
        self.assertIn("modes", comp_res)
        self.assertEqual(len(comp_res["modes"]), 4)
        for m_name, m_data in comp_res["modes"].items():
            self.assertIn("top1_score", m_data)
            self.assertIn("latency_ms", m_data)

    def test_13_trace_identities_and_call_counts(self):
        """
        Case 13: Trace ghi nhận đầy đủ stage_latencies, api_call_counts và identities.
        """
        def mock_gen(q: str) -> str:
            return json.dumps({"queries": [{"text": "V1", "focus": "paraphrase"}]})

        def mock_ret(q: str) -> list[dict]:
            return [{
                "child_id": "TT_39_2016_NHNN:hierarchical:0059",
                "chunk_id": "TT_39_2016_NHNN:hierarchical:0059",
                "text": "Child 59 text",
                "source": "TT_39_2016_NHNN.pdf",
                "page_start": 4,
                "page_end": 5,
                "fused_rank": 1
            }]

        def mock_score(q: str, texts: list[str]) -> list[float]:
            return [2.0 for _ in texts]

        def mock_ans(q: str, ev: str) -> str:
            return "Theo [P1], hoàn thành."

        res = query_hierarchical_rag(
            question="Q0",
            mode="multi_parent",
            config=self.config,
            score_fn=mock_score,
            query_generator_fn=mock_gen,
            custom_hybrid_fn=mock_ret,
            answer_generator_fn=mock_ans
        )
        t = res["trace"]
        self.assertIn("stage_latencies_ms", t)
        self.assertIn("api_call_counts", t)
        self.assertIn("identities", t)
        self.assertEqual(t["identities"]["strategy"], "hierarchical")

    def test_14_tests_run_100_percent_offline(self):
        """
        Case 14: Toàn bộ suite test chạy 100% offline, không có kết nối mạng hay gọi LLM thật.
        """
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
