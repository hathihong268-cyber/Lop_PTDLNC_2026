"""
Ứng dụng Giao diện Web Trực quan hóa Bài thực hành 1 - Buổi 10
Đồ thị Tri thức Pháp luật (Graph RAG Foundation) trên Neo4j & Dense Embeddings

Các chức năng chính:
1. Tổng quan Trạng thái Cơ sở Dữ liệu Đồ thị Neo4j (kb-hops).
2. Khám phá 15 Văn bản Pháp luật & 8 Quan hệ Cấp Tài liệu.
3. Trực quan hóa Cấu trúc Phân cấp Cha - Con (:PARENT_OF).
4. Khám phá Luồng Đọc Tuần tự Giữa các Phân đoạn (:NEXT).
5. Tìm kiếm Vector Nhúng Tiếng Việt (Dense Vector Search trên CPU).
6. Tích hợp Hướng dẫn Truy vấn Trực quan trên Neo4j Browser.
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

# Thêm thư mục hiện tại vào sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# Import các module Buổi 10
from buoi_10_db import get_neo4j_driver, get_db_config

# Cấu hình Trang Streamlit
st.set_page_config(
    page_title="Graph RAG Foundation | Buổi 10",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS cho giao diện hiện đại, chuyên nghiệp
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #4f46e5, #06b6d4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #64748b;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .badge-tag {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 6px;
    }
    .badge-doc { background-color: #3b82f6; color: white; }
    .badge-chunk { background-color: #10b981; color: white; }
    .badge-rel { background-color: #8b5cf6; color: white; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# HÀM TRỢ GIÚP TẢI DỮ LIỆU TỪ NEO4J
# ==============================================================================

@st.cache_resource(show_spinner=False)
def init_neo4j_driver():
    """Khởi tạo và cache driver kết nối Neo4j."""
    try:
        driver = get_neo4j_driver()
        driver.verify_connectivity()
        return driver
    except Exception as e:
        return None


@st.cache_resource(show_spinner="Đang nạp mô hình nhúng tiếng Việt thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5...")
def get_embedding_model_singleton():
    """Tải và cache mô hình nhúng tiếng Việt trên CPU."""
    try:
        from buoi_10_embedding import VietnameseEmbeddingModel
        return VietnameseEmbeddingModel(device="cpu")
    except Exception as e:
        return None


def fetch_database_overview(driver, db_name: str) -> Dict[str, Any]:
    """Lấy số lượng tổng thể các thực thể và quan hệ trong Neo4j."""
    stats = {}
    with driver.session(database=db_name) as session:
        # 1. Đếm Document
        stats["doc_count"] = session.run("MATCH (d:Document) RETURN count(d) AS cnt").single()["cnt"]
        # 2. Đếm Chunk
        stats["chunk_count"] = session.run("MATCH (c:Chunk) RETURN count(c) AS cnt").single()["cnt"]
        # 3. Đếm Quan hệ Doc-to-Doc
        stats["doc_rel_count"] = session.run("""
        MATCH (d1:Document)-[r]->(d2:Document)
        RETURN count(r) AS cnt
        """).single()["cnt"]
        # 4. Chi tiết các loại quan hệ
        rel_records = session.run("""
        MATCH ()-[r]->()
        RETURN type(r) AS rel_type, count(r) AS cnt
        ORDER BY cnt DESC
        """)
        stats["rel_types"] = {r["rel_type"]: r["cnt"] for r in rel_records}
        # 5. Phân bố cấp bậc Chunks
        level_records = session.run("""
        MATCH (c:Chunk)
        RETURN c.level AS lvl, count(c) AS cnt
        ORDER BY cnt DESC
        """)
        stats["level_stats"] = {r["lvl"]: r["cnt"] for r in level_records}
    return stats


def fetch_all_documents(driver, db_name: str) -> pd.DataFrame:
    """Lấy danh sách 15 Document kèm metadata."""
    query = """
    MATCH (d:Document)
    RETURN d.id AS id, d.so_ky_hieu AS so_ky_hieu, d.title AS title,
           d.loai_van_ban AS loai_van_ban, d.co_quan_ban_hanh AS co_quan_ban_hanh,
           d.ngay_ban_hanh AS ngay_ban_hanh, d.tinh_trang_hieu_luc AS tinh_trang_hieu_luc
    ORDER BY d.so_ky_hieu
    """
    with driver.session(database=db_name) as session:
        records = session.run(query)
        data = [r.data() for r in records]
    return pd.DataFrame(data)


def fetch_doc_relationships(driver, db_name: str) -> List[Dict[str, Any]]:
    """Lấy 8 quan hệ giữa các Document."""
    query = """
    MATCH (d1:Document)-[r]->(d2:Document)
    RETURN d1.id AS from_id, d1.so_ky_hieu AS from_so, d1.title AS from_title,
           type(r) AS rel_type, r.relationship AS rel_desc,
           d2.id AS to_id, d2.so_ky_hieu AS to_so, d2.title AS to_title
    ORDER BY rel_type, from_so
    """
    with driver.session(database=db_name) as session:
        records = session.run(query)
        return [r.data() for r in records]


def fetch_doc_hierarchy(driver, db_name: str, doc_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Lấy cấu trúc phân cấp Parent-Child của 1 Document."""
    query = """
    MATCH (p:Chunk {doc_id: $doc_id})-[:PARENT_OF]->(c:Chunk)
    RETURN p.id AS parent_id, p.heading AS parent_heading, p.level AS parent_level,
           c.id AS child_id, c.heading AS child_heading, c.level AS child_level,
           c.text AS child_text
    ORDER BY p.id, c.id
    LIMIT $limit
    """
    with driver.session(database=db_name) as session:
        records = session.run(query, doc_id=doc_id, limit=limit)
        return [r.data() for r in records]


