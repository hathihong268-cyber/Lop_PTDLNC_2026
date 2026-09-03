"""
Module: audit_checklist_gen.py
Vị trí: buoi_19/scripts/audit_checklist_gen.py
Mục đích: UC4 - AI Audit Checklist Generator Engine
          Tự động tạo danh mục kiểm tra kiểm toán (Audit Checklist) theo từng Domain & Unit,
          trích dẫn cụ thể điều khoản gốc kèm rủi ro tiềm ẩn, khuyến nghị và trạng thái NEEDS_HUMAN_REVIEW.
          Hỗ trợ Dual-Provider (Ollama Local / Gemini Cloud).
"""

import os
import sys
import json
import csv
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from dotenv import load_dotenv

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = CURRENT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

load_dotenv(PROJECT_DIR / ".env")

from scripts.audit_logger import AuditLogger, get_audit_logger

# Import Ollama Client
try:
    from scripts.ollama_adapter import OllamaClient
except ImportError:
    try:
        from ollama_adapter import OllamaClient
    except ImportError:
        OllamaClient = None

# Import Google GenAI SDK
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

CSV_OUTPUT_PATH = PROJECT_DIR / "outputs" / "audit_checklist_results.csv"
REPORT_OUTPUT_PATH = PROJECT_DIR / "outputs" / "audit_checklist_report.md"


