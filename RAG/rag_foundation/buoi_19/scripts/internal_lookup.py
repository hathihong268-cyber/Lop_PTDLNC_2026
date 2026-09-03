"""
Module: internal_lookup.py
Vị trí: buoi_19/scripts/internal_lookup.py
Mục đích: Use Case 1 - AI Tra cứu quy định nội bộ tích hợp RBAC, Citation và Audit Trail.
          Hỗ trợ Dual-Provider (Ollama Local / Gemini Cloud).
"""

import os
import sys
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

load_dotenv(PROJECT_DIR / ".env")

from scripts.secure_retrieval_adapter import SecureRetrievalAdapter, get_adapted_secure_retriever
from scripts.audit_logger import AuditLogger, get_audit_logger

# Import Ollama Client
try:
    from scripts.ollama_adapter import OllamaClient
except ImportError:
    try:
        from ollama_adapter import OllamaClient
    except ImportError:
        OllamaClient = None

# Import Google Gemini API Client
try:
    from google import genai
    from google.genai import types
    HAS_GEMINI_SDK = True
except ImportError:
    HAS_GEMINI_SDK = False

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
MODEL_NAME = os.getenv("LLM_MODEL", "gemini-3.6-flash")
INSUFFICIENT_INFO_MSG = "Không tìm thấy đủ thông tin trong phạm vi tài liệu được phép truy cập."


