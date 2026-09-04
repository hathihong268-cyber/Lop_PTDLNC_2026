"""
Ứng dụng Web Streamlit - Buổi 08: Advanced RAG Studio (Hybrid Search, Reranking & Pipeline Tracing).

Giao diện trực quan hóa toàn diện quy trình Advanced RAG:
1. Hỏi đáp Advanced RAG (Grounded Generation & Citation Mapping).
2. So sánh đối đầu 4 chế độ Retrieval (BM25 vs. Semantic vs. Hybrid RRF vs. Cross-Encoder).
3. Pipeline Trace chi tiết (Metrics flow, latency và giải thích thang đo).
4. Đánh giá Benchmark & Gold Dataset Inspection.
"""

from pathlib import Path
import os
import sys
import json
import time
from typing import Dict, List, Any, Optional

import streamlit as st
import pandas as pd

# Đảm bảo import được các module từ thư mục Buổi 08
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from advanced_rag import (
    load_advanced_config,
    get_advanced_status,
    load_chunks,
    query_advanced_rag,
    compare_retrieval_modes,
    ALLOWED_STRATEGIES,
    ALLOWED_MODES,
    DEFAULT_INPUT_DIR
)

REPORTS_DIR = (BASE_DIR / "reports").resolve()
EVAL_FILE = (BASE_DIR / "eval" / "questions.json").resolve()


# ============================================================================
# CACHING VÀ SESSION STATE
# ============================================================================

@st.cache_data(show_spinner=False)
def get_cached_chunks(strategy: str, input_dir: Optional[str] = None):
    """Cache dữ liệu chunks nạp từ đĩa theo từng strategy."""
    chunks, stats = load_chunks(input_path=input_dir, strategy=strategy)
    return chunks, stats


