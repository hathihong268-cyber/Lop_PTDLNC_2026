"""
Ứng dụng Web Streamlit - Buổi 08: Advanced RAG vs Semantic Baseline.
Trực quan hóa Pipeline đa tầng: BM25 Lexical + Dense Semantic + RRF Fusion + Cross-Encoder Reranker.
"""

import os
import sys
import json
import time
from pathlib import Path
import streamlit as st

# Thư mục gốc Buổi 08
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from advanced_rag import (
    load_advanced_config,
    get_advanced_status,
    query_advanced_rag,
    compare_retrieval_modes,
    build_bm25_retriever,
    ALLOWED_STRATEGIES,
    DEFAULT_INPUT_DIR,
    CHROMA_STORAGE_DIR,
    HF_STORAGE_DIR,
)
from rag import load_chunks

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="Advanced RAG Workshop - Buổi 08",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS tinh chỉnh giao diện chuyên nghiệp
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
    }
    .rank-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.85em;
    }
    .rank-up { background-color: #d4edda; color: #155724; }
    .rank-down { background-color: #f8d7da; color: #721c24; }
    .rank-neutral { background-color: #e2e3e5; color: #383d41; }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# CACHE RESOURCES & STATE MANAGEMENT
# ==============================================================================

@st.cache_resource(show_spinner=False)
def get_cached_bm25(strategy: str):
    """Cache BM25 index theo từng strategy trong suốt phiên chạy của process"""
    chunks, _ = load_chunks(DEFAULT_INPUT_DIR, strategy=strategy)
    retriever = build_bm25_retriever(chunks)
    return chunks, retriever


# Khởi tạo session state
if "last_query" not in st.session_state:
    st.session_state["last_query"] = ""
if "last_result" not in st.session_state:
    st.session_state["last_result"] = None
if "last_compare_query" not in st.session_state:
    st.session_state["last_compare_query"] = ""
if "last_compare_result" not in st.session_state:
    st.session_state["last_compare_result"] = None


# ==============================================================================
# SIDEBAR CONFIGURATION & STATUS INSPECTION
# ==============================================================================

with st.sidebar:
    st.title("⚡ Cấu hình Advanced RAG")
    
    # Nạp cấu hình từ .env
    try:
        cfg = load_advanced_config()
    except Exception as e:
        st.error(f"Lỗi nạp .env: {e}")
        cfg = {
            "has_api_key": False,
            "embedding_model": "gemini-embedding-2",
            "embedding_dim": 768,
            "generation_model": "gemini-3.5-flash-lite",
            "max_distance": 0.45,
            "bm25_candidates": 20,
            "semantic_candidates": 20,
            "rerank_candidates": 20,
            "final_top_k": 5,
            "rrf_k": 60,
            "rrf_bm25_weight": 1.0,
            "rrf_semantic_weight": 1.0,
            "reranker_model": "BAAI/bge-reranker-v2-m3",
            "reranker_max_length": 512,
            "rerank_batch_size": 4,
            "rerank_min_score": 0.50,
            "rerank_device": "auto",
        }

    strategy = st.selectbox(
        "Chiến lược chia chunk (Strategy):",
        options=sorted(list(ALLOWED_STRATEGIES)),
        index=sorted(list(ALLOWED_STRATEGIES)).index("hierarchical") if "hierarchical" in ALLOWED_STRATEGIES else 0
    )

    selected_mode = st.selectbox(
        "Chế độ truy xuất (Retrieval Mode):",
        options=["hybrid_rerank", "hybrid", "semantic", "bm25"],
        index=0,
        help="hybrid_rerank là chế độ mặc định đầy đủ nhất của Advanced RAG"
    )

    final_top_k = st.slider(
        "Số lượng Evidence tối đa (Final Top-K):",
        min_value=1,
        max_value=15,
        value=cfg.get("final_top_k", 5)
    )

    st.divider()
    st.subheader("🔍 Trạng thái Hệ thống (Read-Only)")

    try:
        sys_status = get_advanced_status(strategy=strategy, config=cfg)
        st.write(f"**Tập Chunk ({strategy}):** {sys_status['corpus_size']} chunks")
        st.write(f"**Chroma Collection:** `{sys_status['semantic_collection_name']}`")
        if sys_status["collection_exists"]:
            st.success(f"Chroma DB: {sys_status['record_count']} records")
        else:
            st.warning("Chroma DB: Chưa index vector")

        st.write(f"**Gemini API Key:** {'✅ Đã cấu hình' if sys_status['has_api_key'] else '❌ Thiếu API Key'}")
        st.write(f"**Reranker Model:** `{sys_status['reranker_model']}`")
        st.write(f"**Reranker Weights:** {'✅ Đã có trong cache' if sys_status['reranker_cached'] else '⏳ Chưa tải (tải khi gọi)'}")
    except Exception as e:
        st.error(f"Lỗi kiểm tra trạng thái: {e}")

    with st.expander("⚙️ Tham số nâng cao (RRF & Reranker)"):
        st.write(f"• **BM25 Candidates ($K_1$):** {cfg.get('bm25_candidates')}")
        st.write(f"• **Semantic Candidates ($K_2$):** {cfg.get('semantic_candidates')}")
        st.write(f"• **RRF Constant ($k$):** {cfg.get('rrf_k')}")
        st.write(f"• **RRF Weights:** BM25={cfg.get('rrf_bm25_weight')}, Semantic={cfg.get('rrf_semantic_weight')}")
        st.write(f"• **Rerank Candidates:** {cfg.get('rerank_candidates')}")
        st.write(f"• **Rerank Min Score Gate:** {cfg.get('rerank_min_score')}")
        st.write(f"• **Semantic Max Distance Gate:** {cfg.get('max_distance')}")
        st.write(f"• **Rerank Device:** `{cfg.get('rerank_device')}`")


# ==============================================================================
# MAIN PAGE HEADER & TABS
# ==============================================================================

st.title("⚡ Advanced RAG: Hybrid Search & Multilingual Reranking")
st.caption("Workshop Buổi 08 — Kiến trúc RAG cấp sản phẩm: BM25 Okapi + Dense Vector + Reciprocal Rank Fusion + BGE Reranker v2")

tab1, tab2, tab3, tab4 = st.tabs([
    "💬 Hỏi đáp Advanced RAG",
    "⚖️ So sánh Retrieval (Side-by-Side)",
    "🔍 Pipeline Trace & Latency",
    "📊 Đánh giá Benchmark"
])


# ==============================================================================
# TAB 1: HỎI ĐÁP ADVANCED RAG (ANSWER PIPELINE)
# ==============================================================================

with tab1:
    st.subheader("Hỏi đáp văn bản pháp lý với Grounding & Citations")
    
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        default_q = st.session_state["last_query"] if st.session_state["last_query"] else "Điều 7 quy định về những nội dung gì?"
        query_text = st.text_input("Nhập câu hỏi pháp lý tiếng Việt:", value=default_q, key="tab1_question")
    with col_btn:
        st.write("")
        st.write("")
        submit_btn = st.button("🚀 Gửi câu hỏi", type="primary", use_container_width=True)

    if submit_btn and query_text.strip():
        st.session_state["last_query"] = query_text.strip()
        with st.spinner("Đang thực thi quy trình Advanced RAG đa tầng..."):
            try:
                # Nạp BM25 cached cho strategy
                cached_chunks, cached_bm25 = get_cached_bm25(strategy)
                
                cfg_exec = dict(cfg)
                cfg_exec["final_top_k"] = final_top_k
                
                res = query_advanced_rag(
                    question=query_text.strip(),
                    mode=selected_mode,
                    strategy=strategy,
                    top_k=final_top_k,
                    config=cfg_exec,
                    chunks=cached_chunks,
                    custom_retriever=cached_bm25
                )
                st.session_state["last_result"] = res
            except Exception as e:
                st.error(f"Đã xảy ra lỗi trong quá trình truy vấn: {e}")
                st.session_state["last_result"] = None

    # Hiển thị kết quả từ session state
    result = st.session_state.get("last_result")
    if result:
        st.divider()
        status_val = result.get("status")
        
        if status_val == "answered":
            st.success(f"✅ Trạng thái: **Đã trả lời thành công** (Mode: `{result['mode']}` | Tổng thời gian: {result['trace']['latency_ms']['total']} ms)")
            st.markdown("### 📝 Câu trả lời:")
            st.markdown(result["answer"])

            if result.get("citations"):
                st.markdown("#### 📌 Trích dẫn nguồn tài liệu:")
                c_cols = st.columns(len(result["citations"])) if len(result["citations"]) <= 4 else [st]
                for idx, c in enumerate(result["citations"]):
                    p_str = f"tr. {c['page_start']}" if c['page_start'] == c['page_end'] else f"tr. {c['page_start']}-{c['page_end']}"
                    st.info(f"**{c['label']}**: {c['source']} ({p_str}) — ID: `{c['chunk_id']}`")

        elif status_val == "insufficient_evidence":
            st.warning("⚠️ Trạng thái: **Không đủ bằng chứng (Insufficient Evidence)**")
            st.info("Không có đoạn văn bản nào vượt qua ngưỡng kiểm định chất lượng (Confidence Gate). Hệ thống từ chối sinh câu trả lời để phòng tránh ảo giác (Hallucination).")
            if result.get("warnings"):
                for w in result["warnings"]:
                    st.caption(f"Chi tiết: {w}")

        elif status_val == "retrieval_only":
            st.warning("ℹ️ Trạng thái: **Chỉ hoàn tất Truy xuất (Retrieval Only)**")
            st.info(result.get("answer", "Đã truy xuất được nguồn nhưng chưa thể tạo câu trả lời tổng hợp."))
            if result.get("warnings"):
                for w in result["warnings"]:
                    st.caption(f"Cảnh báo: {w}")

        elif status_val == "reranker_unavailable":
            st.error("❌ Trạng thái: **Mô hình Reranker chưa sẵn sàng (Reranker Unavailable)**")
            st.info("""
            Mô hình Cross-Encoder Reranker (`BAAI/bge-reranker-v2-m3`) chưa được tải về máy hoặc gặp sự cố.
            
            **Hướng dẫn khắc phục:**
            1. Chạy lệnh chẩn đoán từ terminal để tải model:
               ```bash
               python advanced_rag.py rerank --strategy hierarchical --question "kiểm tra reranker"
               ```
            2. Hoặc chuyển sang chế độ `hybrid` hoặc `semantic` ở sidebar nếu bạn chưa muốn tải reranker model.
            """)
            if result.get("warnings"):
                for w in result["warnings"]:
                    st.caption(f"Chi tiết lỗi: {w}")

        # Hiển thị các Evidence cards
        if result.get("evidence"):
            st.markdown("### 🗂️ Danh sách Bằng chứng (Evidence Chunks):")
            for idx, ev in enumerate(result["evidence"], start=1):
                p_str = f"tr. {ev['page_start']}" if ev['page_start'] == ev['page_end'] else f"tr. {ev['page_start']}-{ev['page_end']}"
                acc_badge = "✅ Đạt gate" if ev.get("accepted") else "❌ Không đạt gate"
                
                with st.expander(f"Evidence #{idx} — [{acc_badge}] — {ev['source']} ({p_str}) | ID: `{ev['chunk_id']}`", expanded=(idx <= 2)):
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        b_rank = f"#{ev['bm25_rank']}" if ev.get('bm25_rank') else "N/A"
                        b_score = f"{ev['bm25_score']:.4f}" if ev.get('bm25_score') is not None else "N/A"
                        st.metric("BM25 Rank / Score", f"{b_rank} ({b_score})")
                    with c2:
                        s_rank = f"#{ev['semantic_rank']}" if ev.get('semantic_rank') else "N/A"
                        s_dist = f"{ev['semantic_distance']:.4f}" if ev.get('semantic_distance') is not None else "N/A"
                        st.metric("Semantic Rank / Dist", f"{s_rank} (dist={s_dist})")
                    with c3:
                        h_rank = f"#{ev['fused_rank']}" if ev.get('fused_rank') else "N/A"
                        h_score = f"{ev['rrf_score']:.5f}" if ev.get('rrf_score') is not None else "N/A"
                        st.metric("RRF Fused Rank / Score", f"{h_rank} ({h_score})")
                    with c4:
                        r_rank = f"#{ev['rerank_rank']}" if ev.get('rerank_rank') else "N/A"
                        r_score = f"{ev['rerank_score']:.4f}" if ev.get('rerank_score') is not None else "N/A"
                        chg = ev.get('rank_change')
                        chg_str = f"+{chg}" if chg and chg > 0 else str(chg)
                        st.metric("Rerank Rank / Score", f"{r_rank} ({r_score})", delta=chg_str if chg is not None else None)

                    st.markdown(f"**Nội dung trích dẫn:**\n> {ev['text']}")


# ==============================================================================
# TAB 2: SO SÁNH RETRIEVAL (SIDE-BY-SIDE WITHOUT GENERATION)
# ==============================================================================

with tab2:
    st.subheader("So sánh trực quan 4 Chế độ Truy xuất (Không gọi LLM)")
    st.caption("Xem xét sự thay đổi thứ hạng, các chunk được thêm mới, bị loại bỏ hoặc thay đổi vị trí qua từng giai đoạn.")

    col_cq, col_cbtn = st.columns([5, 1])
    with col_cq:
        default_comp_q = st.session_state["last_compare_query"] if st.session_state["last_compare_query"] else "Điều 7 quy định về những nội dung gì?"
        comp_query_text = st.text_input("Nhập câu hỏi để so sánh 4 chế độ retrieval:", value=default_comp_q, key="tab2_question")
    with col_cbtn:
        st.write("")
        st.write("")
        compare_btn = st.button("⚖️ Chạy so sánh", type="primary", use_container_width=True)

    if compare_btn and comp_query_text.strip():
        st.session_state["last_compare_query"] = comp_query_text.strip()
        with st.spinner("Đang chạy so sánh 4 phương thức truy xuất..."):
            try:
                cached_chunks, cached_bm25 = get_cached_bm25(strategy)
                comp_res = compare_retrieval_modes(
                    question=comp_query_text.strip(),
                    strategy=strategy,
                    config=cfg,
                    chunks=cached_chunks,
                    custom_retriever=cached_bm25
                )
                st.session_state["last_compare_result"] = comp_res
            except Exception as e:
                st.error(f"Lỗi so sánh: {e}")
                st.session_state["last_compare_result"] = None

    comp_result = st.session_state.get("last_compare_result")
    if comp_result:
        st.divider()
        st.markdown("### 📊 Bảng đối chiếu thứ hạng tổng hợp:")
        
        table_rows = []
        for r in comp_result["comparison_rows"]:
            rrk_str = f"#{r['rerank_rank']}" if r['rerank_rank'] else "-"
            hyb_str = f"#{r['hybrid_rank']}" if r['hybrid_rank'] else "-"
            sem_str = f"#{r['semantic_rank']}" if r['semantic_rank'] else "-"
            b25_str = f"#{r['bm25_rank']}" if r['bm25_rank'] else "-"
            chg_val = r['rank_change']
            chg_display = f"+{chg_val}" if (chg_val is not None and chg_val > 0) else (str(chg_val) if chg_val is not None else "-")
            
            p_str = f"tr. {r['page_start']}" if r['page_start'] == r['page_end'] else f"tr. {r['page_start']}-{r['page_end']}"
            table_rows.append({
                "Chunk ID": r['chunk_id'],
                "Nguồn": f"{r['source']} ({p_str})",
                "BM25 Rank": b25_str,
                "Semantic Rank": sem_str,
                "RRF Fused Rank": hyb_str,
                "Rerank Rank": rrk_str,
                "Độ dịch chuyển (Rank Change)": chg_display,
                "Các Mode xuất hiện": ", ".join(r['modes_present'])
            })
        st.dataframe(table_rows, use_container_width=True)

        st.markdown("### 🔲 So sánh 4 Cột Kết quả Top-K Cạnh nhau:")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)

        with col_m1:
            st.markdown(f"#### 1. BM25 Okapi ({comp_result['latency_ms']['bm25']} ms)")
            bm25_chunks = [r for r in comp_result["comparison_rows"] if r["bm25_rank"] is not None]
            bm25_chunks.sort(key=lambda x: x["bm25_rank"])
            for item in bm25_chunks[:final_top_k]:
                st.info(f"**Rank #{item['bm25_rank']}**\nID: `{item['chunk_id']}`\n{item['source']}")

        with col_m2:
            st.markdown(f"#### 2. Dense Semantic ({comp_result['latency_ms']['semantic']} ms)")
            sem_chunks = [r for r in comp_result["comparison_rows"] if r["semantic_rank"] is not None]
            sem_chunks.sort(key=lambda x: x["semantic_rank"])
            for item in sem_chunks[:final_top_k]:
                st.info(f"**Rank #{item['semantic_rank']}**\nID: `{item['chunk_id']}`\n{item['source']}")

        with col_m3:
            st.markdown(f"#### 3. Hybrid RRF ({comp_result['latency_ms']['hybrid']} ms)")
            hyb_chunks = [r for r in comp_result["comparison_rows"] if r["hybrid_rank"] is not None]
            hyb_chunks.sort(key=lambda x: x["hybrid_rank"])
            for item in hyb_chunks[:final_top_k]:
                st.info(f"**Fused #{item['hybrid_rank']}**\nID: `{item['chunk_id']}`\n{item['source']}")

        with col_m4:
            st.markdown(f"#### 4. Hybrid + Rerank ({comp_result['latency_ms']['hybrid_rerank']} ms)")
            rrk_chunks = [r for r in comp_result["comparison_rows"] if r["rerank_rank"] is not None]
            rrk_chunks.sort(key=lambda x: x["rerank_rank"])
            for item in rrk_chunks[:final_top_k]:
                chg = item['rank_change']
                delta_lbl = f"(Dịch chuyển: +{chg})" if (chg and chg > 0) else (f"(Dịch chuyển: {chg})" if chg is not None else "")
                st.success(f"**Rerank #{item['rerank_rank']}** {delta_lbl}\nID: `{item['chunk_id']}`\n{item['source']}")


# ==============================================================================
# TAB 3: PIPELINE TRACE & LATENCY
# ==============================================================================

with tab3:
    st.subheader("🔍 Phân tích Pipeline Trace & Độ trễ (Latency)")
    st.caption("Theo dõi số lượng ứng viên qua từng tầng lọc và thời gian thực thi chi tiết.")

    if result and "trace" in result:
        t = result["trace"]
        
        st.markdown("### 🪜 Phễu Ứng viên qua các tầng lọc:")
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            st.metric("1. BM25 Candidates", f"{t['bm25_candidates']} chunks")
        with m2:
            st.metric("2. Semantic Candidates", f"{t['semantic_candidates']} chunks")
        with m3:
            st.metric("3. Union (Overlap)", f"{t['union']} chunks", delta=f"Trùng {t['overlap']}")
        with m4:
            st.metric("4. Đưa vào Rerank", f"{t['reranked']} chunks")
        with m5:
            st.metric("5. Đạt Gate (Accepted)", f"{t['accepted']} chunks")

        st.markdown("### ⏱️ Phân rã Thời gian Thực thi (Latency Breakdown):")
        lat = t["latency_ms"]
        l1, l2, l3, l4, l5, l6 = st.columns(6)
        with l1:
            st.metric("BM25", f"{lat.get('bm25', 0)} ms")
        with l2:
            st.metric("Semantic", f"{lat.get('semantic', 0)} ms")
        with l3:
            st.metric("RRF Fusion", f"{lat.get('fusion', 0)} ms")
        with l4:
            st.metric("Rerank", f"{lat.get('rerank', 0)} ms")
        with l5:
            st.metric("Generation", f"{lat.get('generation', 0)} ms")
        with l6:
            st.metric("Tổng Pipeline", f"{lat.get('total', 0)} ms")

    else:
        st.info("Hãy thực hiện một câu hỏi tại Tab 1 để hiển thị đầy đủ Pipeline Trace của câu hỏi đó.")

    st.divider()
    st.markdown("### 📖 Hướng dẫn Đọc hiểu Chỉ số:")
    c_info1, c_info2 = st.columns(2)
    with c_info1:
        st.markdown("""
        * **BM25 Score**: Điểm số tần suất từ khóa Okapi. Điểm số **càng cao càng tốt** (không bị chặn trên).
        * **Cosine Distance**: Khoảng cách hình học trong không gian vector. Khoảng cách **càng thấp càng tương đồng** (0.0 là trùng khớp hoàn hảo).
        """)
    with c_info2:
        st.markdown("""
        * **RRF Score**: Điểm hợp nhất thứ hạng nghịch đảo $\\frac{w}{k + rank}$. Điểm **càng cao càng tốt**.
        * **Rerank Score**: Điểm tương quan qua hàm $\\text{Sigmoid}(\\text{logit}) \\in [0, 1]$. **Điểm càng cao càng tốt** (*Lưu ý: Không phải là xác suất đúng tuyệt đối*).
        """)


# ==============================================================================
# TAB 4: ĐÁNH GIÁ BENCHMARK (EVALUATION REPORT)
# ==============================================================================

with tab4:
    st.subheader("📊 Báo cáo Đánh giá Hiệu năng Định lượng")
    st.caption("Tổng hợp kết quả kiểm thử trên bộ câu hỏi chuẩn (Ground Truth Benchmark).")

    # Kiểm tra trạng thái tập câu hỏi chuẩn
    questions_file = BASE_DIR / "eval" / "questions.json"
    if questions_file.exists():
        try:
            with open(questions_file, "r", encoding="utf-8") as f:
                q_data = json.load(f)
            unreviewed = sum(1 for q in q_data if q.get("needs_human_review", False))
            if unreviewed > 0:
                st.warning(f"⚠️ Bộ câu hỏi chuẩn (`eval/questions.json`) có **{unreviewed} câu hỏi đang được gắn cờ `needs_human_review=true`**. Kết quả đánh giá chỉ mang tính chất tham khảo cho đến khi được chuyên gia thẩm định hoàn tất.")
        except Exception:
            pass

    # Quét các file báo cáo trong thư mục reports/
    reports_dir = BASE_DIR / "reports"
    report_files = list(reports_dir.glob("*.json")) if reports_dir.exists() else []

    if not report_files:
        st.info("""
        Chưa tìm thấy file báo cáo kết quả nào trong thư mục `reports/`.
        
        **Để sinh báo cáo đánh giá tự động:**
        1. Mở terminal và thực thi module `evaluate.py`:
           ```bash
           python evaluate.py --strategy hierarchical
           ```
        2. Sau khi chạy xong, tải lại trang này để xem các biểu đồ và bảng chỉ số Hit@K, MRR@K, nDCG@K.
        """)
    else:
        selected_report_file = st.selectbox(
            "Chọn file báo cáo để xem chi tiết:",
            options=[f.name for f in report_files]
        )
        try:
            with open(reports_dir / selected_report_file, "r", encoding="utf-8") as f:
                rep_data = json.load(f)
            
            st.markdown(f"**Chiến lược:** `{rep_data.get('strategy', 'N/A')}` | **Thời gian đánh giá:** `{rep_data.get('timestamp', 'N/A')}`")
            if "metrics" in rep_data:
                st.dataframe(rep_data["metrics"], use_container_width=True)
            if "latency_stats" in rep_data:
                st.write("**Thống kê độ trễ:**", rep_data["latency_stats"])
        except Exception as e:
            st.error(f"Lỗi đọc file báo cáo: {e}")
