"""
Unit Tests cho Module Multi-Query Expansion - Buổi 09:
Kiểm thử toàn diện 11 ca kiểm thử bắt buộc:
1. Q0 luôn đứng đầu và giữ nguyên nội dung gốc
2. Strict schema validation
3. NFC normalization, trim và giới hạn max length
4. Duplicate removal (trùng Q0 hoặc trùng lẫn nhau)
5. Legal reference preservation check
6. Loại bỏ số Điều bịa thêm không có trong câu gốc
7. Deterministic IDs (Q0, Q1, Q2, ...)
8. Đúng một generator call duy nhất
9. Cache hit không gọi lại generator lần 2
10. API lỗi trả status 'query_generation_unavailable' rõ ràng
11. Toàn bộ tests chạy hoàn toàn offline không gọi mạng
"""

import unittest
from unittest.mock import patch
from pathlib import Path
import sys
import unicodedata

# Thêm thư mục Buổi 09 vào sys.path để import
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from hierarchical_rag import (
    generate_query_variants,
    clear_query_expansion_cache,
    normalize_query_text,
    normalize_for_dedup,
    find_legal_articles,
    extract_legal_references,
)


class TestMultiQueryExpansion(unittest.TestCase):
    def setUp(self):
        clear_query_expansion_cache()
        self.mock_config = {
            "generation_model": "mock-gemini-model",
            "multi_query_count": 3,
            "multi_query_temperature": 0.2,
            "multi_query_max_chars": 200,
            "api_key": "mock-key",
        }

    def tearDown(self):
        clear_query_expansion_cache()

    def test_01_q0_always_first_and_preserves_content(self):
        """Case 1: Q0 luôn đứng đầu danh sách queries và giữ nguyên nội dung gốc."""
        question = "  Khách hàng cá nhân vay vốn cần đáp ứng điều kiện gì?  "
        expected_q0 = "Khách hàng cá nhân vay vốn cần đáp ứng điều kiện gì?"

        def fake_gen(q, count, temp, model):
            return {
                "queries": [
                    {"text": "Điều kiện vay vốn cá nhân", "focus": "exact_legal_terms"},
                    {"text": "Quy định cho vay cá nhân", "focus": "paraphrase"},
                ]
            }

        res = generate_query_variants(
            question=question,
            config=self.mock_config,
            query_generator_fn=fake_gen,
            use_cache=False,
        )

        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["original_question"], expected_q0)
        self.assertGreaterEqual(len(res["queries"]), 1)

        q0 = res["queries"][0]
        self.assertEqual(q0["query_id"], "Q0")
        self.assertEqual(q0["text"], expected_q0)
        self.assertEqual(q0["origin"], "original")
        self.assertEqual(q0["focus"], "original_intent")

    def test_02_strict_schema_validation(self):
        """Case 2: Kiểm tra cấu trúc schema nghiêm ngặt của kết quả Query Set."""
        question = "Quy định về lãi suất cho vay ngắn hạn?"

        def fake_gen(q, count, temp, model):
            return {
                "queries": [
                    {"text": "Mức trần lãi suất cho vay ngắn hạn", "focus": "exact_legal_terms"},
                    {"text": "Lãi suất tối đa cho vay", "focus": "paraphrase"},
                    {"text": "Hồ sơ áp dụng lãi suất ưu đãi", "focus": "missing_aspect"},
                ]
            }

        res = generate_query_variants(
            question=question,
            config=self.mock_config,
            query_generator_fn=fake_gen,
            use_cache=False,
        )

        required_root_keys = {"original_question", "queries", "model", "generation_latency_ms", "status", "dropped_duplicate_count", "cache_hit"}
        self.assertTrue(required_root_keys.issubset(res.keys()))
        self.assertEqual(res["status"], "ready")
        self.assertIsInstance(res["queries"], list)
        self.assertEqual(len(res["queries"]), 4) # Q0 + 3 variants

        for q in res["queries"]:
            self.assertIn("query_id", q)
            self.assertIn("text", q)
            self.assertIn("origin", q)
            self.assertIn("focus", q)
            self.assertIn(q["origin"], {"original", "generated"})
            self.assertIn(q["focus"], {"original_intent", "exact_legal_terms", "paraphrase", "missing_aspect"})

    def test_03_nfc_trim_and_max_length(self):
        """Case 3: Chuẩn hóa NFC, trim whitespace và đảm bảo giới hạn max length."""
        # Chuỗi tổ hợp NFD: "Điều" với dấu tách rời
        nfd_question = unicodedata.normalize("NFD", "Điều kiện vay vốn")
        long_variant_text = "Nội dung biến thể rất dài " * 20 # > 200 ký tự

        def fake_gen(q, count, temp, model):
            return {
                "queries": [
                    {"text": "   " + unicodedata.normalize("NFD", "Hồ sơ vay vốn") + "   ", "focus": "paraphrase"},
                    {"text": long_variant_text, "focus": "missing_aspect"},
                ]
            }

        res = generate_query_variants(
            question=nfd_question,
            config=self.mock_config,
            query_generator_fn=fake_gen,
            use_cache=False,
        )

        # Kiểm tra Q0 chuẩn hóa NFC
        self.assertEqual(res["original_question"], unicodedata.normalize("NFC", "Điều kiện vay vốn"))
        for q in res["queries"]:
            self.assertEqual(q["text"], unicodedata.normalize("NFC", q["text"]))
            self.assertEqual(q["text"], q["text"].strip())
            self.assertLessEqual(len(q["text"]), self.mock_config["multi_query_max_chars"])

    def test_04_duplicate_removal(self):
        """Case 4: Tự động phát hiện và loại bỏ query trùng lặp với Q0 hoặc trùng lẫn nhau."""
        question = "Điều kiện cho vay vốn ngân hàng"

        def fake_gen(q, count, temp, model):
            return {
                "queries": [
                    {"text": "Điều kiện cho vay vốn ngân hàng", "focus": "paraphrase"}, # Trùng Q0
                    {"text": "điều kiện cho vay vốn ngân hàng", "focus": "exact_legal_terms"}, # Trùng Q0 case-insensitive
                    {"text": "Hồ sơ năng lực tài chính của khách hàng", "focus": "missing_aspect"}, # Hợp lệ 1
                    {"text": "Hồ sơ năng lực tài chính của khách hàng", "focus": "paraphrase"}, # Trùng với hợp lệ 1
                    {"text": "Phương án sử dụng vốn khả thi", "focus": "missing_aspect"}, # Hợp lệ 2
                ]
            }

        res = generate_query_variants(
            question=question,
            config=self.mock_config,
            query_generator_fn=fake_gen,
            use_cache=False,
        )

        self.assertEqual(res["dropped_duplicate_count"], 3) # 2 trùng Q0 + 1 trùng variant trước
        # Queries còn lại: Q0 + 2 variants duy nhất
        self.assertEqual(len(res["queries"]), 3)
        self.assertEqual(res["queries"][0]["text"], question)
        self.assertEqual(res["queries"][1]["text"], "Hồ sơ năng lực tài chính của khách hàng")
        self.assertEqual(res["queries"][2]["text"], "Phương án sử dụng vốn khả thi")

    def test_05_legal_reference_preservation_check(self):
        """Case 5: Kiểm tra ít nhất một biến thể bảo toàn tham chiếu Điều/Thông tư khi câu hỏi có chứa."""
        question = "Quy định về cơ cấu nợ theo Điều 4 Thông tư 02/2023?"

        def fake_gen(q, count, temp, model):
            return {
                "queries": [
                    {"text": "Điều kiện cơ cấu lại thời hạn trả nợ tại Điều 4 Thông tư 02/2023", "focus": "exact_legal_terms"},
                    {"text": "Khách hàng gặp khó khăn được giãn nợ như thế nào", "focus": "paraphrase"},
                ]
            }

        res = generate_query_variants(
            question=question,
            config=self.mock_config,
            query_generator_fn=fake_gen,
            use_cache=False,
        )

        orig_refs = extract_legal_references(question)
        self.assertIn("4", orig_refs["articles"])

        # Kiểm tra có ít nhất 1 variant sinh ra giữ nguyên Điều 4
        preserved = False
        for q in res["queries"][1:]:
            v_refs = extract_legal_references(q["text"])
            if "4" in v_refs["articles"]:
                preserved = True
                break
        self.assertTrue(preserved, "Ít nhất một query variant phải giữ nguyên Điều 4 từ câu gốc.")

    def test_06_reject_hallucinated_article_numbers(self):
        """Case 6: Loại bỏ các biến thể tự ý bịa thêm số Điều không xuất hiện trong câu hỏi gốc."""
        question = "Khách hàng cá nhân vay tiêu dùng cần giấy tờ gì?" # Không có Điều nào

        def fake_gen(q, count, temp, model):
            return {
                "queries": [
                    {"text": "Hồ sơ vay tiêu dùng theo Điều 99", "focus": "exact_legal_terms"}, # Bịa Điều 99
                    {"text": "Giấy tờ chứng minh thu nhập cá nhân", "focus": "paraphrase"}, # Hợp lệ
                    {"text": "Quy định tại Điều 12 về vay tiêu dùng", "focus": "exact_legal_terms"}, # Bịa Điều 12
                    {"text": "Thủ tục thẩm định khoản vay cá nhân", "focus": "missing_aspect"}, # Hợp lệ
                ]
            }

        res = generate_query_variants(
            question=question,
            config=self.mock_config,
            query_generator_fn=fake_gen,
            use_cache=False,
        )

        # 2 biến thể bịa số Điều phải bị loại bỏ
        self.assertEqual(res["dropped_duplicate_count"], 2)
        # Kết quả chỉ gồm Q0 và 2 biến thể hợp lệ
        self.assertEqual(len(res["queries"]), 3)
        for q in res["queries"]:
            articles = find_legal_articles(q["text"])
            self.assertEqual(len(articles), 0, f"Query '{q['text']}' không được chứa số Điều bịa đặt.")

    def test_07_deterministic_ids(self):
        """Case 7: Các query_id phải được đánh số đơn định liên tục Q0, Q1, Q2, Q3."""
        question = "Phương thức cho vay từng lần là gì?"

        def fake_gen(q, count, temp, model):
            return {
                "queries": [
                    {"text": "Định nghĩa cho vay từng lần", "focus": "exact_legal_terms"},
                    {"text": "Quy trình giải ngân theo từng lần", "focus": "paraphrase"},
                    {"text": "Hồ sơ vay vốn theo từng lần", "focus": "missing_aspect"},
                ]
            }

        res = generate_query_variants(
            question=question,
            config=self.mock_config,
            query_generator_fn=fake_gen,
            use_cache=False,
        )

        expected_ids = ["Q0", "Q1", "Q2", "Q3"]
        actual_ids = [q["query_id"] for q in res["queries"]]
        self.assertEqual(actual_ids, expected_ids)

    def test_08_single_generator_call(self):
        """Case 8: Đúng một lần gọi generator API duy nhất cho một lượt expansion."""
        question = "Thời hạn cho vay được xác định như thế nào?"
        call_count = 0

        def counting_gen(q, count, temp, model):
            nonlocal call_count
            call_count += 1
            return {
                "queries": [
                    {"text": "Căn cứ xác định thời hạn vay", "focus": "exact_legal_terms"},
                    {"text": "Thời hạn vay tối đa là bao lâu", "focus": "paraphrase"},
                ]
            }

        res = generate_query_variants(
            question=question,
            config=self.mock_config,
            query_generator_fn=counting_gen,
            use_cache=False,
        )

        self.assertEqual(call_count, 1, "Chỉ được gọi generator duy nhất 1 lần.")
        self.assertEqual(res["status"], "ready")

    def test_09_cache_hit_does_not_call_generator_again(self):
        """Case 9: Cache trong process hoạt động chính xác, lượt gọi thứ 2 hit cache và latency = 0."""
        question = "Điều kiện cơ cấu lại nợ theo Thông tư 02?"
        call_count = 0

        # Generator giả lập cho lần gọi đầu
        def fake_gen(q, count, temp, model):
            nonlocal call_count
            call_count += 1
            return {
                "queries": [
                    {"text": "Tiêu chuẩn cơ cấu nợ Thông tư 02", "focus": "exact_legal_terms"},
                ]
            }

        # Lần 1: Gọi qua fake_gen và ghi nhận vào cache
        res1 = generate_query_variants(
            question=question,
            config=self.mock_config,
            query_generator_fn=fake_gen,
            use_cache=False, # injection bypasses cache
        )
        self.assertEqual(call_count, 1)

        # Thủ công đưa res1 vào cache để kiểm tra cơ chế cache hit độc lập
        from hierarchical_rag import _QUERY_EXPANSION_CACHE
        cache_key = "test_cache_key"
        _QUERY_EXPANSION_CACHE[cache_key] = res1

        # Kiểm tra logic hit cache của generate_query_variants khi không inject generator_fn
        # nhưng thiếu API key: nếu cache hit thì trả về luôn không kiểm tra API key
        with patch("hierarchical_rag.hashlib.sha256") as mock_hash:
            mock_hash.return_value.hexdigest.return_value = cache_key
            res2 = generate_query_variants(
                question=question,
                config=self.mock_config,
                query_generator_fn=None,
                use_cache=True,
            )
            self.assertTrue(res2["cache_hit"])
            self.assertEqual(res2["generation_latency_ms"], 0.0)
            self.assertEqual(res2["status"], "ready")

    def test_10_api_error_returns_explicit_status(self):
        """Case 10: Khi API gặp sự cố, trả về status 'query_generation_unavailable' kèm lỗi rõ ràng, bảo toàn Q0."""
        question = "Khách hàng bị quá hạn nợ xử lý thế nào?"

        def broken_gen(q, count, temp, model):
            raise ConnectionError("Kết nối tới Gemini API thất bại (mock network timeout).")

        res = generate_query_variants(
            question=question,
            config=self.mock_config,
            query_generator_fn=broken_gen,
            use_cache=False,
        )

        self.assertEqual(res["status"], "query_generation_unavailable")
        self.assertIn("error", res)
        self.assertIn("Kết nối tới Gemini API thất bại", res["error"])
        self.assertEqual(len(res["queries"]), 1)
        self.assertEqual(res["queries"][0]["query_id"], "Q0")
        self.assertEqual(res["queries"][0]["text"], question)

    def test_11_unit_tests_run_offline_without_network(self):
        """Case 11: Toàn bộ suite kiểm thử chạy offline hoàn toàn, thiếu API key không gây crash."""
        question = "Nguyên tắc cho vay vốn theo pháp luật?"
        empty_key_config = {**self.mock_config, "api_key": ""}

        res = generate_query_variants(
            question=question,
            config=empty_key_config,
            query_generator_fn=None, # Gọi hàm thật khi không có API key
            use_cache=False,
        )

        # Phải trả về status unavailable an toàn, không gọi mạng
        self.assertEqual(res["status"], "query_generation_unavailable")
        self.assertIn("Thiếu GEMINI_API_KEY", res["error"])
        self.assertEqual(len(res["queries"]), 1)
        self.assertEqual(res["queries"][0]["query_id"], "Q0")


if __name__ == "__main__":
    unittest.main()
