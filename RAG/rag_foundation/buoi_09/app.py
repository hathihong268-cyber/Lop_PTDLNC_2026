"""
Ứng dụng Web Streamlit - Buổi 09: Multi-Query & Parent–Child Retrieval Explorer.
Trực quan hóa Pipeline đa tầng:
Query fan-out → Hybrid per query → Cross-query RRF → Parent expansion → Parent rerank.

Được xây dựng với các nguyên tắc:
1. Giao diện trực quan phân cấp rõ nét (Query Fan-out cards, Query-Child Matrix, Parent-Child Tree).
2. Phân tách rõ ràng giữa Generation API calls và Embedding API calls.
3. Không tự động gọi API hay tải model khi render trang; chỉ thực thi khi người dùng bấm nút.
4. Trạng thái được lưu trữ bền vững trong st.session_state.
"""

import os
import sys
import json
import time
from pathlib import Path
import streamlit as st

# Thư mục gốc Buổi 09
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from hierarchical_rag import (
    load_buoi_09_config,
    get_hierarchical_status,
    build_hierarchy_registry,
    query_hierarchical_rag,
    compare_hierarchical_rag,
    MODES,
    HIERARCHY_STORAGE_DIR,
)
from ui_helpers import (
    build_query_child_matrix_data,
    format_parent_tree_summary,
    build_mode_comparison_rows,
    format_citation_display,
    map_ui_error_message,
)

# ==============================================================================
# CẤU HÌNH TRANG & GIAO DIỆN
# ==============================================================================

