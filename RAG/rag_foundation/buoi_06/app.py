import streamlit as st
import rag

# Set Page Config
st.set_page_config(
    page_title="RAG Workshop - Buổi 06",
    page_icon="🔍",
    layout="wide"
)

# Title & Subtitle
st.title("🔍 RAG Foundation Workshop - Buổi 06")
st.caption("Hệ thống Hỏi Đáp RAG tự động dựa trên tài liệu Ngân hàng Nhà nước Việt Nam")

# Sidebar
with st.sidebar:
    st.header("⚙️ Quản lý Hệ thống")
    
    # System Status
    try:
        stat = rag.status()
        st.metric(label="Số lượng Document", value=stat.get("documents", 0))
        st.metric(label="Số lượng Chunk", value=stat.get("chunks", 0))
    except Exception as e:
        st.error(f"Lỗi lấy trạng thái: {e}")
        
    st.divider()
    
    # Index Button
    if st.button("📥 Index Dữ Liệu Chunks", use_container_width=True, type="primary"):
        with st.spinner("Đang thực hiện index dữ liệu từ Buổi 05..."):
            res = rag.index()
            st.success(f"Đã index thành công {res.get('indexed_chunks', 0)} chunks!")
            st.rerun()
            
    st.divider()
    
    # Top-K Parameter
    k_param = st.slider("Số lượng Top-K Chunks:", min_value=1, max_value=10, value=3)

# Main UI Area
st.subheader("❓ Đặt câu hỏi truy vấn")
question = st.text_input("Nhập câu hỏi của bạn:", placeholder="Ví dụ: Cơ cấu lại thời hạn trả nợ quy định như thế nào?")

submit_btn = st.button("🚀 Gửi Câu Hỏi", type="primary")

if submit_btn or (question and len(question.strip()) > 0 and st.session_state.get("last_q") != question):
    if not question.strip():
        st.warning("Vui lòng nhập nội dung câu hỏi.")
    else:
        st.session_state["last_q"] = question
        with st.spinner("Đang truy vấn vector database và tổng hợp câu trả lời..."):
            answer, chunks = rag.ask_with_chunks(question, k=k_param)
            
        st.markdown("### 💡 Câu trả lời")
        st.info(answer)
        
        st.divider()
        
        st.markdown(f"### 📚 Danh sách Top-{len(chunks)} Chunks Truy Vấn Được")
        if not chunks:
            st.write("Không tìm thấy chunk phù hợp trong cơ sở dữ liệu.")
        else:
            for idx, chunk in enumerate(chunks, 1):
                title = f"Chunk #{idx} | Nguồn: {chunk.get('source', 'Unknown')} (Trang {chunk.get('page_start')}-{chunk.get('page_end')})"
                with st.expander(title, expanded=(idx == 1)):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.caption(f"**Chunk ID:** `{chunk.get('chunk_id')}`")
                    with col2:
                        st.caption(f"**Chiến lược:** `{chunk.get('strategy')}`")
                    with col3:
                        st.caption(f"**Trang:** `{chunk.get('page_start')} - {chunk.get('page_end')}`")
                    
                    st.markdown("**Nội dung đoạn văn (Text):**")
                    st.text_area(
                        label=f"Nội dung #{idx}",
                        value=chunk.get("text", ""),
                        height=140,
                        disabled=True,
                        label_visibility="collapsed"
                    )