def load_eval_questions_data() -> List[Dict[str, Any]]:
    """Đọc bộ câu hỏi benchmark từ eval/questions.json."""
    if EVAL_FILE.exists():
        try:
            with open(EVAL_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def load_available_reports() -> List[Path]:
    """Tìm danh sách các file báo cáo JSON trong thư mục reports/."""
    if REPORTS_DIR.exists():
        return sorted(list(REPORTS_DIR.glob("*.json")), reverse=True)
    return []


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    st.set_page_config(
        page_title="Advanced RAG Studio - Buổi 08",
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # CSS tùy chỉnh giao diện chuyên nghiệp
    st.markdown("""
        <style>
        .main-title {
            font-size: 2.2rem;
            font-weight: 700;
            color: #1E293B;
            margin-bottom: 0.2rem;
        }
        .sub-title {
            font-size: 1.05rem;
            color: #64748B;
            margin-bottom: 1.5rem;
        }
        .metric-box {
            background-color: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 12px;
            text-align: center;
        }
        .evidence-card {
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 14px;
            margin-bottom: 12px;
            background-color: #FFFFFF;
        }
        .evidence-card.accepted {
            border-left: 5px solid #10B981;
        }
        .evidence-card.rejected {
            border-left: 5px solid #EF4444;
            background-color: #FFF5F5;
        }
        .badge-accepted {
            background-color: #D1FAE5;
            color: #065F46;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.85rem;
        }
        .badge-rejected {
            background-color: #FEE2E2;
            color: #991B1B;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.85rem;
        }
        .badge-mode {
            background-color: #E0E7FF;
            color: #3730A3;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)

    # Nạp cấu hình hiện tại
    cfg = load_advanced_config()

    # ========================================================================
    # SIDEBAR: CẤU HÌNH & TRẠNG THÁI HỆ THỐNG
    # ========================================================================
    with st.sidebar:
        st.header("⚙️ Cấu Hình RAG")

        selected_strategy = st.selectbox(
            "Chiến lược Chunking (Strategy):",
            options=sorted(list(ALLOWED_STRATEGIES)),
            index=sorted(list(ALLOWED_STRATEGIES)).index("hierarchical")
        )

        selected_mode = st.selectbox(
            "Chế độ Retrieval (Mode):",
            options=["hybrid_rerank", "hybrid", "semantic", "bm25"],
            index=0,
            help="hybrid_rerank: Two-stage retrieval với Cross-Encoder (mặc định)."
        )

        final_top_k = st.slider("Final Top-K:", min_value=1, max_value=15, value=cfg.get("final_top_k", 5))

        with st.expander("🔧 Tham Số Chi Tiết (Advanced)", expanded=False):
            bm25_cand_k = st.number_input("BM25 Candidate K:", min_value=1, max_value=50, value=cfg.get("bm25_candidates", 20))
            semantic_cand_k = st.number_input("Semantic Candidate K:", min_value=1, max_value=50, value=cfg.get("semantic_candidates", 20))
            rrf_k = st.number_input("RRF Smoothing K:", min_value=1, max_value=100, value=cfg.get("rrf_k", 60))
            w_bm25 = st.slider("Trọng số BM25 (w_bm25):", min_value=0.0, max_value=2.0, value=1.0, step=0.1)
            w_sem = st.slider("Trọng số Semantic (w_sem):", min_value=0.0, max_value=2.0, value=1.0, step=0.1)
            rerank_min_score = st.slider("Rerank Min Score:", min_value=0.0, max_value=1.0, value=cfg.get("rerank_min_score", 0.50), step=0.05)

        # Trạng thái hệ thống (Read-Only)
        st.divider()
        st.subheader("📡 Trạng Thái Hệ Thống")

        status_info = get_advanced_status(strategy=selected_strategy)

        if status_info["has_api_key"]:
            st.success("🔑 Gemini API Key: **Đã cấu hình**")
        else:
            st.error("🔑 Gemini API Key: **Chưa có (.env)**")

        if status_info["collection_exists"]:
            st.success(f"🗄️ Chroma Index: **{status_info['record_count']} records**")
        else:
            st.warning("🗄️ Chroma Index: **Chưa index**")

        st.info(f"📚 BM25 Corpus: **{status_info['corpus_size']} chunks**")
        st.caption(f"🤖 Reranker: `{status_info['reranker_model']}`")
        if status_info["reranker_cached"]:
            st.caption("💾 Reranker Cache: `Đã có cache cục bộ`")
        else:
            st.caption("⏳ Reranker Cache: `Chưa cache (sẽ tải khi chạy)`")

    # ========================================================================
    # MAIN CONTENT: TABS GIAO DIỆN
    # ========================================================================
    st.markdown('<div class="main-title">⚖️ Advanced RAG Studio — Buổi 08</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Hệ thống hỏi đáp pháp lý nâng cao kết hợp Lexical (BM25), Dense Semantic, RRF Fusion & Cross-Encoder Reranking.</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "💬 1. Hỏi đáp Advanced RAG",
        "📊 2. So sánh Retrieval",
        "⏱️ 3. Pipeline Trace",
        "📈 4. Đánh giá (Evaluation)"
    ])

    # ------------------------------------------------------------------------
    # TAB 1: HỎI ĐÁP ADVANCED RAG
    # ------------------------------------------------------------------------
    with tab1:
        st.subheader("Hỏi đáp với Grounding & Citation Mapping")

        # Gợi ý câu hỏi mẫu từ eval/questions.json
        sample_questions = [
            "Cho vay theo quy định của Ngân hàng Nhà nước được định nghĩa như thế nào?",
            "Khách hàng cần đáp ứng những điều kiện gì để được tổ chức tín dụng xem xét cho vay vốn?",
            "Thời hạn cho vay giữa tổ chức tín dụng và khách hàng được xác định dựa trên những căn cứ nào?",
            "Trường hợp nào áp dụng mức trần lãi suất cho vay ngắn hạn do Thống đốc NHNN quy định?",
            "Tổ chức tín dụng xem xét cơ cấu lại thời hạn trả nợ theo những điều kiện nào?",
            "Quy định về lắp đặt hệ thống chống sét và an toàn điện trong phòng cháy chữa cháy tòa nhà văn phòng?"
        ]

        preset_q = st.selectbox("Chọn câu hỏi mẫu hoặc tự nhập bên dưới:", options=["<Tự nhập câu hỏi>"] + sample_questions)
        default_val = "" if preset_q == "<Tự nhập câu hỏi>" else preset_q

        user_query = st.text_area("Nội dung câu hỏi:", value=default_val, height=85, placeholder="Nhập câu hỏi quy định tài chính - ngân hàng tại đây...")

        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            run_query = st.button("🚀 Gửi câu hỏi", type="primary", use_container_width=True)

        if run_query and user_query.strip():
            with st.spinner("Đang thực hiện truy vấn qua quy trình Advanced RAG..."):
                try:
                    # Nạp config động từ UI
                    dynamic_cfg = dict(cfg)
                    dynamic_cfg["final_top_k"] = final_top_k
                    dynamic_cfg["bm25_candidates"] = bm25_cand_k
                    dynamic_cfg["semantic_candidates"] = semantic_cand_k
                    dynamic_cfg["rrf_k"] = rrf_k
                    dynamic_cfg["rrf_bm25_weight"] = w_bm25
                    dynamic_cfg["rrf_semantic_weight"] = w_sem
                    dynamic_cfg["rerank_min_score"] = rerank_min_score

                    res = query_advanced_rag(
                        question=user_query.strip(),
                        mode=selected_mode,
                        strategy=selected_strategy,
                        top_k=final_top_k,
                        config=dynamic_cfg
                    )
                    st.session_state["last_query_result"] = res

                except Exception as e:
                    st.error(f"Lỗi truy vấn: {e}")

        # Hiển thị kết quả truy vấn gần nhất
        if "last_query_result" in st.session_state:
            res = st.session_state["last_query_result"]

            st.divider()

            # Status Badge
            status_map = {
                "answered": ("✅ Trả lời thành công (Grounded Answer)", "success"),
                "insufficient_evidence": ("⚠️ Không đủ bằng chứng đạt ngưỡng tin cậy (Insufficient Evidence)", "warning"),
                "retrieval_only": ("🔍 Chỉ truy xuất nguồn, chưa sinh câu trả lời (Retrieval Only)", "info"),
                "reranker_unavailable": ("❌ Mô hình Reranker không khả dụng (Reranker Unavailable)", "error")
            }
            title, alert_type = status_map.get(res["status"], (res["status"], "info"))

            if alert_type == "success":
                st.success(f"**Trạng thái**: {title} | **Mode**: `{res['mode']}`")
            elif alert_type == "warning":
                st.warning(f"**Trạng thái**: {title} | **Mode**: `{res['mode']}`")
            elif alert_type == "error":
                st.error(f"**Trạng thái**: {title} | **Mode**: `{res['mode']}`")
                st.info("💡 Hướng dẫn: Đảm bảo máy có kết nối Internet để tải mô hình `BAAI/bge-reranker-v2-m3` hoặc kiểm tra thư viện `torch`, `transformers`.")
            else:
                st.info(f"**Trạng thái**: {title} | **Mode**: `{res['mode']}`")

            # Câu trả lời & Trích dẫn
            st.markdown("### 📝 Câu trả lời tổng hợp")
            st.markdown(res["answer"])

            if res.get("citations"):
                st.markdown("#### 📚 Nguồn trích dẫn (Citations)")
                for cit in res["citations"]:
                    st.markdown(f"- **{cit['label']}**: `{cit['source']}` (Trang {cit['page_start']}-{cit['page_end']}) — *Chunk ID: `{cit['chunk_id']}`*")

            if res.get("warnings"):
                with st.expander("⚠️ Cảnh báo trong quá trình xử lý"):
                    for w in res["warnings"]:
                        st.write(f"- {w}")

            # Danh sách Evidence Cards
            st.markdown("### 📑 Bằng chứng truy xuất (Evidence Cards)")
            for ev in res.get("evidence", []):
                card_class = "accepted" if ev["accepted"] else "rejected"
                badge_html = '<span class="badge-accepted">ĐẠT CHUẨN</span>' if ev["accepted"] else '<span class="badge-rejected">BỊ LOẠI</span>'

                scores_parts = []
                if ev.get("rerank_score") is not None:
                    scores_parts.append(f"Rerank Score: **{ev['rerank_score']:.4f}** (Rank #{ev['rerank_rank']}, Chg: `{ev['rank_change']:+d}`)")
                if ev.get("rrf_score") is not None:
                    scores_parts.append(f"RRF Score: **{ev['rrf_score']:.6f}** (Fused #{ev['fused_rank']})")
                if ev.get("semantic_distance") is not None:
                    scores_parts.append(f"Semantic Dist: **{ev['semantic_distance']:.4f}** (Rank #{ev['semantic_rank']})")
                if ev.get("bm25_score") is not None:
                    scores_parts.append(f"BM25 Score: **{ev['bm25_score']:.4f}** (Rank #{ev['bm25_rank']})")

                scores_text = " | ".join(scores_parts)

                with st.container():
                    st.markdown(f"""
                    <div class="evidence-card {card_class}">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <strong>[{ev['evidence_id']}] {ev['source']} (tr. {ev['page_start']}-{ev['page_end']})</strong>
                            {badge_html}
                        </div>
                        <div style="font-size: 0.85rem; color: #475569; margin-bottom: 8px;">
                            <code>ID: {ev['chunk_id']}</code> | {scores_text}
                        </div>
                        <div style="font-size: 0.95rem; line-height: 1.5; color: #1E293B;">
                            {ev['text']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    # ------------------------------------------------------------------------
    # TAB 2: SO SÁNH RETRIEVAL
    # ------------------------------------------------------------------------
    with tab2:
        st.subheader("So Sánh Đối Đầu 4 Chế Độ Retrieval")
        st.caption("Chạy đồng thời cùng một câu hỏi qua cả 4 chế độ: BM25, Semantic, Hybrid RRF và Hybrid + Reranker (TUYỆT ĐỐI KHÔNG gọi LLM Generation).")

        cmp_query = st.text_input("Câu hỏi cần so sánh:", value=default_val or "Điều 7 quy định gì về điều kiện vay vốn?", key="cmp_query")
        run_cmp = st.button("⚡ Chạy So Sánh Đối Đầu", type="primary")

        if run_cmp and cmp_query.strip():
            with st.spinner("Đang chạy đối đầu 4 nhánh retrieval..."):
                try:
                    dynamic_cfg = dict(cfg)
                    dynamic_cfg["final_top_k"] = final_top_k
                    dynamic_cfg["bm25_candidates"] = bm25_cand_k
                    dynamic_cfg["semantic_candidates"] = semantic_cand_k
                    dynamic_cfg["rrf_k"] = rrf_k
                    dynamic_cfg["rrf_bm25_weight"] = w_bm25
                    dynamic_cfg["rrf_semantic_weight"] = w_sem

                    cmp_res = compare_retrieval_modes(
                        question=cmp_query.strip(),
                        strategy=selected_strategy,
                        top_k=final_top_k,
                        config=dynamic_cfg
                    )
                    st.session_state["last_compare_result"] = cmp_res
                except Exception as e:
                    st.error(f"Lỗi so sánh retrieval: {e}")

        if "last_compare_result" in st.session_state:
            cmp_res = st.session_state["last_compare_result"]
            counts = cmp_res["mode_counts"]
            lat = cmp_res["latency_ms"]

            st.divider()

            # Thống kê tổng quan
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("BM25 Top-K", f"{counts['bm25']}", f"{lat['bm25']} ms")
            m2.metric("Semantic Top-K", f"{counts['semantic']}", f"{lat['semantic']} ms")
            m3.metric("Hybrid RRF", f"{counts['hybrid']}", f"{lat['hybrid_fusion']} ms")
            m4.metric("Rerank Top-K", f"{counts['hybrid_rerank']}", f"{lat['rerank']} ms")
            m5.metric("Tổng Unique", f"{counts['union_distinct']}", f"Tổng {lat['total_comparison']} ms")

            # Bảng so sánh tổng hợp
            st.markdown("### 📋 Bảng Thứ Hạng Tổng Hợp")
            df_rows = []
            for r in cmp_res["comparison_rows"]:
                b_r = f"#{r['bm25_rank']}" if r['bm25_rank'] else "-"
                s_r = f"#{r['semantic_rank']}" if r['semantic_rank'] else "-"
                h_r = f"#{r['hybrid_rank']}" if r['hybrid_rank'] else "-"
                re_r = f"#{r['rerank_rank']}" if r['rerank_rank'] else "-"
                chg = f"{r['rank_change']:+d}" if r['rank_change'] is not None else "-"
                modes_str = " + ".join(r["modes_present"])

                df_rows.append({
                    "Chunk ID": r["chunk_id"],
                    "BM25": b_r,
                    "Semantic": s_r,
                    "Hybrid RRF": h_r,
                    "Rerank": re_r,
                    "Rank Change": chg,
                    "Xuất hiện tại": modes_str,
                    "Nguồn": r["source"],
                    "Trang": f"{r['page_start']}-{r['page_end']}"
                })

            st.dataframe(pd.DataFrame(df_rows), use_container_width=True, hide_index=True)

            # 4 Cột hiển thị chi tiết
            st.markdown("### 🔍 So Sánh Chi Tiết Từng Nhánh (Side-by-Side)")
            c1, c2, c3, c4 = st.columns(4)

            with c1:
                st.markdown("#### 1. BM25 Sparse")
                b_items = [r for r in cmp_res["comparison_rows"] if r["bm25_rank"] is not None]
                b_items.sort(key=lambda x: x["bm25_rank"])
                for it in b_items:
                    st.info(f"**#{it['bm25_rank']}** Score: `{it['bm25_score']:.4f}`\n\n`{it['chunk_id']}`\n\n_{it['text'][:90]}..._")

            with c2:
                st.markdown("#### 2. Semantic Dense")
                s_items = [r for r in cmp_res["comparison_rows"] if r["semantic_rank"] is not None]
                s_items.sort(key=lambda x: x["semantic_rank"])
                for it in s_items:
                    st.info(f"**#{it['semantic_rank']}** Dist: `{it['semantic_distance']:.4f}`\n\n`{it['chunk_id']}`\n\n_{it['text'][:90]}..._")

            with c3:
                st.markdown("#### 3. Hybrid RRF")
                h_items = [r for r in cmp_res["comparison_rows"] if r["hybrid_rank"] is not None]
                h_items.sort(key=lambda x: x["hybrid_rank"])
                for it in h_items:
                    st.success(f"**#{it['hybrid_rank']}** RRF: `{it['rrf_score']:.6f}`\n\n`{it['chunk_id']}`\n\n_{it['text'][:90]}..._")

            with c4:
                st.markdown("#### 4. Cross-Encoder")
                r_items = [r for r in cmp_res["comparison_rows"] if r["rerank_rank"] is not None]
                r_items.sort(key=lambda x: x["rerank_rank"])
                for it in r_items:
                    chg_text = f"({it['rank_change']:+d})" if it['rank_change'] is not None else ""
                    st.success(f"**#{it['rerank_rank']}** Score: `{it['rerank_score']:.4f}` {chg_text}\n\n`{it['chunk_id']}`\n\n_{it['text'][:90]}..._")

    # ------------------------------------------------------------------------
    # TAB 3: PIPELINE TRACE
    # ------------------------------------------------------------------------
    with tab3:
        st.subheader("Phân Tích Pipeline Trace Nhiều Tầng")

        if "last_query_result" in st.session_state:
            trace = st.session_state["last_query_result"].get("trace", {})
            lat = trace.get("latency_ms", {})

            # Flow Cards
            st.markdown("### 🔄 Dòng Chảy Ứng Viên (Candidate Funnel)")
            f1, f2, f3, f4, f5 = st.columns(5)
            f1.metric("1. BM25 Candidates", f"{trace.get('bm25_candidates', 0)}")
            f2.metric("2. Semantic Candidates", f"{trace.get('semantic_candidates', 0)}")
            f3.metric("3. Union / Overlap", f"{trace.get('union', 0)} / {trace.get('overlap', 0)}")
            f4.metric("4. Reranked", f"{trace.get('reranked', 0)}")
            f5.metric("5. Accepted Evidence", f"{trace.get('accepted', 0)}")

            # Latency Breakdown
            st.markdown("### ⏱️ Phân Rã Thời Gian Thực Thi (Latency Breakdown)")
            lat_df = pd.DataFrame([
                {"Giai đoạn": "1. BM25 Sparse Search", "Thời gian (ms)": lat.get("bm25", 0.0)},
                {"Giai đoạn": "2. Semantic Dense Search", "Thời gian (ms)": lat.get("semantic", 0.0)},
                {"Giai đoạn": "3. RRF Fusion", "Thời gian (ms)": lat.get("fusion", 0.0)},
                {"Giai đoạn": "4. Cross-Encoder Rerank", "Thời gian (ms)": lat.get("rerank", 0.0)},
                {"Giai đoạn": "5. LLM Grounded Generation", "Thời gian (ms)": lat.get("generation", 0.0)},
                {"Giai đoạn": "👉 Tổng Pipeline", "Thời gian (ms)": lat.get("total", 0.0)},
            ])
            st.dataframe(lat_df, use_container_width=True, hide_index=True)

        else:
            st.info("💡 Hãy thực hiện một câu hỏi ở Tab 1 hoặc chạy So sánh ở Tab 2 để quan sát Pipeline Trace thực tế.")

        # Hướng dẫn hiểu các thang đo
        st.divider()
        st.markdown("### 📖 Hướng Dẫn Ý Nghĩa & Thang Đo Điểm Số")
        st.markdown(r"""
        - **BM25 Score** ($[0, +\infty)$): Điểm khớp từ khóa theo tần suất từ và độ dài văn bản. Điểm càng cao càng liên quan.
        - **Cosine Distance** ($[0, 2]$): Khoảng cách ngữ nghĩa vector trong ChromaDB. Giá trị **càng thấp càng gần nghĩa** ($0.0$ là hoàn toàn trùng khớp).
        - **RRF Score**: Điểm tổng hợp nghịch đảo thứ hạng $1/(k + \text{rank})$. Điểm càng cao thứ bậc càng cao.
        - **Cross-Encoder Score** ($\in [0, 1]$): Điểm chuẩn hóa Sigmoid của mô hình Cross-Encoder. **Lưu ý: Đây chỉ là điểm tương quan ngữ cảnh của mô hình, KHÔNG phải là xác suất chính xác tuyệt đối.**
        """)

    # ------------------------------------------------------------------------
    # TAB 4: ĐÁNH GIÁ (EVALUATION)
    # ------------------------------------------------------------------------
    with tab4:
        st.subheader("Báo Cáo Benchmark & Đánh Giá Định Lượng")

        # Cảnh báo bộ câu hỏi Gold
        st.warning("⚠️ **Lưu ý quan trọng**: Bộ câu hỏi benchmark (`eval/questions.json`) hiện có cờ `needs_human_review: true`, chưa được thẩm định bởi chuyên gia pháp lý. Các kết quả mang tính chất tham khảo thực nghiệm.")

        # Đọc báo cáo trong reports/
        reports = load_available_reports()

        if not reports:
            st.info("ℹ️ Chưa tìm thấy báo cáo benchmark nào trong thư mục `reports/`. Hãy chạy module `evaluate.py` để sinh báo cáo thực nghiệm.")
        else:
            selected_rep_path = st.selectbox("Chọn báo cáo benchmark để xem:", options=reports, format_func=lambda x: x.name)
            try:
                with open(selected_rep_path, "r", encoding="utf-8") as f:
                    rep_data = json.load(f)

                st.markdown(f"#### 📊 Dữ liệu báo cáo: `{selected_rep_path.name}`")
                st.json(rep_data)
            except Exception as e:
                st.error(f"Lỗi đọc file báo cáo: {e}")

        # Trình duyệt bộ câu hỏi đánh giá
        st.divider()
        st.markdown("### 🎯 Danh Sách Câu Hỏi Benchmark Chuẩn (`eval/questions.json`)")
        eval_questions = load_eval_questions_data()

        if eval_questions:
            q_rows = []
            for q in eval_questions:
                q_rows.append({
                    "ID": q.get("query_id"),
                    "Câu hỏi": q.get("question"),
                    "Scope": q.get("scope"),
                    "Chunks liên quan": ", ".join(q.get("relevant_chunk_ids", [])),
                    "Needs Human Review": str(q.get("needs_human_review"))
                })
            st.dataframe(pd.DataFrame(q_rows), use_container_width=True, hide_index=True)
        else:
            st.write("Không tìm thấy dữ liệu trong `eval/questions.json`.")


if __name__ == "__main__":
    main()
