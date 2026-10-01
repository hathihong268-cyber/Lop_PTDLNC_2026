"""
Application: app.py
Vị trí: buoi_17/app.py (hoặc buoi_18/app.py)
Mục đích: Giao diện Web Streamlit cho Buổi 18 - AI Compliance Checker (UC3),
          AI Audit Checklist Generator (UC4) & RBAC Audit Trail.
"""

import os
import sys
import json
import csv
import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Set Page Config
st.set_page_config(
    page_title="AGRIBANK AI COMPLIANCE & AUDIT SYSTEM — BUỔI 18",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Base Paths
BUOI_17_DIR = Path(__file__).resolve().parent
if str(BUOI_17_DIR) not in sys.path:
    sys.path.insert(0, str(BUOI_17_DIR))

load_dotenv(BUOI_17_DIR / ".env")

# Import Core Engines
from scripts.compliance_checker import ComplianceCheckerEngine, CSV_OUTPUT_PATH as UC3_CSV_PATH, REPORT_OUTPUT_PATH as UC3_MD_PATH
from scripts.audit_checklist_gen import AuditChecklistGeneratorEngine, CSV_OUTPUT_PATH as UC4_CSV_PATH, REPORT_OUTPUT_PATH as UC4_MD_PATH
from scripts.audit_logger import AuditLogger, DEFAULT_AUDIT_LOG_PATH

# Cache System Engines
@st.cache_resource
def get_compliance_checker():
    return ComplianceCheckerEngine()

@st.cache_resource
def get_checklist_generator():
    return AuditChecklistGeneratorEngine()

@st.cache_resource
def get_audit_logger():
    return AuditLogger()

compliance_engine = get_compliance_checker()
checklist_engine = get_checklist_generator()
audit_logger = get_audit_logger()

# Initialize Session States for interactive approvals
if "uc3_results" not in st.session_state:
    st.session_state.uc3_results = []

if "uc4_items" not in st.session_state:
    st.session_state.uc4_items = []

# ------------------------------------------------------------------------------
# BANNER TRÊN CÙNG & HEADER
# ------------------------------------------------------------------------------
st.warning("⚠️ **Demo sản phẩm AI Kiểm toán - Kết quả gợi ý cần kiểm toán viên xác minh trước khi ban hành.**")

st.title("🛡️ AGRIBANK AI COMPLIANCE & AUDIT SYSTEM — BUỔI 18")
st.caption("Ứng dụng AI So sánh chéo Quy định Tuân thủ (UC3) & Tự động Sinh Checklist Kiểm toán (UC4) tích hợp RBAC Audit Trail")

# ------------------------------------------------------------------------------
# SIDEBAR: NGƯỜI DÙNG & TÌNH TRẠNG DỮ LIỆU
# ------------------------------------------------------------------------------
st.sidebar.header("🔐 Cấu hình Người dùng Demo")

user_id_demo = st.sidebar.text_input("Mã Người dùng (User ID)", value="auditor_lead_01")
role_options = ["Admin", "Risk_Manager", "KiemToanVien", "Staff", "HR"]
selected_role = st.sidebar.selectbox("Vai trò (User Role)", role_options, index=0)

st.sidebar.divider()
st.sidebar.header("🌐 Trạng thái Kết nối Dữ liệu")

path_internal = BUOI_17_DIR / "data" / "agribank_internal_policies.csv"
path_combined = BUOI_17_DIR / "data" / "chunks_combined_secure.csv"

if path_internal.exists():
    df_int = pd.read_csv(path_internal)
    st.sidebar.success(f"🟢 **Internal Policies**: {len(df_int)} Chunks (10 Văn bản Agribank)")
else:
    st.sidebar.error("🔴 **Internal Policies**: Thiếu file `agribank_internal_policies.csv`!")

if path_combined.exists():
    df_comb = pd.read_csv(path_combined)
    st.sidebar.success(f"🟢 **Combined Corpus**: {len(df_comb)} Chunks (25 Văn bản Tổng hợp)")
else:
    st.sidebar.error("🔴 **Combined Corpus**: Thiếu file `chunks_combined_secure.csv`!")

st.sidebar.divider()

# Reset Session / Clear Audit Log
col_sb1, col_sb2 = st.sidebar.columns(2)
if col_sb1.button("🔄 Reset Session", use_container_width=True):
    st.session_state.uc3_results = []
    st.session_state.uc4_items = []
    st.rerun()

if col_sb2.button("🧹 Clear Logs", use_container_width=True):
    if DEFAULT_AUDIT_LOG_PATH.exists():
        open(DEFAULT_AUDIT_LOG_PATH, "w", encoding="utf-8").close()
    st.sidebar.info("Đã dọn dẹp audit log.")
    st.rerun()

# ------------------------------------------------------------------------------
# CÁC TAB CHÍNH
# ------------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs([
    "⚖️ TAB 1: AI COMPLIANCE CHECKER (UC3)",
    "📝 TAB 2: AUDIT CHECKLIST GENERATOR (UC4)",
    "📜 TAB 3: AUDIT LOG & SYSTEM TRAIL"
])

