"""
Ứng dụng Streamlit - Buổi 07: Hoàn thiện RAG Pipeline với AI Agent.

Sử dụng trực tiếp các hàm public từ module rag.py (không duplicate logic RAG).
"""

from pathlib import Path
import sys
import streamlit as st

# Thư mục gốc Buổi 07 (đường dẫn tuyệt đối động)
BASE_DIR = Path(__file__).resolve().parent

# Import các hàm và hằng số từ rag.py
from rag import (
    load_config,
    get_status,
    index_chunks,
    query_rag,
    ALLOWED_STRATEGIES
)

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="RAG Foundation - Buổi 07",
    page_icon="🔍",
    layout="wide"
)

# Nạp cấu hình từ .env
try:
    config = load_config()
except Exception as e:
    st.error(f"Lỗi nạp cấu hình hệ thống từ file .env: {e}")
    st.stop()


# ============================================================================
# 1. SIDEBAR: CẤU HÌNH & TRẠNG THÁI HỆ THỐNG
# ============================================================================

st.sidebar.title("⚙️ Cấu Hình & Trạng Thái")

# Chọn strategy
strategy_list = sorted(list(ALLOWED_STRATEGIES))
default_index = strategy_list.index("hierarchical") if "hierarchical" in strategy_list else 0
selected_strategy = st.sidebar.selectbox(
    "Chiến lược Chunking (Strategy):",
    options=strategy_list,
    index=default_index,
    help="Chọn chiến lược phân mảnh dữ liệu cần tra cứu hoặc index."
)

# Chọn top-k
selected_top_k = st.sidebar.slider(
    "Số lượng kết quả truy xuất (Top-K):",
    min_value=1,
    max_value=10,
    value=config.get("top_k", 5),
    help="Số lượng chunks liên quan nhất sẽ được lấy từ ChromaDB."
)

st.sidebar.markdown("---")
st.sidebar.subheader("📌 Trạng Thái Collection")

# Lấy trạng thái read-only
try:
    status_info = get_status(strategy=selected_strategy, config=config)
except Exception as e:
    st.sidebar.error(f"Lỗi đọc trạng thái: {e}")
    status_info = {
        "has_api_key": False,
        "embedding_model": config.get("embedding_model", ""),
        "embedding_dim": config.get("embedding_dim", 768),
        "collection_name": "N/A",
        "collection_exists": False,
        "record_count": 0,
    }

api_key_status = "🟢 Có" if status_info.get("has_api_key") else "🔴 Thiếu"
st.sidebar.markdown(f"**API Key:** {api_key_status}")
st.sidebar.markdown(f"**Embedding Model:** `{status_info.get('embedding_model')}`")
st.sidebar.markdown(f"**Embedding Dim:** `{status_info.get('embedding_dim')}`")
st.sidebar.markdown(f"**Generation Model:** `{config.get('generation_model')}`")
st.sidebar.markdown(f"**Max Distance (Threshold):** `{config.get('max_distance')}`")
st.sidebar.markdown(f"**Collection Name:** `{status_info.get('collection_name')}`")

if status_info.get("collection_exists"):
    st.sidebar.success(f"Đã tồn tại ({status_info.get('record_count')} chunks)")
else:
    st.sidebar.warning("Chưa được tạo (0 chunks)")


# ============================================================================
# 2. KHỞI TẠO SESSION STATE
# ============================================================================

if "last_index_result" not in st.session_state:
    st.session_state["last_index_result"] = None

if "last_query_result" not in st.session_state:
    st.session_state["last_query_result"] = None


# ============================================================================
# 3. GIAO DIỆN CHÍNH
# ============================================================================

st.title("🔍 RAG Foundation — Buổi 07")
st.markdown(
    "Hệ thống hỏi đáp tài liệu tài chính - ngân hàng với quy trình **Grounding** "
    "và **Citation Mapping** từ metadata chuẩn xác."
)

tab_qa, tab_index = st.tabs(["💬 Hỏi Đáp Tài Liệu", "📥 Quản Lý Index"])


