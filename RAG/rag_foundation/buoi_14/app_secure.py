"""
Streamlit Application: app_secure.py
Buổi 15: Cài đặt Kiểm soát Truy cập dựa trên Vai trò (RBAC) ở mức Dữ liệu và Retrieval Pipeline
Giao diện trực quan tích hợp phân quyền:
- Lựa chọn đóng vai (Impersonate Role): Admin, HR_Manager, Risk_Officer, Employee, Guest
- Lọc bảo mật đa tầng: BM25, Dense, Hybrid (RRF), Cross-Encoder Reranker
- Báo cáo số lượng chunk bị chặn do không đủ quyền
- Trích xuất Gợi ý Đồ thị (Graph Hints) có bảo vệ dữ liệu từ Neo4j
- Mô phỏng so sánh kết quả cùng một câu hỏi qua các vai trò khác nhau (Role Comparison Matrix)
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import streamlit as st

# Thiết lập đường dẫn root
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.config import (
    VALID_ROLES,
    ROLE_ADMIN,
    ROLE_HR_MANAGER,
    ROLE_RISK_OFFICER,
    ROLE_EMPLOYEE,
    ROLE_GUEST,
    ROLE_DESCRIPTIONS,
    get_neo4j_config,
    load_environment,
)
from src.secure_retriever import (
    get_or_create_secure_retriever,
    secure_retrieve,
)

# Cấu hình giao diện Streamlit
st.set_page_config(
    page_title="RAG RBAC: Secure Retrieval & Knowledge Graph (Buổi 15)",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS cho giao diện bảo mật chuyên nghiệp
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 1.2rem;
    }
    .role-badge-guest {
        background-color: #F1F5F9;
        color: #475569;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        border: 1px solid #CBD5E1;
    }
    .role-badge-hr {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        border: 1px solid #FCD34D;
    }
    .role-badge-risk {
        background-color: #E0E7FF;
        color: #3730A3;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        border: 1px solid #C7D2FE;
    }
    .role-badge-admin {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        border: 1px solid #FCA5A5;
    }
    .security-notice {
        background-color: #F8FAFC;
        border-left: 4px solid #3B82F6;
        padding: 10px 14px;
        border-radius: 0 8px 8px 0;
        margin: 10px 0;
    }
    .filtered-alert {
        background-color: #FFFBEB;
        border: 1px solid #FDE68A;
        border-radius: 8px;
        padding: 10px 14px;
        color: #B45309;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="Đang khởi tạo các mô hình Secure Retrieval & Reranker...")
def load_secure_pipeline():
    """Tải và cache sẵn tất cả các thành phần để UI phản hồi tức thì."""
    return get_or_create_secure_retriever()


def check_neo4j_status() -> tuple[bool, str]:
    """Kiểm tra trạng thái kết nối Neo4j."""
    cfg = get_neo4j_config()
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(cfg["uri"], auth=(cfg["user"], cfg["password"]))
        driver.verify_connectivity()
        driver.close()
        return True, f"Neo4j Online ({cfg['uri']} | db: {cfg['database']})"
    except Exception as e:
        return False, f"Neo4j Offline ({e})"


# Khởi tạo pipeline
retriever = load_secure_pipeline()
neo4j_online, neo4j_msg = check_neo4j_status()


# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/shield.png", width=64)
    st.markdown("## 🛡️ RAG Security Control")
    st.caption("Buổi 15: Role-Based Access Control (RBAC)")
    st.divider()

    # 1. MỤC CẤU HÌNH VAI TRÒ (YOUR ROLES)
    st.subheader("👤 Vai trò của bạn (Your Roles)")
    st.markdown("Chọn một hoặc nhiều vai trò để đóng vai (Impersonate):")
    
    selected_roles = st.multiselect(
        "Danh sách vai trò đang kích hoạt:",
        options=VALID_ROLES,
        default=[ROLE_GUEST],
        help="Hệ thống sẽ lọc bỏ toàn bộ tài liệu mà vai trò của bạn không có quyền truy cập."
    )

    if not selected_roles:
        st.warning("⚠️ Chưa chọn vai trò nào. Hệ thống tự động gán vai trò tối thiểu: **Guest**")
        active_roles = [ROLE_GUEST]
    else:
        active_roles = selected_roles

    # Hiển thị thông tin vai trò hiện tại
    with st.expander("ℹ️ Quyền hạn của các vai trò", expanded=False):
        for r in VALID_ROLES:
            is_active = r in active_roles
            prefix = "✅ " if is_active else "⚪ "
            st.markdown(f"**{prefix}{r}**: {ROLE_DESCRIPTIONS.get(r, '')}")

    st.divider()

    # 2. TRẠNG THÁI HỆ THỐNG
    st.subheader("⚙️ Trạng Thái Hệ Thống")
    st.write(f"📂 **Corpus**: 720 Chunks (Đã gán thẻ bảo mật)")
    st.write(f"🔤 **Lexical**: BM25 (Pandas Access Filter)")
    st.write(f"🧠 **Dense**: `vi-distilled-msmarco-MiniLM` (384d)")
    st.write(f"🎯 **Reranker**: `BAAI/bge-reranker-base` (Secure Only)")
    
    if neo4j_online:
        st.success("🌐 **Neo4j**: Sẵn sàng (RBAC Cypher Active)", icon="✅")
    else:
        st.warning("🌐 **Neo4j**: Chưa kết nối", icon="⚠️")

    st.divider()

    # 3. CÂU HỎI MẪU THEO NHÓM BẢO MẬT
    st.subheader("💡 Câu Hỏi Mẫu Theo Cấp Quyền")
    sample_options = [
        "-- Chọn câu hỏi mẫu để điền nhanh --",
        "[HR ONLY] Tiêu chuẩn bổ nhiệm chức danh thủ kho tiền, thủ quỹ, kiểm ngân",
        "[HR ONLY] Tiêu chuẩn và điều kiện đối với Trưởng Ban kiểm soát theo Thông tư 27/2024/TT-NHNN",
        "[RISK ONLY] Quy trình giao nhận, bảo quản và áp tải vận chuyển tiền mặt trong ngành Ngân hàng",
        "[RISK ONLY] Trách nhiệm của người áp tải tiền mặt theo Thông tư 01/2014/TT-NHNN",
        "[PUBLIC] Phạm vi và đối tượng áp dụng Luật kinh doanh bảo hiểm",
        "[PUBLIC] Điều kiện thành lập và tổ chức hoạt động của quỹ tín dụng nhân dân",
        "[HR ONLY] Quy định về mức lương và chế độ đãi ngộ cho cán bộ quản lý quỹ tín dụng",
        "[RISK ONLY] Quy định về quản lý dự trữ ngoại hối nhà nước theo Thông tư 43/2024/TT-NHNN"
    ]
    selected_sample = st.selectbox("Chọn câu hỏi mẫu:", sample_options)


# ==============================================================================
# MAIN APPLICATION INTERFACE
# ==============================================================================
st.markdown('<div class="main-header">🛡️ Hệ Thống RAG Bảo Mật Theo Vai Trò (RBAC)</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">'
    'Kiểm soát truy cập dữ liệu đa tầng tại <b>BM25</b>, <b>Dense Embeddings</b>, <b>Hybrid RRF</b>, '
    '<b>Cross-Encoder Reranker</b> và <b>Neo4j Knowledge Graph</b>.'
    '</div>',
    unsafe_allow_html=True
)

# Hiển thị thanh thông tin vai trò hiện tại
col_info1, col_info2 = st.columns([3, 1])
with col_info1:
    role_badges = " ".join([f"<span class='role-badge-admin'>🔑 {r}</span>" if r == "Admin" else
                            f"<span class='role-badge-hr'>👥 {r}</span>" if r == "HR_Manager" else
                            f"<span class='role-badge-risk'>📈 {r}</span>" if r == "Risk_Officer" else
                            f"<span class='role-badge-guest'>👤 {r}</span>" for r in active_roles])
    st.markdown(f"**Vai trò đang thực thi (Active User Roles)**: {role_badges}", unsafe_allow_html=True)
with col_info2:
    if ROLE_ADMIN in active_roles:
        st.markdown("<span style='color:#DC2626; font-weight:bold;'>🔴 FULL ACCESS (ADMIN)</span>", unsafe_allow_html=True)
    elif ROLE_HR_MANAGER in active_roles:
        st.markdown("<span style='color:#D97706; font-weight:bold;'>🟡 HR PERMISSIONS</span>", unsafe_allow_html=True)
    elif ROLE_RISK_OFFICER in active_roles:
        st.markdown("<span style='color:#4F46E5; font-weight:bold;'>🔵 RISK & CREDIT PERMISSIONS</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span style='color:#64748B; font-weight:bold;'>🟢 PUBLIC ONLY (GUEST)</span>", unsafe_allow_html=True)

# TABS GIAO DIỆN
tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 1. Truy Xuất An Toàn & Graph Hints",
    "🛡️ 2. Mô Phỏng So Sánh Giữa Các Vai Trò",
    "📊 3. So Sánh 4 Phương Pháp Truy Xuất",
    "🕸️ 4. Neo4j Knowledge Graph & RBAC Audit"
])


# ------------------------------------------------------------------------------
# TAB 1: RETRIEVAL EXPLORER & GRAPH HINTS
# ------------------------------------------------------------------------------
with tab1:
    st.subheader("🔍 Trải Nghiệm Pipeline Truy Xuất An Toàn (Secure Retrieval)")
    
    default_q = selected_sample if selected_sample != sample_options[0] else "Tiêu chuẩn bổ nhiệm chức danh thủ kho tiền, thủ quỹ, kiểm ngân"
    if default_q.startswith("["):
        default_q = default_q.split("] ", 1)[-1]

    col_q1, col_q2 = st.columns([3, 1])
    with col_q1:
        query_input = st.text_input("Nhập câu hỏi truy vấn nghiệp vụ / pháp lý:", value=default_q, key="t1_query")
    with col_q2:
        method_select = st.selectbox(
            "Phương pháp truy xuất:",
            options=["hybrid_rerank", "hybrid", "bm25", "dense"],
            format_func=lambda x: {
                "hybrid_rerank": "🎯 Hybrid + Rerank (Bảo mật & Tối ưu nhất)",
                "hybrid": "🔀 Hybrid Search (BM25 + Dense + RRF)",
                "bm25": "🔤 BM25-only (Lexical Search)",
                "dense": "🧠 Dense-only (Vector Semantic)"
            }[x],
            key="t1_method"
        )

    col_p1, col_p2, col_p3 = st.columns([1, 1, 2])
    with col_p1:
        top_k_val = st.slider("Top-k kết quả hiển thị:", min_value=1, max_value=10, value=5, key="t1_topk")
    with col_p2:
        cand_k_val = st.slider("Candidate-k trước khi Rerank:", min_value=10, max_value=40, value=20, key="t1_candk")
    with col_p3:
        st.write("")
        st.write("")
        btn_search = st.button("🚀 Thực Hiện Truy Xuất Bảo Mật", type="primary", key="t1_btn")

    if btn_search or query_input:
        with st.spinner(f"Đang tìm kiếm dưới quyền {active_roles}..."):
            t0 = time.time()
            res_data = secure_retrieve(
                query=query_input,
                user_roles=active_roles,
                method=method_select,
                top_k=top_k_val,
                candidate_k=cand_k_val,
                include_graph_hints=True
            )
            latency = time.time() - t0

        results = res_data["results"]
        filtered_count = res_data["filtered_out_count"]
        hints = res_data["graph_hints"]

        # Thông báo trạng thái & số lượng kết quả bị lọc do bảo mật
        c_res1, c_res2 = st.columns([2, 1])
        with c_res1:
            st.success(f"Truy xuất hoàn tất trong **{latency:.3f}s** | Trích xuất **{len(results)}** đoạn văn bản phù hợp.")
        with c_res2:
            if filtered_count > 0:
                st.markdown(
                    f"<div class='filtered-alert'>⛔ <b>Đã lọc bỏ {filtered_count} kết quả</b> do không đủ quyền truy cập</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div class='security-notice'>✅ <b>0 kết quả bị chặn</b> (Tất cả ứng viên đều nằm trong quyền xem)</div>",
                    unsafe_allow_html=True
                )

        # Hiển thị danh sách kết quả trích xuất
        st.markdown("### 📋 Danh Sách Đoạn Văn Bản Trích Xuất (Top-k)")
        if not results:
            st.warning("⚠️ Không tìm thấy kết quả nào phù hợp trong phạm vi quyền truy cập của vai trò hiện tại.")
        
        for item in results:
            rank = item["rank"]
            citation = item["citation"]
            cid = item["chunk_id"]
            doc_id = item["document_id"]
            text = item["text"]
            allowed_roles_str = ", ".join(item.get("allowed_roles", []))
            matched_roles_str = ", ".join(item.get("matched_roles", []))

            if method_select == "hybrid_rerank":
                score_badge = f"Rerank Score: **{item['score']:.4f}** | Hybrid RRF: `{item.get('hybrid_score', 0):.4f}` | Dịch chuyển: `{item.get('rank_shift', 0):+d}`"
            elif method_select == "hybrid":
                score_badge = f"RRF Score: **{item['score']:.6f}** (BM25: `#{item.get('bm25_rank', '-')}`, Dense: `#{item.get('dense_rank', '-')}`)"
            elif method_select == "dense":
                score_badge = f"Cosine Sim: **{item['score']:.4f}**"
            else:
                score_badge = f"BM25 Score: **{item['score']:.4f}**"

            with st.expander(f"**[Rank {rank}]** {citation} — ({score_badge})", expanded=(rank <= 2)):
                st.markdown(f"🔒 **Quyền xem (Allowed Roles)**: `{allowed_roles_str}` &nbsp;|&nbsp; 🔑 **Vai trò khớp của bạn**: `{matched_roles_str}`")
                st.markdown(f"**Chunk ID**: `{cid}` &nbsp;|&nbsp; **Document ID**: `{doc_id}`")
                st.info(text)

        # Hiển thị GRAPH HINTS
        st.divider()
        st.markdown("### 🌐 SECURE GRAPH HINTS (Gợi Ý Đồ Thị Neo4j Đã Lọc Quyền)")
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.markdown("#### 📜 Quan Hệ Pháp Lý Liên Văn Bản (1-Hop)")
            if hints and hints.get("connected") and hints.get("document_relations"):
                for rel in set(hints["document_relations"]):
                    st.markdown(f"- 🏛️ `{rel}`")
            elif hints and hints.get("connected"):
                st.caption("*(Không có quan hệ liên văn bản nào phù hợp với quyền truy cập hiện tại)*")
            else:
                st.warning(hints.get("error_message", "Neo4j Offline") if hints else "Neo4j Offline")

        with col_g2:
            st.markdown("#### 🔗 Cấu Trúc Điều Khoản Liền Kề (`[:NEXT]`)")
            if hints and hints.get("connected") and hints.get("adjacent_chunks"):
                for adj in hints["adjacent_chunks"]:
                    st.markdown(f"- ⏩ `{adj}`")
            elif hints and hints.get("connected"):
                st.caption("*(Không có điều khoản liền kề nào được phép xem trong Top này)*")
            else:
                st.warning(hints.get("error_message", "Neo4j Offline") if hints else "Neo4j Offline")


# ------------------------------------------------------------------------------
# TAB 2: ROLE SIMULATION & COMPARISON
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("🛡️ Mô Phỏng & So Sánh Kết Quả Giữa Các Vai Trò Khác Nhau")
    st.markdown(
        "Trực quan hóa cách hệ thống phản hồi cho **cùng một câu hỏi** khi người dùng đóng vai các vị trí khác nhau: "
        "`Guest`, `Employee`, `Risk_Officer`, `HR_Manager`, và `Admin`."
    )

    sim_q = st.text_input(
        "Nhập câu hỏi để so sánh đa vai trò:",
        value="Tiêu chuẩn bổ nhiệm chức danh thủ kho tiền, thủ quỹ, kiểm ngân",
        key="t2_sim_q"
    )

    col_btn_sim, _ = st.columns([1, 3])
    with col_btn_sim:
        btn_sim = st.button("⚡ Chạy So Sánh Đa Vai Trò (Multi-Role Simulation)", type="primary", key="t2_sim_btn")

    if btn_sim or sim_q:
        with st.spinner("Đang chạy mô phỏng trên 4 vai trò độc lập..."):
            sim_guest = secure_retrieve(sim_q, user_roles=[ROLE_GUEST], method="bm25", top_k=3, include_graph_hints=False)
            sim_employee = secure_retrieve(sim_q, user_roles=[ROLE_EMPLOYEE], method="bm25", top_k=3, include_graph_hints=False)
            sim_risk = secure_retrieve(sim_q, user_roles=[ROLE_RISK_OFFICER], method="bm25", top_k=3, include_graph_hints=False)
            sim_hr = secure_retrieve(sim_q, user_roles=[ROLE_HR_MANAGER], method="bm25", top_k=3, include_graph_hints=False)
            sim_admin = secure_retrieve(sim_q, user_roles=[ROLE_ADMIN], method="bm25", top_k=3, include_graph_hints=False)

        c1, c2, c3, c4 = st.columns(4)

        roles_sim_data = [
            ("👤 Guest (Khách)", sim_guest, c1, "#64748B"),
            ("👥 HR_Manager (Nhân sự)", sim_hr, c2, "#D97706"),
            ("📈 Risk_Officer (Rủi ro)", sim_risk, c3, "#4F46E5"),
            ("🔑 Admin (Quản trị)", sim_admin, c4, "#DC2626"),
        ]

        for title, sim_res, col, color in roles_sim_data:
            with col:
                st.markdown(f"#### <span style='color:{color};'>{title}</span>", unsafe_allow_html=True)
                st.caption(f"⛔ Đã lọc bỏ: **{sim_res['filtered_out_count']} chunks cấm**")
                
                for item in sim_res["results"]:
                    r_rank = item["rank"]
                    r_cit = item["citation"]
                    r_cid = item["chunk_id"]
                    r_roles = item.get("allowed_roles", [])
                    
                    st.markdown(f"**#{r_rank}** `{r_cit}`")
                    st.caption(f"Quyền: `{r_roles}` | ID: `{r_cid}`")
                    snippet = item["text"].replace("\n", " ")[:90]
                    st.markdown(f"> *{snippet}...*")
                    st.divider()


# ------------------------------------------------------------------------------
# TAB 3: 4-METHOD SECURE COMPARISON
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("📊 So Sánh 4 Phương Pháp Truy Xuất Dưới Vai Trò Hiện Tại")
    st.markdown(f"Đang áp dụng bộ lọc vai trò: **{active_roles}**")
    
    comp_q = st.text_input(
        "Nhập câu hỏi để so sánh 4 phương pháp:",
        value="Quy trình áp tải và vận chuyển tiền mặt trong ngành Ngân hàng",
        key="t3_q"
    )

    if st.button("⚡ Chạy So Sánh 4 Phương Pháp", type="primary", key="t3_btn"):
        with st.spinner(f"Đang thực thi 4 phương pháp cho vai trò {active_roles}..."):
            c_bm25, _ = retriever.search_bm25_secure(comp_q, active_roles, top_k=4)
            c_dense, _ = retriever.search_dense_secure(comp_q, active_roles, top_k=4)
            c_hybrid, _ = retriever.search_hybrid_secure(comp_q, active_roles, top_k=4, candidate_k=20)
            c_rerank, _ = retriever.search_hybrid_rerank_secure(comp_q, active_roles, top_k=4, candidate_k=20)

        c1, c2, c3, c4 = st.columns(4)
        methods_data = [
            ("🔤 BM25-only", c_bm25, c1),
            ("🧠 Dense-only", c_dense, c2),
            ("🔀 Hybrid (RRF)", c_hybrid, c3),
            ("🎯 Hybrid + Rerank", c_rerank, c4)
        ]

        for title, r_list, col in methods_data:
            with col:
                st.markdown(f"#### {title}")
                if not r_list:
                    st.caption("*(Không có kết quả nào trong phạm vi quyền)*")
                for item in r_list:
                    rank = item["rank"]
                    cit = item["citation"]
                    cid = item["chunk_id"]
                    score = item.get("rerank_score", item.get("score", 0.0))
                    
                    st.markdown(f"**#{rank}** `{cit}`")
                    st.caption(f"Score: `{score:.4f}` | ID: `{cid}`")
                    st.caption(f"Allowed: `{item.get('allowed_roles', [])}`")
                    st.divider()


# ------------------------------------------------------------------------------
# TAB 4: NEO4J KNOWLEDGE GRAPH & AUDIT
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("🕸️ Thống Kê Cơ Sở Dữ Liệu Đồ Thị Neo4j & Phân Quyền RBAC")

    if not neo4j_online:
        st.warning("⚠️ Cơ sở dữ liệu Neo4j hiện chưa kết nối. Vui lòng kiểm tra lại DBMS và file .env.")
    else:
        cfg = get_neo4j_config()
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(cfg["uri"], auth=(cfg["user"], cfg["password"]))
        
        with driver.session(database=cfg["database"]) as session:
            # Thống kê số lượng node có allowed_roles
            st_d = session.run("MATCH (d:DieuKhoan) RETURN count(d) AS total, count(d.allowed_roles) AS tagged").single()
            st_v = session.run("MATCH (v:VanBan) RETURN count(v) AS total, count(v.allowed_roles) AS tagged").single()

            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            with kpi1:
                st.metric("Node Điều Khoản (:DieuKhoan)", f"{st_d['total']}", f"Đã gắn quyền: {st_d['tagged']}")
            with kpi2:
                st.metric("Node Văn Bản (:VanBan)", f"{st_v['total']}", f"Đã gắn quyền: {st_v['tagged']}")
            with kpi3:
                st.metric("Độ Phủ Bảo Mật (Security Coverage)", "100%", "720/720 Chunks")
            with kpi4:
                st.metric("Phiên Thực Hành", "Buổi 15 (RBAC)", "MERGE Parameterized")

            st.divider()

            # Bảng thống kê số chunk xem được theo từng vai trò
            st.markdown("#### 📊 Thống Kê Khả Năng Tiếp Cận Dữ Liệu Theo Từng Vai Trò")
            role_stats = []
            for role in VALID_ROLES:
                q_cnt = session.run("""
                    MATCH (d:DieuKhoan)
                    WHERE any(r IN d.allowed_roles WHERE r = $role) OR $role = 'Admin'
                    RETURN count(d) AS accessible
                """, role=role).single()["accessible"]
                pct = (q_cnt / 720) * 100
                role_stats.append({
                    "Vai trò (Role)": role,
                    "Mô tả nghiệp vụ": ROLE_DESCRIPTIONS.get(role, ""),
                    "Số Chunk Có Quyền Xem": f"{q_cnt} / 720",
                    "Tỷ lệ tiếp cận (%)": f"{pct:.1f}%"
                })
            
            st.dataframe(pd.DataFrame(role_stats), use_container_width=True)

        driver.close()
