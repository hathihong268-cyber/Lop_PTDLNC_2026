"""
Pipeline chính thực thi RAG Foundation: OCR & Chunking (Buổi 05)
Hỗ trợ các chế độ --dry-run (chỉ phân tích/thống kê) và --write (lưu file output)
"""

import sys
import os
import json
import argparse
import asyncio
from pathlib import Path
from typing import List, Dict, Any

# Đảm bảo in UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Thêm thư mục hiện tại vào sys.path
CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))

from schemas import RawDocument, Chunk
from ocr_pipeline import extract_pdf_document
from chunking import chunk_fixed_size, chunk_semantic, chunk_hierarchical

BASE_DIR = CURRENT_DIR.parent
DATADEMO_DIR = BASE_DIR / "datademo"
OUTPUT_DIR = BASE_DIR / "output"
STORAGE_DIR = BASE_DIR / "storage"


def compute_stats(chunks: List[Chunk]) -> Dict[str, Any]:
    """Tính toán thống kê số lượng và độ dài min/max/avg cho danh sách chunk."""
    if not chunks:
        return {"count": 0, "min_len": 0, "max_len": 0, "avg_len": 0}
    
    lengths = [c.metadata.char_count for c in chunks]
    return {
        "count": len(chunks),
        "min_len": min(lengths),
        "max_len": max(lengths),
        "avg_len": round(sum(lengths) / len(lengths), 1)
    }


def print_stats_table(stats_dict: Dict[str, Dict[str, Any]]):
    """In bảng thống kê so sánh 3 chiến lược chunking."""
    print("\n" + "=" * 75)
    print("        BẢNG SO SÁNH 3 CHIẾN LƯỢC CHUNKING (RAG FOUNDATION)")
    print("=" * 75)
    print(f"{'Chiến lược':<20}{'Số lượng Chunk':<18}{'Độ dài Min':<14}{'Độ dài Max':<14}{'Trung bình':<12}")
    print("-" * 75)
    
    names = {
        "fixed_size": "1. Fixed-size",
        "semantic": "2. Semantic",
        "hierarchical": "3. Hierarchical"
    }
    
    for key, stat in stats_dict.items():
        label = names.get(key, key)
        print(f"{label:<20}{stat['count']:<18}{stat['min_len']:<14}{stat['max_len']:<14}{stat['avg_len']:<12}")
    print("=" * 75)


