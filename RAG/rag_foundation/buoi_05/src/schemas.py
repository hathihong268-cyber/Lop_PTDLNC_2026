"""
Định nghĩa Schema dữ liệu cho RAG Foundation Buổi 5
Sử dụng Pydantic để chuẩn hóa cấu trúc dữ liệu Raw Document và Chunk
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RawPage(BaseModel):
    """Đại diện cho dữ liệu thô của 1 trang PDF."""
    page_number: int = Field(..., description="Số thứ tự trang (1-indexed)")
    text: str = Field(..., description="Nội dung văn bản đã chuẩn hóa Unicode NFC")
    ocr_applied: bool = Field(False, description="Trang này có phải dùng OCR (LlamaParse) không")
    quality_score: float = Field(1.0, description="Đánh giá chất lượng text layer (0.0 - 1.0)")


class RawDocument(BaseModel):
    """Đại diện cho toàn bộ tài liệu đã trích xuất từ PDF."""
    source: str = Field(..., description="Tên file PDF nguồn")
    total_pages: int = Field(..., description="Tổng số trang của tài liệu")
    ocr_used: bool = Field(False, description="Tài liệu có trang nào cần chạy OCR không")
    language: str = Field("vie", description="Ngôn ngữ chính (Tiếng Việt)")
    pages: List[RawPage] = Field(default_factory=list, description="Danh sách các trang")
    full_text: str = Field("", description="Toàn bộ nội dung văn bản nối liền")


class ChunkMetadata(BaseModel):
    """Metadata chi tiết gắn kèm từng chunk."""
    strategy: str = Field(..., description="Chiến lược chunking: fixed_size | semantic | hierarchical")
    chunk_index: int = Field(..., description="Thứ tự chunk trong văn bản")
    char_count: int = Field(..., description="Độ dài số ký tự của chunk")
    word_count: int = Field(..., description="Số lượng từ")
    
    # Metadata dành riêng cho Fixed-size
    overlap_chars: Optional[int] = Field(None, description="Số ký tự gối đầu (overlap)")
    
    # Metadata cấu trúc dành cho Hierarchical (Pháp lý VN)
    chuong: Optional[str] = Field(None, description="Tên Chương (nếu có)")
    muc: Optional[str] = Field(None, description="Tên Mục (nếu có)")
    dieu: Optional[str] = Field(None, description="Tên Điều (nếu có)")
    khoan: Optional[str] = Field(None, description="Khoản / Điểm (nếu có)")
    warning: Optional[str] = Field(None, description="Cảnh báo nếu văn bản không có cấu trúc chuẩn")


class Chunk(BaseModel):
    """Cấu trúc dữ liệu chuẩn của một Chunk trong pipeline RAG."""
    chunk_id: str = Field(..., description="Mã định danh duy nhất của chunk")
    strategy: str = Field(..., description="Chiến lược: fixed_size | semantic | hierarchical")
    source: str = Field(..., description="Tên file nguồn")
    page_start: int = Field(..., description="Trang bắt đầu")
    page_end: int = Field(..., description="Trang kết thúc")
    text: str = Field(..., description="Nội dung văn bản trong chunk")
    metadata: ChunkMetadata = Field(..., description="Metadata cấu trúc và định lượng")
