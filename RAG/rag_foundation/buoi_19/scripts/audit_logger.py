"""
Module: audit_logger.py
Vị trí: buoi_17/scripts/audit_logger.py
Mục đích: Quản lý và ghi nhận Nhật ký kiểm toán (Audit Trail) dưới dạng JSONL cho mọi câu hỏi/truy vấn trong Buổi 17.
"""

import os
import sys
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

# Thêm đường dẫn root buoi_17
CURRENT_DIR = Path(__file__).resolve().parent
BUOI_17_DIR = CURRENT_DIR.parent
DEFAULT_AUDIT_LOG_PATH = BUOI_17_DIR / "outputs" / "audit_log.jsonl"


class AuditLogger:
    """
    Bộ ghi nhận Audit Trail tập trung (Centralized Audit Logger).
    Ghi nhận chi tiết mọi hoạt động truy xuất, trạng thái quyền (SUCCESS/DENIED/ERROR),
    danh sách tài liệu/chunk thu được và số lượng ứng viên bị RBAC lọc bỏ.
    """

    def __init__(self, log_file_path: Optional[Path] = None):
        self.log_file_path = Path(log_file_path) if log_file_path else DEFAULT_AUDIT_LOG_PATH
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        user_id_demo: str,
        user_role: List[str],
        query: str,
        action: str = "RETRIEVAL_LOOKUP",
        retrieval_method: str = "hybrid_rerank",
        retrieved_document_ids: Optional[List[str]] = None,
        retrieved_chunk_ids: Optional[List[str]] = None,
        citation_ids: Optional[List[str]] = None,
        rbac_filtered_count: int = 0,
        status: str = "SUCCESS",
        request_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ghi 1 sự kiện audit log vào file .jsonl.

        Tham số:
        - user_id_demo: Mã định danh người dùng demo (e.g., 'usr_hr_01')
        - user_role: Danh sách vai trò của người dùng (e.g., ['HR_Manager'])
        - query: Câu hỏi truy vấn
        - action: Hành động thực hiện (e.g., 'RETRIEVAL_LOOKUP', 'COMPLIANCE_GAP_CHECK')
        - retrieval_method: Phương pháp tìm kiếm dùng ('bm25', 'dense', 'hybrid_rerank')
        - retrieved_document_ids: Danh sách document_id lấy được
        - retrieved_chunk_ids: Danh sách chunk_id lấy được
        - citation_ids: Danh sách trích dẫn / citation
        - rbac_filtered_count: Số lượng candidate chunk bị lọc do không có quyền
        - status: 'SUCCESS' / 'DENIED' / 'ERROR'
        """
        # Sinh request_id nếu chưa truyền vào
        if not request_id:
            request_id = f"req-{uuid.uuid4().hex[:8]}"

        # Lấy timestamp UTC ISO 8601
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Đảm bảo danh sách rỗng nếu None
        retrieved_document_ids = list(set(retrieved_document_ids)) if retrieved_document_ids else []
        retrieved_chunk_ids = retrieved_chunk_ids if retrieved_chunk_ids else []
        citation_ids = citation_ids if citation_ids else []

        # Xây dựng đối tượng log (Tuyệt đối không chứa password / secret / api key)
        event_entry = {
            "timestamp_utc": now_utc,
            "request_id": request_id,
            "user_id_demo": user_id_demo,
            "user_role": user_role if isinstance(user_role, list) else [str(user_role)],
            "action": action,
            "query": query,
            "retrieval_method": retrieval_method,
            "retrieved_document_ids": retrieved_document_ids,
            "retrieved_chunk_ids": retrieved_chunk_ids,
            "citation_ids": citation_ids,
            "rbac_filtered_count": rbac_filtered_count,
            "status": status.upper()
        }

        if error_message:
            event_entry["error_message"] = str(error_message)

        # Ghi vào file audit_log.jsonl
        with open(self.log_file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event_entry, ensure_ascii=False) + "\n")

        return event_entry


# Singleton instance cho AuditLogger
_GLOBAL_AUDIT_LOGGER: Optional[AuditLogger] = None


def get_audit_logger(log_path: Optional[Path] = None) -> AuditLogger:
    global _GLOBAL_AUDIT_LOGGER
    if _GLOBAL_AUDIT_LOGGER is None or log_path is not None:
        _GLOBAL_AUDIT_LOGGER = AuditLogger(log_file_path=log_path)
    return _GLOBAL_AUDIT_LOGGER


if __name__ == "__main__":
    print("=" * 70)
    print("DEMO RUNNING AUDIT LOGGER (BUỔI 17)")
    print("=" * 70)
    logger = get_audit_logger()
    entry = logger.log_event(
        user_id_demo="usr_test_01",
        user_role=["Employee"],
        query="Quy định an toàn kho quỹ",
        action="TEST_LOG",
        retrieval_method="hybrid_rerank",
        retrieved_document_ids=["44209"],
        retrieved_chunk_ids=["doc_44209_dieu_1"],
        citation_ids=["[01/2014/TT-NHNN | Điều 1]"],
        rbac_filtered_count=2,
        status="SUCCESS"
    )
    print("Đã ghi log sự kiện demo:")
    print(json.dumps(entry, indent=2, ensure_ascii=False))
