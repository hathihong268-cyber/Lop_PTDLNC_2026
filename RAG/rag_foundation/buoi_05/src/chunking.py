"""
Module Hiện thực 3 Chiến lược Chunking cho RAG Foundation:
1. Fixed-size (Cố định ký tự + Overlap)
2. Semantic (Ngắt theo ranh giới câu và đoạn văn bản)
3. Hierarchical (Phân cấp theo Chương -> Mục -> Điều -> Khoản của Văn bản Pháp luật VN)
"""

import re
from typing import List, Optional
try:
    from schemas import Chunk, ChunkMetadata, RawDocument
except ImportError:
    from .schemas import Chunk, ChunkMetadata, RawDocument


# ===================================================
# CHIẾN LƯỢC 1: FIXED-SIZE CHUNKING
# ===================================================

def chunk_fixed_size(
    raw_doc: RawDocument, 
    chunk_size: int = 600, 
    chunk_overlap: int = 120
) -> List[Chunk]:
    """
    Cắt văn bản theo kích thước ký tự cố định với bước gối đầu (overlap).
    Cố gắng không ngắt giữa chừng một từ tiếng Việt.
    """
    chunks: List[Chunk] = []
    text = raw_doc.full_text
    total_len = len(text)
    
    if total_len == 0:
        return chunks

    start = 0
    chunk_idx = 1
    step = chunk_size - chunk_overlap

    while start < total_len:
        end = min(start + chunk_size, total_len)
        
        # Nếu chưa chạm cuối, tìm khoảng trắng gần nhất để ngắt trọn vẹn từ
        if end < total_len:
            last_space = text.rfind(" ", start, end)
            if last_space > start + (chunk_size // 2):
                end = last_space

        chunk_text = text[start:end].strip()

        if chunk_text:
            chunk_obj = Chunk(
                chunk_id=f"{raw_doc.source}_fixed_{chunk_idx:04d}",
                strategy="fixed_size",
                source=raw_doc.source,
                page_start=1,  # Trong demo text nối liền
                page_end=raw_doc.total_pages,
                text=chunk_text,
                metadata=ChunkMetadata(
                    strategy="fixed_size",
                    chunk_index=chunk_idx,
                    char_count=len(chunk_text),
                    word_count=len(chunk_text.split()),
                    overlap_chars=chunk_overlap if start > 0 else 0
                )
            )
            chunks.append(chunk_obj)
            chunk_idx += 1

        if end >= total_len:
            break

        start += step

    return chunks


# ===================================================
# CHIẾN LƯỢC 2: SEMANTIC CHUNKING
# ===================================================

def chunk_semantic(
    raw_doc: RawDocument, 
    max_chunk_size: int = 800, 
    min_chunk_size: int = 150
) -> List[Chunk]:
    """
    Ngắt văn bản theo ranh giới ngữ nghĩa:
    - Ưu tiên ngắt đoạn (dấu ngắt dòng kép \n\n)
    - Tách theo câu (. , ! , ?)
    - Gom các câu cùng đoạn sao cho không vượt quá max_chunk_size và không ngắt giữa câu.
    """
    chunks: List[Chunk] = []
    text = raw_doc.full_text
    
    if not text.strip():
        return chunks

    # 1. Tách theo các đoạn văn thô
    raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    
    current_chunk_sentences: List[str] = []
    current_length = 0
    chunk_idx = 1

    # Tách câu bằng regex (chú ý chữ viết tắt và dấu chấm tiếng Việt)
    sentence_regex = re.compile(r'(?<=[.!?])\s+(?=[A-ZÀ-Ỹ0-9])')

    for para in raw_paragraphs:
        sentences = sentence_regex.split(para)
        
        for sent in sentences:
            sent_len = len(sent)
            
            # Nếu thêm câu này vượt quá max_chunk_size và chunk hiện tại đã đủ lớn
            if current_length + sent_len > max_chunk_size and current_length >= min_chunk_size:
                merged_text = " ".join(current_chunk_sentences).strip()
                if merged_text:
                    chunks.append(Chunk(
                        chunk_id=f"{raw_doc.source}_semantic_{chunk_idx:04d}",
                        strategy="semantic",
                        source=raw_doc.source,
                        page_start=1,
                        page_end=raw_doc.total_pages,
                        text=merged_text,
                        metadata=ChunkMetadata(
                            strategy="semantic",
                            chunk_index=chunk_idx,
                            char_count=len(merged_text),
                            word_count=len(merged_text.split())
                        )
                    ))
                    chunk_idx += 1
                current_chunk_sentences = [sent]
                current_length = sent_len
            else:
                current_chunk_sentences.append(sent)
                current_length += sent_len

    # Thêm phần còn lại cuối cùng
    if current_chunk_sentences:
        merged_text = " ".join(current_chunk_sentences).strip()
        if merged_text:
            chunks.append(Chunk(
                chunk_id=f"{raw_doc.source}_semantic_{chunk_idx:04d}",
                strategy="semantic",
                source=raw_doc.source,
                page_start=1,
                page_end=raw_doc.total_pages,
                text=merged_text,
                metadata=ChunkMetadata(
                    strategy="semantic",
                    chunk_index=chunk_idx,
                    char_count=len(merged_text),
                    word_count=len(merged_text.split())
                )
            ))

    return chunks


# ===================================================
# CHIẾN LƯỢC 3: HIERARCHICAL CHUNKING (CẤU TRÚC PHÁP LÝ VN)
# ===================================================

def chunk_hierarchical(raw_doc: RawDocument) -> List[Chunk]:
    """
    Phân mảnh theo cấu trúc cây văn bản quy phạm pháp luật Việt Nam:
    Chương -> Mục -> Điều -> Khoản -> Điểm.
    
    Ràng buộc: Nếu văn bản không có cấu trúc Chương/Điều, KHÔNG được tự bịa
    mà phải ghi nhận cảnh báo và phân tách an toàn.
    """
    chunks: List[Chunk] = []
    text = raw_doc.full_text
    
    if not text.strip():
        return chunks

    # Regex nhận diện mốc cấu trúc pháp lý
    re_chuong = re.compile(r'(?i)^(Chương\s+[IVXLCDM\d]+[^\n]*)', re.MULTILINE)
    re_muc = re.compile(r'(?i)^(Mục\s+\d+[^\n]*)', re.MULTILINE)
    re_dieu = re.compile(r'(?i)^(Điều\s+\d+\.?\s*[^\n]*)', re.MULTILINE)

    # Kiểm tra xem tài liệu có chứa mốc cấu trúc hay không
    dieu_matches = list(re_dieu.finditer(text))
    
    if not dieu_matches:
        # TÌNH HUỐNG RÀNG BUỘC: Không có cấu trúc Chương / Điều
        warning_msg = "Văn bản không chứa cấu trúc phân cấp chuẩn (Chương/Điều). Áp dụng phân mảnh dự phòng theo đoạn lớn."
        print(f"  ⚠️ [CẢNH BÁO HIERARCHICAL] {warning_msg}")
        
        # Fallback an toàn không bịa cấu trúc
        semantic_chunks = chunk_semantic(raw_doc, max_chunk_size=1000)
        for c in semantic_chunks:
            c.strategy = "hierarchical"
            c.chunk_id = c.chunk_id.replace("_semantic_", "_hierarchical_")
            c.metadata.strategy = "hierarchical"
            c.metadata.warning = warning_msg
        return semantic_chunks

    # Nếu có cấu trúc Điều -> Tách từng Điều làm 1 chunk chính
    current_chuong = "Phần mở đầu"
    current_muc = None
    chunk_idx = 1

    for i, match in enumerate(dieu_matches):
        dieu_header = match.group(1).strip()
        start_pos = match.start()
        end_pos = dieu_matches[i + 1].start() if i + 1 < len(dieu_matches) else len(text)
        
        # Tìm Chương/Mục xuất hiện trước Điều này
        preceding_text = text[:start_pos]
        chuong_found = list(re_chuong.finditer(preceding_text))
        if chuong_found:
            current_chuong = chuong_found[-1].group(1).strip()
            
        muc_found = list(re_muc.finditer(preceding_text))
        if muc_found:
            current_muc = muc_found[-1].group(1).strip()
        else:
            current_muc = None

        dieu_body = text[start_pos:end_pos].strip()

        chunk_obj = Chunk(
            chunk_id=f"{raw_doc.source}_hierarchical_{chunk_idx:04d}",
            strategy="hierarchical",
            source=raw_doc.source,
            page_start=1,
            page_end=raw_doc.total_pages,
            text=dieu_body,
            metadata=ChunkMetadata(
                strategy="hierarchical",
                chunk_index=chunk_idx,
                char_count=len(dieu_body),
                word_count=len(dieu_body.split()),
                chuong=current_chuong,
                muc=current_muc,
                dieu=dieu_header
            )
        )
        chunks.append(chunk_obj)
        chunk_idx += 1

    return chunks