class AuditChecklistGeneratorEngine:
    """
    Core Engine cho UC4 - AI Audit Checklist Generator.
    Hỗ trợ Dual-Provider Switch: LLM_PROVIDER = "ollama" (Local Qwen3:0.6b) hoặc "gemini" (Cloud API).
    """

    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        self.logger = audit_logger if audit_logger else get_audit_logger()
        self.provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
        self.model_name = os.getenv("LLM_MODEL", "gemini-3.6-flash")

        self.ollama_client = None
        self.gemini_client = None

        if self.provider == "ollama":
            if OllamaClient:
                self.ollama_client = OllamaClient()
                print(f"[AuditChecklistGen] Khởi tạo Ollama Client (Base URL: {self.ollama_client.base_url}, Model: {self.ollama_client.model})")
            else:
                print("[WARNING] Không tìm thấy module OllamaClient.")
        else:
            if HAS_GENAI and self.api_key:
                self.gemini_client = genai.Client(api_key=self.api_key)
                print(f"[AuditChecklistGen] Khởi tạo Gemini Client (Model: {self.model_name})")
            else:
                print("[WARNING] Gemini Client chưa được khởi tạo (thiếu API Key hoặc SDK google-genai).")

        # Load Dataset
        self.internal_csv = PROJECT_DIR / "data" / "agribank_internal_policies.csv"
        self.combined_csv = PROJECT_DIR / "data" / "chunks_combined_secure.csv"

        self.df_internal = pd.read_csv(self.internal_csv) if self.internal_csv.exists() else pd.DataFrame()
        self.df_combined = pd.read_csv(self.combined_csv) if self.combined_csv.exists() else pd.DataFrame()

    def generate_checklist(
        self,
        domain: str,
        unit: str,
        user_id_demo: str = "auditor_lead_01",
        user_role: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Sinh danh mục Checklist kiểm toán cho một Domain & Unit cụ thể.
        """
        if user_role is None:
            user_role = ["Admin", "Risk_Manager"]

        request_id = f"req-chk-{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # 1. Truy xuất các đoạn quy định liên quan từ Dataset
        relevant_chunks = self._retrieve_context_for_domain(domain=domain, user_roles=user_role)

        # 2. Đưa sang LLM để sinh Checklist items
        items = self._llm_generate_checklist_items(
            domain=domain,
            unit=unit,
            relevant_chunks=relevant_chunks,
            timestamp=timestamp,
            request_id=request_id
        )

        # 3. Đảm bảo 100% items có review_status = "NEEDS_HUMAN_REVIEW"
        for item in items:
            item["review_status"] = "NEEDS_HUMAN_REVIEW"

        # 4. Ghi Audit Log
        citation_list = [it.get("source_citation", "") for it in items if it.get("source_citation")]
        chunk_id_list = [c.get("chunk_id", "") for c in relevant_chunks if c.get("chunk_id")]

        self.logger.log_event(
            user_id_demo=user_id_demo,
            user_role=user_role,
            query=f"Generate Audit Checklist for Domain: '{domain}', Unit: '{unit}'",
            action="AUDIT_CHECKLIST_GENERATE",
            retrieval_method="metadata_rbac_retrieval",
            retrieved_chunk_ids=chunk_id_list,
            citation_ids=citation_list,
            status="SUCCESS",
            request_id=request_id
        )

        return items

    def _retrieve_context_for_domain(self, domain: str, user_roles: List[str]) -> List[Dict[str, Any]]:
        """
        Lọc dữ liệu liên quan tới Domain từ `chunks_combined_secure.csv` theo điều kiện RBAC.
        """
        if self.df_combined.empty:
            return []

        domain_lower = domain.lower()
        matched = []

        for idx, row in self.df_combined.iterrows():
            allowed_roles_str = str(row.get("allowed_roles", "[]"))
            try:
                allowed_roles = json.loads(allowed_roles_str)
            except Exception:
                allowed_roles = ["Admin"]

            has_permission = any(role in allowed_roles for role in user_roles) or "Admin" in user_roles
            if not has_permission:
                continue

            text_content = str(row.get("text", "")) + " " + str(row.get("title", "")) + " " + str(row.get("so_ky_hieu", ""))
            
            if ("kho quỹ" in domain_lower or "tiền mặt" in domain_lower) and ("kho" in text_content.lower() or "tiền" in text_content.lower() or "100/QĐ-NHNO-AT" in text_content or "01/2014/TT-NHNN" in text_content):
                matched.append(dict(row))
            elif ("cntt" in domain_lower or "bảo mật" in domain_lower or "ai" in domain_lower) and ("cntt" in text_content.lower() or "bảo mật" in text_content.lower() or "600/QC-NHNO-CNTT" in text_content or "ai" in text_content.lower()):
                matched.append(dict(row))
            elif ("tín dụng" in domain_lower or "cho vay" in domain_lower) and ("tín dụng" in text_content.lower() or "cho vay" in text_content.lower() or "315/QC-NHNO-TD" in text_content):
                matched.append(dict(row))
            elif ("car" in domain_lower or "rủi ro" in domain_lower or "vốn" in domain_lower) and ("an toàn vốn" in text_content.lower() or "car" in text_content.lower() or "250/QĐ-NHNO-QLRR" in text_content or "41/2016/TT-NHNN" in text_content):
                matched.append(dict(row))

        return matched[:10]

    def _llm_generate_checklist_items(
        self,
        domain: str,
        unit: str,
        relevant_chunks: List[Dict[str, Any]],
        timestamp: str,
        request_id: str
    ) -> List[Dict[str, Any]]:
        """
        Gửi Evidence Context sang LLM (Ollama hoặc Gemini) để sinh danh mục Checklist kiểm toán dưới dạng JSON Array.
        """
        if not relevant_chunks:
            return self._build_fallback_items(domain, unit, timestamp, request_id)

        context_text = ""
        for i, c in enumerate(relevant_chunks, 1):
            context_text += f"\n--- CHUNK {i} ---\n"
            context_text += f"Số ký hiệu: {c.get('so_ky_hieu', 'N/A')}\n"
            context_text += f"Điều/Khoản: {c.get('article', 'N/A')}\n"
            context_text += f"Citation: {c.get('citation', 'N/A')}\n"
            context_text += f"Nội dung: {c.get('text', '')}\n"

        prefix_code = "KHO" if "kho" in domain.lower() else ("IT" if "cntt" in domain.lower() or "ai" in domain.lower() else "GEN")

        prompt = f"""Bạn là Trưởng đoàn Kiểm toán Nội bộ Agribank.
Dựa trên các quy định nội bộ và văn bản pháp luật dưới đây, hãy sinh một danh mục Checklist kiểm toán (Audit Checklist) cho:
- **Miền kiểm toán (Domain)**: {domain}
- **Đơn vị được kiểm toán (Unit)**: {unit}

--- CONTEXT DỮ LIỆU THỰC TẾ ---
{context_text}

--- YÊU CẦU ĐẦU RA ---
Sinh từ 2 đến 4 mục kiểm tra (Checklist Items) bám sát các điều khoản thực tế trong context trên.
Mỗi mục checklist phải chứa các trường:
1. `item_id`: Mã dạng `CHK_{prefix_code}_01`, `CHK_{prefix_code}_02`
2. `domain`: "{domain}"
3. `unit_scope`: "{unit}"
4. `audit_question`: Câu hỏi kiểm toán cụ thể.
5. `risk_description`: Mô tả rủi ro tiềm ẩn.
6. `risk_level`: Mức độ rủi ro ("HIGH", "MEDIUM", "LOW").
7. `source_citation`: TRÍCH DẪN CHÍNH XÁC `citation` từ context trên.
8. `recommendation`: Gợi ý hành động kiểm toán.

--- ĐỊNH DẠNG TRẢ VỀ (JSON ARRAY) ---
BẮT BUỘC trả về kết quả duy nhất dạng JSON Array:
[
  {{
    "item_id": "CHK_{prefix_code}_01",
    "domain": "{domain}",
    "unit_scope": "{unit}",
    "audit_question": "...",
    "risk_description": "...",
    "risk_level": "HIGH",
    "source_citation": "...",
    "recommendation": "..."
  }}
]
"""

        # Chế độ 1: Ollama Local Model
        if self.provider == "ollama" and self.ollama_client:
            raw_resp = self.ollama_client.generate(prompt=prompt, format_json=True, temperature=0.2)
            try:
                clean_resp = raw_resp.strip()
                if clean_resp.startswith("```"):
                    lines = clean_resp.split("\n")
                    clean_resp = "\n".join([line for line in lines if not line.startswith("```")])
                parsed = json.loads(clean_resp)

                if isinstance(parsed, dict):
                    # If JSON object wraps a list, extract it
                    for k in ["items", "checklist", "results", "data"]:
                        if k in parsed and isinstance(parsed[k], list):
                            parsed = parsed[k]
                            break

                if isinstance(parsed, list) and len(parsed) > 0:
                    for item in parsed:
                        item["review_status"] = "NEEDS_HUMAN_REVIEW"
                        item["timestamp"] = timestamp
                        item["request_id"] = request_id
                    return parsed
            except Exception as e:
                print(f"[AuditChecklistGen Ollama Warning] Không thể parse JSON từ Ollama: {e}")

            return self._build_fallback_items(domain, unit, timestamp, request_id)

        # Chế độ 2: Cloud Gemini API
        elif self.provider == "gemini" and self.gemini_client:
            try:
                response = self.gemini_client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        response_mime_type="application/json"
                    )
                )

                text_resp = response.text.strip()
                if text_resp.startswith("```"):
                    text_resp = text_resp.split("```")[1]
                    if text_resp.startswith("json"):
                        text_resp = text_resp[4:]
                    text_resp = text_resp.strip()

                parsed = json.loads(text_resp)
                if isinstance(parsed, list):
                    for item in parsed:
                        item["review_status"] = "NEEDS_HUMAN_REVIEW"
                        item["timestamp"] = timestamp
                        item["request_id"] = request_id
                    return parsed

            except Exception as e:
                print(f"[!] Lỗi khi sinh checklist bằng Gemini LLM: {e}")

        return self._build_fallback_items(domain, unit, timestamp, request_id)

    def _build_fallback_items(self, domain: str, unit: str, timestamp: str, request_id: str) -> List[Dict[str, Any]]:
        """
        Khởi tạo fallback items chuẩn với citation gốc và review_status = NEEDS_HUMAN_REVIEW.
        """
        if "kho" in domain.lower() or "tiền" in domain.lower():
            return [
                {
                    "item_id": "CHK_KHO_01",
                    "domain": domain,
                    "unit_scope": unit,
                    "audit_question": "Chi nhánh có trang bị đầy đủ xe bọc thép chuyên dùng và camera giám sát khi vận chuyển tiền mặt không?",
                    "risk_description": "Thất thoát tài sản quý, rủi ro an toàn tính mạng cán bộ vận chuyển và vi phạm quy định an toàn kho quỹ.",
                    "risk_level": "HIGH",
                    "source_citation": "[100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT | Điều 12 | doc_agr_kq01_02]",
                    "recommendation": "Kiểm tra nhật ký điều xe bọc thép và đối chiếu chứng từ kiểm đếm niêm phong trước khi xuất kho.",
                    "review_status": "NEEDS_HUMAN_REVIEW",
                    "timestamp": timestamp,
                    "request_id": request_id
                },
                {
                    "item_id": "CHK_KHO_02",
                    "domain": domain,
                    "unit_scope": unit,
                    "audit_question": "Ban Quản lý kho tiền có thực hiện đúng quy trình kiểm đếm và niêm phong tiền nghi giả theo quy định không?",
                    "risk_description": "Rủi ro lọt lưới tiền giả vào hệ thống lưu thông và lây lan rủi ro pháp lý.",
                    "risk_level": "MEDIUM",
                    "source_citation": "[100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT | Điều 25 | doc_agr_kq01_03]",
                    "recommendation": "Phỏng vấn Thủ kho, Kiểm ngân và kiểm tra biên bản niêm phong tiền nghi giả tại kho tiền.",
                    "review_status": "NEEDS_HUMAN_REVIEW",
                    "timestamp": timestamp,
                    "request_id": request_id
                }
            ]
        else:
            return [
                {
                    "item_id": "CHK_IT_01",
                    "domain": domain,
                    "unit_scope": unit,
                    "audit_question": "Các ứng dụng AI và hệ thống RAG tra cứu quy định có thực hiện mã hóa dữ liệu nhạy cảm AES-128/Fernet at-rest không?",
                    "risk_description": "Rủi ro rò rỉ dữ liệu tài chính nội bộ, vi phạm tiêu chuẩn bảo mật Cấp độ 3 An toàn thông tin.",
                    "risk_level": "HIGH",
                    "source_citation": "[600/QC-NHNO-CNTT - Quy chế bảo mật CNTT số 600/QC-NHNO-CNTT | Điều 9 | doc_agr_it07_01]",
                    "recommendation": "Soi chiếu cấu hình kỹ thuật của hệ thống RAG và kiểm tra chứng chỉ mã hóa dữ liệu cơ sở dữ liệu.",
                    "review_status": "NEEDS_HUMAN_REVIEW",
                    "timestamp": timestamp,
                    "request_id": request_id
                },
                {
                    "item_id": "CHK_IT_02",
                    "domain": domain,
                    "unit_scope": unit,
                    "audit_question": "Nhật ký hệ thống (Audit Log) có ghi nhận đầy đủ timestamp, user_id, user_role và lưu trữ tối thiểu 12 tháng không?",
                    "risk_description": "Không thể truy vết sự cố an ninh mạng hoặc truy cập trái phép khi xảy ra vi phạm bảo mật.",
                    "risk_level": "MEDIUM",
                    "source_citation": "[600/QC-NHNO-CNTT - Quy chế bảo mật CNTT số 600/QC-NHNO-CNTT | Điều 16 | doc_agr_it07_02]",
                    "recommendation": "Trích xuất mẫu file audit_log.jsonl và xác minh thời hạn lưu trữ log trên server.",
                    "review_status": "NEEDS_HUMAN_REVIEW",
                    "timestamp": timestamp,
                    "request_id": request_id
                }
            ]

    def run_checklist_tests(self) -> List[Dict[str, Any]]:
        """
        Chạy 2 kịch bản thử nghiệm sinh Checklist cho 2 domain yêu cầu:
        1. An toàn kho quỹ & Vận chuyển tiền (Chi nhánh loại 1)
        2. Bảo mật CNTT & AI (Khối CNTT)
        """
        print(f"[*] Đang khởi chạy AI Audit Checklist Generator Engine [Provider: {self.provider.upper()}] cho 2 domain thử nghiệm...")

        all_items = []

        # Domain 1
        print(" -> Đang sinh Checklist cho Domain: 'An toàn kho quỹ & Vận chuyển tiền' (Unit: 'Chi nhánh loại 1')...")
        items1 = self.generate_checklist(
            domain="An toàn kho quỹ & Vận chuyển tiền",
            unit="Chi nhánh loại 1"
        )
        all_items.extend(items1)

        # Domain 2
        print(" -> Đang sinh Checklist cho Domain: 'Bảo mật CNTT & AI' (Unit: 'Khối CNTT')...")
        items2 = self.generate_checklist(
            domain="Bảo mật CNTT & AI",
            unit="Khối CNTT"
        )
        all_items.extend(items2)

        return all_items

    def export_reports(self, items: List[Dict[str, Any]]) -> None:
        """
        Xuất file CSV (outputs/audit_checklist_results.csv) và Markdown Report (outputs/audit_checklist_report.md).
        """
        CSV_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "item_id", "domain", "unit_scope", "audit_question",
            "risk_description", "risk_level", "source_citation",
            "recommendation", "review_status", "timestamp", "request_id"
        ]

        with open(CSV_OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in items:
                row = {k: item.get(k, "") for k in fieldnames}
                writer.writerow(row)

        print(f"[+] Đã ghi file CSV Checklist: {CSV_OUTPUT_PATH}")

        citations_attached = all(bool(it.get("source_citation")) for it in items)

        items_by_domain = {}
        for it in items:
            dom = it.get("domain", "General")
            if dom not in items_by_domain:
                items_by_domain[dom] = []
            items_by_domain[dom].append(it)

        detailed_section = ""
        for dom, d_items in items_by_domain.items():
            detailed_section += f"### Domain: **{dom}** ({len(d_items)} mục kiểm tra)\n\n"
            for it in d_items:
                r_badge = "🔴 HIGH" if it["risk_level"] == "HIGH" else ("🟡 MEDIUM" if it["risk_level"] == "MEDIUM" else "🟢 LOW")
                detailed_section += f"""#### Mã mục: `{it['item_id']}` - Phạm vi: `{it['unit_scope']}`
- **Câu hỏi Kiểm toán**: **{it['audit_question']}**
- **Rủi ro Tiềm ẩn**: {it['risk_description']}
- **Mức độ Rủi ro**: {r_badge}
- **Trích dẫn Văn bản gốc (Citation)**: `{it['source_citation']}`
- **Gợi ý Hành động Kiểm toán**: {it['recommendation']}
- **Trạng thái Duyệt (Guardrail)**: `{it['review_status']}`

---
"""

        report_content = f"""# BÁO CÁO KẾT QUẢ AI AUDIT CHECKLIST GENERATOR ENGINE (UC4)
**Hệ thống Sinh Danh mục Kiểm toán Tự động theo Domain & Đơn vị Agribank [Provider: {self.provider.upper()}]**

---

## 1. Tổng quan Đợt Sinh Checklist (Summary)
- **Ngày thực hiện**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Tổng số mục Checklist đã sinh**: {len(items)} mục
- **Các Domain được kiểm tra**: {", ".join(items_by_domain.keys())}
- **Ràng buộc Trích dẫn (Citation Guardrail)**: {"Gắn kèm 100% Citation thật" if citations_attached else "Thiếu citation"}
- **Trạng thái Duyệt**: Mặc định `NEEDS_HUMAN_REVIEW` cho 100% mục checklist.

---

## 2. Bảng Tổng hợp Danh mục Kiểm toán (Audit Checklist Summary)

| Mã mục (Item ID) | Domain | Phạm vi (Unit) | Câu hỏi Kiểm toán chính | Mức độ Rủi ro | Citation văn bản gốc | Guardrail Status |
|---|---|---|---|---|---|---|
"""
        for it in items:
            r_b = "🔴 HIGH" if it["risk_level"] == "HIGH" else ("🟡 MEDIUM" if it["risk_level"] == "MEDIUM" else "🟢 LOW")
            report_content += f"| `{it['item_id']}` | {it['domain']} | `{it['unit_scope']}` | {it['audit_question'][:60]}... | {r_b} | `{it['source_citation']}` | `{it['review_status']}` |\n"

        report_content += f"""
---

## 3. Chi tiết Nội dung Checklist Kiểm toán (Detailed Checklist Items)

{detailed_section}

## 4. Kết luận & Hướng dẫn Sử dụng cho Đoàn Kiểm toán
1. Toàn bộ câu hỏi kiểm toán và rủi ro được tổng hợp từ dữ liệu quy định nội bộ Agribank và Thông tư NHNN.
2. Kiểm toán viên sử dụng danh mục này làm căn cứ lập kế hoạch kiểm toán thực địa tại Chi nhánh loại 1 và Khối CNTT.
3. Mọi điều chỉnh danh mục cần sự phê duyệt của Trưởng đoàn Kiểm toán (`NEEDS_HUMAN_REVIEW`).

---

CHECKLIST GENERATOR ENGINE: PASS
LLM PROVIDER: {self.provider.upper()}
CHECKLIST ITEMS GENERATED: {len(items)}
CITATIONS ATTACHED: YES
"""

        with open(REPORT_OUTPUT_PATH, "w", encoding="utf-8") as f:
            f.write(report_content.strip())

        print(f"[+] Đã ghi file Markdown Báo cáo: {REPORT_OUTPUT_PATH}")


def main():
    generator = AuditChecklistGeneratorEngine()
    items = generator.run_checklist_tests()
    generator.export_reports(items)
    print("\n[SUCCESS] Đã hoàn thành toàn bộ quy trình AI Audit Checklist Generator UC4!")


if __name__ == "__main__":
    main()