class InternalPolicyLookupSystem:
    """
    Hệ thống AI Tra cứu Quy định Nội bộ (Use Case 1):
    - Tái sử dụng SecureRetriever qua Adapter
    - Lọc quyền RBAC nghiêm ngặt trước khi tạo Prompt cho LLM
    - Hỗ trợ Dual-Provider Switch: Ollama (Local SLM) / Gemini (Cloud API)
    - Yêu cầu LLM trả lời kèm trích dẫn chính xác (Citation)
    - Tự động ghi nhận Nhật ký Kiểm toán (Audit Trail)
    """

    def __init__(
        self,
        retriever_adapter: Optional[SecureRetrievalAdapter] = None,
        audit_logger: Optional[AuditLogger] = None
    ):
        self.adapter = retriever_adapter if retriever_adapter else get_adapted_secure_retriever()
        self.logger = audit_logger if audit_logger else get_audit_logger()
        self.provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        
        self.ollama_client = None
        self.gemini_client = None

        if self.provider == "ollama":
            if OllamaClient:
                self.ollama_client = OllamaClient()
            else:
                print("[WARNING] Không tìm thấy module OllamaClient.")
        else:
            if HAS_GEMINI_SDK and GEMINI_API_KEY:
                try:
                    self.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
                except Exception as e:
                    print(f"[CẢNH BÁO] Không thể khởi tạo Gemini Client: {e}")

    def generate_answer_with_llm(self, question: str, retrieved_results: List[Dict[str, Any]]) -> str:
        """
        Sinh câu trả lời từ LLM (Ollama hoặc Gemini) với ràng buộc nghiêm ngặt:
        - Chỉ trả lời từ Context đã lọc RBAC.
        - Mọi thông tin đi kèm trích dẫn [Citation].
        - Nếu context không đủ: trả về INSUFFICIENT_INFO_MSG.
        """
        if not retrieved_results:
            return INSUFFICIENT_INFO_MSG

        context_blocks = []
        for item in retrieved_results:
            citation_str = item.get("citation", f"[{item.get('chunk_id')}]")
            text_str = item.get("text", "").strip()
            block = f"--- THÔNG TIN TRÍCH DẪN {citation_str} ---\n{text_str}"
            context_blocks.append(block)

        context_payload = "\n\n".join(context_blocks)

        system_instruction = (
            "Bạn là Trợ lý AI Tra cứu Quy định Nội bộ Ngân hàng Agribank.\n"
            "Nhiệm vụ của bạn là trả lời câu hỏi của người dùng CHỈ dựa trên Ngữ cảnh (Context) được cung cấp dưới đây.\n\n"
            "QUY TẮC BẮT BUỘC:\n"
            "1. Tuyệt đối CHỈ sử dụng thông tin có trong Ngữ cảnh (Context). KHÔNG dùng kiến thức bên ngoài.\n"
            "2. Mọi thông tin/ý kiến đưa ra TRONG CÂU TRẢ LỜI PHẢI ĐI KÈM TRÍCH DẪN rõ ràng dạng [Số hiệu văn bản | Điều | chunk_id].\n"
            f"3. Nếu Ngữ cảnh không chứa đủ thông tin để trả lời câu hỏi, bạn BẮT BUỘC phải trả lời chính xác câu: \"{INSUFFICIENT_INFO_MSG}\"\n"
            "4. Tuyệt đối KHÔNG bịa đặt thông tin hoặc tạo trích dẫn giả."
        )

        prompt = f"{system_instruction}\n\nNGỮ CẢNH ĐƯỢC PHÉP TRUY CẬP:\n{context_payload}\n\nCÂU HỎI: {question}\n\nCÂU TRẢ LỜI (kèm trích dẫn):"

        # Chế độ 1: Ollama Local Model
        if self.provider == "ollama" and self.ollama_client:
            response_text = self.ollama_client.generate(prompt=prompt, format_json=False, temperature=0.1)
            if response_text and not response_text.startswith("[RULE-ENGINE FALLBACK]"):
                return response_text.strip()

        # Chế độ 2: Cloud Gemini API
        elif self.provider == "gemini" and self.gemini_client:
            try:
                response = self.gemini_client.models.generate_content(
                    model=MODEL_NAME,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.1
                    )
                )
                if response.text and response.text.strip():
                    return response.text.strip()
            except Exception as e:
                print(f"[CẢNH BÁO LLM] Lỗi gọi API Gemini: {e}")

        # Fallback dựa trên context đã retrieve
        answers = []
        for item in retrieved_results:
            citation_str = item.get("citation", "")
            snippet = item.get("text", "").replace("\n", " ")[:200]
            answers.append(f"Theo {citation_str}: {snippet}...")
        
        return "\n\n".join(answers) if answers else INSUFFICIENT_INFO_MSG

    def lookup(
        self,
        question: str,
        user_role: List[str],
        user_id_demo: str = "usr_demo",
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Hàm xử lý tra cứu chính (Unified Policy Lookup).
        """
        request_id = f"req-{uuid.uuid4().hex[:8]}"

        retrieval_output = self.adapter.retrieve(
            query=question,
            user_roles=user_role,
            method="hybrid_rerank",
            top_k=top_k
        )

        results = retrieval_output.get("results", [])
        filtered_out_count = retrieval_output.get("filtered_out_count", 0)

        citations = [r.get("citation", "") for r in results if r.get("citation")]
        chunk_ids = [r.get("chunk_id", "") for r in results if r.get("chunk_id")]
        doc_ids = list({r.get("document_id", "") for r in results if r.get("document_id")})

        is_denied = (len(results) == 0 and filtered_out_count > 0)
        
        if is_denied or not results:
            answer = INSUFFICIENT_INFO_MSG
            status = "DENIED" if is_denied else "SUCCESS"
            citations = []
            results = []
        else:
            answer = self.generate_answer_with_llm(question, results)
            if answer == INSUFFICIENT_INFO_MSG:
                citations = []
                results = []
            status = "SUCCESS" if answer != INSUFFICIENT_INFO_MSG else ("DENIED" if filtered_out_count > 0 else "SUCCESS")

        self.logger.log_event(
            user_id_demo=user_id_demo,
            user_role=user_role if isinstance(user_role, list) else [str(user_role)],
            query=question,
            action="INTERNAL_POLICY_LOOKUP",
            retrieval_method="hybrid_rerank",
            retrieved_document_ids=doc_ids,
            retrieved_chunk_ids=chunk_ids,
            citation_ids=citations,
            rbac_filtered_count=filtered_out_count,
            status=status,
            request_id=request_id
        )

        return {
            "request_id": request_id,
            "question": question,
            "user_role": user_role,
            "access_scope": retrieval_output.get("user_roles", user_role),
            "answer": answer,
            "citations": citations,
            "document_id": doc_ids,
            "chunk_id": chunk_ids,
            "filtered_out_count": filtered_out_count,
            "status": status,
            "review_status": "NEEDS_HUMAN_REVIEW",
            "retrieved_results": results
        }


if __name__ == "__main__":
    print("=" * 70)
    print("DEMO USE CASE 1 — AI TRA CỨU QUY ĐỊNH NỘI BỘ (BUỔI 19 LOCAL OLLAMA)")
    print("=" * 70)

    system = InternalPolicyLookupSystem()
    
    test_res = system.lookup(
        question="Tiêu chuẩn chức danh thủ kho tiền, thủ quỹ",
        user_role=["HR_Manager"],
        user_id_demo="usr_hr_test"
    )

    print(f"Request ID   : {test_res['request_id']}")
    print(f"Access Scope : {test_res['access_scope']}")
    print(f"Citations    : {test_res['citations']}")
    print(f"Answer       :\n{test_res['answer']}")
