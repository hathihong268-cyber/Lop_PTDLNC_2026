"""
Module helper UI cho Streamlit App Buổi 09:
Cung cấp các hàm thuần Python (100% offline, không phụ thuộc trình duyệt hay mạng)
để định dạng ma trận Query-Child, cây phân cấp Parent-Child, bảng so sánh chế độ và xử lý thông báo lỗi UX.
"""

from typing import Any


def build_query_child_matrix_data(
    fused_children: list[dict],
    query_set: dict
) -> list[dict[str, Any]]:
    """
    Xây dựng dữ liệu ma trận Query - Child:
    - Hàng là từng Child hit.
    - Cột gồm thông tin Child, điểm MQ-RRF, số query hỗ trợ và thứ hạng trong từng query Q0..Qn.
    """
    if not fused_children:
        return []

    queries = query_set.get("queries", []) if query_set else []
    query_ids = [q.get("query_id", f"Q{i}") for i, q in enumerate(queries)]
    if not query_ids:
        query_ids = ["Q0"]

    matrix_rows = []
    for c in fused_children:
        cid = c.get("child_id") or c.get("chunk_id", "N/A")
        p_ranks = c.get("per_query_ranks", {})
        supp_queries = c.get("support_query_ids", [])
        
        row = {
            "MQ_Rank": c.get("multi_query_rank", "?"),
            "Child_ID": cid,
            "Source": c.get("source", "N/A"),
            "Pages": f"tr. {c.get('page_start', '?')}-{c.get('page_end', '?')}",
            "MQ_RRF_Score": round(float(c.get("multi_query_rrf_score", 0.0)), 6),
            "Support_Count": len(supp_queries),
            "Support_Queries": ", ".join(supp_queries),
        }

        for q_id in query_ids:
            if q_id in p_ranks:
                row[q_id] = f"#{p_ranks[q_id]}"
            elif q_id in supp_queries:
                row[q_id] = "✓"
            else:
                row[q_id] = "—"

        matrix_rows.append(row)

    return matrix_rows


def format_parent_tree_summary(
    parent_candidate: dict,
    grouped_children: list[dict] = None
) -> dict[str, Any]:
    """
    Chuẩn hóa thông tin hiển thị cây phân cấp Parent Document:
    - Trích xuất tiêu đề điều khoản, phạm vi trang và nguồn tài liệu.
    - Tính toán độ lệch thứ hạng (Rank Movement: parent_rank -> rerank_rank).
    - Tách biệt Anchor Child và Supporting Children.
    """
    p = parent_candidate
    st = p.get("structural_path", {})
    law_str = st.get("law") or p.get("source", "N/A")
    art_str = f"Điều {st.get('article')}" if st.get("article") else "Văn bản mở đầu"
    
    old_rank = p.get("parent_rank", 1)
    new_rank = p.get("parent_rerank_rank", old_rank)
    rank_delta = p.get("parent_rank_change", old_rank - new_rank)

    anchor_id = p.get("anchor_child_id", "")
    scoring_ids = set(p.get("scoring_child_ids", []))
    
    children_info = []
    if grouped_children:
        for c in grouped_children:
            cid = c.get("child_id") or c.get("chunk_id", "")
            is_anchor = (cid == anchor_id)
            is_scored = (cid in scoring_ids)
            children_info.append({
                "child_id": cid,
                "is_anchor": is_anchor,
                "is_scored": is_scored,
                "multi_query_rank": c.get("multi_query_rank", "?"),
                "support_queries": c.get("support_query_ids", []),
                "snippet": (c.get("text", "")[:120] + "...") if c.get("text") else ""
            })

    return {
        "parent_id": p.get("parent_id", "N/A"),
        "law_title": f"{law_str} - {art_str}",
        "source": p.get("source", "N/A"),
        "pages": f"tr. {p.get('page_start', 1)}-{p.get('page_end', 1)}",
        "char_count": p.get("char_count", len(p.get("text", ""))),
        "parent_rrf_score": round(float(p.get("parent_rrf_score", 0.0)), 6),
        "parent_rerank_score": round(float(p.get("parent_rerank_score", 0.0)), 4) if "parent_rerank_score" in p else None,
        "old_rank": old_rank,
        "new_rank": new_rank,
        "rank_delta": rank_delta,
        "rank_delta_str": f"+{rank_delta}" if rank_delta > 0 else str(rank_delta),
        "anchor_child_id": anchor_id,
        "supporting_child_count": len(p.get("supporting_child_ids", [])),
        "support_queries": p.get("support_query_ids", []),
        "ambiguous": p.get("ambiguous", False),
        "warnings": p.get("warnings", []),
        "children": children_info,
        "full_text": p.get("text", "")
    }


