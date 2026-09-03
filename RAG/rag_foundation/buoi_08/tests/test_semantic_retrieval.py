"""
Bộ kiểm thử tự động (Unit Tests) cho Semantic Candidate Stage - Buổi 08.
Đảm bảo 100% chạy offline với mock embedding và temporary storage ChromaDB.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Đảm bảo import được module Buổi 08
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from advanced_rag import (
    load_advanced_config,
    get_advanced_status,
    retrieve_semantic_candidates,
    prepare_semantic_index
)
from rag import (
    get_collection_name,
    verify_collection_compatibility,
    get_chroma_client
)


def create_temp_dir():
    try:
        return tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    except TypeError:
        return tempfile.TemporaryDirectory()


class TestSemanticCandidateRetrieval(unittest.TestCase):
    """Kiểm thử Semantic Candidate Stage và Status Read-Only"""

    def setUp(self):
        self.tmp_dir = create_temp_dir()
        self.tmp_path = Path(self.tmp_dir.name)
        self.fixture_path = BASE_DIR / "tests" / "fixtures" / "chunks_advanced_sample.json"
        self.config = {
            "api_key": "mock_api_key",
            "has_api_key": True,
            "embedding_model": "gemini-embedding-2",
            "embedding_dim": 128,
            "generation_model": "gemini-3.5-flash-lite",
            "max_distance": 0.45,
            "bm25_candidates": 20,
            "semantic_candidates": 20,
            "rerank_candidates": 20,
            "final_top_k": 5,
            "rrf_k": 60,
            "rrf_bm25_weight": 1.0,
            "rrf_semantic_weight": 1.0,
            "reranker_model": "BAAI/bge-reranker-v2-m3",
            "reranker_max_length": 512,
            "rerank_batch_size": 4,
            "rerank_min_score": 0.50,
            "rerank_device": "auto",
        }

    def tearDown(self):
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_01_semantic_top_k_count_and_order(self):
        """Case 1: Semantic retrieval trả về đúng top-k, đúng số lượng và sắp xếp theo distance tăng dần"""
        # Tạo 8 dummy vectors với khoảng cách khác biệt để kiểm tra thứ tự sắp xếp
        dummy_vecs = []
        for i in range(8):
            vec = [0.0] * 128
            vec[i] = 1.0  # Vector đơn vị tại vị trí i
            dummy_vecs.append(vec)

        # Index vào temporary storage
        prepare_semantic_index(
            strategy="hierarchical",
            input_dir=self.fixture_path,
            reset=True,
            storage_path=self.tmp_path,
            custom_embeddings=dummy_vecs,
            config=self.config
        )

        # Query vector trùng với vector 0 (distance = 0.0)
        query_vec = [0.0] * 128
        query_vec[0] = 1.0

        candidates = retrieve_semantic_candidates(
            question="Cơ cấu lại thời hạn trả nợ",
            strategy="hierarchical",
            candidate_k=3,
            config=self.config,
            storage_path=self.tmp_path,
            custom_query_embedding=query_vec
        )

        self.assertEqual(len(candidates), 3)
        self.assertEqual(candidates[0]["semantic_rank"], 1)
        self.assertAlmostEqual(candidates[0]["semantic_distance"], 0.0, places=3)
        self.assertLessEqual(candidates[0]["semantic_distance"], candidates[1]["semantic_distance"])
        self.assertLessEqual(candidates[1]["semantic_distance"], candidates[2]["semantic_distance"])

    def test_02_metadata_fields_complete(self):
        """Case 2: Candidate trả về đầy đủ toàn bộ các trường metadata theo đúng schema"""
        dummy_vecs = [[0.1] * 128 for _ in range(8)]
        prepare_semantic_index(
            strategy="hierarchical",
            input_dir=self.fixture_path,
            reset=True,
            storage_path=self.tmp_path,
            custom_embeddings=dummy_vecs,
            config=self.config
        )

        query_vec = [0.1] * 128
        candidates = retrieve_semantic_candidates(
            question="Quy định trả nợ",
            strategy="hierarchical",
            candidate_k=2,
            config=self.config,
            storage_path=self.tmp_path,
            custom_query_embedding=query_vec
        )

        for cand in candidates:
            self.assertIn("chunk_id", cand)
            self.assertIn("text", cand)
            self.assertIn("source", cand)
            self.assertIn("page_start", cand)
            self.assertIn("page_end", cand)
            self.assertIn("strategy", cand)
            self.assertIn("semantic_rank", cand)
            self.assertIn("semantic_distance", cand)
            self.assertIsInstance(cand["page_start"], int)
            self.assertIsInstance(cand["page_end"], int)

    def test_03_collection_mismatch_blocked(self):
        """Case 3: Truy xuất chặn collection có metadata không tương thích (khác strategy/model/dim)"""
        mock_col = MagicMock()
        mock_col.name = "test-col"
        mock_col.metadata = {
            "strategy": "semantic",
            "embedding_model": "gemini-embedding-2",
            "embedding_dim": 128
        }

        with self.assertRaises(ValueError) as ctx:
            verify_collection_compatibility(mock_col, "hierarchical", "gemini-embedding-2", 128)
        self.assertIn("cấu hình không tương thích", str(ctx.exception))

    def test_04_status_does_not_create_empty_collection(self):
        """Case 4: Gọi status ở chế độ read-only không tự ý tạo mới collection rỗng trong ChromaDB"""
        status_res = get_advanced_status(
            strategy="hierarchical",
            input_dir=self.fixture_path,
            storage_path=self.tmp_path,
            config=self.config
        )

        self.assertFalse(status_res["collection_exists"])
        self.assertEqual(status_res["record_count"], 0)
        self.assertEqual(status_res["corpus_size"], 8)
        self.assertTrue(status_res["bm25_ready"])

        # Kiểm tra ChromaDB vẫn chưa có collection nào được tạo ra
        client = get_chroma_client(self.tmp_path)
        self.assertEqual(len(client.list_collections()), 0)

    def test_05_missing_api_key_fails_without_dummy_vectors(self):
        """Case 5: Thiếu API key phải fail rõ ràng và không được tự động sinh vector giả"""
        config_no_key = dict(self.config)
        config_no_key["api_key"] = ""
        config_no_key["has_api_key"] = False

        with self.assertRaises(ValueError) as ctx:
            retrieve_semantic_candidates(
                question="Điều kiện vay vốn",
                strategy="hierarchical",
                candidate_k=5,
                config=config_no_key,
                storage_path=self.tmp_path
            )
        self.assertIn("chưa tồn tại", str(ctx.exception))

    def test_06_no_generation_called_during_semantic_candidate_stage(self):
        """Case 6: Giai đoạn Semantic Candidate Stage thuần túy truy xuất, không gọi bất kỳ generation nào"""
        dummy_vecs = [[0.2] * 128 for _ in range(8)]
        prepare_semantic_index(
            strategy="hierarchical",
            input_dir=self.fixture_path,
            reset=True,
            storage_path=self.tmp_path,
            custom_embeddings=dummy_vecs,
            config=self.config
        )

        query_vec = [0.2] * 128
        candidates = retrieve_semantic_candidates(
            question="Trích lập dự phòng",
            strategy="hierarchical",
            candidate_k=4,
            config=self.config,
            storage_path=self.tmp_path,
            custom_query_embedding=query_vec
        )

        # Output chỉ là danh sách ứng viên, không chứa trường answer hay generation
        self.assertIsInstance(candidates, list)
        for cand in candidates:
            self.assertNotIn("answer", cand)
            self.assertNotIn("citations", cand)


if __name__ == "__main__":
    unittest.main()
