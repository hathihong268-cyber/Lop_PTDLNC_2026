"""
Module: citation.py
Buổi 14: Hybrid Search + Reranking + Mini Knowledge Graph
Nhiệm vụ: Định dạng trích dẫn (citation) chính xác dựa trên metadata thực tế của từng chunk.
"""

from typing import Dict, Any


def format_citation(chunk_metadata: Dict[str, Any]) -> str:
    """
    Tạo chuỗi citation chuẩn từ metadata của chunk.
    Cú pháp chuẩn: [Tên văn bản / Số hiệu | Điều / Khoản | chunk_id]
    
    Ví dụ:
    [Nghị định số 46/2023/NĐ-CP | Điều 73 | doc_163441_dieu_73]
    [Thông tư số 01/2014/TT-NHNN | Điều 55 | doc_44209_dieu_55]
    """
    # 1. Xác định tên văn bản hoặc số hiệu
    title = str(chunk_metadata.get("title", "")).strip()
    so_ky_hieu = str(chunk_metadata.get("so_ky_hieu", "")).strip()
    doc_id = str(chunk_metadata.get("document_id", "")).strip()
    
    # Rút gọn tiêu đề nếu quá dài để hiển thị citation gọn gàng
    if so_ky_hieu:
        doc_label = so_ky_hieu
    elif title:
        doc_label = title[:50] + "..." if len(title) > 50 else title
    else:
        doc_label = f"Doc_{doc_id}"

    # 2. Xác định vị trí điều khoản / chương
    article = str(chunk_metadata.get("article", "")).strip()
    chapter = str(chunk_metadata.get("chapter", "")).strip()
    clause = str(chunk_metadata.get("clause", "")).strip()
    
    location_parts = []
    if chapter and not article:
        location_parts.append(chapter)
    if article:
        # Nếu article là "Điều 73. Bổ nhiệm..." -> lấy "Điều 73" hoặc giữ nguyên
        art_clean = article.split(".")[0].strip() if "." in article else article
        location_parts.append(art_clean)
    if clause:
        location_parts.append(f"Khoản {clause}" if not clause.startswith("Khoản") else clause)
        
    location_label = " - ".join(location_parts) if location_parts else "Toàn văn"

    # 3. Chunk ID
    chunk_id = str(chunk_metadata.get("chunk_id", "")).strip()

    return f"[{doc_label} | {location_label} | {chunk_id}]"