# ==============================================================================
# TAB 1: UC3 - AI COMPLIANCE CHECKER
# ==============================================================================
with tab1:
    st.subheader("⚖️ AI Compliance Checker - Kiểm tra & So sánh chéo Quy định")
    st.write("Đối chiếu các quy định nội bộ Agribank với Thông tư/Nghị định quản lý nhà nước để phát hiện mâu thuẫn, chồng chéo và đánh giá Severity.")

    col_t1_1, col_t1_2 = st.columns([3, 1])
    
    domain_filter = col_t1_1.selectbox(
        "Chọn Bộ lọc Domain Nghiệp vụ để quét:",
        ["Tất cả Domains", "An toàn kho quỹ & Tiền mặt", "CAR & Quản lý rủi ro", "Hoạt động Tín dụng & Ủy quyền"]
    )

    btn_scan = col_t1_2.button("⚡ Phát hiện xung đột & Mâu thuẫn", type="primary", use_container_width=True)

    if btn_scan:
        with st.spinner("Đang truy xuất Evidence Package và gọi AI đối chiếu mâu thuẫn..."):
            all_res = compliance_engine.run_compliance_tests()
            if domain_filter != "Tất cả Domains":
                filtered_res = [r for r in all_res if r.get("domain") == domain_filter]
            else:
                filtered_res = all_res
            st.session_state.uc3_results = filtered_res
            compliance_engine.export_reports(all_res)

    results = st.session_state.uc3_results

    if results:
        st.divider()
        st.subheader(f"🔍 Danh sách Mâu thuẫn / Chênh lệch Phát hiện ({len(results)} kết quả)")

        # Render Cards
        for idx, item in enumerate(results, start=1):
            sev = item.get("severity", "MEDIUM")
            if sev == "HIGH":
                sev_badge = "🔴 HIGH"
                border_color = "red"
            elif sev == "MEDIUM":
                sev_badge = "🟡 MEDIUM"
                border_color = "orange"
            else:
                sev_badge = "🟢 LOW"
                border_color = "green"

            with st.container(border=True):
                st.markdown(f"### Mẫu #{idx} | Conflict ID: `{item['conflict_id']}` | Domain: **{item['domain']}**")
                
                col_c1, col_c2 = st.columns(2)
                
                with col_c1:
                    st.info(f"**VĂN BẢN A (NỘI BỘ AGRIBANK)**\n\n**Số ký hiệu**: `{item['doc_a_id']}`\n\n**Trích dẫn**: {item['doc_a_citation']}")
                    st.write(f"**Nội dung:** {item['doc_a_text']}")
                
                with col_c2:
                    st.success(f"**VĂN BẢN B (ĐỐI CHIẾU)**\n\n**Số ký hiệu**: `{item['doc_b_id']}`\n\n**Trích dẫn**: {item['doc_b_citation']}")
                    st.write(f"**Nội dung:** {item['doc_b_text']}")

                st.markdown("---")
                col_info1, col_info2, col_info3 = st.columns(3)
                col_info1.markdown(f"**Loại xung đột**: `{item['conflict_type']}`")
                col_info2.markdown(f"**Severity**: {sev_badge}")
                col_info3.markdown(f"**Guardrail Status**: `{item['review_status']}`")

                st.markdown("**Phân tích chi tiết từ AI:**")
                st.warning(f"💡 {item['description']}")

                # Auditor Action Toggle
                col_act1, col_act2 = st.columns([2, 2])
                with col_act1:
                    if st.button(f"✅ Phê duyệt & Đưa vào Biên bản ({item['conflict_id']})", key=f"btn_approve_{idx}"):
                        item["review_status"] = "APPROVED_BY_AUDITOR"
                        st.success("Đã cập nhật trạng thái phê duyệt!")
                        st.rerun()

        st.divider()
        st.subheader("📥 Tải xuống Kết quả UC3")
        col_dl1, col_dl2 = st.columns(2)
        
        if UC3_CSV_PATH.exists():
            with open(UC3_CSV_PATH, "rb") as f_csv:
                col_dl1.download_button(
                    label="📄 Tải Báo cáo CSV (compliance_conflicts.csv)",
                    data=f_csv,
                    file_name="compliance_conflicts.csv",
                    mime="text/csv",
                    use_container_width=True
                )

        if UC3_MD_PATH.exists():
            with open(UC3_MD_PATH, "rb") as f_md:
                col_dl2.download_button(
                    label="📝 Tải Báo cáo Markdown (compliance_conflict_report.md)",
                    data=f_md,
                    file_name="compliance_conflict_report.md",
                    mime="text/markdown",
                    use_container_width=True
                )
    else:
        st.info("Bấm nút **'Phát hiện xung đột & Mâu thuẫn'** ở trên để thực hiện kiểm tra.")

