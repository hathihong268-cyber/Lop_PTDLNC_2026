"""
Unit tests for Chunking Strategies (Buoi 05)
Kiểm tra các trường hợp:
1. Fixed-size chunking with overlap
2. Semantic chunking without breaking sentences
3. Hierarchical chunking on legal documents (Chương/Điều/Khoản)
4. Hierarchical warning when structure is missing
"""

import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from schemas import RawDocument, RawPage
from chunking import chunk_fixed_size, chunk_semantic, chunk_hierarchical


def test_fixed_size():
    doc = RawDocument(
        source="test_fixed.pdf",
        total_pages=1,
        full_text="Ngân hàng Nhà nước Việt Nam ban hành thông tư quy định về tỷ lệ an toàn vốn. Quy định này áp dụng cho toàn hệ thống."
    )
    chunks = chunk_fixed_size(doc, chunk_size=50, chunk_overlap=15)
    assert len(chunks) >= 2, "Fixed size chunking should split into multiple chunks"
    assert chunks[0].strategy == "fixed_size"
    print("✅ Test Fixed-size Chunking: PASS")


def test_semantic():
    doc = RawDocument(
        source="test_semantic.pdf",
        total_pages=1,
        full_text="Đoạn thứ nhất bàn về đối tượng áp dụng.\n\nĐoạn thứ hai bàn về nguyên tắc cấp tín dụng. Các tổ chức tín dụng phải tuân thủ nghiêm ngặt."
    )
    chunks = chunk_semantic(doc, max_chunk_size=100, min_chunk_size=20)
    assert len(chunks) == 2, f"Semantic chunking expected 2 chunks, got {len(chunks)}"
    assert chunks[0].strategy == "semantic"
    print("✅ Test Semantic Chunking: PASS")


def test_hierarchical_with_structure():
    doc = RawDocument(
        source="test_legal.pdf",
        total_pages=1,
        full_text="""Chương I: QUY ĐỊNH CHUNG
Điều 1. Phạm vi điều chỉnh
Thông tư này quy định về hoạt động cho vay.

Điều 2. Đối tượng áp dụng
1. Tổ chức tín dụng.
2. Khách hàng vay vốn."""
    )
    chunks = chunk_hierarchical(doc)
    assert len(chunks) == 2, f"Hierarchical expected 2 chunks for 2 Điều, got {len(chunks)}"
    assert chunks[0].metadata.dieu.startswith("Điều 1")
    assert chunks[1].metadata.dieu.startswith("Điều 2")
    assert chunks[0].metadata.chuong == "Chương I: QUY ĐỊNH CHUNG"
    print("✅ Test Hierarchical Chunking (Có cấu trúc): PASS")


def test_hierarchical_without_structure():
    doc = RawDocument(
        source="test_no_structure.pdf",
        total_pages=1,
        full_text="Đây là một bức thư thông báo chung không có chương điều nào cả. Nội dung rất ngắn gọn."
    )
    chunks = chunk_hierarchical(doc)
    assert len(chunks) >= 1
    assert chunks[0].metadata.warning is not None, "Warning should be set when no structure is found"
    print("✅ Test Hierarchical Chunking (Không có cấu trúc & Warning): PASS")


if __name__ == "__main__":
    test_fixed_size()
    test_semantic()
    test_hierarchical_with_structure()
    test_hierarchical_without_structure()
    print("\n🎉 TẤT CẢ UNIT TESTS CHUNKING ĐÃ PASS THÀNH CÔNG!")