# --- TAB 1: HỎI ĐÁP TÀI LIỆU ---
with tab_qa:
    st.subheader("Đặt câu hỏi tra cứu")

    user_question = st.text_area(
        "Nội dung câu hỏi:",
        height=100,
        placeholder="Ví dụ: Tổ chức tín dụng được cơ cấu lại thời hạn trả nợ trong những trường hợp nào?",
        help="Nhập câu hỏi bằng tiếng Việt để tra cứu thông tin trong các văn bản quy định."
    )

    can_query = True
    query_block_reason = ""

    if not user_question.strip():
        can_query = False
    elif not status_info.get("has_api_key"):
        can_query = False
        query_block_reason = "Vui lòng cấu hình GEMINI_API_KEY trong file .env trước khi hỏi đáp."
    elif not status_info.get("collection_exists") or status_info.get("record_count") == 0:
        can_query = False
        query_block_reason = f"Collection '{status_info.get('collection_name')}' chưa có dữ liệu. Hãy chuyển sang tab 'Quản Lý Index' để nạp dữ liệu trước."

    if query_block_reason:
        st.info(f"ℹ️ {query_block_reason}")

    if st.button("🚀 Gửi câu hỏi", disabled=not can_query, type="primary"):
        with st.spinner("Đang truy xuất dữ liệu và tạo câu trả lời..."):
            try:
                res = query_rag(
                    question=user_question,
                    top_k=selected_top_k,
                    strategy=selected_strategy,
                    config=config
                )
                st.session_state["last_query_result"] = res
            except Exception as e:
                err_clean = str(e)
                if config.get("api_key") and config["api_key"] in err_clean:
                    err_clean = err_clean.replace(config["api_key"], "***")
                st.error(f"Lỗi trong quá trình xử lý câu hỏi: {err_clean}")

    # Hiển thị kết quả hỏi đáp gần nhất
    q_res = st.session_state.get("last_query_result")
    if q_res:
        st.markdown("---")
        status = q_res.get("status")

        if status == "answered":
            st.success("✅ Đã tạo câu trả lời với đầy đủ căn cứ trích dẫn")
            st.markdown("### 💡 Câu trả lời")
            st.markdown(q_res.get("answer", ""))

            # Hiển thị citations
            citations = q_res.get("citations", [])
            if citations:
                st.markdown("#### 📚 Trích dẫn nguồn tài liệu")
                for idx, cit in enumerate(citations, start=1):
                    p_str = f"trang {cit['page_start']}" if cit['page_start'] == cit['page_end'] else f"trang {cit['page_start']}-{cit['page_end']}"
                    st.markdown(f"**[{idx}]** `{cit['source']}` — *{p_str}* (Chunk: `{cit['chunk_id']}`)")

        elif status == "insufficient_evidence":
            st.warning("⚠️ " + q_res.get("answer", "Không tìm thấy đủ thông tin liên quan trong tài liệu đã cung cấp."))
            st.caption("Các đoạn dữ liệu truy xuất được đều vượt ngưỡng khoảng cách tin cậy (Confidence Gate), hệ thống chủ động ngắt tiến trình sinh câu trả lời để chống bịa đặt.")

        elif status == "retrieval_only":
            st.warning("⚠️ " + q_res.get("answer", "Đã truy xuất được nguồn nhưng chưa thể tạo câu trả lời tổng hợp."))
            st.caption("Đã tìm thấy bằng chứng liên quan nhưng tiến trình gọi Gemini Generation API gặp sự cố hoặc trả về nội dung rỗng.")

        # Cảnh báo nếu có
        warnings = q_res.get("warnings", [])
        if warnings:
            st.markdown("---")
            with st.expander("⚠️ Cảnh báo hệ thống", expanded=False):
                for w in warnings:
                    st.write(f"- {w}")

        # Hiển thị danh sách evidence
        st.markdown("---")
        st.subheader("📑 Nguồn tham khảo (Evidence)")
        evidences = q_res.get("evidence", [])

        if not evidences:
            st.info("Chưa có bằng chứng truy xuất.")
        else:
            st.caption(
                "Ghi chú: Chỉ số Khoảng cách (Distance) thể hiện độ lệch cosine. "
                "Giá trị càng nhỏ chứng tỏ nội dung càng gần với câu hỏi. "
                f"Ngưỡng chấp nhận hiện tại là <= {config.get('max_distance')}."
            )

            for ev in evidences:
                is_acc = ev.get("accepted", False)
                status_icon = "🟢 ĐẠT" if is_acc else "🔴 VƯỢT NGƯỠNG (BỎ QUA)"
                p_start = ev.get("page_start", 1)
                p_end = ev.get("page_end", 1)
                page_label = f"tr. {p_start}" if p_start == p_end else f"tr. {p_start}-{p_end}"

                summary_header = f"{ev.get('source')} – {page_label} – {ev.get('chunk_id')} | [{status_icon}] (dist: {ev.get('distance')})"

                with st.expander(summary_header, expanded=is_acc):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Evidence ID:** `{ev.get('evidence_id')}`")
                        st.markdown(f"**File nguồn:** `{ev.get('source')}`")
                        st.markdown(f"**Trang:** `{page_label}`")
                    with col2:
                        st.markdown(f"**Chunk ID:** `{ev.get('chunk_id')}`")
                        st.markdown(f"**Khoảng cách:** `{ev.get('distance')}`")
                        st.markdown(f"**Trạng thái Gate:** `{status_icon}`")

                    st.markdown("**Nội dung đoạn văn:**")
                    st.text_area(
                        label=f"Content_{ev.get('evidence_id')}",
                        value=ev.get("text", ""),
                        height=120,
                        disabled=True,
                        label_visibility="collapsed"
                    )