# ==============================================================================
# TAB 2: UC4 - AI AUDIT CHECKLIST GENERATOR
# ==============================================================================
with tab2:
    st.subheader("📝 AI Audit Checklist Generator - Sinh Checklist Kiểm toán Tự động")
    st.write("Nhận đầu vào Domain và Đơn vị (Unit) để AI tự động trích xuất quy định, sinh câu hỏi kiểm toán, phân tích rủi ro và gợi ý hành động kiểm toán.")

    col_t2_1, col_t2_2, col_t2_3 = st.columns([2, 2, 1])

    sel_domain = col_t2_1.selectbox(
        "Chọn Phạm vi Domain:",
        ["An toàn kho quỹ & Vận chuyển tiền", "Bảo mật CNTT & AI", "Hoạt động Tín dụng & Cho vay", "CAR & Quản lý rủi ro"]
    )

    sel_unit = col_t2_2.selectbox(
        "Chọn Đơn vị được Kiểm toán (Unit):",
        ["Chi nhánh loại 1", "Phòng giao dịch", "Khối CNTT", "Phòng Kế toán"]
    )

    btn_gen_chk = col_t2_3.button("📝 Tạo bản nháp Checklist", type="primary", use_container_width=True)

    if btn_gen_chk:
        with st.spinner(f"Đang phân tích quy định và sinh Checklist cho {sel_domain} tại {sel_unit}..."):
            items = checklist_engine.generate_checklist(
                domain=sel_domain,
                unit=sel_unit,
                user_id_demo=user_id_demo,
                user_role=[selected_role]
            )
            st.session_state.uc4_items = items
            checklist_engine.export_reports(items)

    chk_items = st.session_state.uc4_items

    if chk_items:
        st.divider()
        st.subheader(f"📋 Danh mục Checklist Kiểm toán đã sinh ({len(chk_items)} mục)")

        # Display Dataframe
        df_show = []
        for it in chk_items:
            df_show.append({
                "Mã mục": it.get("item_id"),
                "Domain": it.get("domain"),
                "Đơn vị (Unit)": it.get("unit_scope"),
                "Câu hỏi Kiểm toán": it.get("audit_question"),
                "Rủi ro Tiềm ẩn": it.get("risk_description"),
                "Mức rủi ro": it.get("risk_level"),
                "Citation Văn bản gốc": it.get("source_citation"),
                "Gợi ý Hành động": it.get("recommendation"),
                "Trạng thái": it.get("review_status")
            })
        
        st.dataframe(pd.DataFrame(df_show), use_container_width=True)

        st.markdown("### 🔍 Chi tiết từng Mục Checklist Kiểm toán")
        for idx, it in enumerate(chk_items, start=1):
            r_lvl = it.get("risk_level", "MEDIUM")
            r_badge = "🔴 HIGH" if r_lvl == "HIGH" else ("🟡 MEDIUM" if r_lvl == "MEDIUM" else "🟢 LOW")
            
            with st.expander(f"Mục #{idx} [{it.get('item_id')}] - {it.get('audit_question')[:80]}..."):
                st.write(f"**Câu hỏi Kiểm toán**: **{it.get('audit_question')}**")
                st.write(f"**Rủi ro Tiềm ẩn**: {it.get('risk_description')}")
                st.write(f"**Mức độ Rủi ro**: {r_badge}")
                st.write(f"**Gợi ý Hành động Kiểm toán**: {it.get('recommendation')}")
                st.info(f"📌 **Citation Trích dẫn Văn bản gốc**:\n\n`{it.get('source_citation')}`")

        st.divider()
        st.subheader("📥 Tải xuống Checklist UC4")
        col_c_dl1, col_c_dl2 = st.columns(2)

        if UC4_CSV_PATH.exists():
            with open(UC4_CSV_PATH, "rb") as f_chk_csv:
                col_c_dl1.download_button(
                    label="📄 Tải Checklist CSV (audit_checklist_results.csv)",
                    data=f_chk_csv,
                    file_name="audit_checklist_results.csv",
                    mime="text/csv",
                    use_container_width=True
                )

        json_bytes = json.dumps(chk_items, ensure_ascii=False, indent=2).encode("utf-8")
        col_c_dl2.download_button(
            label="📦 Tải Checklist JSON (audit_checklist_results.json)",
            data=json_bytes,
            file_name="audit_checklist_results.json",
            mime="application/json",
            use_container_width=True
        )
    else:
        st.info("Chọn Domain & Đơn vị rồi bấm nút **'Tạo bản nháp Checklist'** ở trên để bắt đầu.")