def fetch_next_sequence(driver, db_name: str, doc_id: str, limit: int = 15) -> List[Dict[str, Any]]:
    """Lấy luồng đọc tuần tự NEXT của một văn bản."""
    query = """
    MATCH (c1:Chunk {doc_id: $doc_id})-[:NEXT]->(c2:Chunk)
    RETURN c1.id AS from_id, c1.heading AS from_heading, c1.level AS from_level,
           c2.id AS to_id, c2.heading AS to_heading, c2.level AS to_level
    ORDER BY c1.seq_order
    LIMIT $limit
    """
    with driver.session(database=db_name) as session:
        records = session.run(query, doc_id=doc_id, limit=limit)
        return [r.data() for r in records]


def vector_search(driver, db_name: str, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
    """Tìm kiếm vector tương đồng trên Neo4j Vector Index 'chunk_embeddings'."""
    query = """
    CALL db.index.vector.queryNodes('chunk_embeddings', $top_k, $query_vector)
    YIELD node AS chunk, score
    OPTIONAL MATCH (chunk)-[:PART_OF]->(doc:Document)
    RETURN chunk.id AS chunk_id, chunk.heading AS heading, chunk.level AS level,
           chunk.text AS text, score,
           doc.id AS doc_id, doc.so_ky_hieu AS so_ky_hieu, doc.title AS doc_title
    ORDER BY score DESC
    """
    with driver.session(database=db_name) as session:
        records = session.run(query, top_k=top_k, query_vector=query_vector)
        return [r.data() for r in records]


# ==============================================================================
# GIAO DIỆN CHÍNH STREAMLIT
# ==============================================================================

def main():
    cfg = get_db_config()
    db_name = cfg["database"]

    # Header
    st.markdown('<div class="main-header">⚖️ Đồ Thị Tri Thức & Vector Nhúng Pháp Luật</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sub-header">Bài thực hành 1 (Buổi 10): Phân tách dữ liệu phân cấp, Dense Embeddings (CPU) và Neo4j Graph Database <b>[{db_name}]</b></div>',
        unsafe_allow_html=True
    )

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Thông Tin Kết Nối")
        driver = init_neo4j_driver()
        if driver:
            st.success(f"🟢 **Neo4j Connected**\n\nURI: `{cfg['uri']}`\n\nDatabase: `{db_name}`")
        else:
            st.error(f"🔴 **Neo4j Offline**\n\nKhông thể kết nối tới `{cfg['uri']}`. Hãy đảm bảo DBMS đã Start trên Neo4j Desktop.")

        st.markdown("---")
        st.markdown("### 🤖 Cấu Hình Mô Hình")
        st.info("""
        - **Model**: `thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5`
        - **Embedding Dim**: `384`
        - **Device**: `CPU` (PyTorch)
        - **Similarity**: `Cosine`
        """)

        st.markdown("---")
        st.markdown("### 🔗 Liên Kết Nhanh")
        st.markdown("- 👉 [Mở Neo4j Browser (Cổng 7474)](http://localhost:7474)")
        if st.button("🔄 Làm mới dữ liệu"):
            st.rerun()

    if not driver:
        st.warning("⚠️ **Dịch vụ Neo4j chưa hoạt động.** Vui lòng bật Neo4j Desktop và bấm Start trên instance của bạn.")
        return

    # Lấy dữ liệu thống kê
    try:
        stats = fetch_database_overview(driver, db_name)
    except Exception as e:
        st.error(f"Lỗi truy vấn Neo4j: {e}")
        return

    # Hàng chỉ số Metrics
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(label="Văn bản (:Document)", value=f"{stats['doc_count']} / 15", delta="Đạt chuẩn đề bài")
    with c2:
        st.metric(label="Quan hệ Cấp Văn Bản", value=f"{stats['doc_rel_count']} / 8", delta="Đạt chuẩn đề bài")
    with c3:
        st.metric(label="Phân đoạn (:Chunk)", value=f"{stats['chunk_count']:,}", delta="Hierarchical Chunks")
    with c4:
        st.metric(label="Vector Index", value="chunk_embeddings", delta="384 dims (Cosine)")

    st.markdown("---")

    # Các Tabs chức năng
    tab_stats, tab_docs, tab_hierarchy, tab_next, tab_search, tab_cypher = st.tabs([
        "📊 Thống Kê & Quan Hệ",
        "📑 15 Văn Bản Pháp Luật",
        "🌳 Cấu Trúc Phân Cấp (PARENT_OF)",
        "🔗 Luồng Đọc Tuần Tự (NEXT)",
        "🔍 Tìm Kiếm Vector (Embeddings)",
        "💻 Neo4j Browser & Cypher"
    ])

    # --------------------------------------------------------------------------
    # TAB 1: THỐNG KÊ & QUAN HỆ
    # --------------------------------------------------------------------------
    with tab_stats:
        st.subheader("📊 Tổng Quan Thực Thể & Các Loại Quan Hệ Trong Đồ Thị")
        col_rel, col_lvl = st.columns(2)

        with col_rel:
            st.markdown("##### 📌 Phân Bố Các Loại Mối Quan Hệ (Relationships)")
            df_rels = pd.DataFrame(list(stats["rel_types"].items()), columns=["Loại Quan Hệ", "Số Lượng"])
            st.dataframe(df_rels, use_container_width=True, hide_index=True)

        with col_lvl:
            st.markdown("##### 📁 Phân Bố Cấp Độ Phân Đoạn (Chunk Levels)")
            df_lvls = pd.DataFrame(list(stats["level_stats"].items()), columns=["Cấp Bậc (Level)", "Số Phân Đoạn"])
            st.dataframe(df_lvls, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("##### 🔗 Chi Tiết 8 Mối Liên Kết Giữa Các Văn Bản Pháp Luật")
        doc_rels = fetch_doc_relationships(driver, db_name)
        if doc_rels:
            df_doc_rels = pd.DataFrame([
                {
                    "STT": i,
                    "Văn Bản Nguồn": f"{r['from_so']} ({r['from_id']})",
                    "Loại Quan Hệ": f"[:{r['rel_type']}]",
                    "Ý Nghĩa Pháp Lý": r['rel_desc'],
                    "Văn Bản Đích": f"{r['to_so']} ({r['to_id']})"
                }
                for i, r in enumerate(doc_rels, 1)
            ])
            st.dataframe(df_doc_rels, use_container_width=True, hide_index=True)

    # --------------------------------------------------------------------------
    # TAB 2: 15 VĂN BẢN PHÁP LUẬT
    # --------------------------------------------------------------------------
    with tab_docs:
        st.subheader("📑 Danh Sách 15 Văn Bản Pháp Luật Đã Được Nạp")
        df_docs = fetch_all_documents(driver, db_name)
        search_kw = st.text_input("🔍 Lọc theo Số hiệu, Cơ quan hoặc Tiêu đề văn bản:", "")
        if search_kw:
            filtered_df = df_docs[
                df_docs['so_ky_hieu'].str.contains(search_kw, case=False, na=False) |
                df_docs['title'].str.contains(search_kw, case=False, na=False) |
                df_docs['co_quan_ban_hanh'].str.contains(search_kw, case=False, na=False)
            ]
        else:
            filtered_df = df_docs

        st.dataframe(
            filtered_df[[
                'id', 'so_ky_hieu', 'loai_van_ban', 'co_quan_ban_hanh',
                'ngay_ban_hanh', 'tinh_trang_hieu_luc', 'title'
            ]],
            use_container_width=True,
            hide_index=True
        )

    # --------------------------------------------------------------------------
    # TAB 3: CẤU TRÚC PHÂN CẤP CHA - CON
    # --------------------------------------------------------------------------
    with tab_hierarchy:
        st.subheader("🌳 Khám Phá Cấu Trúc Phân Cấp Cha - Con (:PARENT_OF)")
        st.caption("Minh họa mô hình phân cấp: Chương ➔ Mục ➔ Điều ➔ Khoản ➔ Đoạn/Bảng biểu chi tiết.")

        df_docs_list = fetch_all_documents(driver, db_name)
        doc_options = {f"{r['so_ky_hieu']} - {r['title'][:60]}...": r['id'] for _, r in df_docs_list.iterrows()}
        selected_doc_label = st.selectbox("Chọn văn bản để kiểm tra phân cấp:", list(doc_options.keys()))
        selected_doc_id = doc_options[selected_doc_label]

        hier_records = fetch_doc_hierarchy(driver, db_name, str(selected_doc_id), limit=30)
        if hier_records:
            st.success(f"Tìm thấy các mối quan hệ Cha - Con trong văn bản ID: `{selected_doc_id}`")
            for i, r in enumerate(hier_records[:10], 1):
                with st.expander(f"#{i} [{r['parent_level'].upper()}] {r['parent_heading']} ➔ [{r['child_level'].upper()}] {r['child_heading']}"):
                    st.markdown(f"**Nút Cha (Parent Chunk):** `{r['parent_id']}` (Cấp: `{r['parent_level']}`)")
                    st.markdown(f"**Nút Con (Child Chunk):** `{r['child_id']}` (Cấp: `{r['child_level']}`)")
                    st.markdown(f"**Nội dung phân đoạn con:**")
                    st.info(r['child_text'])
        else:
            st.info("Văn bản này không có quan hệ phân cấp sâu hoặc đang được cập nhật.")

    # --------------------------------------------------------------------------
    # TAB 4: LUỒNG ĐỌC TUẦN TỰ NEXT
    # --------------------------------------------------------------------------
    with tab_next:
        st.subheader("🔗 Chuỗi Luồng Đọc Tuần Tự (:NEXT)")
        st.caption("Liên kết giữa các phân đoạn anh em liền kề giúp giữ nguyên mạch đọc văn bản pháp luật.")

        selected_next_doc = st.selectbox("Chọn văn bản xem luồng NEXT:", list(doc_options.keys()), key="next_doc_select")
        next_doc_id = doc_options[selected_next_doc]

        next_records = fetch_next_sequence(driver, db_name, str(next_doc_id), limit=15)
        if next_records:
            st.write(f"Luồng đọc tuần tự 15 chunks đầu tiên của văn bản `{next_doc_id}`:")
            for i, r in enumerate(next_records, 1):
                col_a, col_arrow, col_b = st.columns([4, 1, 4])
                with col_a:
                    st.code(f"[{r['from_level']}] {r['from_heading']}\nID: {r['from_id']}")
                with col_arrow:
                    st.markdown("<h3 style='text-align: center; color: #10b981;'>➔ [:NEXT] ➔</h3>", unsafe_allow_html=True)
                with col_b:
                    st.code(f"[{r['to_level']}] {r['to_heading']}\nID: {r['to_id']}")
        else:
            st.info("Chưa tìm thấy quan hệ NEXT cho văn bản này.")

    # --------------------------------------------------------------------------
    # TAB 5: TÌM KIẾM VECTOR TIẾNG VIỆT
    # --------------------------------------------------------------------------
    with tab_search:
        st.subheader("🔍 Tìm Kiếm Vector Tương Đồng (Dense Embeddings trên CPU)")
        st.caption("Mô hình nhúng: `thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5` (384 chiều, Cosine Similarity)")

        query_input = st.text_input(
            "Nhập nội dung truy vấn câu hỏi pháp luật:",
            value="Quy định về việc đóng gói, niêm phong và vận chuyển tiền mặt"
        )
        top_k_slider = st.slider("Số lượng Chunks phù hợp nhất (Top K):", min_value=1, max_value=10, value=3)

        if st.button("🚀 Thực hiện Tìm kiếm Vector", type="primary"):
            embedder = get_embedding_model_singleton()
            if embedder:
                with st.spinner("Đang tạo vector nhúng trên CPU và truy vấn Vector Index trên Neo4j..."):
                    t0 = time.time()
                    q_vec = embedder.embed_query(query_input)
                    search_results = vector_search(driver, db_name, q_vec, top_k=top_k_slider)
                    elapsed = time.time() - t0

                st.success(f"Hoàn tất tìm kiếm trong **{elapsed:.2f}s**! Tìm thấy **{len(search_results)}** phân đoạn liên quan nhất:")

                for rank, res in enumerate(search_results, 1):
                    score_pct = res['score'] * 100
                    st.markdown(f"#### #{rank}. {res['heading']} (Độ tương đồng: `{score_pct:.1f}%`)")
                    st.markdown(f"- **Văn bản nguồn**: [{res['so_ky_hieu']}] {res['doc_title']}")
                    st.markdown(f"- **Chunk ID**: `{res['chunk_id']}` | **Cấp độ**: `{res['level']}`")
                    st.text_area(
                        label=f"Nội dung phân đoạn #{rank}",
                        value=res['text'],
                        height=120,
                        key=f"chunk_result_{rank}"
                    )
                    st.markdown("---")
            else:
                st.error("Không thể khởi tạo mô hình nhúng. Vui lòng kiểm tra lại môi trường PyTorch CPU.")

    # --------------------------------------------------------------------------
    # TAB 6: NEO4J BROWSER & CYPHER
    # --------------------------------------------------------------------------
    with tab_cypher:
        st.subheader("💻 Mở Neo4j Browser và Các Câu Truy Vấn Mẫu")
        st.markdown("""
        Bạn có thể mở giao diện đồ thị gốc của Neo4j tại: 👉 **[http://localhost:7474](http://localhost:7474)**
        - **Connect URL**: `bolt://localhost:7687`
        - **Username**: `neo4j`
        - **Password**: `abcd1234`
        - **Chuyển database**: Gõ lệnh `:use kb-hops`
        """)

        st.markdown("##### 💡 Các câu truy vấn Cypher hay dùng để khám phá đồ thị:")

        c1_code = """// 1. Xem toàn bộ 15 văn bản và 8 quan hệ liên kết
MATCH (d1:Document)-[r]->(d2:Document)
RETURN d1, r, d2"""
        st.code(c1_code, language="cypher")

        c2_code = """// 2. Xem cây phân cấp Cha - Con của Điều 1 (Thông tư 01/2014)
MATCH (d:Chunk {id: '44209_d_1'})-[:PARENT_OF]->(c:Chunk)
RETURN d, c"""
        st.code(c2_code, language="cypher")

        c3_code = """// 3. Xem chuỗi đọc tuần tự [:NEXT] qua 5 phân đoạn liên tiếp
MATCH path = (start:Chunk {id: '44209_preamble'})-[:NEXT*1..4]->(next:Chunk)
RETURN path"""
        st.code(c3_code, language="cypher")


if __name__ == "__main__":
    main()
