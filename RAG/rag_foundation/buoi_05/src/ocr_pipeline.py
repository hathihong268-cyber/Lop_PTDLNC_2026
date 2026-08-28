"""
Module Xử lý OCR & Trích xuất Văn bản PDF Tiếng Việt
Hỗ trợ PyMuPDF Text Layer và Fallback sang LlamaParse (llama-cloud)
Chuẩn hóa Unicode NFC toàn diện
"""

import os
import sys
import re
import unicodedata
import asyncio
from pathlib import Path
from typing import Tuple, List, Optional
from dotenv import load_dotenv

# Import Schema
try:
    from schemas import RawDocument, RawPage
except ImportError:
    from .schemas import RawDocument, RawPage

# Nạp biến môi trường từ .env (hỗ trợ nhiều vị trí)
CURRENT_DIR = Path(__file__).resolve().parent
for env_candidate in [
    CURRENT_DIR / ".env",
    CURRENT_DIR.parent.parent.parent / "agribank-rag" / "buoi_05" / "RAG" / "rag_foundation" / "buoi_05" / "src" / ".env",
    Path.cwd() / ".env"
]:
    if env_candidate.exists():
        load_dotenv(dotenv_path=env_candidate, override=True)



def normalize_unicode_nfc(text: str) -> str:
    """
    Chuẩn hóa văn bản tiếng Việt sang dạng Unicode dựng sẵn (NFC).
    Giải quyết triệt để lỗi gõ dấu tổ hợp (NFD) thường gặp khi trích xuất PDF.
    """
    if not text:
        return ""
    # Chuẩn hóa NFC
    normalized = unicodedata.normalize("NFC", text)
    # Loại bỏ các ký tự điều khiển rác (ngoại trừ \n, \r, \t)
    clean_chars = [
        c for c in normalized 
        if c in ["\n", "\r", "\t"] or unicodedata.category(c)[0] != "C"
    ]
    return "".join(clean_chars)


def assess_text_quality(text: str) -> Tuple[bool, str, float]:
    """
    Đánh giá chất lượng Text Layer của trang PDF:
    - Kiểm tra trang rỗng / scan thuần
    - Kiểm tra ký tự thay thế lỗi \\ufffd
    - Kiểm tra số lượng từ bị lỗi số lẫn chữ (ví dụ: th6ng, l2O23l) do OCR cũ
    - Kiểm tra tỷ lệ ký tự in được
    """
    raw = text.strip()
    if not raw:
        return True, "Trang rỗng hoặc là file scan thuần (không có text layer)", 0.0

    total_len = len(raw)
    if total_len < 15:
        return True, "Số lượng ký tự quá ít (nghi vấn trang scan hoặc trích xuất lỗi)", 0.2

    # 1. Đếm ký tự lỗi Unicode thay thế '\ufffd'
    replacement_count = raw.count("\ufffd")
    if replacement_count > 0 and (replacement_count / total_len) > 0.03:
        return True, f"Phát hiện {replacement_count} ký tự lỗi font/encoding (\\ufffd)", 0.3

    # 2. Kiểm tra tỷ lệ ký tự in được
    printable_count = sum(1 for c in raw if c.isprintable() or c in "\n\t")
    score = printable_count / total_len
    if score < 0.8:
        return True, f"Tỷ lệ ký tự không đọc được cao ({score:.1%})", score

    # 3. Kiểm tra hiện tượng số lẫn trong từ tiếng Việt do OCR lỗi font (ví dụ: th6ng tu, didu)
    corrupted_words = re.findall(r'[a-zA-ZÀ-ỹ]+[0-9]+[a-zA-ZÀ-ỹ]+', raw)
    if len(corrupted_words) >= 3:
        return True, f"Phát hiện {len(corrupted_words)} từ bị lỗi số chèn chữ (lỗi font/encoding)", 0.4

    return False, "Text layer chất lượng tốt", score


