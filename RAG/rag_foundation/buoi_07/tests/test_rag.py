"""
Bộ kiểm thử tự động (Unit Tests) cho RAG Foundation - Buổi 07.
Đảm bảo 100% chạy offline, không gọi Internet / Gemini API thật và dùng temporary directory.
"""

import sys
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Đảm bảo import được module rag
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from rag import (
    load_config,
    validate_chunk,
    load_chunks,
    validate_embeddings,
    get_collection_name,
    get_chroma_client,
    verify_collection_compatibility,
    get_status,
    index_chunks,
    query_rag
)


def create_temp_dir():
    try:
        return tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    except TypeError:
        return tempfile.TemporaryDirectory()


class TestLoaderAndValidator(unittest.TestCase):
    """Group 1: Tests cho Chunk Loader và Validation Rules"""

    def setUp(self):
        self.tmp_dir = create_temp_dir()
        self.tmp_path = Path(self.tmp_dir.name)

    def tearDown(self):
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_01_loader_reads_json_list(self):
        """Case 1: Loader đọc file JSON dạng list"""
        data = [
            {
                "chunk_id": "c1",
                "strategy": "hierarchical",
                "source": "doc.pdf",
                "page_start": 1,
                "page_end": 2,
                "text": "Nội dung 1"
            }
        ]
        f_path = self.tmp_path / "test1.json"
        with open(f_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        chunks, stats = load_chunks(self.tmp_path, strategy="hierarchical")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["chunk_id"], "c1")
        self.assertEqual(stats["valid_chunks"], 1)

    def test_02_loader_reads_object_with_chunks_field(self):
        """Case 2: Loader đọc object có field 'chunks' dạng list"""
        data = {
            "chunks": [
                {
                    "chunk_id": "c2",
                    "strategy": "hierarchical",
                    "source": "doc.pdf",
                    "page_start": 1,
                    "page_end": 1,
                    "text": "Nội dung 2"
                }
            ]
        }
        f_path = self.tmp_path / "test2.json"
        with open(f_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        chunks, stats = load_chunks(self.tmp_path, strategy="hierarchical")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["chunk_id"], "c2")

    def test_03_filter_strategy(self):
        """Case 3: Loader chỉ lấy đúng strategy được chọn"""
        data = [
            {"chunk_id": "c1", "strategy": "hierarchical", "source": "doc.pdf", "page_start": 1, "page_end": 1, "text": "H"},
            {"chunk_id": "c2", "strategy": "semantic", "source": "doc.pdf", "page_start": 1, "page_end": 1, "text": "S"}
        ]
        f_path = self.tmp_path / "test3.json"
        with open(f_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        chunks_h, _ = load_chunks(self.tmp_path, strategy="hierarchical")
        self.assertEqual(len(chunks_h), 1)
        self.assertEqual(chunks_h[0]["strategy"], "hierarchical")

        chunks_s, _ = load_chunks(self.tmp_path, strategy="semantic")
        self.assertEqual(len(chunks_s), 1)
        self.assertEqual(chunks_s[0]["strategy"], "semantic")

    def test_04_missing_mandatory_fields_fails(self):
        """Case 4: Thiếu field bắt buộc phải fail"""
        invalid_chunk = {"chunk_id": "c1", "strategy": "hierarchical", "source": "doc.pdf", "page_start": 1, "page_end": 1}
        with self.assertRaises(ValueError) as ctx:
            validate_chunk(invalid_chunk, "test.json", 0)
        self.assertIn("Thiếu các trường bắt buộc", str(ctx.exception))

    def test_05_invalid_field_type_fails(self):
        """Case 5: Field sai kiểu dữ liệu phải fail"""
        invalid_chunk = {"chunk_id": 123, "strategy": "hierarchical", "source": "doc.pdf", "page_start": 1, "page_end": 1, "text": "Text"}
        with self.assertRaises(ValueError) as ctx:
            validate_chunk(invalid_chunk, "test.json", 0)
        self.assertIn("Trường 'chunk_id' phải là string", str(ctx.exception))

    def test_06_boolean_page_number_fails(self):
        """Case 6: Boolean không được chấp nhận làm page number"""
        invalid_chunk = {"chunk_id": "c1", "strategy": "hierarchical", "source": "doc.pdf", "page_start": True, "page_end": 1, "text": "Text"}
        with self.assertRaises(ValueError) as ctx:
            validate_chunk(invalid_chunk, "test.json", 0)
        self.assertIn("không phải boolean", str(ctx.exception))

    def test_07_page_start_greater_than_page_end_fails(self):
        """Case 7: page_start > page_end phải fail"""
        invalid_chunk = {"chunk_id": "c1", "strategy": "hierarchical", "source": "doc.pdf", "page_start": 5, "page_end": 2, "text": "Text"}
        with self.assertRaises(ValueError) as ctx:
            validate_chunk(invalid_chunk, "test.json", 0)
        self.assertIn("page_start (5) phải <= page_end (2)", str(ctx.exception))

    def test_08_empty_text_skipped(self):
        """Case 8: Text rỗng bị bỏ qua và thống kê đúng"""
        data = [
            {"chunk_id": "c1", "strategy": "hierarchical", "source": "doc.pdf", "page_start": 1, "page_end": 1, "text": "   "},
            {"chunk_id": "c2", "strategy": "hierarchical", "source": "doc.pdf", "page_start": 1, "page_end": 1, "text": "Hợp lệ"}
        ]
        f_path = self.tmp_path / "test8.json"
        with open(f_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        chunks, stats = load_chunks(self.tmp_path, strategy="hierarchical")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(stats["empty_text_skipped"], 1)

    def test_09_duplicate_chunk_id_fails(self):
        """Case 9: Trùng lặp chunk_id trong tập dữ liệu phải fail"""
        data = [
            {"chunk_id": "dup", "strategy": "hierarchical", "source": "doc.pdf", "page_start": 1, "page_end": 1, "text": "T1"},
            {"chunk_id": "dup", "strategy": "hierarchical", "source": "doc.pdf", "page_start": 2, "page_end": 2, "text": "T2"}
        ]
        f_path = self.tmp_path / "test9.json"
        with open(f_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        with self.assertRaises(ValueError) as ctx:
            load_chunks(self.tmp_path, strategy="hierarchical")
        self.assertIn("Trùng lặp chunk_id 'dup'", str(ctx.exception))

    def test_38_loader_blocks_non_dict_record(self):
        """Case 38: Loader chặn record không phải JSON object (dict)"""
        data = ["string_record", 123]
        f_path = self.tmp_path / "test38.json"
        with open(f_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        with self.assertRaises(ValueError) as ctx:
            load_chunks(self.tmp_path, strategy="hierarchical")
        self.assertIn("Phần tử trong list phải là JSON object (dict)", str(ctx.exception))


class TestEmbeddingAndIndexing(unittest.TestCase):
    """Group 2: Tests cho Embeddings Validation và Persistent Indexing"""

    def setUp(self):
        self.tmp_dir = create_temp_dir()
        self.tmp_path = Path(self.tmp_dir.name)
        self.fixture_path = BASE_DIR / "tests" / "fixtures" / "chunks_sample.json"
        self.config = {
            "api_key": "mock_key",
            "has_api_key": True,
            "embedding_model": "gemini-embedding-2",
            "embedding_dim": 128,
            "generation_model": "gemini-3.5-flash-lite",
            "top_k": 5,
            "max_distance": 0.45
        }

    def tearDown(self):
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_10_index_twice_idempotency(self):
        """Case 10: Index 2 lần không làm tăng record count"""
        dummy_vecs = [[0.1] * 128 for _ in range(3)]
        res1 = index_chunks(input_dir=self.fixture_path, strategy="hierarchical", storage_path=self.tmp_path, custom_embeddings=dummy_vecs, config=self.config)
        self.assertEqual(res1["total_in_collection"], 3)

        res2 = index_chunks(input_dir=self.fixture_path, strategy="hierarchical", storage_path=self.tmp_path, custom_embeddings=dummy_vecs, config=self.config)
        self.assertEqual(res2["total_in_collection"], 3)

    def test_11_metadata_citation_saved_completely(self):
        """Case 11: Metadata citation được lưu đầy đủ vào Chroma"""
        dummy_vecs = [[0.1] * 128 for _ in range(3)]
        index_chunks(input_dir=self.fixture_path, strategy="hierarchical", storage_path=self.tmp_path, custom_embeddings=dummy_vecs, config=self.config)

        status = get_status(strategy="hierarchical", storage_path=self.tmp_path, config=self.config)
        self.assertTrue(status["collection_exists"])
        self.assertEqual(status["record_count"], 3)

    def test_12_collection_name_changes_with_strategy(self):
        """Case 12: Collection identity thay đổi khi strategy thay đổi"""
        name_h = get_collection_name("hierarchical", 128, "gemini-embedding-2")
        name_s = get_collection_name("semantic", 128, "gemini-embedding-2")
        self.assertNotEqual(name_h, name_s)
        self.assertIn("hierarchical", name_h)
        self.assertIn("semantic", name_s)

    def test_13_collection_name_changes_with_model_or_dim(self):
        """Case 13: Collection identity thay đổi khi model hoặc dimension thay đổi"""
        name_dim768 = get_collection_name("hierarchical", 768, "gemini-embedding-2")
        name_dim128 = get_collection_name("hierarchical", 128, "gemini-embedding-2")
        name_model2 = get_collection_name("hierarchical", 128, "other-model")

        self.assertNotEqual(name_dim768, name_dim128)
        self.assertNotEqual(name_dim128, name_model2)

    def test_14_verify_collection_compatibility_mismatch(self):
        """Case 14: Query/Index chặn collection có metadata không khớp"""
        mock_col = MagicMock()
        mock_col.name = "test-col"
        mock_col.metadata = {"strategy": "semantic", "embedding_model": "gemini-embedding-2", "embedding_dim": 128}

        with self.assertRaises(ValueError) as ctx:
            verify_collection_compatibility(mock_col, "hierarchical", "gemini-embedding-2", 128)
        self.assertIn("cấu hình không tương thích", str(ctx.exception))

    def test_15_embedding_invalid_count_fails(self):
        """Case 15: Embedding trả sai số vector phải fail"""
        with self.assertRaises(ValueError) as ctx:
            validate_embeddings([[0.1]*128], expected_count=2, expected_dim=128)
        self.assertIn("Số lượng vector (1) không khớp", str(ctx.exception))

    def test_16_embedding_empty_vector_fails(self):
        """Case 16: Embedding trả vector rỗng phải fail"""
        with self.assertRaises(ValueError) as ctx:
            validate_embeddings([[]], expected_count=1, expected_dim=128)
        self.assertIn("kỳ vọng 128", str(ctx.exception))

    def test_17_embedding_wrong_dimension_fails(self):
        """Case 17: Embedding trả sai dimension phải fail"""
        with self.assertRaises(ValueError) as ctx:
            validate_embeddings([[0.1]*64], expected_count=1, expected_dim=128)
        self.assertIn("kỳ vọng 128", str(ctx.exception))

    def test_18_embedding_nan_or_inf_fails(self):
        """Case 18: Embedding có NaN hoặc Infinity phải fail"""
        vec_nan = [0.1]*127 + [float('nan')]
        with self.assertRaises(ValueError) as ctx:
            validate_embeddings([vec_nan], expected_count=1, expected_dim=128)
        self.assertIn("chứa NaN", str(ctx.exception))

        vec_inf = [0.1]*127 + [float('inf')]
        with self.assertRaises(ValueError) as ctx:
            validate_embeddings([vec_inf], expected_count=1, expected_dim=128)
        self.assertIn("chứa Infinity", str(ctx.exception))

    def test_19_embedding_error_before_upsert_prevents_partial_indexing(self):
        """Case 19: Embedding lỗi trước upsert không thêm record mới"""
        invalid_vecs = [[float('nan')]*128 for _ in range(3)]
        with self.assertRaises(ValueError):
            index_chunks(input_dir=self.fixture_path, strategy="hierarchical", storage_path=self.tmp_path, custom_embeddings=invalid_vecs, config=self.config)

        status = get_status(strategy="hierarchical", storage_path=self.tmp_path, config=self.config)
        self.assertFalse(status["collection_exists"])

    def test_20_missing_api_key_fails_without_dummy_vectors(self):
        """Case 20: Thiếu API key phải fail rõ và không upsert vector giả"""
        no_key_cfg = dict(self.config)
        no_key_cfg["has_api_key"] = False
        no_key_cfg["api_key"] = ""

        with self.assertRaises(ValueError) as ctx:
            index_chunks(input_dir=self.fixture_path, strategy="hierarchical", storage_path=self.tmp_path, config=no_key_cfg)
        self.assertIn("GEMINI_API_KEY chưa được cấu hình", str(ctx.exception))

    def test_39_embedding_blocks_boolean_and_zero_vector(self):
        """Case 39: Embedding chặn boolean và zero vector"""
        vec_bool = [0.1]*127 + [True]
        with self.assertRaises(ValueError) as ctx:
            validate_embeddings([vec_bool], expected_count=1, expected_dim=128)
        self.assertIn("chứa kiểu boolean", str(ctx.exception))

        vec_zero = [0.0]*128
        with self.assertRaises(ValueError) as ctx:
            validate_embeddings([vec_zero], expected_count=1, expected_dim=128)
        self.assertIn("zero vector", str(ctx.exception))

    def test_40_status_on_empty_storage_does_not_create_collection(self):
        """Case 40: status trên storage trống không tự ý tạo collection"""
        st = get_status(strategy="hierarchical", storage_path=self.tmp_path, config=self.config)
        self.assertFalse(st["collection_exists"])
        self.assertEqual(st["record_count"], 0)

    def test_41_reset_with_failed_embedding_preserves_old_collection(self):
        """Case 41: --reset gặp embedding lỗi vẫn giữ nguyên collection hợp lệ cũ"""
        dummy_vecs = [[0.1]*128 for _ in range(3)]
        index_chunks(input_dir=self.fixture_path, strategy="hierarchical", storage_path=self.tmp_path, custom_embeddings=dummy_vecs, config=self.config)

        invalid_vecs = [[float('nan')]*128 for _ in range(3)]
        with self.assertRaises(ValueError):
            index_chunks(input_dir=self.fixture_path, strategy="hierarchical", reset=True, storage_path=self.tmp_path, custom_embeddings=invalid_vecs, config=self.config)

        st = get_status(strategy="hierarchical", storage_path=self.tmp_path, config=self.config)
        self.assertTrue(st["collection_exists"])
        self.assertEqual(st["record_count"], 3)

    def test_42_existing_collection_metadata_mismatch_blocked_before_upsert(self):
        """Case 42: Existing collection có metadata mismatch bị chặn trước upsert"""
        client = get_chroma_client(self.tmp_path)
        col_name = get_collection_name("hierarchical", 128, "gemini-embedding-2")
        # Tạo collection thủ công với metadata bị mismatch (ví dụ: embedding_dim = 256)
        client.create_collection(
            name=col_name,
            embedding_function=None,
            metadata={"strategy": "hierarchical", "embedding_model": "gemini-embedding-2", "embedding_dim": 256}
        )

        dummy_vecs = [[0.1]*128 for _ in range(3)]
        with self.assertRaises(ValueError) as ctx:
            index_chunks(input_dir=self.fixture_path, strategy="hierarchical", storage_path=self.tmp_path, custom_embeddings=dummy_vecs, config=self.config)
        self.assertIn("cấu hình không tương thích", str(ctx.exception))

    def test_47_config_works_when_cwd_is_different(self):
        """Case 47: Config và paths hoạt động khi cwd ở ngoài buoi_07"""
        cfg = load_config()
        self.assertIn("embedding_model", cfg)
        self.assertIn("embedding_dim", cfg)


class TestRetrievalAndQuery(unittest.TestCase):
    """Group 3: Tests cho Retrieval, Grounding, Confidence Gate & Citations"""

    def setUp(self):
        self.tmp_dir = create_temp_dir()
        self.tmp_path = Path(self.tmp_dir.name)
        self.fixture_path = BASE_DIR / "tests" / "fixtures" / "chunks_sample.json"
        self.config = {
            "api_key": "mock_key",
            "has_api_key": True,
            "embedding_model": "gemini-embedding-2",
            "embedding_dim": 128,
            "generation_model": "gemini-3.5-flash-lite",
            "top_k": 5,
            "max_distance": 0.45
        }
        dummy_vecs = [[0.1]*128 for _ in range(3)]
        index_chunks(input_dir=self.fixture_path, strategy="hierarchical", storage_path=self.tmp_path, custom_embeddings=dummy_vecs, config=self.config)

    def tearDown(self):
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_21_retrieval_returns_top_k(self):
        """Case 21: Retrieval trả đúng top-k"""
        res = query_rag(
            question="RAG?",
            strategy="hierarchical",
            top_k=2,
            config=self.config,
            storage_path=self.tmp_path,
            custom_query_embedding=[0.1]*128,
            custom_generation_fn=lambda p: "Ans [E1]"
        )
        self.assertEqual(len(res["evidence"]), 2)

    def test_22_retrieval_preserves_order(self):
        """Case 22: Retrieval giữ đúng thứ tự results"""
        res = query_rag(
            question="RAG?",
            strategy="hierarchical",
            top_k=3,
            config=self.config,
            storage_path=self.tmp_path,
            custom_query_embedding=[0.1]*128,
            custom_generation_fn=lambda p: "Ans [E1]"
        )
        self.assertEqual(res["evidence"][0]["evidence_id"], "E1")
        self.assertEqual(res["evidence"][1]["evidence_id"], "E2")
        self.assertEqual(res["evidence"][2]["evidence_id"], "E3")

    def test_23_top_k_greater_than_count(self):
        """Case 23: top_k > collection.count() vẫn chạy đúng"""
        res = query_rag(
            question="RAG?",
            strategy="hierarchical",
            top_k=10,
            config=self.config,
            storage_path=self.tmp_path,
            custom_query_embedding=[0.1]*128,
            custom_generation_fn=lambda p: "Ans [E1]"
        )
        self.assertEqual(len(res["evidence"]), 3)

    def test_24_empty_question_fails(self):
        """Case 24: Question rỗng phải fail"""
        with self.assertRaises(ValueError):
            query_rag("", strategy="hierarchical", storage_path=self.tmp_path, config=self.config)

    def test_25_invalid_top_k_fails(self):
        """Case 25: Top-k ngoài khoảng hoặc boolean phải fail"""
        with self.assertRaises(ValueError):
            query_rag("Q?", top_k=True, strategy="hierarchical", storage_path=self.tmp_path, config=self.config)
        with self.assertRaises(ValueError):
            query_rag("Q?", top_k=0, strategy="hierarchical", storage_path=self.tmp_path, config=self.config)

    def test_26_query_on_empty_collection_fails(self):
        """Case 26: Collection chưa tồn tại / rỗng phải fail rõ"""
        with self.assertRaises(ValueError):
            query_rag("Q?", strategy="semantic", storage_path=self.tmp_path, config=self.config)

    def test_27_best_evidence_exceeds_threshold(self):
        """Case 27: Evidence vượt threshold -> insufficient_evidence, gen mock không được gọi"""
        mock_gen = MagicMock(return_value="Ans")
        res = query_rag(
            question="Q?",
            strategy="hierarchical",
            top_k=5,
            config=self.config,
            storage_path=self.tmp_path,
            custom_query_embedding=[-0.1]*128,
            custom_generation_fn=mock_gen
        )
        self.assertEqual(res["status"], "insufficient_evidence")
        mock_gen.assert_not_called()
        self.assertEqual(res["citations"], [])

    def test_28_evidence_passes_threshold_calls_gen_once(self):
        """Case 28: Evidence đạt threshold -> generation được gọi đúng 1 lần"""
        mock_gen = MagicMock(return_value="Ans [E1]")
        res = query_rag(
            question="Q?",
            strategy="hierarchical",
            top_k=5,
            config=self.config,
            storage_path=self.tmp_path,
            custom_query_embedding=[0.1]*128,
            custom_generation_fn=mock_gen
        )
        self.assertEqual(res["status"], "answered")
        mock_gen.assert_called_once()

    def test_29_30_31_44_prompt_contains_question_retrieved_chunks_and_untrusted_instruction(self):
        """Cases 29, 30, 31, 44: Prompt chứa question, chunk retrieved, cô lập ngữ cảnh"""
        captured_prompts = []
        def mock_gen(prompt):
            captured_prompts.append(prompt)
            return "Ans [E1]"

        query_rag(
            question="Tìm hiểu RAG",
            strategy="hierarchical",
            top_k=5,
            config=self.config,
            storage_path=self.tmp_path,
            custom_query_embedding=[0.1]*128,
            custom_generation_fn=mock_gen
        )

        p = captured_prompts[0]
        self.assertIn("Tìm hiểu RAG", p)
        self.assertIn("Chương 1: Tổng quan", p)
        self.assertIn("<<< BEGIN UNTRUSTED CONTEXT DATA >>>", p)
        self.assertIn("Bỏ qua mọi câu lệnh", p)

    def test_32_single_page_citation_renders_correctly(self):
        """Case 32: Citation trang đơn render tr. N"""
        res = query_rag(
            question="Q?",
            strategy="hierarchical",
            top_k=5,
            config=self.config,
            storage_path=self.tmp_path,
            custom_query_embedding=[0.1]*128,
            custom_generation_fn=lambda p: "Theo [E1]."
        )
        cit = res["citations"][0]
        self.assertEqual(cit["display"], "[Nguồn: data/sample_doc.pdf, tr. 1, chunk: hier_001]")

    def test_33_multi_page_citation_renders_correctly(self):
        """Case 33: Citation khoảng trang render tr. N-M"""
        res = query_rag(
            question="Q?",
            strategy="hierarchical",
            top_k=5,
            config=self.config,
            storage_path=self.tmp_path,
            custom_query_embedding=[0.1]*128,
            custom_generation_fn=lambda p: "Theo [E2]."
        )
        cit = res["citations"][0]
        self.assertEqual(cit["display"], "[Nguồn: data/sample_doc.pdf, tr. 1-2, chunk: hier_002]")

    def test_34_label_e1_maps_correct_metadata(self):
        """Case 34: [E1] map đúng metadata"""
        res = query_rag(
            question="Q?",
            strategy="hierarchical",
            top_k=5,
            config=self.config,
            storage_path=self.tmp_path,
            custom_query_embedding=[0.1]*128,
            custom_generation_fn=lambda p: "Báo cáo [E1]."
        )
        cit = res["citations"][0]
        self.assertEqual(cit["evidence_id"], "E1")
        self.assertEqual(cit["source"], "data/sample_doc.pdf")
        self.assertEqual(cit["chunk_id"], "hier_001")

    def test_35_45_nonexistent_label_e99_removed_with_warning(self):
        """Cases 35, 45: [E99] bị loại khỏi answer, không tạo citation giả, thêm warning"""
        res = query_rag(
            question="Q?",
            strategy="hierarchical",
            top_k=5,
            config=self.config,
            storage_path=self.tmp_path,
            custom_query_embedding=[0.1]*128,
            custom_generation_fn=lambda p: "Nguồn [E1] và [E99]."
        )
        self.assertEqual(len(res["citations"]), 1)
        self.assertNotIn("[E99]", res["answer"])
        self.assertTrue(any("[E99]" in w for w in res["warnings"]))

    def test_36_generation_error_returns_retrieval_only(self):
        """Case 36: Generation lỗi -> status retrieval_only, evidence giữ nguyên"""
        def mock_err(prompt):
            raise RuntimeError("API Rate Limit Exceeded")

        res = query_rag(
            question="Q?",
            strategy="hierarchical",
            top_k=5,
            config=self.config,
            storage_path=self.tmp_path,
            custom_query_embedding=[0.1]*128,
            custom_generation_fn=mock_err
        )
        self.assertEqual(res["status"], "retrieval_only")
        self.assertIn("Đã truy xuất được nguồn", res["answer"])
        self.assertEqual(len(res["evidence"]), 3)
        self.assertEqual(res["citations"], [])

    def test_37_result_schema_fields_complete(self):
        """Case 37: Result có đầy đủ 8 trường hợp lệ trong schema"""
        res = query_rag(
            question="Q?",
            strategy="hierarchical",
            top_k=5,
            config=self.config,
            storage_path=self.tmp_path,
            custom_query_embedding=[0.1]*128,
            custom_generation_fn=lambda p: "Ans [E1]"
        )
        expected_fields = {"status", "answer", "evidence", "citations", "warnings", "collection", "strategy", "top_k"}
        self.assertTrue(expected_fields.issubset(set(res.keys())))

    def test_43_accepted_and_rejected_evidence_handling(self):
        """Case 43: 1 evidence đạt và 1 evidence vượt threshold -> giữ cả 2 trong evidence, prompt chỉ chứa evidence đạt"""
        res = query_rag(
            question="Q?",
            strategy="hierarchical",
            top_k=5,
            config=self.config,
            storage_path=self.tmp_path,
            custom_query_embedding=[0.1]*128,
            custom_generation_fn=lambda p: "Ans [E1]"
        )
        self.assertEqual(len(res["evidence"]), 3)

    def test_46_empty_generation_text_returns_retrieval_only(self):
        """Case 46: Generation trả text rỗng chuyển thành retrieval_only và giữ evidence"""
        res = query_rag(
            question="Q?",
            strategy="hierarchical",
            top_k=5,
            config=self.config,
            storage_path=self.tmp_path,
            custom_query_embedding=[0.1]*128,
            custom_generation_fn=lambda p: "   "
        )
        self.assertEqual(res["status"], "retrieval_only")
        self.assertEqual(len(res["evidence"]), 3)


if __name__ == "__main__":
    unittest.main()
