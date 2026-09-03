"""
Script: prepare_corpus.py
Buổi 14: Hybrid Search + Reranking + Mini Knowledge Graph
Nhiệm vụ: Chuẩn hóa dữ liệu từ kb+hops (content.csv + metadata.csv) thành chunks_normalized.csv
phục vụ làm nguồn chung cho BM25, Dense, Hybrid Retrieval và Reranker.
"""

import os
import sys
import re
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional

# Đảm bảo in UTF-8 trên console Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Import BeautifulSoup
try:
    from bs4 import BeautifulSoup, Tag
except ImportError:
    print("[ERROR] BeautifulSoup4 chưa được cài đặt. Vui lòng cài đặt bằng: pip install beautifulsoup4")
    sys.exit(1)

# Import pandas
try:
    import pandas as pd
except ImportError:
    print("[ERROR] pandas chưa được cài đặt. Vui lòng cài đặt bằng: pip install pandas")
    sys.exit(1)


# ==============================================================================
# HÀM XỬ LÝ & LÀM SẠCH VĂN BẢN
# ==============================================================================

def clean_text(text: str) -> str:
    """Làm sạch khoảng trắng thừa, ký tự ẩn UTF-8 mà không làm mất dấu tiếng Việt hay số hiệu."""
    if not text:
        return ""
    # Thay thế các khoảng trắng đặc biệt / non-breaking spaces
    text = re.sub(r'[\xa0\u200b\u200c\u200d\u200e\u200f\t]+', ' ', text)
    # Chuẩn hóa xuống dòng
    text = re.sub(r'\r\n|\r', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Strip từng dòng
    lines = [line.strip() for line in text.split('\n')]
    return '\n'.join([l for l in lines if l]).strip()


def table_to_clean_text(table_tag: Tag) -> str:
    """Chuyển đổi thẻ table HTML thành text / bảng Markdown sạch sẽ."""
    rows = []
    for tr in table_tag.find_all('tr'):
        cells = [clean_text(td.get_text(separator=" ", strip=True)) for td in tr.find_all(['td', 'th'])]
        if any(cells):
            rows.append(cells)
    if not rows:
        return ""

    # Header Quốc hiệu / Số hiệu
    if len(rows) <= 3 and len(rows[0]) == 2 and any("CỘNG HÒA" in str(c).upper() or "VIỆT NAM" in str(c).upper() for c in rows[0]):
        header_text = []
        for r in rows:
            header_text.append(" | ".join([c for c in r if c]))
        return "\n".join(header_text)

    # Chuyển bảng thành định dạng Markdown
    max_cols = max(len(r) for r in rows)
    formatted_rows = []
    for r in rows:
        r_padded = r + [''] * (max_cols - len(r))
        formatted_rows.append('| ' + ' | '.join(r_padded) + ' |')
    if len(rows) > 1:
        separator = '| ' + ' | '.join(['---'] * max_cols) + ' |'
        formatted_rows.insert(1, separator)
    return '\n'.join(formatted_rows)


# ==============================================================================
# BỘ PHÂN TÁCH VĂN BẢN PHÁP LUẬT (LEGAL HIERARCHICAL CHUNKER)
# ==============================================================================

class LegalCorpusParser:
    """
    Trích xuất cấu trúc văn bản quy định từ HTML thành các chunk hoàn chỉnh
    đáp ứng yêu cầu retrieval chính xác và giữ nguyên thông tin citation.
    """

    RE_CHUONG = re.compile(r'^(CHƯƠNG|Chương)\s+([IVXLCDM\d]+)(\.|\:|\-|\s|$)(.*)', re.IGNORECASE)
    RE_MUC = re.compile(r'^(MỤC|Mục)\s+([IVXLCDM\d]+)(\.|\:|\-|\s|$)(.*)', re.IGNORECASE)
    RE_DIEU = re.compile(r'^(ĐIỀU|Điều)\s+(\d+[a-zA-Z]?)(\.|\:|\-|\s|$)(.*)', re.IGNORECASE)
    RE_KHOAN = re.compile(r'^(\d+)\.\s+(.*)')

    def extract_blocks_from_html(self, html_content: str) -> List[Dict[str, Any]]:
        """Bóc tách các khối nội dung từ HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')
        body = soup.body if soup.body else soup

        blocks = []
        for element in body.descendants:
            if not isinstance(element, Tag):
                continue

            if element.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div']:
                if element.find_parent(['p', 'table']):
                    continue
                if element.name == 'div' and element.find(['p', 'table', 'div']):
                    continue

                text = clean_text(element.get_text(separator=" ", strip=True))
                if text:
                    blocks.append({'type': 'paragraph', 'text': text})

            elif element.name == 'table':
                if element.find_parent('table'):
                    continue
                table_md = table_to_clean_text(element)
                if table_md:
                    blocks.append({'type': 'table', 'text': table_md})

        return blocks

    def parse_document(self, doc_id: str, metadata_row: Dict[str, Any], html_content: str) -> List[Dict[str, Any]]:
        """Phân tích một văn bản thành các chunks có cấu trúc phân cấp."""
        blocks = self.extract_blocks_from_html(html_content)
        chunks: List[Dict[str, Any]] = []

        current_chapter = ""
        current_section = ""
        current_article = ""
        current_article_heading = ""
        
        # Buffer cho nội dung của Điều hoặc Khoản
        article_paragraphs: List[str] = []
        preamble_blocks: List[str] = []
        
        doc_title = metadata_row.get("title", "")
        doc_type = metadata_row.get("loai_van_ban", "")
        so_ky_hieu = metadata_row.get("so_ky_hieu", "")
        eff_date = metadata_row.get("ngay_co_hieu_luc", "")
        status = metadata_row.get("tinh_trang_hieu_luc", "")

        def flush_article():
            """Đóng gói và tạo chunk cho Điều hiện tại."""
            nonlocal article_paragraphs, current_article, current_article_heading
            if not article_paragraphs or not current_article:
                return

            full_art_text = "\n".join(article_paragraphs).strip()
            if not full_art_text:
                return

            # Kiểm tra xem có tách thành các Khoản con không
            # Nếu nội dung ngắn (< 600 ký tự) hoặc không chia rõ khoản, lưu thành 1 chunk Điều
            # Nếu có các Khoản rõ ràng (1., 2., 3.), ta có thể tách theo Khoản hoặc lưu toàn bộ Điều
            # Để retrieval tối ưu và không mất ngữ cảnh tiêu đề Điều, lưu mỗi Điều là 1 chunk chính
            # Hoặc tách Khoản nếu Điều dài. Ở đây tạo chunk theo cấp Điều kèm các Khoản:
            art_id_clean = re.sub(r'[^a-zA-Z0-9]', '_', current_article)
            chunk_uid = f"doc_{doc_id}_{art_id_clean}"

            # Đảm bảo ngữ cảnh đầy đủ cho retrieval:
            # [Số hiệu / Tiêu đề VB] - [Chương / Mục] - [Điều] - [Nội dung]
            context_prefix = []
            if so_ky_hieu:
                context_prefix.append(f"[{so_ky_hieu}]")
            if current_chapter:
                context_prefix.append(f"{current_chapter}")
            if current_article_heading and not full_art_text.startswith(current_article_heading):
                context_prefix.append(f"{current_article_heading}")

            full_text = "\n".join(context_prefix + [full_art_text]).strip() if context_prefix else full_art_text

            chunks.append({
                "chunk_id": chunk_uid,
                "document_id": str(doc_id),
                "text": full_text,
                "source_file": "kb+hops/content.csv",
                "title": doc_title,
                "so_ky_hieu": so_ky_hieu,
                "document_type": doc_type,
                "chapter": current_chapter,
                "section": current_section,
                "article": current_article_heading or current_article,
                "clause": "",
                "effective_date": eff_date,
                "status": status,
            })
            article_paragraphs = []

        for block in blocks:
            text = block["text"]

            # 1. Kiểm tra Chương
            ch_match = self.RE_CHUONG.match(text)
            if ch_match and len(text) < 200:
                flush_article()
                current_chapter = text
                current_section = ""
                current_article = ""
                current_article_heading = ""
                continue

            # 2. Kiểm tra Mục
            sec_match = self.RE_MUC.match(text)
            if sec_match and len(text) < 200:
                flush_article()
                current_section = text
                current_article = ""
                current_article_heading = ""
                continue

            # 3. Kiểm tra Điều
            art_match = self.RE_DIEU.match(text)
            if art_match:
                flush_article()
                dieu_num = art_match.group(2)
                current_article = f"dieu_{dieu_num}"
                current_article_heading = text
                article_paragraphs.append(text)
                continue

            # Nếu đang trong 1 Điều
            if current_article:
                article_paragraphs.append(text)
            else:
                # Phần mở đầu (Preamble / Căn cứ ban hành)
                preamble_blocks.append(text)

        # Flush Điều cuối cùng
        flush_article()

        # Nếu có phần mở đầu / căn cứ ban hành, lưu thành 1 chunk preamble
        if preamble_blocks:
            preamble_text = "\n".join(preamble_blocks).strip()
            if len(preamble_text) > 30:
                p_uid = f"doc_{doc_id}_preamble"
                chunks.append({
                    "chunk_id": p_uid,
                    "document_id": str(doc_id),
                    "text": f"[{so_ky_hieu}] CĂN CỨ VÀ THẨM QUYỀN BAN HÀNH:\n{preamble_text}",
                    "source_file": "kb+hops/content.csv",
                    "title": doc_title,
                    "so_ky_hieu": so_ky_hieu,
                    "document_type": doc_type,
                    "chapter": "",
                    "section": "",
                    "article": "Căn cứ ban hành",
                    "clause": "",
                    "effective_date": eff_date,
                    "status": status,
                })

        # Trường hợp văn bản không có Điều rõ ràng (hoặc văn bản ngắn)
        if not chunks and blocks:
            full_body = "\n".join([b["text"] for b in blocks]).strip()
            chunks.append({
                "chunk_id": f"doc_{doc_id}_full",
                "document_id": str(doc_id),
                "text": full_body,
                "source_file": "kb+hops/content.csv",
                "title": doc_title,
                "so_ky_hieu": so_ky_hieu,
                "document_type": doc_type,
                "chapter": "",
                "section": "",
                "article": "",
                "clause": "",
                "effective_date": eff_date,
                "status": status,
            })

        return chunks


# ==============================================================================
# HÀM THỰC THI CHÍNH
# ==============================================================================

def find_source_data_dir() -> Path:
    """Tìm đường dẫn tới thư mục chứa dữ liệu nguồn kb+hops."""
    script_dir = Path(__file__).resolve().parent
    buoi_14_dir = script_dir.parent
    
    candidates = [
        buoi_14_dir.parent / "buoi_10" / "graph_rag_labs" / "kb+hops",
        buoi_14_dir.parent.parent.parent / "Rag_thuchanh" / "RAG" / "rag_foundation" / "buoi_10" / "graph_rag_labs" / "kb+hops",
        buoi_14_dir.parent / "kb+hops",
    ]
    for c in candidates:
        if (c / "metadata.csv").exists() and (c / "content.csv").exists():
            return c.resolve()
            
    raise FileNotFoundError(f"Không tìm thấy thư mục kb+hops trong các đường dẫn kiểm tra: {candidates}")


def main():
    print("=" * 70)
    print("CHUẨN HÓA CORPUS PHỤC VỤ RETRIEVAL & CITATION — BUỔI 14")
    print("=" * 70)

    # 1. Định vị đường dẫn
    buoi_14_dir = Path(__file__).resolve().parent.parent
    data_dir = find_source_data_dir()
    output_dir = buoi_14_dir / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = output_dir / "chunks_normalized.csv"

    print(f"[*] Thư mục nguồn (Read-only): {data_dir}")
    print(f"[*] File xuất dữ liệu chuẩn hóa: {output_csv}")

    # 2. Đọc metadata.csv
    metadata_path = data_dir / "metadata.csv"
    meta_df = pd.read_csv(metadata_path, dtype=str).fillna("")
    print(f"[+] Đã đọc {len(meta_df)} văn bản từ metadata.csv")

    metadata_map = {}
    for _, row in meta_df.iterrows():
        doc_id = str(row["id"]).strip()
        metadata_map[doc_id] = row.to_dict()

    # 3. Đọc content.csv
    content_path = data_dir / "content.csv"
    content_df = pd.read_csv(content_path, dtype=str).fillna("")
    print(f"[+] Đã đọc {len(content_df)} bản ghi từ content.csv")

    # 4. Phân tách và chuẩn hóa Chunks
    parser = LegalCorpusParser()
    all_chunks: List[Dict[str, Any]] = []
    seen_chunk_ids = set()

    for _, row in content_df.iterrows():
        doc_id = str(row["id"]).strip()
        html_content = row.get("content_html", "")
        meta_row = metadata_map.get(doc_id, {})

        doc_chunks = parser.parse_document(doc_id, meta_row, html_content)
        
        for chk in doc_chunks:
            base_id = chk["chunk_id"]
            final_id = base_id
            counter = 1
            while final_id in seen_chunk_ids:
                final_id = f"{base_id}_{counter}"
                counter += 1
            chk["chunk_id"] = final_id
            seen_chunk_ids.add(final_id)
            all_chunks.append(chk)

    # 5. Tạo DataFrame kết quả
    chunks_df = pd.DataFrame(all_chunks)

    # Đảm bảo schema thứ tự cột chuẩn
    columns_order = [
        "chunk_id",
        "document_id",
        "title",
        "so_ky_hieu",
        "document_type",
        "chapter",
        "section",
        "article",
        "clause",
        "text",
        "source_file",
        "effective_date",
        "status"
    ]
    chunks_df = chunks_df[columns_order]

    # 6. Kiểm tra tính toàn vẹn (Integrity Check)
    total_chunks = len(chunks_df)
    unique_chunks = chunks_df["chunk_id"].nunique()
    num_docs = chunks_df["document_id"].nunique()
    empty_text_chunks = (chunks_df["text"].str.strip() == "").sum()
    duplicate_chunks = total_chunks - unique_chunks

    # Ghi ra file CSV UTF-8
    chunks_df.to_csv(output_csv, index=False, encoding="utf-8")
    print(f"\n[SUCCESS] Đã lưu thành công: {output_csv} ({os.path.getsize(output_csv):,} bytes)")

    # 7. In thống kê theo yêu cầu Prompt 1
    print("\n" + "=" * 70)
    print("THỐNG KÊ KẾT QUẢ CHUẨN HÓA CORPUS")
    print("=" * 70)
    print(f"Tổng số chunk:           {total_chunks}")
    print(f"Số document:             {num_docs}")
    print(f"Số chunk thiếu text:     {empty_text_chunks}")
    print(f"Duplicate chunk_id:      {duplicate_chunks}")
    print(f"Tính duy nhất chunk_id:  {'ĐẠT (100% Unique)' if duplicate_chunks == 0 else 'LỖI'}")

    # 8. In 3 Sample Records
    print("\n" + "-" * 70)
    print("3 SAMPLE RECORDS:")
    print("-" * 70)
    samples = chunks_df.sample(min(3, len(chunks_df)), random_state=42)
    for idx, (_, sample) in enumerate(samples.iterrows(), 1):
        print(f"\n[Sample {idx}]")
        print(f"  • chunk_id:      {sample['chunk_id']}")
        print(f"  • document_id:   {sample['document_id']}")
        print(f"  • so_ky_hieu:    {sample['so_ky_hieu']}")
        print(f"  • title:         {sample['title']}")
        print(f"  • article:       {sample['article']}")
        print(f"  • status:        {sample['status']}")
        text_preview = sample['text'].replace('\n', ' ')
        if len(text_preview) > 150:
            text_preview = text_preview[:150] + "..."
        print(f"  • text preview:  {text_preview}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
