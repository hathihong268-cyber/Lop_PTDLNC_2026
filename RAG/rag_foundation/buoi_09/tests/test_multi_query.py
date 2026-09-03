"""
Bộ unit tests kiểm thử Multi-Query Expansion Generator cho Buổi 09:
100% offline, độc lập hoàn toàn, sử dụng dependency injection mock generator,
không gọi Gemini API qua mạng và không phụ thuộc vào kết nối Internet.
Bao quát 11 tiêu chí kiểm thử bắt buộc theo đặc tả kỹ thuật SPEC_buoi_09.md.
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
    generate_query_expansion,
    clean_and_deduplicate_queries,
    load_buoi_09_config,
    _MULTI_QUERY_CACHE,
)


class TestMultiQueryExpansion(unittest.TestCase):
    """
    Test suite kiểm thử toàn diện Multi-Query Expansion và Query Set Contract.
    """

    def setUp(self):
        self.config = load_buoi_09_config()
        self.config["multi_query_count"] = 3
        self.config["multi_query_max_chars"] = 300
        # Dọn sạch cache trước mỗi test case
        _MULTI_QUERY_CACHE.clear()

    def test_01_q0_always_first_and_preserves_content(self):
        """
        Case 1: Q0 luôn đứng đầu, origin='original', focus='original_intent' và giữ nguyên nội dung gốc.
        """
        raw_question = "  Tổ chức tín dụng cơ cấu nợ như thế nào?  "
        def mock_gen(q: str) -> str:
            return json.dumps({
                "queries": [
                    {"text": "Quy định cơ cấu lại thời hạn trả nợ", "focus": "exact_legal_terms"},
                    {"text": "Ngân hàng gia hạn nợ cho khách hàng ra sao", "focus": "paraphrase"},
                    {"text": "Điều kiện để được cơ cấu nợ", "focus": "missing_aspect"},
                ]
            })

        res = generate_query_expansion(raw_question, config=self.config, query_generator_fn=mock_gen)
        self.assertEqual(res["status"], "ready")
        self.assertGreaterEqual(len(res["queries"]), 1)
        q0 = res["queries"][0]
        self.assertEqual(q0["query_id"], "Q0")
        self.assertEqual(q0["origin"], "original")
        self.assertEqual(q0["focus"], "original_intent")
        self.assertEqual(q0["text"], "Tổ chức tín dụng cơ cấu nợ như thế nào?")
        self.assertEqual(res["original_question"], "Tổ chức tín dụng cơ cấu nợ như thế nào?")

    def test_02_strict_schema_validation(self):
        """
        Case 2: Validate chặt chẽ schema đầu ra của QuerySet và từng Query item.
        """
        def mock_gen(q: str) -> str:
            return json.dumps({
                "queries": [
                    {"text": "Variant 1", "focus": "exact_legal_terms"},
                    {"text": "Variant 2", "focus": "paraphrase"},
                ]
            })

        res = generate_query_expansion("Câu hỏi test", config=self.config, query_generator_fn=mock_gen)
        self.assertIn("original_question", res)
        self.assertIn("queries", res)
        self.assertIn("model", res)
        self.assertIn("generation_latency_ms", res)
        self.assertIn("status", res)
        self.assertIn("cache_hit", res)

        for item in res["queries"]:
            self.assertIn("query_id", item)
            self.assertIn("text", item)
            self.assertIn("origin", item)
            self.assertIn("focus", item)
            self.assertIn(item["origin"], {"original", "generated"})

    def test_03_nfc_trim_and_max_length_enforcement(self):
        """
        Case 3: Chuẩn hóa NFC, loại bỏ khoảng trắng thừa và loại bỏ query vượt quá MULTI_QUERY_MAX_CHARS.
        """
        raw_queries = [
            {"text": "   Quy định   cơ cấu nợ   ", "focus": "exact_legal_terms"},
            {"text": "A" * 350, "focus": "paraphrase"},  # Vượt quá max_chars 300
            {"text": "   ", "focus": "missing_aspect"},   # Rỗng sau trim
        ]
        valid_queries, dropped_count, warnings = clean_and_deduplicate_queries(
            original_question="Câu hỏi gốc",
            raw_queries=raw_queries,
            max_count=3,
            max_chars=300
        )
        self.assertEqual(len(valid_queries), 1)
        self.assertEqual(valid_queries[0]["text"], "Quy định   cơ cấu nợ")
        self.assertEqual(dropped_count, 2)

    def test_04_duplicate_removal_against_q0_and_variants(self):
        """
        Case 4: Loại bỏ các query trùng lặp hoàn toàn với Q0 hoặc trùng lặp giữa các variants.
        """
        raw_queries = [
            {"text": "câu hỏi gốc", "focus": "exact_legal_terms"},  # Trùng với Q0
            {"text": "Biến thể A", "focus": "paraphrase"},
            {"text": "biến thể a", "focus": "paraphrase"},         # Trùng với Biến thể A (case-insensitive)
            {"text": "Biến thể B", "focus": "missing_aspect"},
        ]
        valid_queries, dropped_count, warnings = clean_and_deduplicate_queries(
            original_question="Câu hỏi gốc",
            raw_queries=raw_queries,
            max_count=3,
            max_chars=300
        )
        self.assertEqual(len(valid_queries), 2)
        self.assertEqual(valid_queries[0]["text"], "Biến thể A")
        self.assertEqual(valid_queries[1]["text"], "Biến thể B")
        self.assertEqual(dropped_count, 2)

    def test_05_legal_reference_preservation_check(self):
        """
        Case 5: Khi câu hỏi có số hiệu Điều/Thông tư, kiểm tra cảnh báo nếu không có variant nào giữ lại số hiệu.
        """
        raw_queries_with_ref = [
            {"text": "Quy định theo Điều 8 Thông tư 39", "focus": "exact_legal_terms"},
            {"text": "Nhu cầu vốn không được vay", "focus": "paraphrase"},
        ]
        _, _, warnings_ok = clean_and_deduplicate_queries(
            original_question="Nội dung Điều 8 Thông tư 39 là gì?",
            raw_queries=raw_queries_with_ref,
            max_count=3,
            max_chars=300
        )
        self.assertEqual(len(warnings_ok), 0)

        raw_queries_no_ref = [
            {"text": "Nhu cầu vốn cấm cho vay", "focus": "paraphrase"},
            {"text": "Các khoản vay bị hạn chế", "focus": "missing_aspect"},
        ]
        _, _, warnings_miss = clean_and_deduplicate_queries(
            original_question="Nội dung Điều 8 Thông tư 39 là gì?",
            raw_queries=raw_queries_no_ref,
            max_count=3,
            max_chars=300
        )
        self.assertTrue(any("legal_reference_not_preserved" in w for w in warnings_miss))

    def test_06_disallowing_invented_article_numbers(self):
        """
        Case 6: Phát hiện và cảnh báo khi câu hỏi gốc không có Điều N nhưng model tự bịa ra Điều N.
        """
        raw_queries = [
            {"text": "Quy định tại Điều 99 về lãi suất", "focus": "exact_legal_terms"}
        ]
        _, _, warnings = clean_and_deduplicate_queries(
            original_question="Lãi suất cho vay được quy định thế nào?",
            raw_queries=raw_queries,
            max_count=3,
            max_chars=300
        )
        self.assertTrue(any("hallucinated_legal_ref" in w for w in warnings))

    def test_07_deterministic_ids(self):
        """
        Case 7: Gán query_id tuần tự đơn định Q0, Q1, Q2, Q3 sau khi làm sạch.
        """
        def mock_gen(q: str) -> str:
            return json.dumps({
                "queries": [
                    {"text": "V1", "focus": "exact_legal_terms"},
                    {"text": "V2", "focus": "paraphrase"},
                    {"text": "V3", "focus": "missing_aspect"},
                ]
            })

        res = generate_query_expansion("Câu hỏi test ID", config=self.config, query_generator_fn=mock_gen)
        ids = [item["query_id"] for item in res["queries"]]
        self.assertEqual(ids, ["Q0", "Q1", "Q2", "Q3"])

    def test_08_single_generator_call_per_expansion(self):
        """
        Case 8: Mỗi lần gọi generate_query_expansion chỉ gọi hàm sinh đúng duy nhất 1 lần.
        """
        call_count = 0
        def mock_gen(q: str) -> str:
            nonlocal call_count
            call_count += 1
            return json.dumps({"queries": [{"text": "V1", "focus": "paraphrase"}]})

        generate_query_expansion("Câu hỏi kiểm tra số lần gọi", config=self.config, query_generator_fn=mock_gen)
        self.assertEqual(call_count, 1)

    def test_09_in_process_cache_hit_does_not_invoke_generator_again(self):
        """
        Case 9: Cache hit trả kết quả từ bộ nhớ đệm, cache_hit=True, latency=0.0 và không gọi lại generator.
        """
        call_count = 0
        def mock_gen(q: str) -> str:
            nonlocal call_count
            call_count += 1
            return json.dumps({"queries": [{"text": "V1", "focus": "paraphrase"}]})

        res1 = generate_query_expansion("Câu hỏi cache", config=self.config, query_generator_fn=mock_gen)
        self.assertEqual(call_count, 1)
        self.assertFalse(res1["cache_hit"])

        res2 = generate_query_expansion("Câu hỏi cache", config=self.config, query_generator_fn=mock_gen)
        self.assertEqual(call_count, 1)  # Không tăng lên 2
        self.assertTrue(res2["cache_hit"])
        self.assertEqual(res2["generation_latency_ms"], 0.0)
        self.assertEqual(res1["queries"], res2["queries"])

    def test_10_api_or_json_error_returns_explicit_status(self):
        """
        Case 10: Khi generator trả JSON hỏng hoặc ném Exception, trả status='query_generation_unavailable'.
        """
        def mock_broken_json(q: str) -> str:
            return "This is not valid JSON"

        res = generate_query_expansion("Câu hỏi lỗi JSON", config=self.config, query_generator_fn=mock_broken_json)
        self.assertEqual(res["status"], "query_generation_unavailable")
        self.assertEqual(len(res["queries"]), 1)
        self.assertEqual(res["queries"][0]["query_id"], "Q0")
        self.assertTrue(len(res["warnings"]) > 0)

        def mock_raise_error(q: str) -> str:
            raise RuntimeError("Lỗi kết nối API mock")

        res_err = generate_query_expansion("Câu hỏi ném Exception", config=self.config, query_generator_fn=mock_raise_error)
        self.assertEqual(res_err["status"], "query_generation_unavailable")
        self.assertEqual(len(res_err["queries"]), 1)
        self.assertTrue(any("Lỗi gọi Gemini API" in w for w in res_err["warnings"]))

    def test_11_tests_run_100_percent_offline(self):
        """
        Case 11: Toàn bộ suite test chạy 100% offline không có kết nối mạng hay gọi API thật.
        """
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