async def process_single_pdf(pdf_path: Path, is_write: bool):
    print(f"\n{'='*75}")
    print(f"📄 BẮT ĐẦU XỬ LÝ: {pdf_path.name}")
    print(f"{'='*75}")

    # 1. OCR & Trích xuất văn bản
    raw_doc = await extract_pdf_document(str(pdf_path))
    
    print(f"\n[KẾT QUẢ TRÍCH XUẤT]")
    print(f"  - Tổng số trang : {raw_doc.total_pages}")
    print(f"  - Dùng OCR      : {'Có (LlamaParse)' if raw_doc.ocr_used else 'Không (PyMuPDF Text Layer)'}")
    print(f"  - Tổng số ký tự : {len(raw_doc.full_text):,} ký tự")

    # 2. Áp dụng 3 chiến lược chunking
    fixed_chunks = chunk_fixed_size(raw_doc, chunk_size=600, chunk_overlap=120)
    semantic_chunks = chunk_semantic(raw_doc, max_chunk_size=800, min_chunk_size=150)
    hierarchical_chunks = chunk_hierarchical(raw_doc)

    # 3. Thống kê định lượng
    stats = {
        "fixed_size": compute_stats(fixed_chunks),
        "semantic": compute_stats(semantic_chunks),
        "hierarchical": compute_stats(hierarchical_chunks)
    }
    print_stats_table(stats)

    # 4. In mẫu metadata của 1 chunk đại diện
    print("\n🔍 [VÍ DỤ METADATA CỦA MỘT CHUNK ĐIỂN HÌNH - HIERARCHICAL]:")
    sample_chunk = hierarchical_chunks[0] if hierarchical_chunks else (fixed_chunks[0] if fixed_chunks else None)
    if sample_chunk:
        print(json.dumps(sample_chunk.model_dump(), ensure_ascii=False, indent=2))

    # 5. Lưu dữ liệu nếu bật cờ --write
    if is_write:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        
        base_name = pdf_path.stem
        
        # Lưu Raw Document
        raw_output_path = OUTPUT_DIR / f"{base_name}_raw.json"
        with open(raw_output_path, "w", encoding="utf-8") as f:
            json.dump(raw_doc.model_dump(), f, ensure_ascii=False, indent=2)
            
        # Lưu Chunks theo từng chiến lược
        chunks_payload = {
            "source": raw_doc.source,
            "total_pages": raw_doc.total_pages,
            "stats": stats,
            "strategies": {
                "fixed_size": [c.model_dump() for c in fixed_chunks],
                "semantic": [c.model_dump() for c in semantic_chunks],
                "hierarchical": [c.model_dump() for c in hierarchical_chunks]
            }
        }
        
        chunks_output_path = OUTPUT_DIR / f"{base_name}_chunks.json"
        with open(chunks_output_path, "w", encoding="utf-8") as f:
            json.dump(chunks_payload, f, ensure_ascii=False, indent=2)

        print(f"\n💾 [ĐÃ GHI DỮ LIỆU THÀNH CÔNG]")
        print(f"  -> File Raw Text : {raw_output_path.name}")
        print(f"  -> File Chunks   : {chunks_output_path.name}")
    else:
        print("\nℹ️ [CHẾ ĐỘ DRY-RUN] Chưa ghi dữ liệu ra đĩa. Dùng cờ '--write' để lưu kết quả.")


def print_error_scenarios_report():
    print("\n" + "=" * 75)
    print("     BÁO CÁO CÁC TÌNH HUỐNG LỖI ĐÃ XỬ LÝ TRONG PIPELINE (BUỔI 5)")
    print("=" * 75)
    print("1. [Lỗi Font / Encoding / Ký tự lạ trong PDF]:")
    print("   -> Tự động đánh giá chất lượng Text Layer và chuẩn hóa Unicode NFC.")
    print("   -> Nếu trang có tỷ lệ rác cao hoặc rỗng -> Kích hoạt fallback LlamaParse.")
    print("\n2. [Văn bản không có cấu trúc phân cấp (Không có Chương/Điều)]:")
    print("   -> Hierarchical chunker không tự bịa đặt heading; ghi nhận cảnh báo")
    print("      và tự động fallback sang phân mảnh theo đoạn lớn an toàn.")
    print("\n3. [Chưa cấu hình API Key LlamaParse hoặc Key không hợp lệ]:")
    print("   -> Không làm dừng/sập tiến trình, tự động dùng text layer sẵn có kèm")
    print("      thông báo hướng dẫn bổ sung key trong file .env.")
    print("=" * 75 + "\n")


async def main():
    parser = argparse.ArgumentParser(description="RAG Foundation: OCR & Chunking Pipeline")
    parser.add_argument("--file", type=str, help="Tên file PDF cụ thể trong datademo/ cần xử lý")
    parser.add_argument("--write", action="store_true", help="Ghi kết quả raw và chunk vào thư mục output/")
    parser.add_argument("--dry-run", action="store_true", help="Chạy thử nghiệm không ghi đĩa (mặc định)")
    
    args = parser.parse_args()
    is_write = args.write

    # Tìm danh sách file PDF cần xử lý
    if args.file:
        target_pdf = Path(args.file)
        if not target_pdf.is_absolute():
            target_pdf = DATADEMO_DIR / args.file
        pdf_files = [target_pdf]
    else:
        pdf_files = list(DATADEMO_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"❌ Không tìm thấy file PDF nào trong: {DATADEMO_DIR}")
        return

    for pdf in pdf_files:
        await process_single_pdf(pdf, is_write=is_write)

    print_error_scenarios_report()


if __name__ == "__main__":
    asyncio.run(main())
