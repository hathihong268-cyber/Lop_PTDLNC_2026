"""
Module: internal_lookup.py
Vị trí: buoi_17/scripts/internal_lookup.py
Mục đích: Use Case 1 - AI Tra cứu quy định nội bộ tích hợp RBAC, Citation và Audit Trail.
"""

import os
import sys
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Reconfigure stdout/stderr cho UTF-8 trên Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BUOI_17_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUOI_17_DIR))

# Tải biến môi trường từ buoi_17/.env
load_dotenv(BUOI_17_DIR / ".env")

from scripts.secure_retrieval_adapter import SecureRetrievalAdapter, get_adapted_secure_retriever
from scripts.audit_logger import AuditLogger, get_audit_logger

# Import Google Gemini API Client
try:
    from google import genai
    from google.genai import types
    HAS_GEMINI_SDK = True
except ImportError:
    HAS_GEMINI_SDK = False

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_GENERATION_MODEL", "gemini-2.5-flash")

# Chuỗi phản hồi mặc định khi không tìm thấy đủ thông tin trong phạm vi quyền
INSUFFICIENT_INFO_MSG = "Không tìm thấy đủ thông tin trong phạm vi tài liệu được phép truy cập."


class InternalPolicyLookupSystem:
    """
    Hệ thống AI Tra cứu Quy định Nội bộ (Use Case 1):
    - Tái sử dụng SecureRetriever qua Adapter
    - Lọc quyền RBAC nghiêm ngặt trước khi tạo Prompt cho LLM
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
        
        # Khởi tạo Gemini client nếu SDK khả dụng
        self.gemini_client = None
        if HAS_GEMINI_SDK and GEMINI_API_KEY:
            try:
                self.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
            except Exception as e:
                print(f"[CẢNH BÁO] Không thể khởi tạo Gemini Client: {e}")

    def generate_answer_with_llm(self, question: str, retrieved_results: List[Dict[str, Any]]) -> str:
        """
        Sinh câu trả lời từ LLM với ràng buộc nghiêm ngặt:
        - Chỉ trả lời từ Context đã lọc RBAC.
        - Không bịa câu trả lời / trích dẫn giả.
        - Nếu context không đủ: trả về INSUFFICIENT_INFO_MSG.
        """
        if not retrieved_results:
            return INSUFFICIENT_INFO_MSG

        # Xây dựng Context text có chứa Citation ID cho LLM
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
            "1. Tuyệt đối CHỈ sử dụng thông tin có trong Ngữ cảnh (Context). KHÔNG dùng kiến thức bên ngoài để tự bổ sung.\n"
            "2. Mọi thông tin/ý kiến đưa ra TRONG CÂU TRẢ LỜI PHẢI ĐI KÈM TRÍCH DẪN rõ ràng dạng [Số hiệu văn bản | Điều | chunk_id] từ Ngữ cảnh.\n"
            f"3. Nếu Ngữ cảnh không chứa đủ thông tin để trả lời câu hỏi, bạn BẮT BUỘC phải trả lời chính xác câu: \"{INSUFFICIENT_INFO_MSG}\"\n"
            "4. Tuyệt đối KHÔNG bịa đặt thông tin hoặc tạo trích dẫn giả."
        )

        prompt = f"NGỮ CẢNH ĐƯỢC PHÉP TRUY CẬP:\n{context_payload}\n\nCÂU HỎI: {question}\n\nCÂU TRẢ LỜI (kèm trích dẫn):"

        # Nếu có Gemini client -> Gọi API Gemini thật
        if self.gemini_client:
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

        # Fallback tạo câu trả lời dựa trên context đã retrieve nếu API gián đoạn
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
        Hàm xử lý tra cứu chính (Unified Policy Lookup):
        
        Input:
        - question
        - user_role
        - top_k
        
        Output:
        - answer
        - citations
        - document_id/chunk_id
        - access_scope
        - request_id
        """
        request_id = f"req-{uuid.uuid4().hex[:8]}"

        # 1. Truy xuất an toàn qua SecureRetrievalAdapter (RBAC Pre-filtering)
        retrieval_output = self.adapter.retrieve(
            query=question,
            user_roles=user_role,
            method="hybrid_rerank",
            top_k=top_k
        )

        results = retrieval_output.get("results", [])
        filtered_out_count = retrieval_output.get("filtered_out_count", 0)

        # Trích xuất metadata
        citations = [r.get("citation", "") for r in results if r.get("citation")]
        chunk_ids = [r.get("chunk_id", "") for r in results if r.get("chunk_id")]
        doc_ids = list({r.get("document_id", "") for r in results if r.get("document_id")})

        # 2. Kiểm tra nếu không có kết quả hợp lệ hoặc câu hỏi bị từ chối
        is_denied = (len(results) == 0 and filtered_out_count > 0)
        
        if is_denied or not results:
            answer = INSUFFICIENT_INFO_MSG
            status = "DENIED" if is_denied else "SUCCESS"
            citations = []
            results = []
        else:
            # 3. Sinh câu trả lời từ LLM trên tập context hợp lệ
            answer = self.generate_answer_with_llm(question, results)
            if answer == INSUFFICIENT_INFO_MSG:
                citations = []
                results = []
            status = "SUCCESS" if answer != INSUFFICIENT_INFO_MSG else ("DENIED" if filtered_out_count > 0 else "SUCCESS")

        # 4. Ghi nhận Nhật ký Kiểm toán (Audit Trail)
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
            "retrieved_results": results
        }


if __name__ == "__main__":
    print("=" * 70)
    print("DEMO USE CASE 1 — AI TRA CỨU QUY ĐỊNH NỘI BỘ (BUỔI 17)")
    print("=" * 70)

    system = InternalPolicyLookupSystem()
    
    # Run test
    test_res = system.lookup(
        question="Tiêu chuẩn chức danh thủ kho tiền, thủ quỹ",
        user_role=["HR_Manager"],
        user_id_demo="usr_hr_test"
    )

    print(f"Request ID   : {test_res['request_id']}")
    print(f"Access Scope : {test_res['access_scope']}")
    print(f"Citations    : {test_res['citations']}")
    print(f"Answer       :\n{test_res['answer']}")
