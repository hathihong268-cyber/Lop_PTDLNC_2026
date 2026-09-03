"""
Bộ kiểm thử tự động (Unit Tests) cho Reciprocal Rank Fusion & Hybrid Retrieval - Buổi 08.
Đảm bảo 100% chạy offline, kiểm thử công thức số học RRF, tie-break, metadata validation và pipeline trace.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Đảm bảo import được module Buổi 08
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from advanced_rag import (
    reciprocal_rank_fusion,
    retrieve_hybrid_candidates
)


class TestReciprocalRankFusion(unittest.TestCase):
    """Kiểm thử Thuật toán Reciprocal Rank Fusion (RRF) và Hybrid Pipeline Trace"""

    def setUp(self):
        self.bm25_results = [
            {
                "chunk_id": "chunk_01",
                "text": "Nội dung Điều 4 về cơ cấu nợ.",
                "source": "TT_02.pdf",
                "page_start": 1,
                "page_end": 2,
                "strategy": "hierarchical",
                "bm25_rank": 1,
                "bm25_score": 5.5
            },
            {
                "chunk_id": "chunk_02",
                "text": "Nội dung Điều 8 về nhu cầu vốn.",
                "source": "TT_39.pdf",
                "page_start": 3,
                "page_end": 4,
                "strategy": "hierarchical",
                "bm25_rank": 2,
                "bm25_score": 4.0
            }
        ]

        self.semantic_results = [
            {
                "chunk_id": "chunk_01",
                "text": "Nội dung Điều 4 về cơ cấu nợ.",
                "source": "TT_02.pdf",
                "page_start": 1,
                "page_end": 2,
                "strategy": "hierarchical",
                "semantic_rank": 1,
                "semantic_distance": 0.15
            },
            {
                "chunk_id": "chunk_03",
                "text": "Nội dung Điều 13 về lãi suất cho vay.",
                "source": "TT_39.pdf",
                "page_start": 5,
                "page_end": 6,
                "strategy": "hierarchical",
                "semantic_rank": 2,
                "semantic_distance": 0.25
            }
        ]

    def test_01_rrf_formula_arithmetic_precision(self):
        """Case 1: Công thức RRF tính toán chuẩn xác theo từng số hạng"""
        k_rrf = 60
        w_b = 1.0
        w_s = 1.0

        fused, stats = reciprocal_rank_fusion(
            bm25_results=self.bm25_results,
            semantic_results=self.semantic_results,
            k_rrf=k_rrf,
            w_bm25=w_b,
            w_semantic=w_s
        )

        # chunk_01 xuất hiện ở rank 1 cả 2 nhánh:
        # score = 1.0 / (60 + 1) + 1.0 / (60 + 1) = 2 / 61 ≈ 0.032787
        expected_score_01 = (1.0 / 61.0) + (1.0 / 61.0)
        self.assertEqual(fused[0]["chunk_id"], "chunk_01")
        self.assertAlmostEqual(fused[0]["rrf_score"], expected_score_01, places=5)
        self.assertEqual(fused[0]["fused_rank"], 1)

    def test_02_candidate_overlap_no_duplicates(self):
        """Case 2: Candidate xuất hiện ở cả hai nhánh được union theo chunk_id và không bị nhân bản"""
        fused, stats = reciprocal_rank_fusion(
            bm25_results=self.bm25_results,
            semantic_results=self.semantic_results,
            k_rrf=60
        )

        chunk_ids = [c["chunk_id"] for c in fused]
        self.assertEqual(len(chunk_ids), len(set(chunk_ids)))
        self.assertEqual(len(fused), 3)  # chunk_01 (overlap), chunk_02 (bm25 only), chunk_03 (semantic only)
        self.assertEqual(fused[0]["matched_by"], ["bm25", "semantic"])

    def test_03_candidate_bm25_only_preserved(self):
        """Case 3: Candidate chỉ xuất hiện ở nhánh BM25 vẫn được bảo toàn với semantic_rank = None"""
        fused, _ = reciprocal_rank_fusion(
            bm25_results=self.bm25_results,
            semantic_results=self.semantic_results,
            k_rrf=60
        )

        c2 = next(c for c in fused if c["chunk_id"] == "chunk_02")
        self.assertIsNotNone(c2["bm25_rank"])
        self.assertIsNone(c2["semantic_rank"])
        self.assertIsNone(c2["semantic_distance"])
        self.assertEqual(c2["matched_by"], ["bm25"])
        # score = 1.0 / (60 + 2) = 1/62 ≈ 0.016129
        self.assertAlmostEqual(c2["rrf_score"], 1.0 / 62.0, places=5)

    def test_04_candidate_semantic_only_preserved(self):
        """Case 4: Candidate chỉ xuất hiện ở nhánh Semantic vẫn được bảo toàn với bm25_rank = None"""
        fused, _ = reciprocal_rank_fusion(
            bm25_results=self.bm25_results,
            semantic_results=self.semantic_results,
            k_rrf=60
        )

        c3 = next(c for c in fused if c["chunk_id"] == "chunk_03")
        self.assertIsNone(c3["bm25_rank"])
        self.assertIsNone(c3["bm25_score"])
        self.assertIsNotNone(c3["semantic_rank"])
        self.assertEqual(c3["matched_by"], ["semantic"])
        self.assertAlmostEqual(c3["rrf_score"], 1.0 / 62.0, places=5)

    def test_05_weight_zero_removes_branch_contribution(self):
        """Case 5: Thiết lập trọng số = 0.0 sẽ triệt tiêu đóng góp điểm của nhánh tương ứng"""
        fused, _ = reciprocal_rank_fusion(
            bm25_results=self.bm25_results,
            semantic_results=self.semantic_results,
            k_rrf=60,
            w_bm25=1.0,
            w_semantic=0.0  # Tắt điểm semantic
        )

        # chunk_03 chỉ có semantic nên khi w_semantic=0 điểm phải bằng 0.0
        c3 = next(c for c in fused if c["chunk_id"] == "chunk_03")
        self.assertEqual(c3["rrf_score"], 0.0)

        # chunk_01 chỉ nhận điểm từ BM25 (1/61)
        c1 = next(c for c in fused if c["chunk_id"] == "chunk_01")
        self.assertAlmostEqual(c1["rrf_score"], 1.0 / 61.0, places=5)

    def test_06_deterministic_tie_breaking(self):
        """Case 6: Khi 2 candidate có cùng RRF score, áp dụng tie-break deterministic và ổn định"""
        b_list = [
            {"chunk_id": "chunk_X", "text": "T1", "source": "f.pdf", "page_start": 1, "page_end": 1, "bm25_rank": 1, "bm25_score": 1.0},
            {"chunk_id": "chunk_B", "text": "T2", "source": "f.pdf", "page_start": 1, "page_end": 1, "bm25_rank": 2, "bm25_score": 0.5},
            {"chunk_id": "chunk_A", "text": "T3", "source": "f.pdf", "page_start": 1, "page_end": 1, "bm25_rank": 2, "bm25_score": 0.5},
        ]
        s_list = []  # Không có semantic

        fused, _ = reciprocal_rank_fusion(b_list, s_list, k_rrf=60, w_bm25=1.0, w_semantic=1.0)

        # chunk_A và chunk_B cùng có rank 2 (cùng RRF score = 1/62), tie-break theo chunk_id: chunk_A -> chunk_B
        self.assertEqual(fused[0]["chunk_id"], "chunk_X")
        self.assertEqual(fused[1]["chunk_id"], "chunk_A")
        self.assertEqual(fused[2]["chunk_id"], "chunk_B")

    def test_07_metadata_mismatch_fails_clearly(self):
        """Case 7: Cùng chunk_id nhưng metadata (text/source/page) sai lệch giữa 2 nhánh phải raise ValueError"""
        corrupted_semantic = [
            {
                "chunk_id": "chunk_01",
                "text": "Nội dung bị sai lệch khác với BM25.",  # Mismatch text
                "source": "TT_02.pdf",
                "page_start": 1,
                "page_end": 2,
                "semantic_rank": 1,
                "semantic_distance": 0.15
            }
        ]

        with self.assertRaises(ValueError) as ctx:
            reciprocal_rank_fusion(self.bm25_results, corrupted_semantic)
        self.assertIn("Metadata mismatch", str(ctx.exception))

    def test_08_pipeline_trace_counts_and_latency(self):
        """Case 8: Pipeline trace ghi nhận đầy đủ số lượng candidates từng chặng và latency"""
        fused, stats = reciprocal_rank_fusion(
            bm25_results=self.bm25_results,
            semantic_results=self.semantic_results,
            k_rrf=60,
            top_n=2
        )

        self.assertEqual(stats["bm25_candidate_count"], 2)
        self.assertEqual(stats["semantic_candidate_count"], 2)
        self.assertEqual(stats["union_count"], 3)
        self.assertEqual(stats["overlap_count"], 1)
        self.assertEqual(stats["fused_count"], 2)  # Cắt theo top_n=2

    def test_09_hybrid_calls_each_retriever_once(self):
        """Case 9: Pipeline Hybrid Search gọi đúng mỗi nhánh retrieval một lần"""
        import tempfile
        tmp_dir = tempfile.TemporaryDirectory()
        tmp_path = Path(tmp_dir.name)

        config = {
            "api_key": "mock",
            "has_api_key": True,
            "embedding_model": "gemini-embedding-2",
            "embedding_dim": 128,
            "generation_model": "gemini-3.5-flash-lite",
            "max_distance": 0.45,
            "bm25_candidates": 2,
            "semantic_candidates": 2,
            "rerank_candidates": 5,
            "final_top_k": 2,
            "rrf_k": 60,
            "rrf_bm25_weight": 1.0,
            "rrf_semantic_weight": 1.0,
            "reranker_model": "BAAI/bge-reranker-v2-m3",
            "reranker_max_length": 512,
            "rerank_batch_size": 4,
            "rerank_min_score": 0.50,
            "rerank_device": "auto",
        }

        fixture_path = BASE_DIR / "tests" / "fixtures" / "chunks_advanced_sample.json"
        dummy_vecs = [[0.1] * 128 for _ in range(8)]
        from advanced_rag import prepare_semantic_index
        prepare_semantic_index(
            strategy="hierarchical",
            input_dir=fixture_path,
            reset=True,
            storage_path=tmp_path,
            custom_embeddings=dummy_vecs,
            config=config
        )

        mock_retriever = MagicMock()
        mock_retriever.search.return_value = self.bm25_results

        # Gọi hybrid retrieval với mock retriever, custom storage path và dummy query embedding
        dummy_query_vec = [0.1] * 128
        res = retrieve_hybrid_candidates(
            question="Cơ cấu thời hạn trả nợ",
            strategy="hierarchical",
            config=config,
            chunks=self.bm25_results,
            storage_path=tmp_path,
            custom_retriever=mock_retriever,
            custom_query_embedding=dummy_query_vec
        )

        # Kiểm tra retriever được gọi đúng 1 lần
        mock_retriever.search.assert_called_once()
        self.assertIn("trace", res)
        self.assertIn("latency_ms", res["trace"])
        self.assertIn("bm25", res["trace"]["latency_ms"])
        self.assertIn("semantic", res["trace"]["latency_ms"])
        self.assertIn("fusion", res["trace"]["latency_ms"])

        try:
            tmp_dir.cleanup()
        except Exception:
            pass

    def test_10_no_reranker_or_generation_loaded(self):
        """Case 10: Quy trình Hybrid Fusion hoàn toàn không gọi Reranker model hay LLM generation"""
        fused, _ = reciprocal_rank_fusion(self.bm25_results, self.semantic_results)
        for cand in fused:
            self.assertNotIn("rerank_score", cand)
            self.assertNotIn("answer", cand)
            self.assertNotIn("citations", cand)


if __name__ == "__main__":
    unittest.main()