# --- TAB 2: QUẢN LÝ INDEX ---
with tab_index:
    st.subheader(f"Quản lý Index cho Strategy: `{selected_strategy}`")
    st.markdown(
        "Nạp các chunks đã chuẩn bị từ Buổi 05 vào ChromaDB Persistent Storage. "
        "Quá trình này sẽ gọi Gemini Embedding API để tạo vector 768 chiều."
    )

    reset_col = st.checkbox(
        "Reset collection trước khi index",
        value=False,
        help="Nếu chọn, collection đích cũ sẽ được xóa và tạo lại mới sau khi toàn bộ embedding đã được tạo và kiểm tra thành công."
    )

    if not status_info.get("has_api_key"):
        st.warning("⚠️ Chưa cấu hình GEMINI_API_KEY trong file .env. Không thể thực hiện index dữ liệu.")

    if st.button("📥 Bắt đầu Index dữ liệu", disabled=not status_info.get("has_api_key"), type="primary"):
        with st.spinner(f"Đang nạp dữ liệu và tạo embeddings cho strategy '{selected_strategy}'..."):
            try:
                index_res = index_chunks(
                    strategy=selected_strategy,
                    reset=reset_col,
                    config=config
                )
                st.session_state["last_index_result"] = index_res
                st.success(f"✅ Index hoàn tất cho strategy '{selected_strategy}'!")
                st.rerun()
            except Exception as e:
                err_msg = str(e)
                if config.get("api_key") and config["api_key"] in err_msg:
                    err_msg = err_msg.replace(config["api_key"], "***")
                st.error(f"Lỗi khi index dữ liệu: {err_msg}")

    idx_res = st.session_state.get("last_index_result")
    if idx_res:
        st.markdown("---")
        st.markdown("### 📊 Kết quả Index gần nhất")
        st.markdown(f"- **Strategy:** `{idx_res.get('strategy')}`")
        st.markdown(f"- **Collection Name:** `{idx_res.get('collection_name')}`")
        st.markdown(f"- **Chế độ Reset:** `{'Có' if idx_res.get('reset') else 'Không'}`")
        st.markdown(f"- **Số Chunks Đã Nạp Lượt Này:** `{idx_res.get('chunks_indexed')}`")
        st.markdown(f"- **Tổng Chunks Hiện Có Trong Collection:** `{idx_res.get('total_in_collection')}`")