# ==============================================================================
# TAB 3: AUDIT LOG & SYSTEM TRAIL
# ==============================================================================
with tab3:
    st.subheader("📜 Nhật ký Kiểm toán & Log Hệ thống (Audit Trail)")
    st.caption("Hiển thị lịch sử tra cứu, quét xung đột quy định và sinh checklist. Đảm bảo bảo mật 100% không lộ secret.")

    audit_file = DEFAULT_AUDIT_LOG_PATH
    if not audit_file.exists():
        st.info("Chưa có nhật ký kiểm toán. Hãy thực hiện thao tác ở Tab 1 hoặc Tab 2 để phát sinh log.")
    else:
        with open(audit_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        logs = []
        for line in lines:
            try:
                data = json.loads(line)
                data.pop("password", None)
                data.pop("api_key", None)
                data.pop("secret", None)
                logs.append(data)
            except Exception:
                pass

        if logs:
            df_log = pd.DataFrame(logs)
            
            # Filters
            col_fl1, col_fl2 = st.columns(2)
            all_actions = ["Tất cả"] + df_log["action"].unique().tolist() if "action" in df_log.columns else ["Tất cả"]
            selected_act = col_fl1.selectbox("Lọc theo Hành động (Action):", all_actions)
            
            if selected_act != "Tất cả":
                df_log = df_log[df_log["action"] == selected_act]

            st.success(f"Hiển thị {len(df_log)} sự kiện kiểm toán:")
            st.dataframe(df_log, use_container_width=True)
        else:
            st.warning("Audit Log trống.")