async def run_llamaparse_ocr(pdf_path: str, api_key: str) -> Optional[str]:
    """
    Gửi PDF lên LlamaParse qua SDK llama-cloud để thực hiện Agentic OCR.
    Bảo mật: Không in/log API Key ra console hoặc log.
    """
    try:
        from llama_cloud import AsyncLlamaCloud
        
        print(f"[OCR] Đang gửi tài liệu '{Path(pdf_path).name}' lên LlamaParse Cloud...")
        # Sử dụng API Key an toàn
        client = AsyncLlamaCloud(api_key=api_key)

        file_obj = await client.files.create(file=pdf_path, purpose="parse")
        result = await client.parsing.parse(
            file_id=file_obj.id,
            tier="agentic",
            version="latest",
            expand=["markdown_full"],
        )
        print("[OCR] Nhận kết quả LlamaParse thành công!")
        return result.markdown_full
    except Exception as e:
        print(f"[CẢNH BÁO OCR] Lỗi khi gọi LlamaParse API: {e}")
        return None


async def extract_pdf_document(pdf_path: str) -> RawDocument:
    """
    Quy trình trích xuất văn bản độc lập từ file PDF:
    1. Mở PDF bằng PyMuPDF (chế độ chỉ đọc)
    2. Đọc từng trang và kiểm tra chất lượng text layer (có try-catch chống sập job)
    3. Nếu phát hiện trang lỗi/rỗng -> Gọi LlamaParse OCR
    4. Chuẩn hóa toàn bộ về Unicode NFC
    """
    path_obj = Path(pdf_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Không tìm thấy file PDF tại: {pdf_path}")

    import pymupdf as fitz  # pymupdf >= 1.24; tránh DeprecationWarning của import fitz

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    pages: List[RawPage] = []
    has_corrupted_page = False

    print(f"\n[XỬ LÝ] Đang đọc file: {path_obj.name} ({total_pages} trang)")

    # 1. Trích xuất text từng trang bằng PyMuPDF (lỗi 1 trang không làm dừng job)
    for page_idx in range(total_pages):
        try:
            page = doc[page_idx]
            raw_page_text = page.get_text()
            normalized_text = normalize_unicode_nfc(raw_page_text)
            
            is_corrupted, reason, score = assess_text_quality(normalized_text)
            
            if is_corrupted:
                print(f"  ⚠️ Trang {page_idx + 1}: {reason}")
                has_corrupted_page = True

            pages.append(RawPage(
                page_number=page_idx + 1,
                text=normalized_text,
                ocr_applied=False,
                quality_score=score
            ))
        except Exception as page_err:
            print(f"  ❌ Lỗi đọc trang {page_idx + 1}: {page_err} (bỏ qua và tiếp tục)")
            has_corrupted_page = True
            pages.append(RawPage(
                page_number=page_idx + 1,
                text="",
                ocr_applied=False,
                quality_score=0.0
            ))

    # 2. Fallback sang LlamaParse nếu phát hiện trang lỗi hoặc scan
    ocr_applied_document = False
    if has_corrupted_page:
        api_key = os.getenv("LLAMA_CLOUD_API_KEY", "")
        # Kiểm tra key hợp lệ (không phải key mặc định)
        if api_key and api_key != "KEY CỦA BẠN":
            print("[TIẾN TRÌNH] Kích hoạt LlamaParse OCR cho file bị lỗi text layer...")
            ocr_markdown = await run_llamaparse_ocr(pdf_path, api_key)
            if ocr_markdown:
                ocr_applied_document = True
                # Chuẩn hóa NFC kết quả từ OCR
                clean_ocr_text = normalize_unicode_nfc(ocr_markdown)
                # Cập nhật lại danh sách trang từ OCR markdown (tách theo phân trang nếu có)
                pages = [RawPage(
                    page_number=1,
                    text=clean_ocr_text,
                    ocr_applied=True,
                    quality_score=1.0
                )]
        else:
            print("  ℹ️ [GHI CHÚ] Chưa cấu hình LLAMA_CLOUD_API_KEY trong .env (sử dụng text layer hiện có kèm cảnh báo).")

    full_text = "\n\n".join([p.text for p in pages if p.text])

    return RawDocument(
        source=path_obj.name,
        total_pages=total_pages,
        ocr_used=ocr_applied_document,
        language="vie",
        pages=pages,
        full_text=full_text
    )