def build_mode_comparison_rows(comparison_data: dict) -> list[dict[str, Any]]:
    """
    Định dạng bảng so sánh đối chuẩn 4 chế độ:
    - single_flat, multi_flat, single_parent, multi_parent.
    - Hiển thị đầy đủ thông tin: ID, Score, Law, Accepted count, Context chars, Latency, API calls.
    """
    modes_data = comparison_data.get("modes", {})
    mode_order = ["single_flat", "multi_flat", "single_parent", "multi_parent"]
    
    rows = []
    for m in mode_order:
        if m not in modes_data:
            continue
        info = modes_data[m]
        is_parent = "parent" in m
        is_multi = "multi" in m
        
        rows.append({
            "Mode": m,
            "Unit_Type": "Parent Document" if is_parent else "Child Chunk",
            "Top_1_ID": info.get("top1_id", "N/A"),
            "Top_1_Score": info.get("top1_score", 0.0),
            "Top_1_Law": info.get("top1_law", "N/A"),
            "Top_1_Source": info.get("top1_source", "N/A"),
            "Accepted_Count": info.get("accepted_evidence_count", 0),
            "Candidates_Count": info.get("candidate_count", 0),
            "Latency_ms": info.get("latency_ms", 0.0),
            "Generation_Calls": 0,  # Lệnh so sánh không gọi answer generation
            "Embedding_Calls": 4 if is_multi else 1,
            "Status": info.get("status", "ready")
        })

    return rows


def format_citation_display(cit: dict) -> str:
    """
    Định dạng chuỗi hiển thị trích dẫn pháp lý rõ ràng:
    [Nguồn: TT_39_2016_NHNN.pdf, Điều 8, tr. 1-18, parent: TT_39_2016_NHNN:d08:w01]
    """
    st = cit.get("structural_path", {})
    law_str = st.get("law") or cit.get("source", "N/A")
    art_str = f"Điều {st.get('article')}" if st.get("article") else "Văn bản mở đầu"
    p_start = cit.get("page_start", 1)
    p_end = cit.get("page_end", 1)
    page_str = f"tr. {p_start}" if p_start == p_end else f"tr. {p_start}-{p_end}"

    if cit.get("parent_id"):
        return f"[Nguồn: {law_str}, {art_str}, {page_str}, parent: {cit['parent_id']}]"
    elif cit.get("chunk_id"):
        return f"[Nguồn: {law_str}, {art_str}, {page_str}, chunk: {cit['chunk_id']}]"
    return f"[Nguồn: {law_str}, {art_str}, {page_str}]"


def map_ui_error_message(status_code: str, raw_error: str = "") -> dict[str, str]:
    """
    Ánh xạ mã trạng thái lỗi sang thông báo hướng dẫn người dùng thân thiện (không lộ API key/stack trace).
    """
    error_mapping = {
        "hierarchy_not_ready": {
            "title": "Chưa xây dựng Hierarchy Registry",
            "message": "Hệ thống chưa tìm thấy dữ liệu Hierarchy Store. Vui lòng bấm nút 'Xây dựng lại Hierarchy Registry' tại Sidebar hoặc chạy lệnh CLI 'build-hierarchy'.",
            "type": "error"
        },
        "collection_not_ready": {
            "title": "Chroma Collection chưa sẵn sàng",
            "message": "Chưa tìm thấy dữ liệu vector trong ChromaDB. Vui lòng chạy lệnh 'prepare-semantic --strategy hierarchical' để lập chỉ mục.",
            "type": "warning"
        },
        "query_generation_unavailable": {
            "title": "Không thể sinh câu hỏi mở rộng",
            "message": "GEMINI_API_KEY chưa được cấu hình hoặc API không phản hồi. Hệ thống đã tự động chuyển về câu hỏi gốc Q0.",
            "type": "warning"
        },
        "multi_query_partial": {
            "title": "Chế độ mở rộng đa biến thể bị gián đoạn",
            "message": "Một số biến thể query bị lỗi, hệ thống đã nỗ lực truy xuất bằng các query hợp lệ còn lại và Q0.",
            "type": "warning"
        },
        "reranker_unavailable": {
            "title": "Cross-Encoder Reranker không khả dụng",
            "message": "Không thể tải hoặc nạp mô hình Reranker. Vui lòng kiểm tra dung lượng ổ đĩa tại storage/huggingface hoặc kết nối mạng.",
            "type": "error"
        },
        "insufficient_evidence": {
            "title": "Không đủ bằng chứng đạt ngưỡng",
            "message": "Tất cả các tài liệu truy xuất được đều có điểm Rerank thấp hơn ngưỡng quy định (RERANK_MIN_SCORE). Hệ thống từ chối suy diễn pháp lý.",
            "type": "info"
        },
        "generation_error": {
            "title": "Lỗi sinh câu trả lời",
            "message": "Không thể kết nối với Gemini Generation API để tổng hợp câu trả lời. Bằng chứng pháp lý vẫn được bảo toàn.",
            "type": "error"
        }
    }

    if status_code in error_mapping:
        return error_mapping[status_code]
    
    return {
        "title": "Thông báo trạng thái",
        "message": raw_error or f"Trạng thái pipeline: {status_code}",
        "type": "info"
    }
