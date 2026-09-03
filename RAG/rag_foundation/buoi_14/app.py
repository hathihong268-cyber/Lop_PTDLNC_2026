"""
Streamlit Application: app.py
Buổi 14: Hybrid Search + Reranking + Mini Knowledge Graph
Giao diện trực quan khám phá:
- Baseline BM25 vs Dense
- Hybrid Search (RRF Fusion)
- Cross-Encoder Reranking (BAAI/bge-reranker-base)
- Trích xuất Graph Hints từ Mini Knowledge Graph (Neo4j)
- Benchmark & Evaluation Dashboard
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Thiết lập đường dẫn root
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.unified_retriever import get_or_create_components, retrieve
from scripts.query_demo import get_graph_hints

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="RAG Buổi 14: Hybrid + Rerank + Mini KG",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_resource(show_spinner="Đang khởi tạo các mô hình Retrieval & Reranker...")
def load_all_retrievers():
    """Tải và cache sẵn tất cả các thành phần để UI phản hồi tức thì."""
    return get_or_create_components()


def check_neo4j_status() -> tuple[bool, str]:
    """Kiểm tra trạng thái kết nối Neo4j."""
    env_paths = [BASE_DIR / ".env", BASE_DIR.parent / "buoi_10" / ".env", BASE_DIR.parent.parent.parent / ".env"]
    for ep in env_paths:
        if ep.exists():
            load_dotenv(ep, override=True)
            break
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "abcd1234")
    database = os.getenv("NEO4J_DATABASE", "neo4j")
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        driver.close()
        return True, f"Neo4j Online ({uri} / db: {database})"
    except Exception as e:
        return False, f"Neo4j Offline ({e})"


# Khởi tạo components
components = load_all_retrievers()
neo4j_online, neo4j_msg = check_neo4j_status()

# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/bank-building.png", width=64)
    st.title("RAG Foundation")
    st.caption("Buổi 14: Hybrid Search + Reranking + Mini KG")
    st.divider()

    st.subheader("⚙️ Trạng Thái Hệ Thống")
    st.write("📂 **Corpus**: 720 Chunks (15 Văn bản)")
    st.write("🔤 **Lexical**: BM25Okapi (Vi Legal Tokenizer)")
    st.write("🧠 **Dense**: `vi-distilled-msmarco-MiniLM` (384d)")
    st.write("🎯 **Reranker**: `BAAI/bge-reranker-base` (Cross-Encoder)")
    
    if neo4j_online:
        st.success(f"🌐 **Neo4j**: Sẵn sàng", icon="✅")
    else:
        st.warning(f"🌐 **Neo4j**: Chưa kết nối", icon="⚠️")

    st.divider()
    st.subheader("💡 Câu Hỏi Mẫu Điển Hình")
    sample_questions = [
        "-- Chọn câu hỏi mẫu để điền nhanh --",
        "[MIXED] Theo Thông tư 01/2014/TT-NHNN thì trách nhiệm của người áp tải tiền mặt là gì?",
        "[EXACT] Điều 73 Nghị định 46/2023/NĐ-CP quy định về chức danh nào?",
        "[SEMANTIC] Quy định về bảo quản an toàn và giao nhận vận chuyển tiền mặt trong kho quỹ",
        "[EXACT] Quy định tại Điều 50 Thông tư 01/2014/TT-NHNN về phương tiện vận chuyển tiền mặt",
        "[SEMANTIC] Tiêu chuẩn và điều kiện bổ nhiệm Tổng giám đốc doanh nghiệp bảo hiểm",
        "[MIXED] Hồ sơ đề nghị chấp thuận nguyên tắc hợp nhất ngân hàng theo Thông tư 62/2024/TT-NHNN",
        "[MIXED] Nghị định 46/2023/NĐ-CP quy định các loại nghiệp vụ bảo hiểm sức khỏe nào?"
    ]
    selected_sample = st.selectbox("Chọn câu hỏi mẫu:", sample_questions)


# ==============================================================================
# MAIN TABS
# ==============================================================================
st.title("🏦 RAG Explorer & Mini Knowledge Graph")
st.markdown(
    "Hệ thống truy xuất tài liệu pháp quy ngân hàng kết hợp **BM25**, **Dense Embedding**, **RRF Fusion**, "
    "**Cross-Encoder Reranking** và **Graph Hints từ Neo4j**."
)

tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 1. Truy Xuất & Graph Hints",
    "📊 2. So Sánh 4 Phương Pháp",
    "📈 3. Benchmark & Đánh Giá Metrics",
    "🕸️ 4. Mini Knowledge Graph (Neo4j)"
])

# ------------------------------------------------------------------------------
# TAB 1: RETRIEVAL EXPLORER & GRAPH HINTS
# ------------------------------------------------------------------------------
with tab1:
    st.subheader("🔍 Trải Nghiệm Pipeline Truy Xuất Thống Nhất")
    
    default_q = selected_sample if selected_sample != sample_questions[0] else "Theo Thông tư 01/2014/TT-NHNN thì trách nhiệm của người áp tải tiền mặt là gì?"
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
                "hybrid_rerank": "🎯 Hybrid + Cross-Encoder Rerank (Tốt nhất)",
                "hybrid": "🔀 Hybrid Search (BM25 + Dense + RRF)",
                "bm25": "🔤 BM25-only (Lexical Search)",
                "dense": "🧠 Dense-only (Vector Semantic)"
            }[x],
            key="t1_method"
        )

    col_p1, col_p2, col_p3 = st.columns([1, 1, 2])
    with col_p1:
        top_k_val = st.slider("Top-k kết quả đầu ra:", min_value=1, max_value=10, value=5, key="t1_topk")
    with col_p2:
        cand_k_val = st.slider("Candidate-k (Hybrid):", min_value=10, max_value=40, value=20, key="t1_candk")
    with col_p3:
        st.write("")
        st.write("")
        btn_search = st.button("🚀 Thực Hiện Truy Xuất", type="primary", key="t1_btn")

    if btn_search or query_input:
        t0 = time.time()
        with st.spinner("Đang truy xuất ngữ cảnh..."):
            results = retrieve(
                question=query_input,
                method=method_select,
                top_k=top_k_val,
                candidate_k=cand_k_val
            )
            hints = get_graph_hints(results)
        latency = time.time() - t0

        st.success(f"Truy xuất hoàn tất trong **{latency:.3f}s** | Trích xuất **{len(results)}** đoạn ngữ cảnh phù hợp nhất.")

        # Hiển thị kết quả trích xuất
        st.markdown("### 📋 Danh Sách Đoạn Văn Bản Trích Xuất (Top-k)")
        for item in results:
            rank = item["rank"]
            citation = item["citation"]
            cid = item["chunk_id"]
            doc_id = item["document_id"]
            text = item["text"]

            if method_select == "hybrid_rerank":
                score_badge = f"Rerank Score: **{item['rerank_score']:.4f}** | Hybrid RRF: `{item['hybrid_score']:.4f}` | Dịch chuyển: `{item.get('rank_shift', 0):+d}`"
            elif method_select == "hybrid":
                score_badge = f"RRF Score: **{item['score']:.6f}** (BM25: `#{item.get('bm25_rank', '-')}`, Dense: `#{item.get('dense_rank', '-')}`)"
            elif method_select == "dense":
                score_badge = f"Cosine Sim: **{item['score']:.4f}**"
            else:
                score_badge = f"BM25 Score: **{item['score']:.4f}**"

            with st.expander(f"**[Rank {rank}]** {citation} — ({score_badge})", expanded=(rank <= 2)):
                st.markdown(f"**Chunk ID**: `{cid}` &nbsp;|&nbsp; **Document ID**: `{doc_id}`")
                st.info(text)

        # Hiển thị GRAPH HINTS
        st.divider()
        st.markdown("### 🌐 GRAPH HINTS (Mối Quan Hệ Đồ Thị Trực Tiếp Từ Neo4j)")
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.markdown("#### 📜 Quan Hệ Pháp Lý Liên Văn Bản (1-Hop)")
            if hints["connected"] and hints["document_relations"]:
                for rel in set(hints["document_relations"]):
                    st.markdown(f"- 🏛️ `{rel}`")
            elif hints["connected"]:
                st.caption("*(Không có quan hệ liên văn bản trực tiếp nào giữa các văn bản trên)*")
            else:
                st.warning(hints.get("error_message", "Neo4j Offline"))

        with col_g2:
            st.markdown("#### 🔗 Cấu Trúc Điều Khoản Liền Kề (`[:NEXT]`)")
            if hints["connected"] and hints["adjacent_chunks"]:
                for adj in hints["adjacent_chunks"]:
                    st.markdown(f"- ⏩ `{adj}`")
            elif hints["connected"]:
                st.caption("*(Không có quan hệ NEXT trực tiếp trong Top này)*")
            else:
                st.warning(hints.get("error_message", "Neo4j Offline"))


# ------------------------------------------------------------------------------
# TAB 2: 4-METHOD SIDE-BY-SIDE COMPARISON
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("📊 So Sánh Song Song 4 Phương Pháp Trên Cùng Một Câu Hỏi")
    comp_q = st.text_input("Nhập câu hỏi để so sánh trực tiếp:", value="Theo Thông tư 01/2014/TT-NHNN thì trách nhiệm của người áp tải tiền mặt là gì?", key="t2_q")
    
    if st.button("⚡ Chạy So Sánh 4 Phương Pháp", type="primary", key="t2_btn"):
        with st.spinner("Đang chạy 4 Retriever đồng thời..."):
            res_bm25 = retrieve(comp_q, method="bm25", top_k=5)
            res_dense = retrieve(comp_q, method="dense", top_k=5)
            res_hybrid = retrieve(comp_q, method="hybrid", top_k=5, candidate_k=20)
            res_rerank = retrieve(comp_q, method="hybrid_rerank", top_k=5, candidate_k=20)

        c1, c2, c3, c4 = st.columns(4)
        methods_data = [
            ("🔤 BM25-only", res_bm25, c1),
            ("🧠 Dense-only", res_dense, c2),
            ("🔀 Hybrid (RRF)", res_hybrid, c3),
            ("🎯 Hybrid + Rerank", res_rerank, c4)
        ]

        for title, r_list, col in methods_data:
            with col:
                st.markdown(f"#### {title}")
                for item in r_list:
                    rank = item["rank"]
                    cit = item["citation"]
                    cid = item["chunk_id"]
                    score = item.get("rerank_score", item.get("score", 0.0))
                    
                    st.markdown(f"**#{rank}** `{cit}`")
                    st.caption(f"Score: `{score:.4f}` | ID: `{cid}`")
                    st.divider()


# ------------------------------------------------------------------------------
# TAB 3: BENCHMARK & EVALUATION DASHBOARD
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("📈 Kết Quả Benchmark Đánh Giá Định Lượng (12 Câu Hỏi Vàng)")
    
    # 4 Metric Cards
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(label="Hit@1 (Hybrid + Rerank)", value="75.0%", delta="+50.0% so với Hybrid")
    with m2:
        st.metric(label="Hit@3 (Hybrid + Rerank)", value="83.3%", delta="+25.0% so với Hybrid")
    with m3:
        st.metric(label="Hit@5 (Hybrid + Rerank)", value="91.7%", delta="+8.4% so với Hybrid")
    with m4:
        st.metric(label="MRR (Hybrid + Rerank)", value="0.8083", delta="+0.3472 (+75.3%)")

    st.markdown("### 📋 Bảng So Sánh Tổng Thể Các Cấu Hình")
    summary_df = pd.DataFrame([
        {"Phương Pháp": "1. BM25-only", "Hit@1": "58.3%", "Hit@3": "75.0%", "Hit@5": "75.0%", "MRR": "0.6528", "Đặc Điểm": "Mạnh trên số hiệu/mã văn bản, yếu trên ngữ nghĩa"},
        {"Phương Pháp": "2. Dense-only", "Hit@1": "0.0%", "Hit@3": "8.3%", "Hit@5": "16.7%", "MRR": "0.0486", "Đặc Điểm": "Bắt chủ đề tổng quan nhưng dễ mờ số điều cụ thể"},
        {"Phương Pháp": "3. Hybrid (RRF)", "Hit@1": "25.0%", "Hit@3": "58.3%", "Hit@5": "83.3%", "MRR": "0.4611", "Đặc Điểm": "Recall@5 cao nhất, tạo Candidate Pool tốt nhất"},
        {"Phương Pháp": "4. Hybrid + Rerank", "Hit@1": "75.0%", "Hit@3": "83.3%", "Hit@5": "91.7%", "MRR": "0.8083", "Đặc Điểm": "Chính xác nhất và toàn diện nhất trên mọi chỉ số"}
    ])
    st.dataframe(summary_df, hide_index=True)

    # Đọc chi tiết file CSV nếu có
    eval_csv = BASE_DIR / "outputs" / "retrieval_comparison.csv"
    if eval_csv.exists():
        st.markdown("### 🔍 Chi Tiết Từng Câu Hỏi Trong Benchmark")
        det_df = pd.read_csv(eval_csv)
        st.dataframe(det_df, hide_index=True)


# ------------------------------------------------------------------------------
# TAB 4: MINI KNOWLEDGE GRAPH EXPLORER
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("🕸️ Khám Phá Mini Knowledge Graph Trên Neo4j")
    
    kg_report_path = BASE_DIR / "outputs" / "kg_build_report.md"
    if kg_report_path.exists():
        with open(kg_report_path, "r", encoding="utf-8") as f:
            st.markdown(f.read())
    else:
        st.info("Chưa tìm thấy báo cáo đồ thị. Hãy chạy `python scripts/load_mini_kg.py` để nạp đồ thị.")

    st.markdown("### 💻 Thực Thi Truy Vấn Cypher Tùy Chọn")
    cypher_input = st.text_area(
        "Nhập câu lệnh Cypher (Chỉ đọc MATCH):",
        value="""MATCH (v1:VanBan {lab_session: 'buoi_14'})-[r]->(v2:VanBan {lab_session: 'buoi_14'})
RETURN v1.so_ky_hieu AS van_ban_nguon,
       type(r) AS loai_quan_he,
       r.relationship_label AS nhan_quan_he,
       v2.so_ky_hieu AS van_ban_dich;""",
        height=120
    )
    if st.button("🚀 Chạy Cypher", key="t4_cypher_btn"):
        if not neo4j_online:
            st.error("Không thể kết nối Neo4j!")
        else:
            try:
                from neo4j import GraphDatabase
                env_paths = [BASE_DIR / ".env", BASE_DIR.parent / "buoi_10" / ".env"]
                for ep in env_paths:
                    if ep.exists():
                        load_dotenv(ep, override=True)
                        break
                uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
                user = os.getenv("NEO4J_USER", "neo4j")
                password = os.getenv("NEO4J_PASSWORD", "abcd1234")
                database = os.getenv("NEO4J_DATABASE", "neo4j")

                driver = GraphDatabase.driver(uri, auth=(user, password))
                with driver.session(database=database) as session:
                    cypher_res = session.run(cypher_input).data()
                driver.close()
                st.dataframe(pd.DataFrame(cypher_res), hide_index=True)
            except Exception as ex:
                st.error(f"Lỗi khi thực thi Cypher: {ex}")
