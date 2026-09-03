"""
Bộ kiểm thử tự động (Unit Tests) cho BM25 Lexical Retrieval - Buổi 08.
Đảm bảo 100% chạy offline, không gọi Gemini API, ChromaDB hay Reranker.
"""

import sys
import unittest
from pathlib import Path

# Đảm bảo import được module Buổi 08
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from advanced_rag import (
    tokenize_vi_legal,
    BM25Retriever,
    build_bm25_retriever,
    search_bm25
)


class TestBM25LexicalRetrieval(unittest.TestCase):
    """Kiểm thử Tokenizer tiếng Việt pháp lý và BM25 Retrieval"""

    def setUp(self):
        self.sample_chunks = [
            {
                "chunk_id": "chunk_01",
                "strategy": "hierarchical",
                "source": "TT_02_2023_NHNN.pdf",
                "page_start": 2,
                "page_end": 3,
                "text": "Thông tư 02/2023/TT-NHNN, Điều 4 quy định về cơ cấu lại thời hạn trả nợ cho khách hàng gặp khó khăn."
            },
            {
                "chunk_id": "chunk_02",
                "strategy": "hierarchical",
                "source": "TT_39_2016_NHNN.pdf",
                "page_start": 4,
                "page_end": 5,
                "text": "Thông tư 39/2016/TT-NHNN, Điều 8 Khoản 2 quy định các nhu cầu vốn không được tổ chức tín dụng cho vay."
            },
            {
                "chunk_id": "chunk_03",
                "strategy": "hierarchical",
                "source": "TT_06_2023_NHNN.pdf",
                "page_start": 1,
                "page_end": 1,
                "text": "Thông tư 06/2023/TT-NHNN sửa đổi bổ sung một số điều của Thông tư 39 về quy chế cho vay của tổ chức tín dụng."
            }
        ]

    def test_01_tokenizer_preserves_vietnamese_accents(self):
        """Case 1: Tokenizer giữ nguyên vẹn dấu tiếng Việt (Unicode NFC)"""
        text = "cơ cấu lại thời hạn trả nợ và trích lập dự phòng rủi ro"
        tokens = tokenize_vi_legal(text)
        expected = ["cơ", "cấu", "lại", "thời", "hạn", "trả", "nợ", "và", "trích", "lập", "dự", "phòng", "rủi", "ro"]
        self.assertEqual(tokens, expected)

    def test_02_tokenizer_preserves_article_and_clause_numbers(self):
        """Case 2: Tokenizer giữ đúng số hiệu Điều, Khoản và chữ số"""
        text = "Điều 7, Khoản 2 Thông tư 39/2016/TT-NHNN"
        tokens = tokenize_vi_legal(text)
        self.assertIn("điều", tokens)
        self.assertIn("7", tokens)
        self.assertIn("khoản", tokens)
        self.assertIn("2", tokens)
        self.assertIn("thông", tokens)
        self.assertIn("tư", tokens)
        self.assertIn("39", tokens)
        self.assertIn("2016", tokens)

    def test_03_same_preprocessing_for_corpus_and_query(self):
        """Case 3: Corpus và query được xử lý đồng nhất qua cùng một hàm tokenizer"""
        raw_doc = "ĐIỀU 4: CƠ CẤU LẠI THỜI HẠN TRẢ NỢ."
        raw_query = "điều 4 cơ cấu lại thời hạn trả nợ?"

        doc_tokens = tokenize_vi_legal(raw_doc)
        query_tokens = tokenize_vi_legal(raw_query)

        # Cả 2 đều phải cho ra cùng tập tokens cốt lõi
        self.assertEqual(doc_tokens, ["điều", "4", "cơ", "cấu", "lại", "thời", "hạn", "trả", "nợ"])
        self.assertEqual(query_tokens, ["điều", "4", "cơ", "cấu", "lại", "thời", "hạn", "trả", "nợ"])

    def test_04_exact_legal_term_ranks_higher(self):
        """Case 4: Chunk chứa chính xác từ khóa pháp lý (Điều 4, cơ cấu lại) phải có điểm BM25 cao hơn và xếp rank 1"""
        retriever = build_bm25_retriever(self.sample_chunks)
        results = retriever.search("Điều 4 cơ cấu lại thời hạn trả nợ", top_k=3)

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["chunk_id"], "chunk_01")
        self.assertGreater(results[0]["bm25_score"], results[1]["bm25_score"])
        self.assertEqual(results[0]["bm25_rank"], 1)

    def test_05_candidate_k_greater_than_corpus_size_works(self):
        """Case 5: candidate_k lớn hơn số lượng chunk trong corpus vẫn hoạt động an toàn mà không lỗi"""
        retriever = build_bm25_retriever(self.sample_chunks)
        results = retriever.search("tổ chức tín dụng", top_k=100)

        # Trả về tối đa toàn bộ số lượng chunk trong corpus (3 chunk)
        self.assertEqual(len(results), len(self.sample_chunks))
        self.assertEqual([r["bm25_rank"] for r in results], [1, 2, 3])

    def test_06_empty_question_fails_clearly(self):
        """Case 6: Câu hỏi rỗng, whitespace hoặc không có token hợp lệ phải raise ValueError rõ ràng"""
        retriever = build_bm25_retriever(self.sample_chunks)

        with self.assertRaises(ValueError) as ctx1:
            retriever.search("", top_k=5)
        self.assertIn("không được để rỗng", str(ctx1.exception))

        with self.assertRaises(ValueError) as ctx2:
            retriever.search("   ", top_k=5)
        self.assertIn("không được để rỗng", str(ctx2.exception))

        with self.assertRaises(ValueError) as ctx3:
            retriever.search("... ,,, !!! ???", top_k=5)
        self.assertIn("không chứa bất kỳ từ khóa hợp lệ nào", str(ctx3.exception))

    def test_07_deterministic_tie_breaking(self):
        """Case 7: Khi các chunk có cùng BM25 score (ví dụ điểm 0.0), sắp xếp ổn định và có tính đơn định (deterministic)"""
        chunks_same_score = [
            {"chunk_id": "chunk_Z", "text": "Văn bản số một về thuế.", "source": "f1.pdf", "page_start": 1, "page_end": 1},
            {"chunk_id": "chunk_A", "text": "Văn bản số hai về hải quan.", "source": "f2.pdf", "page_start": 1, "page_end": 1},
            {"chunk_id": "chunk_M", "text": "Văn bản số ba về giao thông.", "source": "f3.pdf", "page_start": 1, "page_end": 1},
        ]
        retriever = build_bm25_retriever(chunks_same_score)
        results = retriever.search("ngân hàng tín dụng", top_k=3)

        # Cả 3 chunk đều có điểm 0.0 nhưng phải được tie-break theo chunk_id tăng dần: chunk_A -> chunk_M -> chunk_Z
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["chunk_id"], "chunk_A")
        self.assertEqual(results[1]["chunk_id"], "chunk_M")
        self.assertEqual(results[2]["chunk_id"], "chunk_Z")

    def test_08_standalone_search_bm25_function_matches_contract(self):
        """Case 8: Hàm độc lập search_bm25 tuân thủ đúng schema đầu ra và không làm biến đổi chunk gốc"""
        original_text = self.sample_chunks[0]["text"]
        results = search_bm25("Điều 8 không được cho vay", self.sample_chunks, candidate_k=2)

        self.assertEqual(len(results), 2)
        top_cand = results[0]
        self.assertEqual(top_cand["chunk_id"], "chunk_02")
        self.assertIn("bm25_rank", top_cand)
        self.assertIn("bm25_score", top_cand)
        self.assertIn("source", top_cand)
        self.assertIn("page_start", top_cand)
        self.assertIn("page_end", top_cand)

        # Chunk gốc không bị thay đổi
        self.assertEqual(self.sample_chunks[0]["text"], original_text)


if __name__ == "__main__":
    unittest.main()
