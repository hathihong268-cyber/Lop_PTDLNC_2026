"""Pipeline trích xuất PDF tiếng Việt và so sánh chiến lược chunking cho Buổi 5.

Mặc định là dry-run: không ghi file, không gọi LlamaParse và không gửi dữ liệu ra
ngoài máy. Chỉ ``--write`` mới tạo output; LlamaParse chỉ được gọi khi text layer
PyMuPDF lỗi hoặc không dùng được.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import sys
import tempfile
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "datademo"
OUTPUT_DIR = ROOT / "output"
ENV_FILE = ROOT / "src" / ".env"

HEADING_PATTERNS = (
    ("chapter", re.compile(r"^\s*(CHƯƠNG|PHẦN)\s+[IVXLCDM0-9]+\b.*", re.I)),
    ("section", re.compile(r"^\s*MỤC\s+[IVXLCDM0-9]+\b.*", re.I)),
    ("article", re.compile(r"^\s*ĐIỀU\s+\d+\b.*", re.I)),
    ("clause", re.compile(r"^\s*\d+\.\s+.+")),
    ("point", re.compile(r"^\s*[a-zđ]\)\s+.+", re.I)),
)


@dataclass
class PageText:
    page: int
    text: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class DocumentText:
    source: str
    page_count: int
    ocr_used: bool
    language: str
    pages: list[PageText]
    warnings: list[str] = field(default_factory=list)


def utf8_console() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def normalise(text: str) -> str:
    return unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")


def text_problems(text: str) -> list[str]:
    """Các dấu hiệu thực tế của text layer hỏng; không dùng LLM để phán đoán."""
    compact = re.sub(r"\s+", "", text)
    problems: list[str] = []
    if not compact:
        problems.append("text_rong")
    if "\ufffd" in text:
        problems.append("ky_tu_thay_the")
    if re.search(r"(?:Ã.|Ä.|Â.|�)", text):
        problems.append("dau_hieu_loi_encoding")
    # Font PDF lỗi thường biến dấu tiếng Việt thành số hoặc chữ hoa giữa một từ
    # (ví dụ ``di6m``, ``aOi``). Chỉ fallback khi có nhiều lần để tránh nhầm số điều.
    digit_inside_word = len(re.findall(r"(?<=[A-Za-zĐđ])\d(?=[A-Za-zĐđ])", text))
    mixed_case_word = len(re.findall(r"\b[A-Za-zĐđ]*[a-zđ][A-ZĐ][A-Za-zĐđ]*\b", text))
    if digit_inside_word >= 3:
        problems.append("so_chen_trong_tu_do_loi_font")
    if mixed_case_word >= 3:
        problems.append("hoa_thuong_bat_thuong_trong_tu")
    controls = sum(ord(char) < 32 and char not in "\n\t" for char in text)
    if compact and controls / len(compact) > 0.02:
        problems.append("nhieu_ky_tu_dieu_khien")
    return problems


def extract_pymupdf(pdf: Path) -> DocumentText:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("Thiếu PyMuPDF. Cài requirements trước khi chạy --write.") from exc

    pages: list[PageText] = []
    with fitz.open(pdf) as document:
        for number, page in enumerate(document, start=1):
            try:
                text = normalise(page.get_text("text", sort=True))
                warnings = text_problems(text)
            except Exception as exc:  # PDF/font hỏng cũng cần fallback OCR toàn bộ file.
                text, warnings = "", [f"pymupdf_exception:{type(exc).__name__}"]
            pages.append(PageText(page=number, text=text, warnings=warnings))
    return DocumentText(pdf.name, len(pages), False, "vi", pages)


def render_pdf_for_ocr(pdf: Path, destination: Path) -> None:
    """Raster hoá toàn bộ trang vào PDF dẫn xuất, tuyệt đối không sửa PDF nguồn."""
    import fitz

    destination.parent.mkdir(parents=True, exist_ok=True)
    rendered = fitz.open()
    with fitz.open(pdf) as source:
        for page in source:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            target = rendered.new_page(width=page.rect.width, height=page.rect.height)
            target.insert_image(target.rect, pixmap=pixmap)
        rendered.save(destination, garbage=4, deflate=True)
    rendered.close()


async def ocr_entire_file(rendered_pdf: Path, source_name: str, page_count: int) -> DocumentText:
    """Gọi đúng API Llama Cloud được cung cấp, chỉ sau khi fallback được quyết định."""
    try:
        from dotenv import load_dotenv
        from llama_cloud import AsyncLlamaCloud
    except ImportError as exc:
        raise RuntimeError("Thiếu llama-cloud hoặc python-dotenv. Cài requirements trước.") from exc

    load_dotenv(ENV_FILE)  # Nạp vào process để xác thực; không log hoặc in giá trị key.
    api_key = os.getenv("LLAMA_CLOUD_API_KEY") or os.getenv("LLAMA_PARSE_API_KEY")
    if not api_key:
        raise RuntimeError("Không tìm thấy API key Llama Cloud trong src/.env hoặc biến môi trường.")
    client = AsyncLlamaCloud(api_key=api_key)
    file_obj = await client.files.create(file=str(rendered_pdf), purpose="parse")
    result = await client.parsing.parse(
        file_id=file_obj.id,
        tier="agentic",
        version="latest",
        expand=["markdown_full"],
    )
    markdown = normalise(result.markdown_full or "")
    # API mẫu chỉ bảo đảm markdown_full. Không bịa số trang nếu response không tách trang.
    return DocumentText(
        source=source_name,
        page_count=page_count,
        ocr_used=True,
        language="vi",
        pages=[PageText(1, markdown, ["ocr_toan_tai_lieu; page mapping chi biet 1..N"])],
        warnings=["LlamaParse markdown_full không bảo đảm ranh giới từng trang; page_start/page_end dùng 1..N."],
    )


def page_range(document: DocumentText, start: int, end: int) -> tuple[int, int]:
    if document.ocr_used:
        return 1, document.page_count
    return start, end


def chunk_record(document: DocumentText, strategy: str, index: int, text: str, start: int, end: int,
                 structure: dict[str, str] | None = None) -> dict[str, Any]:
    page_start, page_end = page_range(document, start, end)
    result: dict[str, Any] = {
        "chunk_id": f"{Path(document.source).stem}:{strategy}:{index:04d}",
        "strategy": strategy,
        "source": document.source,
        "page_start": page_start,
        "page_end": page_end,
        "text": normalise(text).strip(),
    }
    if structure:
        result["structure"] = structure
    return result


def split_to_limit(text: str, size: int) -> list[str]:
    """Giới hạn cuối cùng cho đoạn/câu quá dài, ưu tiên khoảng trắng trước khi cắt cứng."""
    pieces: list[str] = []
    remaining = text.strip()
    while len(remaining) > size:
        cut = remaining.rfind(" ", 0, size + 1)
        if cut <= 0:
            cut = size
        pieces.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        pieces.append(remaining)
    return pieces


def fixed_chunks(document: DocumentText, size: int, overlap: int) -> list[dict[str, Any]]:
    full = "\n\n".join(page.text for page in document.pages)
    chunks: list[dict[str, Any]] = []
    position = 0
    while position < len(full):
        text = full[position:position + size].strip()
        if text:
            start_page = next((p.page for p in document.pages if p.text and full.find(p.text) + len(p.text) > position), 1)
            end_page = start_page
            chunks.append(chunk_record(document, "fixed-size", len(chunks) + 1, text, start_page, end_page))
        position += max(1, size - overlap)
    return chunks


def semantic_chunks(document: DocumentText, size: int) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    buffer, first_page, last_page = "", 1, 1
    for page in document.pages:
        units = [unit.strip() for unit in re.split(r"\n\s*\n|\n(?=[A-ZĐ])", page.text) if unit.strip()]
        for unit in units:
            if buffer and len(buffer) + len(unit) + 2 > size:
                chunks.append(chunk_record(document, "semantic", len(chunks) + 1, buffer, first_page, last_page))
                buffer, first_page = "", page.page
            if len(unit) > size:
                sentences = re.split(r"(?<=[.!?;:])\s+", unit)
                for sentence in sentences:
                    for part in split_to_limit(sentence, size):
                        if buffer and len(buffer) + len(part) + 1 > size:
                            chunks.append(chunk_record(document, "semantic", len(chunks) + 1, buffer, first_page, last_page))
                            buffer, first_page = "", page.page
                        buffer = (buffer + " " + part).strip()
                        last_page = page.page
            else:
                buffer = (buffer + "\n\n" + unit).strip()
                last_page = page.page
    if buffer:
        chunks.append(chunk_record(document, "semantic", len(chunks) + 1, buffer, first_page, last_page))
    return chunks


def detect_heading(line: str) -> tuple[str, str] | None:
    for level, pattern in HEADING_PATTERNS:
        if pattern.match(line):
            return level, line.strip()
    return None


def hierarchical_chunks(document: DocumentText, size: int) -> tuple[list[dict[str, Any]], list[str]]:
    chunks: list[dict[str, Any]] = []
    warnings: list[str] = []
    path: dict[str, str] = {}
    buffer, start_page, found_heading = "", 1, False
    for page in document.pages:
        for raw_line in page.text.splitlines():
            found = detect_heading(raw_line)
            if found:
                if buffer.strip():
                    chunks.append(chunk_record(document, "hierarchical", len(chunks) + 1, buffer, start_page, page.page, path.copy() or None))
                level, title = found
                level_order = ["chapter", "section", "article", "clause", "point"]
                for lower in level_order[level_order.index(level) + 1:]:
                    path.pop(lower, None)
                path[level] = title
                buffer, start_page, found_heading = raw_line, page.page, True
            else:
                for line in split_to_limit(raw_line, size):
                    if buffer and len(buffer) + len(line) + 1 > size:
                        chunks.append(chunk_record(document, "hierarchical", len(chunks) + 1, buffer, start_page, page.page, path.copy() or None))
                        buffer, start_page = "", page.page
                    buffer = (buffer + "\n" + line).strip()
    if buffer.strip():
        chunks.append(chunk_record(document, "hierarchical", len(chunks) + 1, buffer, start_page, document.pages[-1].page, path.copy() or None))
    if not found_heading:
        warnings.append("Không tìm thấy heading theo mẫu Chương/Phần/Mục/Điều/Khoản/Điểm; không bịa cấu trúc.")
    return chunks, warnings


def statistics(chunks: list[dict[str, Any]]) -> dict[str, float | int]:
    lengths = [len(chunk["text"]) for chunk in chunks]
    return {"chunk_count": len(chunks), "length_min": min(lengths, default=0),
            "length_max": max(lengths, default=0), "length_avg": round(mean(lengths), 2) if lengths else 0}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def raw_payload(document: DocumentText) -> dict[str, Any]:
    """Lưu metadata đủ ở từng trang để dùng lại cho bài sau mà không cần OCR lại."""
    return {
        "source": document.source,
        "page_count": document.page_count,
        "ocr_used": document.ocr_used,
        "language": document.language,
        "warnings": document.warnings,
        "pages": [
            {
                "source": document.source,
                "page": page.page,
                "ocr_used": document.ocr_used,
                "language": document.language,
                "text": page.text,
                "warnings": page.warnings,
            }
            for page in document.pages
        ],
    }


async def process_pdf(pdf: Path, write: bool, size: int, overlap: int) -> dict[str, Any]:
    document = extract_pymupdf(pdf)
    bad_pages = [page.page for page in document.pages if page.warnings]
    if bad_pages:
        if not write:
            return {"source": pdf.name, "dry_run": True, "would_use_ocr": True, "bad_pages": bad_pages}
        temp_dir = Path(tempfile.mkdtemp(prefix="buoi5_ocr_"))
        try:
            rendered = temp_dir / f"{pdf.stem}__rendered.pdf"
            render_pdf_for_ocr(pdf, rendered)
            document = await ocr_entire_file(rendered, pdf.name, document.page_count)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    elif not write:
        return {"source": pdf.name, "dry_run": True, "would_use_ocr": False, "pages": document.page_count}

    fixed = fixed_chunks(document, size, overlap)
    semantic = semantic_chunks(document, size)
    hierarchical, hierarchy_warnings = hierarchical_chunks(document, size)
    document.warnings.extend(hierarchy_warnings)
    report = {"source": pdf.name, "ocr_used": document.ocr_used,
              "statistics": {"fixed-size": statistics(fixed), "semantic": statistics(semantic), "hierarchical": statistics(hierarchical)},
              "warnings": document.warnings}
    if write:
        stem = pdf.stem
        write_json(OUTPUT_DIR / "raw" / f"{stem}.json", raw_payload(document))
        for strategy, chunks in (("fixed-size", fixed), ("semantic", semantic), ("hierarchical", hierarchical)):
            write_json(OUTPUT_DIR / "chunks" / f"{stem}__{strategy}.json", chunks)
        write_json(OUTPUT_DIR / "reports" / f"{stem}__report.json", report)
    return report


async def main() -> int:
    utf8_console()
    parser = argparse.ArgumentParser(description="PDF → raw NFC → chunks (không embedding, không LLM).")
    parser.add_argument("--write", action="store_true", help="Cho phép ghi output và gọi LlamaParse nếu cần OCR.")
    parser.add_argument("--file", type=Path, help="Chỉ xử lý một PDF trong datademo.")
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--overlap", type=int, default=150)
    args = parser.parse_args()
    if args.chunk_size <= 0 or args.overlap < 0 or args.overlap >= args.chunk_size:
        parser.error("chunk-size phải dương và overlap phải từ 0 đến nhỏ hơn chunk-size.")
    pdfs = [args.file] if args.file else sorted(INPUT_DIR.glob("*.pdf"))
    if not pdfs:
        print("Không tìm thấy PDF trong datademo.")
        return 1
    for pdf in pdfs:
        if not pdf.is_absolute():
            pdf = INPUT_DIR / pdf.name
        if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
            print(f"Bỏ qua tệp không hợp lệ: {pdf}")
            continue
        try:
            result = await process_pdf(pdf, args.write, args.chunk_size, args.overlap)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except RuntimeError as exc:
            print(f"LỖI: {exc}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
