"""
Ứng dụng Giao diện Web Streamlit: Hệ thống Multi-hop Graph RAG và Hỏi Đáp Pháp Luật
Bài thực hành 2 - Buổi 11: Multi-hop Graph RAG và Ứng dụng Hỏi Đáp (QA)

Tính năng:
1. Hỏi đáp Pháp luật thông minh với Vector Search + Đồ thị Đa bước (Multi-hop) + Gemini 2.5 Flash.
2. Trực quan hóa Đường dẫn liên kết Đồ thị (Graph Traversal Paths).
3. So sánh trực quan hiệu quả giữa 0-Hop (Chỉ Vector), 1-Hop và 2-Hops.
4. Bộ 5 câu hỏi kiểm thử chuẩn của đề bài kèm tính năng xuất báo cáo so sánh `qa_comparison.md`.
5. Bảng điều khiển khám phá dữ liệu 15 Văn bản và 8 Quan hệ trong Neo4j `kb-hops`.
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from dotenv import load_dotenv

import streamlit as st

# Cấu hình UTF-8 trên Windows console
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Đường dẫn gốc
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# Import module Bước 1, Bước 2, Bước 3
from buoi_11_db import get_neo4j_driver, get_db_config, verify_connection
from buoi_11_retrieval import search_graph_rag_context, get_embedding_model, DEFAULT_RELATIONSHIPS
from buoi_11_qa import generate_graph_rag_answer, DEFAULT_GENERATION_MODEL, SYSTEM_INSTRUCTION

# Cấu hình giao diện Streamlit
st.set_page_config(
    page_title="Multi-hop Graph RAG | Buổi 11",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 5 Câu hỏi kiểm thử chuẩn theo đề bài Buổi 11 Bước 4
BENCHMARK_QUESTIONS = [
    {
        "id": 1,
        "title": "Câu hỏi 1 (Quan hệ Thay thế)",
        "question": "Nghị định 46/2023/NĐ-CP thay thế cho nghị định nào, và nghị định bị thay thế đó có nội dung gì nổi bật về kinh doanh bảo hiểm?",
        "expected_rel": "THAY_THE",
        "description": "Truy vấn quan hệ thay thế giữa Nghị định 46/2023 và Nghị định 73/2016"
    },
    {
        "id": 2,
        "title": "Câu hỏi 2 (Quan hệ Hợp nhất)",
        "question": "Văn bản hợp nhất số 52/VBHN-NHNN được hợp nhất từ văn bản nào, và quy định về hồ sơ, thủ tục cấp giấy phép lần đầu của ngân hàng thương mại gồm những tài liệu gì?",
        "expected_rel": "HOP_NHAT",
        "description": "Truy vấn quan hệ hợp nhất của Văn bản 52/VBHN-NHNN"
    },
    {
        "id": 3,
        "title": "Câu hỏi 3 (Quan hệ Sửa đổi, bổ sung)",
        "question": "Thông tư số 01/2025/TT-NHNN quy định về cấp giấy phép quỹ tín dụng nhân dân được sửa đổi, bổ sung bởi văn bản nào, và những nội dung sửa đổi bổ sung chính là gì?",
        "expected_rel": "SUA_DOI_BO_SUNG",
        "description": "Truy vấn quan hệ sửa đổi bổ sung của Thông tư 01/2025"
    },
    {
        "id": 4,
        "title": "Câu hỏi 4 (Quan hệ Căn cứ)",
        "question": "Thông tư số 41/2016/TT-NHNN về tỷ lệ an toàn vốn của ngân hàng căn cứ vào luật nào, và luật đó quy định chức năng nhiệm vụ của cơ quan nào?",
        "expected_rel": "CAN_CU",
        "description": "Truy vấn quan hệ căn cứ pháp lý của Thông tư 41/2016"
    },
    {
        "id": 5,
        "title": "Câu hỏi 5 (Văn bản bổ sung & Sửa đổi)",
        "question": "Hoạt động giao nhận, vận chuyển tiền mặt và tài sản quý của Ngân hàng Nhà nước được điều chỉnh bởi Thông tư nào, và Thông tư đó có được sửa đổi bổ sung bởi văn bản nào không?",
        "expected_rel": "SUA_DOI_BO_SUNG / VAN_BAN_BO_SUNG",
        "description": "Truy vấn điều chỉnh và sửa đổi bổ sung văn bản tiền tệ"
    }
]


# ==============================================================================
# HÀM CACHE VÀ TRỢ GIÚP DỮ LIỆU
# ==============================================================================

@st.cache_resource(show_spinner=False)
def load_cached_embedding_model():
    """Tải mô hình nhúng 1 lần vào bộ nhớ cache."""
    return get_embedding_model()


@st.cache_data(ttl=60, show_spinner=False)
def get_database_statistics() -> Dict[str, Any]:
    """Lấy thống kê chi tiết từ Neo4j kb-hops."""
    cfg = get_db_config()
    driver = get_neo4j_driver()
    stats = {
        "connected": False,
        "doc_count": 0,
        "chunk_count": 0,
        "rel_count": 0,
        "doc_rel_count": 0,
        "doc_rels": [],
        "docs": [],
        "error": None
    }

    try:
        driver.verify_connectivity()
        with driver.session(database=cfg["database"]) as session:
            doc_cnt_record = session.run("MATCH (d:Document) RETURN count(d) AS cnt").single()
            chunk_cnt_record = session.run("MATCH (c:Chunk) RETURN count(c) AS cnt").single()
            rel_cnt_record = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt").single()
            doc_rel_cnt_record = session.run("MATCH (d1:Document)-[r]->(d2:Document) RETURN count(r) AS cnt").single()

            stats["doc_count"] = doc_cnt_record["cnt"] if doc_cnt_record else 0
            stats["chunk_count"] = chunk_cnt_record["cnt"] if chunk_cnt_record else 0
            stats["rel_count"] = rel_cnt_record["cnt"] if rel_cnt_record else 0
            stats["doc_rel_count"] = doc_rel_cnt_record["cnt"] if doc_rel_cnt_record else 0

            # Chi tiết quan hệ
            stats["doc_rels"] = session.run("""
            MATCH (d1:Document)-[r]->(d2:Document)
            RETURN d1.so_ky_hieu AS from_so, d1.title AS from_title, type(r) AS rel_type, r.relationship AS rel_desc, d2.so_ky_hieu AS to_so, d2.title AS to_title
            ORDER BY rel_type, from_so
            """).data()

            # Danh sách Document
            stats["docs"] = session.run("""
            MATCH (d:Document)
            RETURN d.id AS id, d.so_ky_hieu AS so_ky_hieu, d.title AS title, d.co_quan_ban_hanh AS co_quan, d.ngay_ban_hanh AS ngay_ban_hanh, d.tinh_trang_hieu_luc AS tinh_trang
            ORDER BY d.so_ky_hieu
            """).data()

        stats["connected"] = True
    except Exception as e:
        stats["error"] = str(e)
    finally:
        driver.close()

    return stats


# Khởi tạo mô hình nhúng ngầm
try:
    load_cached_embedding_model()
except Exception:
    pass


# ==============================================================================
# GIAO DIỆN CHÍNH (STREAMLIT UI)
# ==============================================================================

# Header chính
st.title("⚖️ Hệ thống Multi-hop Graph RAG - Hỏi Đáp Pháp Luật")
st.caption("Bài thực hành 2 - Buổi 11 | Kết hợp Tìm kiếm Vector (MSMARCO), Đồ thị Tri thức Đa bước Neo4j và Gemini 2.5 Flash LLM")

# Sidebar - Cấu hình hệ thống
with st.sidebar:
    st.header("⚙️ Cấu hình Hệ thống")

    # Kiểm tra trạng thái DB
    db_stats = get_database_statistics()
    if db_stats["connected"]:
        st.success(f"🟢 Neo4j: `{db_stats['doc_count']}` Văn bản | `{db_stats['chunk_count']:,}` Chunks", icon=":material/check_circle:")
    else:
        st.error(f"🔴 Neo4j Chưa kết nối: {db_stats['error']}", icon=":material/error:")

    st.divider()

    # Tham số Multi-hop Graph RAG
    st.subheader("🔍 Tham số Truy xuất")
    top_k = st.slider("Số lượng Chunk trực tiếp (Top-K):", min_value=1, max_value=8, value=3, step=1, help="Số lượng phân đoạn văn bản tìm kiếm trực tiếp bằng Vector (Hop 0)")
    num_hops = st.slider("Số bước nhảy Đồ thị (Num Hops):", min_value=0, max_value=3, value=1, step=1, help="0: Chỉ Vector truyền thống; 1: 1 bước nhảy; 2: 2 bước nhảy")
    chunks_per_hop_doc = st.slider("Số Chunk mỗi văn bản liên quan:", min_value=1, max_value=4, value=2, step=1, help="Số phân đoạn trích xuất từ mỗi tài liệu tìm thấy qua liên kết đa bước")

    selected_rels = st.multiselect(
        "Mối quan hệ cho phép duyệt:",
        options=DEFAULT_RELATIONSHIPS,
        default=DEFAULT_RELATIONSHIPS,
        help="Chọn các liên kết pháp luật cần duyệt trong đồ thị"
    )

    st.divider()

    # Tham số Gemini LLM
    st.subheader("🤖 Tham số Mô hình LLM")
    gen_model = st.selectbox(
        "Mô hình Gemini:",
        options=["gemini-2.5-flash", "gemini-1.5-flash", "gemini-flash-latest"],
        index=0
    )
    temperature = st.slider("Độ sáng tạo (Temperature):", min_value=0.0, max_value=0.7, value=0.1, step=0.05, help="Giá trị thấp (0.0 - 0.2) giúp câu trả lời chuẩn xác và trung thực với luật")

    st.divider()
    st.markdown("👨‍💻 **Thực hành Buổi 11** | Graph RAG Foundation")


# ==============================================================================
# CÁC TAB CHỨC NĂNG
# ==============================================================================

tab_qa, tab_compare, tab_benchmark, tab_graph = st.tabs([
    "💬 Hỏi đáp Tương tác (QA)",
    "🔬 So sánh Đa bước (0-Hop vs 1-Hop)",
    "🧪 5 Câu hỏi Kiểm thử Đề bài",
    "📊 Khám phá Đồ thị Tri thức"
])


# ------------------------------------------------------------------------------
# TAB 1: HỎI ĐÁP TƯƠNG TÁC (INTERACTIVE QA)
# ------------------------------------------------------------------------------
with tab_qa:
    st.markdown("### 💬 Hỏi Đáp Pháp Luật với Graph RAG Đa bước")
    st.write("Nhập câu hỏi tra cứu luật. Hệ thống sẽ tự động thực hiện Vector Search, duyệt Đồ thị $N$ bước nhảy để tìm văn bản liên quan và sinh câu trả lời bằng Gemini.")

    # Gợi ý nhanh câu hỏi mẫu
    st.markdown("**Gợi ý câu hỏi mẫu nhanh:**")
    quick_cols = st.columns(3)
    preset_q = ""
    with quick_cols[0]:
        if st.button("📌 Nghị định 46/2023 thay thế văn bản nào?", key="btn_q1"):
            preset_q = BENCHMARK_QUESTIONS[0]["question"]
    with quick_cols[1]:
        if st.button("📌 Văn bản 52/VBHN hợp nhất từ đâu?", key="btn_q2"):
            preset_q = BENCHMARK_QUESTIONS[1]["question"]
    with quick_cols[2]:
        if st.button("📌 Thông tư 41/2016 căn cứ vào luật nào?", key="btn_q4"):
            preset_q = BENCHMARK_QUESTIONS[3]["question"]

    user_query = st.text_area(
        "Nhập câu hỏi pháp luật:",
        value=preset_q if preset_q else "",
        placeholder="Ví dụ: Nghị định 46/2023/NĐ-CP thay thế cho nghị định nào, và nghị định bị thay thế đó có nội dung gì nổi bật?",
        height=100
    )

    col_btn, _ = st.columns([1, 4])
    with col_btn:
        btn_submit = st.button("🚀 Gửi câu hỏi", type="primary")

    if btn_submit and user_query.strip():
        with st.spinner(f"🔍 Đang truy xuất Đồ thị ({num_hops} hops) và gọi {gen_model}..."):
            t_start = time.time()
            res = generate_graph_rag_answer(
                query=user_query.strip(),
                top_k=top_k,
                num_hops=num_hops,
                rel_types=selected_rels,
                chunks_per_hop_doc=chunks_per_hop_doc,
                model_name=gen_model,
                temperature=temperature
            )
            total_elapsed = time.time() - t_start

        # Hiển thị Metrics thời gian
        m = res["metrics"]
        met_cols = st.columns(4)
        met_cols[0].metric("⏱️ Tổng thời gian", f"{total_elapsed:.2f}s")
        met_cols[1].metric("📄 Chunk trực tiếp (Hop 0)", f"{m['num_direct_chunks']}")
        met_cols[2].metric("🔗 Liên kết đồ thị", f"{m['num_traversal_paths']}")
        met_cols[3].metric("📑 Chunk đa bước (Hop 1..N)", f"{m['num_hop_chunks']}")

        st.divider()

        # Hiển thị Câu trả lời từ LLM
        with st.container(border=True):
            st.markdown("### 💡 Câu trả lời từ Hệ thống Graph RAG:")
            st.markdown(res["answer"])

        # Hiển thị Đường dẫn liên kết Đồ thị (nếu có)
        if res["traversal_paths"]:
            with st.container(border=True):
                st.markdown("### 🔗 Đường dẫn Mối quan hệ Đồ thị Khám phá được:")
                for idx, path in enumerate(res["traversal_paths"], 1):
                    rels_info = " ➔ ".join([f"**[:{r['type']}]** ({r.get('relationship','')})" for r in path["relationships"]])
                    st.info(f"**Liên kết {idx} (Cách {path['hop_distance']} hop):** `{path['seed_so_ky_hieu']}` ➔ {rels_info} ➔ `{path['target_so_ky_hieu']}` (*{path['target_title']}*)")

        # Hiển thị Chi tiết Ngữ cảnh truy xuất
        with st.expander("📚 Xem chi tiết tất cả Phân đoạn Ngữ cảnh đã nạp vào Prompt"):
            st.markdown("#### 1. Phân đoạn khớp trực tiếp (Vector Search - Hop 0):")
            for i, c in enumerate(res["retrieval_data"].get("initial_chunks", []), 1):
                st.markdown(f"**[{i}] Score: `{c['score']:.4f}` | Văn bản: `{c['doc_so_ky_hieu']}` - {c['doc_title']}**")
                st.caption(f"Tiêu đề mục: {c['heading']}")
                st.text(c["text"])
                st.write("---")

            if res["retrieval_data"].get("hop_chunks"):
                st.markdown("#### 2. Phân đoạn thu thập từ Mở rộng Đa bước (Multi-hop Chunks):")
                for i, hc in enumerate(res["retrieval_data"]["hop_chunks"], 1):
                    st.markdown(f"**[{i}] Hop: `{hc['hop_level']}` | Văn bản đích: `{hc['doc_so_ky_hieu']}` - {hc['doc_title']}**")
                    st.caption(f"Tiêu đề mục: {hc['heading']}")
                    st.text(hc["text"])
                    st.write("---")


# ------------------------------------------------------------------------------
# TAB 2: SO SÁNH ĐA BƯỚC (0-HOP VS 1-HOP VS 2-HOPS)
# ------------------------------------------------------------------------------
with tab_compare:
    st.markdown("### 🔬 So sánh Đối chiếu: 0-Hop (Chỉ Vector) vs 1-Hop (Graph Multi-hop)")
    st.write("Thực hiện cùng một câu hỏi phức tạp trên 2 cấu hình để thấy rõ sự vượt trội của Graph RAG so với Vector RAG truyền thống.")

    compare_query = st.selectbox(
        "Chọn câu hỏi đối chiếu:",
        options=[q["question"] for q in BENCHMARK_QUESTIONS],
        index=0
    )

    if st.button("🧪 Bắt đầu So sánh Đối chiếu (0-Hop vs 1-Hop)", type="primary"):
        with st.spinner("Đang chạy mô phỏng 0-Hop và 1-Hop song song..."):
            driver = get_neo4j_driver()
            try:
                res_0 = generate_graph_rag_answer(query=compare_query, top_k=3, num_hops=0, driver=driver, model_name=gen_model)
                res_1 = generate_graph_rag_answer(query=compare_query, top_k=3, num_hops=1, driver=driver, model_name=gen_model)
            finally:
                driver.close()

        # Hiển thị 2 cột so sánh
        col_hop0, col_hop1 = st.columns(2)

        with col_hop0:
            with st.container(border=True):
                st.markdown("#### 🔴 Cấu hình: 0-HOP (Chỉ Vector Search)")
                st.caption("Tìm kiếm vector thông thường - Không mở rộng đồ thị")
                st.metric("Số văn bản tìm thấy", f"{len(res_0['sources'])}")
                st.metric("Số liên kết đồ thị", "0")
                st.divider()
                st.markdown("**Câu trả lời sinh ra:**")
                st.markdown(res_0["answer"])

        with col_hop1:
            with st.container(border=True):
                st.markdown("#### 🟢 Cấu hình: 1-HOP (Vector + Graph Traversal)")
                st.caption("Tìm kiếm Vector kết hợp duyệt đồ thị quan hệ pháp luật")
                st.metric("Số văn bản tìm thấy", f"{len(res_1['sources'])} (Gốc + Liên quan)")
                st.metric("Số liên kết đồ thị", f"{len(res_1['traversal_paths'])}")
                st.divider()
                st.markdown("**Câu trả lời sinh ra:**")
                st.markdown(res_1["answer"])

        st.success("✅ **Nhận xét kết quả**: Khi sử dụng 0-hop, LLM chỉ nhận được thông tin của văn bản gốc và thiếu ngữ cảnh của văn bản liên quan (bị thay thế/căn cứ/hợp nhất). Khi bật 1-hop, hệ thống tự động tìm thấy mối quan hệ trong đồ thị và trích xuất nội dung bổ sung giúp trả lời đầy đủ 100% yêu cầu!", icon=":material/insights:")


# ------------------------------------------------------------------------------
# TAB 3: 5 CÂU HỎI KIỂM THỬ ĐỀ BÀI (BENCHMARK)
# ------------------------------------------------------------------------------
with tab_benchmark:
    st.markdown("### 🧪 Kiểm thử 5 Câu hỏi Chuẩn theo Đề bài Buổi 11 (Bước 4)")
    st.write("Đánh giá toàn diện đường ống hỏi đáp trên 5 kịch bản tra cứu văn bản quy phạm pháp luật đa bước.")

    for item in BENCHMARK_QUESTIONS:
        with st.container(border=True):
            st.markdown(f"#### 📌 {item['title']}: `{item['expected_rel']}`")
            st.markdown(f"**Câu hỏi**: {item['question']}")
            st.caption(f"Mô tả: {item['description']}")

            if st.button(f"▶️ Chạy kiểm thử Câu {item['id']}", key=f"run_bench_{item['id']}"):
                with st.spinner(f"Đang xử lý Câu {item['id']}..."):
                    bench_res = generate_graph_rag_answer(
                        query=item["question"],
                        top_k=3,
                        num_hops=1,
                        model_name=gen_model
                    )

                st.markdown("**💡 Kết quả trả lời:**")
                st.markdown(bench_res["answer"])

                if bench_res["traversal_paths"]:
                    st.info(f"🔗 **Đường dẫn quan hệ:** {', '.join([p['seed_so_ky_hieu'] + ' ➔ ' + p['target_so_ky_hieu'] for p in bench_res['traversal_paths']])}")


# ------------------------------------------------------------------------------
# TAB 4: KHÁM PHÁ ĐỒ THỊ TRI THỨC (GRAPH EXPLORER)
# ------------------------------------------------------------------------------
with tab_graph:
    st.markdown("### 📊 Cơ sở Dữ liệu Đồ thị Neo4j `kb-hops`")
    st.write("Tổng quan về 15 Văn bản pháp luật và 8 Mối quan hệ liên kết trong cơ sở tri thức đồ thị.")

    db_stats = get_database_statistics()
    if db_stats["connected"]:
        st_m1, st_m2, st_m3, st_m4 = st.columns(4)
        st_m1.metric("Văn bản (Documents)", f"{db_stats['doc_count']}")
        st_m2.metric("Phân đoạn (Chunks)", f"{db_stats['chunk_count']:,}")
        st_m3.metric("Tổng quan hệ đồ thị", f"{db_stats['rel_count']:,}")
        st_m4.metric("Quan hệ Doc-to-Doc", f"{db_stats['doc_rel_count']}")

        st.divider()

        st.markdown("#### 🔗 Danh sách 8 Mối quan hệ Liên kết giữa các Văn bản:")
        if db_stats["doc_rels"]:
            df_rels = pd.DataFrame(db_stats["doc_rels"])
            df_rels.columns = ["Từ Văn bản", "Tên Văn bản gốc", "Loại quan hệ", "Mô tả quan hệ", "Tới Văn bản", "Tên Văn bản đích"]
            st.dataframe(df_rels, hide_index=True)

        st.divider()

        st.markdown("#### 📚 Danh sách 15 Văn bản Pháp luật trong Cơ sở Dữ liệu:")
        if db_stats["docs"]:
            df_docs = pd.DataFrame(db_stats["docs"])
            df_docs.columns = ["ID", "Số ký hiệu", "Trích yếu / Tiêu đề", "Cơ quan ban hành", "Ngày ban hành", "Tình trạng"]
            st.dataframe(df_docs, hide_index=True)
    else:
        st.error(f"Không thể tải dữ liệu đồ thị: {db_stats['error']}")
