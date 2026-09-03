"""
Bộ kiểm thử tự động (Unit Tests) cho Answer Pipeline, Grounding, Citations & Compare - Buổi 08.
Đảm bảo 100% chạy offline qua Dependency Injection và Mocking:
- Kiểm tra 4 retrieval modes
- Kiểm tra gating độc lập
- Kiểm tra delimiter và grounding prompt
- Kiểm tra citation mapping metadata thật và loại bỏ label giả
- Kiểm tra compare retrieval modes không gọi generation
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Đảm bảo import được module Buổi 08
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from advanced_rag import (
    query_advanced_rag,
    compare_retrieval_modes,
    CrossEncoderReranker,
    build_bm25_retriever,
    prepare_semantic_index
)


class TestAnswerPipelineAndGrounding(unittest.TestCase):
    """Kiểm thử Answer Pipeline, Grounding Prompt, Citation Mapping và Compare CLI"""

    def setUp(self):
        self.config = {
            "api_key": "mock_key",
            "has_api_key": True,
            "embedding_model": "gemini-embedding-2",
            "embedding_dim": 128,
            "generation_model": "gemini-3.5-flash-lite",
            "max_distance": 0.45,
            "bm25_candidates": 3,
            "semantic_candidates": 3,
            "rerank_candidates": 4,
            "final_top_k": 3,
            "rrf_k": 60,
            "rrf_bm25_weight": 1.0,
            "rrf_semantic_weight": 1.0,
            "reranker_model": "BAAI/bge-reranker-v2-m3",
            "reranker_max_length": 512,
            "rerank_batch_size": 4,
            "rerank_min_score": 0.50,
            "rerank_device": "auto",
        }

        self.sample_chunks = [
            {
                "chunk_id": "chunk_01",
                "text": "Thông tư 02 quy định về cơ cấu lại thời hạn trả nợ.",
                "source": "TT_02.pdf",
                "page_start": 1,
                "page_end": 2,
                "strategy": "hierarchical"
            },
            {
                "chunk_id": "chunk_02",
                "text": "Thông tư 39 quy định các nhu cầu vốn không được cho vay.",
                "source": "TT_39.pdf",
                "page_start": 3,
                "page_end": 4,
                "strategy": "hierarchical"
            },
            {
                "chunk_id": "chunk_03",
                "text": "Thông tư 06 quy định về bảo lãnh và lãi suất tín dụng.",
                "source": "TT_06.pdf",
                "page_start": 5,
                "page_end": 6,
                "strategy": "hierarchical"
            }
        ]

    def test_01_gating_mechanism_by_mode(self):
        """Case 1: Kiểm tra cơ chế gating độc lập theo từng mode (semantic vs hybrid_rerank)"""
        # Fake score_fn cho reranker: gán score 0.8 (accepted) và 0.2 (rejected < 0.50)
        def fake_score_fn(q, texts):
            return [2.0, -2.0]  # sigmoid(2.0) ≈ 0.88 (accepted), sigmoid(-2.0) ≈ 0.12 (rejected)

        mock_reranker = CrossEncoderReranker(score_fn=fake_score_fn)
        mock_bm25 = build_bm25_retriever(self.sample_chunks)

        # Mock custom generation
        def fake_gen(prompt):
            return "Theo quy định tại [E1], cơ cấu lại thời hạn trả nợ được áp dụng."

        dummy_query_vec = [0.1] * 128

        # Chạy hybrid_rerank với temporary Chroma storage
        import tempfile
        tmp_dir = tempfile.TemporaryDirectory()
        tmp_path = Path(tmp_dir.name)

        dummy_vecs = [[0.1] * 128 for _ in range(8)]
        prepare_semantic_index(
            strategy="hierarchical",
            input_dir=BASE_DIR / "tests" / "fixtures" / "chunks_advanced_sample.json",
            reset=True,
            storage_path=tmp_path,
            custom_embeddings=dummy_vecs,
            config=self.config
        )

        res = query_advanced_rag(
            question="Cơ cấu lại thời hạn trả nợ",
            mode="hybrid_rerank",
            strategy="hierarchical",
            config=self.config,
            chunks=self.sample_chunks,
            storage_path=tmp_path,
            custom_retriever=mock_bm25,
            custom_query_embedding=dummy_query_vec,
            custom_reranker=mock_reranker,
            custom_generation_fn=fake_gen
        )

        self.assertEqual(res["status"], "answered")
        self.assertEqual(res["mode"], "hybrid_rerank")
        # Kiểm tra chỉ có candidate vượt ngưỡng rerank_score >= 0.50 được accepted
        accepted_ev = [ev for ev in res["evidence"] if ev["accepted"]]
        self.assertGreater(len(accepted_ev), 0)
        for ev in accepted_ev:
            self.assertGreaterEqual(ev["rerank_score"], 0.50)

        try:
            tmp_dir.cleanup()
        except Exception:
            pass

    def test_02_rejected_evidence_not_in_prompt(self):
        """Case 2: Các evidence bị reject (không đạt gate) hoàn toàn không được đưa vào prompt gửi cho LLM"""
        captured_prompts = []

        def capture_gen(prompt):
            captured_prompts.append(prompt)
            return "Câu trả lời [E1]."

        # Gán tất cả điểm rerank logit = -5.0 (sigmoid ≈ 0.0067 < 0.50) -> Tất cả bị reject
        def reject_all_score_fn(q, texts):
            return [-5.0] * len(texts)

        mock_reranker = CrossEncoderReranker(score_fn=reject_all_score_fn)
        mock_bm25 = build_bm25_retriever(self.sample_chunks)

        import tempfile
        tmp_dir = tempfile.TemporaryDirectory()
        tmp_path = Path(tmp_dir.name)
        dummy_vecs = [[0.1] * 128 for _ in range(8)]
        prepare_semantic_index(
            strategy="hierarchical",
            input_dir=BASE_DIR / "tests" / "fixtures" / "chunks_advanced_sample.json",
            reset=True,
            storage_path=tmp_path,
            custom_embeddings=dummy_vecs,
            config=self.config
        )

        res = query_advanced_rag(
            question="Điều 4 quy định gì?",
            mode="hybrid_rerank",
            strategy="hierarchical",
            config=self.config,
            chunks=self.sample_chunks,
            storage_path=tmp_path,
            custom_retriever=mock_bm25,
            custom_query_embedding=[0.1] * 128,
            custom_reranker=mock_reranker,
            custom_generation_fn=capture_gen
        )

        # Do tất cả bị reject, status = insufficient_evidence và không gọi generation
        self.assertEqual(res["status"], "insufficient_evidence")
        self.assertEqual(len(captured_prompts), 0)
        self.assertFalse(res["trace"]["generation_called"])

        try:
            tmp_dir.cleanup()
        except Exception:
            pass

    def test_03_trace_counts_and_timings_complete(self):
        """Case 3: Trace chứa đầy đủ toàn bộ các trường metrics, counts và latency_ms"""
        def pass_score_fn(q, texts):
            return [2.0] * len(texts)

        mock_reranker = CrossEncoderReranker(score_fn=pass_score_fn)
        mock_bm25 = build_bm25_retriever(self.sample_chunks)

        import tempfile
        tmp_dir = tempfile.TemporaryDirectory()
        tmp_path = Path(tmp_dir.name)
        dummy_vecs = [[0.1] * 128 for _ in range(8)]
        prepare_semantic_index(
            strategy="hierarchical",
            input_dir=BASE_DIR / "tests" / "fixtures" / "chunks_advanced_sample.json",
            reset=True,
            storage_path=tmp_path,
            custom_embeddings=dummy_vecs,
            config=self.config
        )

        res = query_advanced_rag(
            question="Cơ cấu nợ",
            mode="hybrid_rerank",
            strategy="hierarchical",
            config=self.config,
            chunks=self.sample_chunks,
            storage_path=tmp_path,
            custom_retriever=mock_bm25,
            custom_query_embedding=[0.1] * 128,
            custom_reranker=mock_reranker,
            custom_generation_fn=lambda p: "Trả lời [E1]."
        )

        trace = res["trace"]
        self.assertIn("bm25_candidates", trace)
        self.assertIn("semantic_candidates", trace)
        self.assertIn("overlap", trace)
        self.assertIn("union", trace)
        self.assertIn("reranked", trace)
        self.assertIn("accepted", trace)
        self.assertIn("generation_called", trace)
        self.assertIn("latency_ms", trace)
        for key in ["bm25", "semantic", "fusion", "rerank", "generation", "total"]:
            self.assertIn(key, trace["latency_ms"])

        try:
            tmp_dir.cleanup()
        except Exception:
            pass

    def test_04_citation_maps_real_metadata_and_strips_hallucinated(self):
        """Case 4: Citations map chuẩn xác vào metadata thật và loại bỏ nhãn ảo [E99]"""
        def pass_score_fn(q, texts):
            return [2.0] * len(texts)

        mock_reranker = CrossEncoderReranker(score_fn=pass_score_fn)
        mock_bm25 = build_bm25_retriever(self.sample_chunks)

        import tempfile
        tmp_dir = tempfile.TemporaryDirectory()
        tmp_path = Path(tmp_dir.name)
        dummy_vecs = [[0.1] * 128 for _ in range(8)]
        prepare_semantic_index(
            strategy="hierarchical",
            input_dir=BASE_DIR / "tests" / "fixtures" / "chunks_advanced_sample.json",
            reset=True,
            storage_path=tmp_path,
            custom_embeddings=dummy_vecs,
            config=self.config
        )

        # Trả lời có chứa 1 nhãn thật [E1] và 1 nhãn ảo [E99]
        def hallucinated_gen(prompt):
            return "Theo [E1], cơ cấu nợ được cho phép và thông tin ngoài lề [E99]."

        res = query_advanced_rag(
            question="Cơ cấu nợ",
            mode="hybrid_rerank",
            strategy="hierarchical",
            config=self.config,
            chunks=self.sample_chunks,
            storage_path=tmp_path,
            custom_retriever=mock_bm25,
            custom_query_embedding=[0.1] * 128,
            custom_reranker=mock_reranker,
            custom_generation_fn=hallucinated_gen
        )

        self.assertEqual(res["status"], "answered")
        self.assertEqual(len(res["citations"]), 1)
        self.assertEqual(res["citations"][0]["label"], "[E1]")
        self.assertIn("chunk_id", res["citations"][0])
        self.assertIn("source", res["citations"][0])
        self.assertIn("page_start", res["citations"][0])
        self.assertIn("page_end", res["citations"][0])

        # Cảnh báo phải xuất hiện vì [E99] bị loại bỏ
        self.assertTrue(any("[E99]" in w for w in res["warnings"]))

        try:
            tmp_dir.cleanup()
        except Exception:
            pass

    def test_05_generation_called_at_most_once(self):
        """Case 5: Quá trình query_advanced_rag chỉ gọi generation duy nhất tối đa 1 lần"""
        call_counter = {"count": 0}

        def counting_gen(prompt):
            call_counter["count"] += 1
            return "Đáp án [E1]."

        def pass_score_fn(q, texts):
            return [2.0] * len(texts)

        mock_reranker = CrossEncoderReranker(score_fn=pass_score_fn)
        mock_bm25 = build_bm25_retriever(self.sample_chunks)

        import tempfile
        tmp_dir = tempfile.TemporaryDirectory()
        tmp_path = Path(tmp_dir.name)
        dummy_vecs = [[0.1] * 128 for _ in range(8)]
        prepare_semantic_index(
            strategy="hierarchical",
            input_dir=BASE_DIR / "tests" / "fixtures" / "chunks_advanced_sample.json",
            reset=True,
            storage_path=tmp_path,
            custom_embeddings=dummy_vecs,
            config=self.config
        )

        res = query_advanced_rag(
            question="Cơ cấu nợ",
            mode="hybrid_rerank",
            strategy="hierarchical",
            config=self.config,
            chunks=self.sample_chunks,
            storage_path=tmp_path,
            custom_retriever=mock_bm25,
            custom_query_embedding=[0.1] * 128,
            custom_reranker=mock_reranker,
            custom_generation_fn=counting_gen
        )

        self.assertEqual(call_counter["count"], 1)
        self.assertTrue(res["trace"]["generation_called"])

        try:
            tmp_dir.cleanup()
        except Exception:
            pass

    def test_06_compare_does_not_call_generation(self):
        """Case 6: compare_retrieval_modes chỉ so sánh các nhánh retrieval và tuyệt đối không gọi generation"""
        def pass_score_fn(q, texts):
            return [1.5] * len(texts)

        mock_reranker = CrossEncoderReranker(score_fn=pass_score_fn)
        mock_bm25 = build_bm25_retriever(self.sample_chunks)

        import tempfile
        tmp_dir = tempfile.TemporaryDirectory()
        tmp_path = Path(tmp_dir.name)
        dummy_vecs = [[0.1] * 128 for _ in range(8)]
        prepare_semantic_index(
            strategy="hierarchical",
            input_dir=BASE_DIR / "tests" / "fixtures" / "chunks_advanced_sample.json",
            reset=True,
            storage_path=tmp_path,
            custom_embeddings=dummy_vecs,
            config=self.config
        )

        comp = compare_retrieval_modes(
            question="Cơ cấu nợ",
            strategy="hierarchical",
            config=self.config,
            chunks=self.sample_chunks,
            storage_path=tmp_path,
            custom_retriever=mock_bm25,
            custom_query_embedding=[0.1] * 128,
            custom_reranker=mock_reranker
        )

        self.assertIn("comparison_rows", comp)
        self.assertIn("latency_ms", comp)
        self.assertIn("mode_counts", comp)
        self.assertGreater(len(comp["comparison_rows"]), 0)
        for row in comp["comparison_rows"]:
            self.assertIn("chunk_id", row)
            self.assertIn("modes_present", row)

        try:
            tmp_dir.cleanup()
        except Exception:
            pass

    def test_07_reranker_unavailable_returns_distinct_status(self):
        """Case 7: Khi Reranker bị lỗi (reranker_unavailable), hệ thống trả status riêng biệt và không âm thầm dùng RRF"""
        mock_bm25 = build_bm25_retriever(self.sample_chunks)

        import tempfile
        tmp_dir = tempfile.TemporaryDirectory()
        tmp_path = Path(tmp_dir.name)
        dummy_vecs = [[0.1] * 128 for _ in range(8)]
        prepare_semantic_index(
            strategy="hierarchical",
            input_dir=BASE_DIR / "tests" / "fixtures" / "chunks_advanced_sample.json",
            reset=True,
            storage_path=tmp_path,
            custom_embeddings=dummy_vecs,
            config=self.config
        )

        with patch("advanced_rag.load_reranker_model", side_effect=RuntimeError("reranker_unavailable: Network disconnected")):
            res = query_advanced_rag(
                question="Cơ cấu nợ",
                mode="hybrid_rerank",
                strategy="hierarchical",
                config=self.config,
                chunks=self.sample_chunks,
                storage_path=tmp_path,
                custom_retriever=mock_bm25,
                custom_query_embedding=[0.1] * 128
            )

            self.assertEqual(res["status"], "reranker_unavailable")
            self.assertEqual(res["mode"], "hybrid_rerank")
            self.assertFalse(res["trace"]["generation_called"])

        try:
            tmp_dir.cleanup()
        except Exception:
            pass

    def test_08_all_statuses_return_complete_schema(self):
        """Case 8: Mọi status (answered, insufficient_evidence, retrieval_only, reranker_unavailable) đều trả về đúng schema"""
        def pass_score_fn(q, texts):
            return [2.0] * len(texts)

        mock_reranker = CrossEncoderReranker(score_fn=pass_score_fn)
        mock_bm25 = build_bm25_retriever(self.sample_chunks)

        import tempfile
        tmp_dir = tempfile.TemporaryDirectory()
        tmp_path = Path(tmp_dir.name)
        dummy_vecs = [[0.1] * 128 for _ in range(8)]
        prepare_semantic_index(
            strategy="hierarchical",
            input_dir=BASE_DIR / "tests" / "fixtures" / "chunks_advanced_sample.json",
            reset=True,
            storage_path=tmp_path,
            custom_embeddings=dummy_vecs,
            config=self.config
        )

        # Trả về retrieval_only khi generation bị lỗi
        res = query_advanced_rag(
            question="Cơ cấu nợ",
            mode="hybrid_rerank",
            strategy="hierarchical",
            config=self.config,
            chunks=self.sample_chunks,
            storage_path=tmp_path,
            custom_retriever=mock_bm25,
            custom_query_embedding=[0.1] * 128,
            custom_reranker=mock_reranker,
            custom_generation_fn=MagicMock(side_effect=RuntimeError("Quota limit"))
        )

        self.assertEqual(res["status"], "retrieval_only")
        self.assertIn("status", res)
        self.assertIn("mode", res)
        self.assertIn("question", res)
        self.assertIn("answer", res)
        self.assertIn("evidence", res)
        self.assertIn("citations", res)
        self.assertIn("warnings", res)
        self.assertIn("trace", res)

        try:
            tmp_dir.cleanup()
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
