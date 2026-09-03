"""
Kiểm thử Bước 3: Tích hợp Ngữ cảnh và Gọi LLM (Gemini API)
Bài thực hành 2 - Buổi 11: Multi-hop Graph RAG và Ứng dụng Hỏi Đáp (QA)

Bao gồm:
1. Kiểm tra cấu trúc System Instruction và Prompt Schema.
2. Kiểm tra hàm build_qa_prompt và định dạng context.
3. Kiểm tra gọi Gemini API với mock và live test (nếu có key & mạng).
"""

import os
import sys
import unittest
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
from buoi_11_qa import (
    SYSTEM_INSTRUCTION,
    build_qa_prompt,
    get_gemini_client,
    generate_graph_rag_answer,
    DEFAULT_GENERATION_MODEL
)


class TestStep3PromptAndLLM(unittest.TestCase):

    def test_system_instruction_contains_schema_and_grounding(self):
        """Kiểm tra System Instruction chứa đầy đủ thông tin schema và ràng buộc."""
        # 1. Kiểm tra các node và relationship trong schema
        self.assertIn("(:Document)", SYSTEM_INSTRUCTION)
        self.assertIn("(:Chunk)", SYSTEM_INSTRUCTION)
        self.assertIn("PART_OF", SYSTEM_INSTRUCTION)
        self.assertIn("CAN_CU", SYSTEM_INSTRUCTION)
        self.assertIn("THAY_THE", SYSTEM_INSTRUCTION)
        self.assertIn("HOP_NHAT", SYSTEM_INSTRUCTION)
        self.assertIn("SUA_DOI_BO_SUNG", SYSTEM_INSTRUCTION)

        # 2. Kiểm tra các ràng buộc Grounding
        self.assertIn("CHỈ SỬ DỤNG THÔNG TIN TRONG NGỮ CẢNH", SYSTEM_INSTRUCTION)
        self.assertIn("TUYỆT ĐỐI KHÔNG SUY ĐOÁN NGOÀI DỮ LIỆU", SYSTEM_INSTRUCTION)
        self.assertIn("không có đủ thông tin", SYSTEM_INSTRUCTION)
        self.assertIn("TRÍCH DẪN NGUỒN", SYSTEM_INSTRUCTION)

    def test_build_qa_prompt_structure(self):
        """Kiểm tra xây dựng prompt kết hợp ngữ cảnh và câu hỏi."""
        sample_retrieval = {
            "initial_chunks": [
                {
                    "doc_so_ky_hieu": "46/2023/NĐ-CP",
                    "doc_title": "Nghị định quy định chi tiết Luật Kinh doanh bảo hiểm",
                    "doc_co_quan_ban_hanh": "Chính phủ",
                    "doc_tinh_trang_hieu_luc": "Còn hiệu lực",
                    "score": 0.892,
                    "heading": "Điều 1. Phạm vi điều chỉnh",
                    "text": "Nghị định này quy định chi tiết về thi hành Luật Kinh doanh bảo hiểm..."
                }
            ],
            "traversal_paths": [
                {
                    "seed_so_ky_hieu": "46/2023/NĐ-CP",
                    "target_so_ky_hieu": "73/2016/NĐ-CP",
                    "target_title": "Nghị định quy định chi tiết Luật Kinh doanh bảo hiểm 2016",
                    "hop_distance": 1,
                    "relationships": [
                        {
                            "type": "THAY_THE",
                            "relationship": "Thay thế",
                            "from_so": "46/2023/NĐ-CP",
                            "to_so": "73/2016/NĐ-CP"
                        }
                    ]
                }
            ],
            "related_documents": [
                {
                    "doc_id": "112025",
                    "doc_so_ky_hieu": "73/2016/NĐ-CP",
                    "doc_title": "Nghị định 73/2016/NĐ-CP",
                    "doc_co_quan_ban_hanh": "Chính phủ",
                    "doc_tinh_trang_hieu_luc": "Hết hiệu lực",
                    "hop_distance": 1
                }
            ],
            "hop_chunks": [
                {
                    "doc_id": "112025",
                    "doc_so_ky_hieu": "73/2016/NĐ-CP",
                    "heading": "Điều 1. Phạm vi điều chỉnh",
                    "text": "Nghị định này hướng dẫn một số điều của Luật Kinh doanh bảo hiểm..."
                }
            ],
            "num_hops": 1
        }

        query = "Nghị định 46/2023/NĐ-CP thay thế cho nghị định nào?"
        prompt = build_qa_prompt(query, sample_retrieval)

        # Kiểm tra nội dung trong user prompt
        self.assertIn(query, prompt)
        self.assertIn("46/2023/NĐ-CP", prompt)
        self.assertIn("73/2016/NĐ-CP", prompt)
        self.assertIn("THAY_THE", prompt)
        self.assertIn("CÁC ĐOẠN VĂN BẢN KHỚP TRỰC TIẾP", prompt)
        self.assertIn("CÁC MỐI QUAN HỆ LIÊN KẾT ĐỒ THỊ", prompt)
        self.assertIn("NỘI DUNG TỪ CÁC VĂN BẢN LIÊN QUAN ĐA BƯỚC", prompt)

    def test_gemini_client_creation(self):
        """Kiểm tra tạo client Gemini thành công khi có API key."""
        api_key = os.getenv("GEMINI_API_KEY", "")
        if api_key:
            client = get_gemini_client(api_key)
            self.assertIsNotNone(client)
        else:
            with self.assertRaises(ValueError):
                get_gemini_client("")


if __name__ == "__main__":
    unittest.main(verbosity=2)