st.set_page_config(
    page_title="RAG Foundation — Buổi 09: Multi-query & Parent–Child Retrieval",
    page_icon="🌳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS tinh chỉnh visual hierarchy và card layout
st.markdown("""
<style>
    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1e3a8a;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #475569;
        margin-bottom: 1.2rem;
        font-weight: 500;
    }
    .pipeline-badge {
        display: inline-block;
        background: linear-gradient(135deg, #e0f2fe 0%, #dbeafe 100%);
        color: #1e40af;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 1rem;
        border: 1px solid #bfdbfe;
    }
    .query-card-q0 {
        background-color: #f0fdf4;
        border-left: 4px solid #16a34a;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .query-card-variant {
        background-color: #f8fafc;
        border-left: 4px solid #3b82f6;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .parent-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .rank-delta-up {
        color: #16a34a;
        font-weight: 700;
    }
    .rank-delta-down {
        color: #dc2626;
        font-weight: 700;
    }
    .rank-delta-same {
        color: #64748b;
        font-weight: 700;
    }
    .metric-pill {
        display: inline-block;
        background-color: #f1f5f9;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        margin-right: 6px;
        color: #334155;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# KHỞI TẠO SESSION STATE
# ==============================================================================

if "buoi09_last_result" not in st.session_state:
    st.session_state["buoi09_last_result"] = None

if "buoi09_last_comparison" not in st.session_state:
    st.session_state["buoi09_last_comparison"] = None

if "buoi09_question_input" not in st.session_state:
    st.session_state["buoi09_question_input"] = "Điều kiện vay vốn và các nhu cầu vốn không được cho vay được quy định thế nào?"


# ==============================================================================
# SIDEBAR - RUNTIME CONFIG & SYSTEM MONITOR
# ==============================================================================

def render_sidebar():
    with st.sidebar:
        st.markdown("### ⚙️ Cấu Hình Pipeline (Buổi 09)")

        config = load_buoi_09_config()
        hierarchy_stat = get_hierarchical_status()

        # 1. Chế độ truy xuất
        mode_options = ["multi_parent", "single_parent", "multi_flat", "single_flat"]
        selected_mode = st.selectbox(
            "Chế độ RAG (Mode):",
            options=mode_options,
            index=0,
            help="multi_parent: Fan-out retrieval kết hợp mở rộng Parent Document."
        )

        st.divider()

        # 2. Tham số mở rộng truy vấn & RRF
        st.markdown("##### 🔀 Tham Số Multi-Query & RRF")
        col_mq1, col_mq2 = st.columns(2)
        with col_mq1:
            multi_query_count = st.slider("Số Query sinh thêm:", min_value=1, max_value=5, value=config["multi_query_count"], help="MULTI_QUERY_COUNT")
        with col_mq2:
            per_query_cands = st.slider("Child mỗi Query:", min_value=5, max_value=30, value=config["per_query_candidates"], help="PER_QUERY_CANDIDATES")

        # 3. Tham số Parent Aggregation & Context Budget
        st.markdown("##### 🏛️ Tham Số Parent & Budget")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            parent_candidates_lim = st.slider("Parent Candidates:", min_value=3, max_value=20, value=config["parent_candidates"], help="PARENT_CANDIDATES")
        with col_p2:
            final_parent_k = st.slider("Final Top K Parent:", min_value=1, max_value=10, value=config["final_parent_top_k"], help="FINAL_PARENT_TOP_K")

        rerank_min_score = st.slider(
            "Ngưỡng Rerank Gate (Min Score):",
            min_value=0.0,
            max_value=1.0,
            value=float(config["rerank_min_score"]),
            step=0.05,
            help="RERANK_MIN_SCORE: Parent có điểm sigmoid thấp hơn sẽ bị loại."
        )

        st.divider()

        # 4. Trạng thái hệ thống & Model Cards
        st.markdown("##### 📦 Mô Hình & Tài Nguyên")
        st.caption(f"**Strategy**: `hierarchical` (Cố định)")
        st.caption(f"**Embedding**: `{config['embedding_model']}`")
        st.caption(f"**Generation**: `{config['generation_model']}`")
        st.caption(f"**Reranker**: `{config['reranker_model']}` ({config['rerank_device']})")

        # Trạng thái Gemini API Key (Bảo mật không lộ key)
        if config["has_api_key"]:
            st.success("🔑 Gemini API Key: `Đã kết nối (••••••••)`")
        else:
            st.warning("⚠️ Gemini API Key: `Chưa cấu hình`")

        # Trạng thái Hierarchy Store
        if hierarchy_stat["hierarchy_ready"]:
            st.success(
                f"🏛️ Hierarchy Store: `Sẵn sàng`\n\n"
                f"- **Văn bản (Sources)**: {hierarchy_stat['total_sources']}\n"
                f"- **Child Chunks**: {hierarchy_stat['total_children']}\n"
                f"- **Parent Documents**: {hierarchy_stat['total_parents']}\n"
                f"- **Ambiguous Cases**: {hierarchy_stat.get('warning_counts', {}).get('ambiguous_hierarchy_fallback', 0)}"
            )
        else:
            st.error("❌ Hierarchy Store: `Chưa sẵn sàng` (Cần build hierarchy)")

        st.divider()

        # 5. Thao tác Quản trị (Admin Actions)
        with st.expander("🛠️ Thao tác Quản Trị Hệ Thống"):
            st.warning("Các hành động dưới đây chỉ thực thi khi bạn xác nhận rõ ràng.")
            confirm_build = st.checkbox("Xác nhận xây dựng lại Hierarchy Registry")
            if st.button("🏗️ Xây dựng Hierarchy Registry", disabled=not confirm_build):
                with st.spinner("Đang phân giải cấu trúc 318 chunks thành Parent Documents..."):
                    try:
                        res = build_hierarchy_registry()
                        st.success(f"Đã tạo {res['parents_count']} Parent Documents từ {res['children_count']} Child Chunks!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi build hierarchy: {e}")

        # Trả về runtime config đã cập nhật
        runtime_config = dict(config)
        runtime_config["multi_query_count"] = multi_query_count
        runtime_config["per_query_candidates"] = per_query_cands
        runtime_config["parent_candidates"] = parent_candidates_lim
        runtime_config["final_parent_top_k"] = final_parent_k
        runtime_config["rerank_min_score"] = rerank_min_score

        return selected_mode, runtime_config, hierarchy_stat


# ==============================================================================
# MAIN APPLICATION BODY
# ==============================================================================

def main():
    # Tiêu đề & Subtitle theo đúng đặc tả
    st.markdown('<div class="main-header">RAG Foundation — Buổi 09: Multi-query & Parent–Child Retrieval</div>', unsafe_allow_html=True)
    st.markdown('<div class="pipeline-badge">🚀 Kiến trúc đa tầng: Query fan-out → Hybrid per query → Cross-query RRF → Parent expansion → Parent rerank</div>', unsafe_allow_html=True)

    # Render Sidebar và lấy runtime config
    selected_mode, runtime_config, hierarchy_stat = render_sidebar()

    # Tạo 5 Tabs chức năng
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💬 1. Hỏi Đáp Advanced RAG",
        "🔀 2. Query Fan-out & Matrix",
        "🏛️ 3. Parent–Child Explorer",
        "📊 4. So Sánh 4 Chế Độ",
        "📈 5. Đánh Giá & Benchmark"
    ])

    # ==========================================================================
    # TAB 1: ASK ADVANCED RAG
    # ==========================================================================
    with tab1:
        st.markdown("#### 💬 Truy Vấn Pháp Lý Với Pipeline Đa Tầng")
        
        # Mẫu câu hỏi gợi ý
        sample_questions = [
            "Điều kiện vay vốn và các nhu cầu vốn không được cho vay được quy định thế nào?",
            "Thời hạn cho vay và việc cơ cấu lại thời hạn trả nợ được quy định ra sao?",
            "Quy định về lãi suất cho vay và lãi suất quá hạn đối với khách hàng?",
            "Hồ sơ đề nghị vay vốn gồm những tài liệu, giấy tờ gì theo quy định của Ngân hàng Nhà nước?"
        ]
        
        col_q1, col_q2 = st.columns([3, 1])
        with col_q1:
            selected_sample = st.selectbox("Chọn câu hỏi mẫu nhanh:", ["-- Tự nhập câu hỏi --"] + sample_questions, index=1)
        with col_q2:
            current_mode = st.selectbox("Chế độ thực thi:", options=list(MODES), index=list(MODES).index(selected_mode), key="tab1_mode_select")

        default_q = selected_sample if selected_sample != "-- Tự nhập câu hỏi --" else st.session_state["buoi09_question_input"]
        question_text = st.text_area(
            "Câu hỏi pháp lý của bạn:",
            value=default_q,
            height=90,
            placeholder="Nhập câu hỏi liên quan đến Thông tư 39/2016/TT-NHNN, 06/2023/TT-NHNN, 02/2023/TT-NHNN..."
        )

        col_btn, col_info = st.columns([1, 3])
        with col_btn:
            run_query = st.button("🚀 Thực Thi Truy Xuất & Trả Lời", type="primary")

        if run_query:
            if not question_text.strip():
                st.warning("Vui lòng nhập câu hỏi trước khi thực thi.")
            elif not hierarchy_stat["hierarchy_ready"]:
                err = map_ui_error_message("hierarchy_not_ready")
                st.error(f"**{err['title']}**: {err['message']}")
            else:
                with st.spinner(f"Đang thực thi Pipeline RAG ({current_mode})..."):
                    try:
                        res = query_hierarchical_rag(
                            question=question_text.strip(),
                            mode=current_mode,
                            config=runtime_config
                        )
                        st.session_state["buoi09_last_result"] = res
                    except Exception as e:
                        st.error(f"Lỗi thực thi Pipeline: {e}")

        # Hiển thị kết quả từ session_state
        last_res = st.session_state.get("buoi09_last_result")
        if last_res:
            t = last_res["trace"]
            st.divider()

            # Thanh đo lường thời gian & API calls
            st.markdown("##### ⏱️ Phân Tích Hiệu Năng & Ngân Sách Cuộc Gọi API")
            lat = t.get("stage_latencies_ms", {})
            api_c = t.get("api_call_counts", {})
            
            col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
            with col_m1:
                st.metric("Tổng Thời Gian", f"{lat.get('total', 0.0):.1f} ms")
            with col_m2:
                st.metric("Rerank Latency", f"{lat.get('rerank', 0.0):.1f} ms")
            with col_m3:
                st.metric("Gen Latency", f"{lat.get('generation', 0.0):.1f} ms")
            with col_m4:
                st.metric("Generation Calls", f"{api_c.get('generation_calls', 0)} calls", help="Tối đa 2 calls trong multi_parent")
            with col_m5:
                st.metric("Embedding Calls", f"{api_c.get('embedding_calls', 0)} calls", help="Được đếm riêng biệt")

            # Cảnh báo lỗi UX thân thiện
            if last_res["status"] != "ready":
                err_ui = map_ui_error_message(last_res["status"])
                st.info(f"💡 **{err_ui['title']}**: {err_ui['message']}")

            # Hiển thị câu trả lời tổng hợp
            st.markdown("##### 📝 Câu Trả Lời Pháp Lý (Answer):")
            st.markdown(last_res["answer"])

            # Danh mục trích dẫn Citations
            st.markdown("##### 🏷️ Danh Mục Trích Dẫn Pháp Lý (Citations):")
            citations = last_res.get("citations", [])
            if citations:
                for cit in citations:
                    with st.container(border=True):
                        st.markdown(f"**[{cit['evidence_id']}] {format_citation_display(cit)}**")
                        st.caption(
                            f"• **Parent ID**: `{cit.get('parent_id') or 'N/A'}` | "
                            f"• **Anchor Child**: `{cit.get('anchor_child_id') or 'N/A'}` | "
                            f"• **Rerank Score**: `{cit.get('parent_rerank_score', 0.0):.4f}`"
                        )
                        if cit.get("ambiguous"):
                            st.warning("⚠️ Trích dẫn này thuộc văn bản có cấu trúc Ambiguous (cần người dùng kiểm tra kỹ).")
            else:
                st.caption("_(Không có trích dẫn nào được chấp nhận vượt qua Gate)_")

            # Cảnh báo ghi nhận trong pipeline
            if last_res.get("warnings"):
                with st.expander(f"⚠️ Cảnh Báo Ghi Nhận ({len(last_res['warnings'])} mục)"):
                    for w in last_res["warnings"]:
                        st.write(f"- {w}")

    # ==========================================================================
    # TAB 2: QUERY FAN-OUT & MATRIX
    # ==========================================================================
    with tab2:
        st.markdown("#### 🔀 Mở Rộng Truy Vấn (Query Fan-out) & Ma Trận Query–Child")
        last_res = st.session_state.get("buoi09_last_result")

        if not last_res or not last_res.get("query_set"):
            st.info("Chưa có dữ liệu Multi-Query. Hãy thực thi một câu hỏi ở chế độ `multi_parent` hoặc `multi_flat` tại Tab 1.")
        else:
            q_set = last_res["query_set"]
            fused_children = last_res.get("child_hits", [])

            st.markdown("##### 📋 Danh Sách Query Set (Fan-out Variants):")
            for q in q_set.get("queries", []):
                is_q0 = (q.get("origin") == "original")
                card_class = "query-card-q0" if is_q0 else "query-card-variant"
                badge_title = "🌟 [Q0] CÂU HỎI GỐC (Original Intent)" if is_q0 else f"🔹 [{q.get('query_id')}] Biến Thể ({q.get('focus')})"
                
                st.markdown(f"""
                <div class="{card_class}">
                    <strong>{badge_title}</strong><br/>
                    <span style="font-size: 1.05rem;">"{q.get('text')}"</span>
                </div>
                """, unsafe_allow_html=True)

            st.divider()

            # Ma trận Query - Child
            st.markdown("##### 📊 Ma Trận Ánh Xạ Query ↔ Child Chunks (Cross-Query Coverage Matrix)")
            st.caption("Bảng hiển thị thứ hạng của từng Child chunk trong các nhánh query, số lượng query hỗ trợ và điểm hợp nhất MQ-RRF.")
            
            matrix_data = build_query_child_matrix_data(fused_children, q_set)
            if matrix_data:
                st.dataframe(matrix_data, use_container_width=True)
            else:
                st.write("Không có dữ liệu Child Chunks.")

    # ==========================================================================
    # TAB 3: PARENT–CHILD EXPLORER
    # ==========================================================================
    with tab3:
        st.markdown("#### 🏛️ Cây Phân Cấp Parent–Child & Biến Động Thứ Hạng (Rank Movement)")
        last_res = st.session_state.get("buoi09_last_result")

        if not last_res or not last_res.get("parent_candidates"):
            st.info("Chưa có dữ liệu Parent Documents. Hãy thực thi một câu hỏi ở chế độ `single_parent` hoặc `multi_parent` tại Tab 1.")
        else:
            parents = last_res.get("parent_candidates", [])
            fused_children = last_res.get("child_hits", [])
            
            # Gom nhóm children theo parent_id
            children_by_parent = {}
            for c in fused_children:
                pid = c.get("parent_id")
                if pid:
                    children_by_parent.setdefault(pid, []).append(c)

            st.markdown(f"**Tìm thấy {len(parents)} Parent Candidates (Tổng hợp từ {len(fused_children)} Fused Child Hits):**")

            for p_idx, p in enumerate(parents, start=1):
                summary = format_parent_tree_summary(p, children_by_parent.get(p.get("parent_id"), []))
                
                # Delta Rank styling
                delta = summary["rank_delta"]
                if delta > 0:
                    delta_badge = f'<span class="rank-delta-up">▲ +{delta} (Thăng hạng)</span>'
                elif delta < 0:
                    delta_badge = f'<span class="rank-delta-down">▼ {delta} (Tụt hạng)</span>'
                else:
                    delta_badge = '<span class="rank-delta-same">■ 0 (Giữ nguyên)</span>'

                score_str = f"MQ-RRF: {summary['parent_rrf_score']:.4f}"
                if summary["parent_rerank_score"] is not None:
                    score_str += f" → Rerank: {summary['parent_rerank_score']:.4f}"

                expander_title = f"Parent #{summary['new_rank']}: {summary['parent_id']} ({summary['law_title']}) | {score_str} | Rank Movement: {delta_badge}"
                
                with st.expander(expander_title, expanded=(p_idx <= 2)):
                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.markdown(f"• **Nguồn & Trang**: `{summary['source']}` ({summary['pages']})")
                        st.markdown(f"• **Kích thước**: `{summary['char_count']} ký tự`")
                        st.markdown(f"• **Anchor Child**: `{summary['anchor_child_id']}`")
                    with col_info2:
                        st.markdown(f"• **Thứ hạng gốc → sau Rerank**: `#{summary['old_rank']}` → `#{summary['new_rank']}`")
                        st.markdown(f"• **Số Query hỗ trợ**: `{len(summary['support_queries'])}` ({', '.join(summary['support_queries'])})")
                        if summary["ambiguous"]:
                            st.warning("⚠️ Văn bản thuộc diện Ambiguous Hierarchy.")

                    # Danh sách Supporting Children
                    st.markdown("###### 📎 Các Child Chunks Hỗ Trợ (Supporting Children):")
                    for c in summary["children"]:
                        anchor_tag = "🌟 `[Anchor Child]`" if c["is_anchor"] else ""
                        scored_tag = "🎯 `[Scoring Child]`" if c["is_scored"] else ""
                        st.markdown(f"- **`{c['child_id']}`** (MQ-Rank: `#{c['multi_query_rank']}`) {anchor_tag} {scored_tag}")
                        if c["snippet"]:
                            st.caption(f"  _\"{c['snippet']}\"_")

                    # Xem toàn văn Parent Document
                    with st.expander("📄 Xem toàn văn nội dung Parent Document"):
                        st.text_area("Toàn văn Parent Document:", value=summary["full_text"], height=200, disabled=True, key=f"parent_txt_{summary['parent_id']}")

    # ==========================================================================
    # TAB 4: MODE COMPARISON (RETRIEVAL ONLY)
    # ==========================================================================
    with tab4:
        st.markdown("#### 📊 So Sánh Đối Chuẩn 4 Chế Độ RAG (Retrieval & Rerank Only)")
        st.caption("Chạy cùng một câu hỏi qua 4 chế độ ở tầng Retrieval & Reranking mà TUYỆT ĐỐI KHÔNG gọi Gemini Generation API.")

        comp_q = st.text_input(
            "Câu hỏi so sánh đối chuẩn:",
            value=st.session_state["buoi09_question_input"],
            key="comp_question_input"
        )

        if st.button("⚡ Chạy So Sánh 4 Chế Độ", type="primary"):
            if not comp_q.strip():
                st.warning("Vui lòng nhập câu hỏi.")
            else:
                with st.spinner("Đang thực thi so sánh đối chuẩn qua 4 chế độ..."):
                    try:
                        comp_res = compare_hierarchical_rag(
                            question=comp_q.strip(),
                            config=runtime_config
                        )
                        st.session_state["buoi09_last_comparison"] = comp_res
                    except Exception as e:
                        st.error(f"Lỗi so sánh chế độ: {e}")

        last_comp = st.session_state.get("buoi09_last_comparison")
        if last_comp:
            st.divider()
            st.markdown("##### 📋 Bảng Tổng Hợp Chỉ Số 4 Chế Độ:")
            comp_rows = build_mode_comparison_rows(last_comp)
            st.dataframe(comp_rows, use_container_width=True)

            st.info("ℹ️ **Lưu ý nguyên tắc kỹ thuật**: Hệ thống không tự ý tuyên bố mode nào 'chiến thắng' nếu chưa đối chiếu với Ground Truth Gold Labels trong tập kiểm thử chuẩn hóa.")

    # ==========================================================================
    # TAB 5: EVALUATION & BENCHMARK
    # ==========================================================================
    with tab5:
        st.markdown("#### 📈 Báo Cáo Đánh Giá Chất Lượng & Benchmark")
        
        report_dir = BASE_DIR / "reports"
        report_files = sorted(list(report_dir.glob("eval_report_*.json")), reverse=True)

        if report_files:
            latest_file = report_files[0]
            st.success(f"Đã nạp báo cáo đánh giá mới nhất: `{latest_file.name}`")
            try:
                with open(latest_file, "r", encoding="utf-8") as fp:
                    eval_data = json.load(fp)

                col_e1, col_e2, col_e3, col_e4 = st.columns(4)
                with col_e1:
                    st.metric("Child Recall@K", f"{eval_data.get('child_recall_at_k', 0.0):.2%}")
                with col_e2:
                    st.metric("Parent Recall@K", f"{eval_data.get('parent_recall_at_k', 0.0):.2%}")
                with col_e3:
                    st.metric("MRR@K", f"{eval_data.get('mrr_at_k', 0.0):.4f}")
                with col_e4:
                    st.metric("nDCG@K", f"{eval_data.get('ndcg_at_k', 0.0):.4f}")

                st.divider()
                st.json(eval_data)
            except Exception as e:
                st.error(f"Không thể đọc file báo cáo: {e}")
        else:
            st.info(
                "Chưa có file báo cáo đánh giá trong thư mục `reports/`.\n\n"
                "Bạn có thể chạy script đánh giá offline qua CLI:\n"
                "```powershell\n"
                ".\\rag_foundation\\buoi_05\\.venv\\Scripts\\python.exe .\\rag_foundation\\buoi_09\\evaluate.py\n"
                "```"
            )


if __name__ == "__main__":
    main()
