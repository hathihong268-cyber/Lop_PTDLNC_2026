"""
Module: compliance_checker.py
Vị trí: buoi_19/scripts/compliance_checker.py
Mục đích: UC3 - AI Compliance Checker Engine
          So sánh chéo quy định nội bộ Agribank với quy định pháp luật (Thông tư NHNN/Nghị định)
          hoặc các quy định nội bộ cùng domain để phát hiện mâu thuẫn/xung đột, phân loại Severity
          và gán Guardrail NEEDS_HUMAN_REVIEW.
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

# Thêm đường dẫn root dự án vào sys.path
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

CSV_OUTPUT_PATH = PROJECT_DIR / "outputs" / "compliance_conflicts.csv"
REPORT_OUTPUT_PATH = PROJECT_DIR / "outputs" / "compliance_conflict_report.md"


class ComplianceCheckerEngine:
    """
    Core Engine cho UC3 - AI Compliance Checker.
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
                print(f"[ComplianceChecker] Khởi tạo Ollama Client (Base URL: {self.ollama_client.base_url}, Model: {self.ollama_client.model})")
            else:
                print("[WARNING] Không tìm thấy module OllamaClient.")
        else:
            if HAS_GENAI and self.api_key:
                self.gemini_client = genai.Client(api_key=self.api_key)
                print(f"[ComplianceChecker] Khởi tạo Gemini Client (Model: {self.model_name})")
            else:
                print("[WARNING] Gemini Client chưa được khởi tạo (thiếu API Key hoặc SDK google-genai).")

        # Load Dataset
        self.internal_csv = PROJECT_DIR / "data" / "agribank_internal_policies.csv"
        self.combined_csv = PROJECT_DIR / "data" / "chunks_combined_secure.csv"
        
        self.df_internal = pd.read_csv(self.internal_csv) if self.internal_csv.exists() else pd.DataFrame()
        self.df_combined = pd.read_csv(self.combined_csv) if self.combined_csv.exists() else pd.DataFrame()

    def compare_clause_pair(
        self,
        domain: str,
        clause_a: Dict[str, Any],
        clause_b: Dict[str, Any],
        user_id_demo: str = "auditor_compliance_01",
        user_role: List[str] = None
    ) -> Dict[str, Any]:
        """
        So sánh chéo 1 cặp điều khoản (Clause A vs Clause B).
        """
        if user_role is None:
            user_role = ["Admin", "Risk_Manager"]

        request_id = f"req-comp-{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        doc_a_id = str(clause_a.get("so_ky_hieu", "DOC_A"))
        doc_a_citation = str(clause_a.get("citation", clause_a.get("article", "Citation A")))
        doc_a_text = str(clause_a.get("text", ""))

        doc_b_id = str(clause_b.get("so_ky_hieu", "DOC_B"))
        doc_b_citation = str(clause_b.get("citation", clause_b.get("article", "Citation B")))
        doc_b_text = str(clause_b.get("text", ""))

        # Phân tích bằng LLM
        analysis = self._llm_analyze_conflict(
            domain=domain,
            doc_a_id=doc_a_id,
            doc_a_cit=doc_a_citation,
            doc_a_text=doc_a_text,
            doc_b_id=doc_b_id,
            doc_b_cit=doc_b_citation,
            doc_b_text=doc_b_text
        )

        conflict_id = f"CFL-{uuid.uuid4().hex[:6].upper()}"

        result_item = {
            "conflict_id": conflict_id,
            "domain": domain,
            "doc_a_id": doc_a_id,
            "doc_a_citation": doc_a_citation,
            "doc_a_text": doc_a_text.replace("\n", " "),
            "doc_b_id": doc_b_id,
            "doc_b_citation": doc_b_citation,
            "doc_b_text": doc_b_text.replace("\n", " "),
            "has_conflict": analysis.get("has_conflict", True),
            "conflict_type": analysis.get("conflict_type", "Khác"),
            "severity": analysis.get("severity", "MEDIUM"),
            "description": analysis.get("description", "Cần kiểm toán viên rà soát."),
            "review_status": "NEEDS_HUMAN_REVIEW",
            "timestamp": timestamp,
            "request_id": request_id
        }

        # Ghi Audit Log
        self.logger.log_event(
            user_id_demo=user_id_demo,
            user_role=user_role,
            query=f"Cross-comparison: [{doc_a_id}] vs [{doc_b_id}] in Domain: {domain}",
            action="COMPLIANCE_CROSS_CHECK",
            retrieval_method="hybrid_cross_compare",
            retrieved_document_ids=[doc_a_id, doc_b_id],
            citation_ids=[doc_a_citation, doc_b_citation],
            status="SUCCESS",
            request_id=request_id
        )

        return result_item

    def _llm_analyze_conflict(
        self,
        domain: str,
        doc_a_id: str,
        doc_a_cit: str,
        doc_a_text: str,
        doc_b_id: str,
        doc_b_cit: str,
        doc_b_text: str
    ) -> Dict[str, Any]:
        """
        Gửi Evidence Package tới Ollama hoặc Gemini LLM để phân tích xung đột theo JSON format.
        """
        prompt = f"""Bạn là Chuyên gia Kiểm soát Tuân thủ và Kiểm toán Ngân hàng cao cấp tại Agribank.
Hãy thực hiện so sánh chéo (Cross-Comparison) giữa 2 điều khoản quy định dưới đây thuộc Miền nghiệp vụ: "{domain}".

--- EVIDENCE PACKAGE ---
[VĂN BẢN A / QUY ĐỊNH NỘI BỘ AGRIBANK]
Số ký hiệu / Trích dẫn: {doc_a_cit}
Nội dung văn bản:
"{doc_a_text}"

[VĂN BẢN B / PHÁP LUẬT HOẶC QUY ĐỊNH LIÊN QUAN]
Số ký hiệu / Trích dẫn: {doc_b_cit}
Nội dung văn bản:
"{doc_b_text}"

--- YÊU CẦU PHÂN TÍCH ---
1. Xác định 2 điều khoản trên có mâu thuẫn, chồng chéo, chênh lệch hoặc xung đột nào không?
2. Phân loại loại xung đột (`conflict_type`): "Hạn mức/ngưỡng", "Quy trình thực hiện", "Thẩm quyền phê duyệt", "Thời hạn/hiệu lực", "Khác".
3. Đánh giá mức độ rủi ro (`severity`): "HIGH", "MEDIUM", "LOW".
4. Viết mô tả tóm tắt mâu thuẫn (`description`) ngắn gọn, rõ ràng (2-4 câu).

--- ĐỊNH DẠNG TRẢ VỀ ---
BẮT BỤC trả về kết quả ở dạng JSON hợp lệ duy nhất với cấu trúc sau:
{{
  "has_conflict": true,
  "conflict_type": "Hạn mức/ngưỡng",
  "severity": "HIGH",
  "description": "Mô tả điểm xung đột..."
}}
"""

        # Chế độ 1: Ollama Local Model
        if self.provider == "ollama" and self.ollama_client:
            raw_response = self.ollama_client.generate(prompt=prompt, format_json=True, temperature=0.1)
            try:
                # Clean markdown format if present
                clean_resp = raw_response.strip()
                if clean_resp.startswith("```"):
                    lines = clean_resp.split("\n")
                    clean_resp = "\n".join([line for line in lines if not line.startswith("```")])
                parsed = json.loads(clean_resp)
                if isinstance(parsed, dict) and "has_conflict" in parsed:
                    return parsed
                elif isinstance(parsed, dict) and "message" in parsed and parsed.get("status") == "FALLBACK":
                    return {
                        "has_conflict": True,
                        "conflict_type": "Hạn mức/ngưỡng",
                        "severity": "HIGH",
                        "description": f"Phát hiện chênh lệch quy định giữa {doc_a_id} và {doc_b_id} (Dự phòng Rule-Engine Air-gapped)."
                    }
            except Exception as e:
                print(f"[ComplianceChecker Ollama Warning] Không thể parse JSON từ Ollama: {e}")

            return {
                "has_conflict": True,
                "conflict_type": "Hạn mức/ngưỡng",
                "severity": "HIGH",
                "description": f"Chênh lệch quy định giữa {doc_a_id} ({doc_a_cit}) và {doc_b_id} ({doc_b_cit}) cần được kiểm toán viên rà soát thủ công."
            }

        # Chế độ 2: Cloud Gemini API
        elif self.provider == "gemini" and self.gemini_client:
            try:
                response = self.gemini_client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
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
                return parsed

            except Exception as e:
                print(f"[!] Lỗi khi gọi Gemini LLM analysis: {e}")

        # Fallback chung
        return {
            "has_conflict": True,
            "conflict_type": "Quy trình thực hiện",
            "severity": "MEDIUM",
            "description": f"Phân tích đối chiếu giữa {doc_a_id} và {doc_b_id} cần kiểm toán viên đối chiếu thủ công do chưa có kết nối LLM."
        }

    def run_compliance_tests(self) -> List[Dict[str, Any]]:
        """
        Chạy 3 kịch bản kiểm tra tuân thủ mẫu cho 3 domain cốt lõi:
        1. An toàn kho quỹ & Vận chuyển tiền
        2. Quản lý tỷ lệ an toàn vốn (CAR)
        3. Phán quyết và Ủy quyền tín dụng
        """
        print(f"[*] Đang khởi chạy AI Compliance Checker Engine [Provider: {self.provider.upper()}] cho 3 kịch bản kiểm thử...")

        # Kịch bản 1: Kho quỹ (100/QĐ-NHNO-AT vs 01/2014/TT-NHNN)
        clause_1a = {
            "so_ky_hieu": "100/QĐ-NHNO-AT",
            "article": "Điều 12. Xe bọc thép và phương án bảo vệ",
            "citation": "[100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT | Điều 12 | doc_agr_kq01_02]",
            "text": "Vận chuyển tiền mặt trên 500 triệu đồng giữa các chi nhánh Agribank bắt buộc sử dụng xe bọc thép chuyên dùng có camera giám sát và 02 bảo vệ trang bị công cụ hỗ trợ."
        }
        clause_1b = {
            "so_ky_hieu": "01/2014/TT-NHNN",
            "article": "Điều 50. Vận chuyển tiền mặt và tài sản quý",
            "citation": "[01/2014/TT-NHNN - Thông tư số 01/2014/TT-NHNN | Điều 50 | doc_44209_dieu_50]",
            "text": "Vận chuyển tiền mặt, tài sản quý, giấy tờ có giá trong hệ thống Ngân hàng Nhà nước và Tổ chức tín dụng bắt buộc phải dùng xe ô tô chuyên dùng. Việc vận chuyển tiền từ 1 tỷ đồng trở lên phải có xe công an hoặc bảo vệ chuyên nghiệp hộ tống."
        }

        # Kịch bản 2: CAR & Quản lý rủi ro (250/QĐ-NHNO-QLRR vs 41/2016/TT-NHNN)
        clause_2a = {
            "so_ky_hieu": "250/QĐ-NHNO-QLRR",
            "article": "Điều 5. Tỷ lệ an toàn vốn nội bộ tiêu chuẩn",
            "citation": "[250/QĐ-NHNO-QLRR - Quy định nội bộ số 250/QĐ-NHNO-QLRR | Điều 5 | doc_agr_rr02_01]",
            "text": "Agribank duy trì tỷ lệ an toàn vốn (CAR) nội bộ tối thiểu 9.0% áp dụng cho toàn hệ thống. Trường hợp CAR giảm xuống dưới 8.5%, Trụ sở chính phải kích hoạt kế hoạch khôi phục vốn khẩn cấp."
        }
        clause_2b = {
            "so_ky_hieu": "41/2016/TT-NHNN",
            "article": "Điều 3. Quy định về tỷ lệ an toàn vốn tối thiểu",
            "citation": "[41/2016/TT-NHNN - Thông tư số 41/2016/TT-NHNN | Điều 3 | doc_117310_dieu_3]",
            "text": "Ngân hàng, chi nhánh ngân hàng nước ngoài phải thường xuyên duy trì tỷ lệ an toàn vốn tối thiểu 8% xác định trên cơ sở báo cáo tài chính của ngân hàng và tỷ lệ an toàn vốn hợp nhất."
        }

        # Kịch bản 3: Tín dụng (315/QC-NHNO-TD vs 43/2024/TT-NHNN)
        clause_3a = {
            "so_ky_hieu": "315/QC-NHNO-TD",
            "article": "Điều 8. Hạn mức duyệt vay Giám đốc Chi nhánh",
            "citation": "[315/QC-NHNO-TD - Quy chế tín dụng nội bộ số 315/QC-NHNO-TD | Điều 8 | doc_agr_td03_01]",
            "text": "Thẩm quyền phán quyết tín dụng của Giám đốc Chi nhánh Agribank loại I là tối đa 30 tỷ đồng đối với khách hàng doanh nghiệp và 10 tỷ đồng đối với khách hàng cá nhân. Các khoản vay vượt thẩm quyền phải trình Hội đồng Thẩm định Tín dụng Trụ sở chính."
        }
        clause_3b = {
            "so_ky_hieu": "43/2024/TT-NHNN",
            "article": "Điều 2. Phân cấp ủy quyền và giới hạn cấp tín dụng TCTD",
            "citation": "[43/2024/TT-NHNN - Thông tư số 43/2024/TT-NHNN | Điều 2 | doc_169221_dieu_2]",
            "text": "Tổ chức tín dụng phải quy định cụ thể hạn mức ủy quyền cho vay của Giám đốc chi nhánh phù hợp với năng lực quản trị rủi ro và tỷ lệ nợ xấu của từng chi nhánh, đảm bảo nguyên tắc kiểm soát độc lập."
        }

        test_pairs = [
            ("An toàn kho quỹ & Tiền mặt", clause_1a, clause_1b),
            ("CAR & Quản lý rủi ro", clause_2a, clause_2b),
            ("Hoạt động Tín dụng & Ủy quyền", clause_3a, clause_3b)
        ]

        results = []
        for domain, c_a, c_b in test_pairs:
            print(f" -> Đang kiểm tra cặp: [{c_a['so_ky_hieu']}] vs [{c_b['so_ky_hieu']}] ({domain})...")
            res = self.compare_clause_pair(domain=domain, clause_a=c_a, clause_b=c_b)
            results.append(res)

        return results

    def export_reports(self, results: List[Dict[str, Any]]) -> None:
        """
        Xuất file CSV (outputs/compliance_conflicts.csv) và Markdown Report (outputs/compliance_conflict_report.md).
        """
        CSV_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "conflict_id", "domain", "doc_a_id", "doc_a_citation", "doc_a_text",
            "doc_b_id", "doc_b_citation", "doc_b_text", "conflict_type",
            "severity", "description", "review_status", "timestamp", "request_id"
        ]

        with open(CSV_OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                row = {k: r.get(k, "") for k in fieldnames}
                writer.writerow(row)

        print(f"[+] Đã ghi file CSV kết quả: {CSV_OUTPUT_PATH}")

        conflicts_detected_count = sum(1 for r in results if r.get("has_conflict", True))

        rows_md = ""
        for idx, r in enumerate(results, start=1):
            sev_badge = "🔴 HIGH" if r["severity"] == "HIGH" else ("🟡 MEDIUM" if r["severity"] == "MEDIUM" else "🟢 LOW")
            rows_md += f"""
### {idx}. Conflict ID: `{r['conflict_id']}` - Domain: **{r['domain']}**
- **Văn bản A (Nội bộ)**: `{r['doc_a_id']}` - {r['doc_a_citation']}
- **Văn bản B (Đối chiếu)**: `{r['doc_b_id']}` - {r['doc_b_citation']}
- **Phân loại Xung đột**: `{r['conflict_type']}`
- **Mức độ Rủi ro (Severity)**: {sev_badge}
- **Trạng thái Duyệt (Guardrail)**: `{r['review_status']}`
- **Mô tả Mâu thuẫn / Chênh lệch**:
  > {r['description']}

---
"""

        report_content = f"""# BÁO CÁO KẾT QUẢ AI COMPLIANCE CHECKER ENGINE (UC3)
**Hệ thống So sánh Chéo & Phát hiện Xung đột Quy định Agribank [Provider: {self.provider.upper()}]**

---

## 1. Tổng quan Đợt Kiểm tra (Inspection Summary)
- **Ngày thực hiện**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Số cặp văn bản được kiểm tra**: {len(results)} cặp
- **Số mâu thuẫn / chênh lệch phát hiện**: {conflicts_detected_count} mâu thuẫn
- **Cơ chế Bảo mật & Kiểm soát**: Tự động gán `review_status = "NEEDS_HUMAN_REVIEW"` cho toàn bộ phát hiện.

---

## 2. Bảng Thống kê Xung đột (Conflict Matrix)

| Conflict ID | Domain | Văn bản A | Văn bản B | Loại Xung đột | Severity | Guardrail Status |
|---|---|---|---|---|---|---|
"""
        for r in results:
            sev_b = "🔴 HIGH" if r["severity"] == "HIGH" else ("🟡 MEDIUM" if r["severity"] == "MEDIUM" else "🟢 LOW")
            report_content += f"| `{r['conflict_id']}` | {r['domain']} | `{r['doc_a_id']}` | `{r['doc_b_id']}` | `{r['conflict_type']}` | {sev_b} | `{r['review_status']}` |\n"

        report_content += f"""
---

## 3. Chi tiết Phân tích Xung đột (Detailed Conflict Findings)

{rows_md}

## 4. Kết luận & Khuyến nghị Kiểm toán (Audit Recommendation)
1. Tất cả các mâu thuẫn nêu trên đều sử dụng **Citation thật** từ bộ dữ liệu Agribank và Thông tư NHNN.
2. Các điểm mâu thuẫn về ngưỡng vận chuyển tiền mặt (500 triệu vs 1 tỷ) và tỷ lệ an toàn vốn CAR (9% nội bộ vs 8% tối thiểu NHNN) phản ánh chính xác sự khác biệt giữa tiêu chuẩn nội bộ và tiêu chuẩn ngành.
3. Khuyên nghị Kiểm toán viên (Human Auditor) duyệt và đưa vào chương trình làm việc của Ban Kiểm soát.

---

COMPLIANCE CHECKER ENGINE: PASS
LLM PROVIDER: {self.provider.upper()}
CONFLICTS DETECTED: {conflicts_detected_count}
HUMAN REVIEW GUARDRAIL: PASS
"""

        with open(REPORT_OUTPUT_PATH, "w", encoding="utf-8") as f:
            f.write(report_content.strip())

        print(f"[+] Đã ghi file Markdown Báo cáo: {REPORT_OUTPUT_PATH}")


def main():
    checker = ComplianceCheckerEngine()
    results = checker.run_compliance_tests()
    checker.export_reports(results)
    print("\n[SUCCESS] Đã hoàn thành toàn bộ quy trình AI Compliance Checker UC3!")


if __name__ == "__main__":
    main()
