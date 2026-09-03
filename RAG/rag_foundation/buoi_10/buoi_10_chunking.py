"""
Module Buoc 1: Phan tich HTML, Lam sach va Phan tach cau truc phan cap (Chunking)
Bai thuc hanh 1 - Buoi 10: Graph RAG Foundation
"""

import os
import sys
import re
import json
import uuid
import pandas as pd
from bs4 import BeautifulSoup, Tag, NavigableString
from pathlib import Path
from typing import List, Dict, Any, Optional

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def clean_text(text: str) -> str:
    """Lam sach khoang trang, ky tu dac biet, newline thua."""
    if not text:
        return ""
    # Chuyen cac whitespace va non-breaking spaces thanh single space
    text = re.sub(r'[\xa0\u200b\u200e\u200f\t]+', ' ', text)
    # Gom nhieu newline thanh max 2 newline
    text = re.sub(r'\r\n|\r', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Xoa khoang trang dau cuoi moi dong
    lines = [line.strip() for line in text.split('\n')]
    return '\n'.join(lines).strip()


def table_to_clean_text(table_tag: Tag) -> str:
    """Chuyen doi the table HTML thanh van ban bang bieu Markdown sach se."""
    rows = []
    for tr in table_tag.find_all('tr'):
        cells = [clean_text(td.get_text(separator=" ", strip=True)) for td in tr.find_all(['td', 'th'])]
        if any(cells):
            rows.append(cells)
    if not rows:
        return ""
    
    # Kiem tra neu la table header Quoc Hieu / So Hieu (2 cot metadata)
    if len(rows) <= 3 and len(rows[0]) == 2 and any("CỘNG HÒA" in str(c).upper() or "VIỆT NAM" in str(c).upper() for c in rows[0]):
        # Format thanh text thong tin hanh chinh
        header_text = []
        for r in rows:
            header_text.append(" | ".join([c for c in r if c]))
        return "\n".join(header_text)
    
    # Chuyen thanh Markdown Table
    max_cols = max(len(r) for r in rows)
    formatted_rows = []
    for r in rows:
        r_padded = r + [''] * (max_cols - len(r))
        formatted_rows.append('| ' + ' | '.join(r_padded) + ' |')
    if len(rows) > 1:
        separator = '| ' + ' | '.join(['---'] * max_cols) + ' |'
        formatted_rows.insert(1, separator)
    return '\n'.join(formatted_rows)


class HTMLHierarchicalChunker:
    """
    Bo phan tach cau truc van ban phap luat tu HTML theo mo hinh phan cap:
    Document -> Chuong -> Muc -> Dieu -> Khoan / Doan / Bang bieu.
    """

    # Regex nhan dien cac cap phan cap
    RE_CHUONG = re.compile(r'^(CHƯƠNG|Chương)\s+([IVXLCDM\d]+)(\.|\:|\-|\s|$)(.*)', re.IGNORECASE)
    RE_MUC = re.compile(r'^(MỤC|Mục)\s+([IVXLCDM\d]+)(\.|\:|\-|\s|$)(.*)', re.IGNORECASE)
    RE_DIEU = re.compile(r'^(ĐIỀU|Điều)\s+(\d+[a-zA-Z]?)(\.|\:|\-|\s|$)(.*)', re.IGNORECASE)
    RE_KHOAN = re.compile(r'^(\d+)\.\s+(.*)')

    def __init__(self):
        pass

    def extract_blocks_from_html(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Trich xuat cac khoi van ban (paragraphs, tables, headings) theo thu tu tuyen tinh
        dong thoi lam sach cac the HTML long nhau.
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        body = soup.body if soup.body else soup

        blocks = []

        for element in body.descendants:
            if not isinstance(element, Tag):
                continue

            # Chi xu ly cac the cap khoi truc tiep
            if element.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div']:
                # Tranh lay trung van ban neu the cha la p hoac div da chua no
                if element.find_parent(['p', 'table']):
                    continue
                
                # Bo qua the div neu ben trong chua the p hoac table
                if element.name == 'div' and element.find(['p', 'table', 'div']):
                    continue

                text = clean_text(element.get_text(separator=" ", strip=True))
                if text:
                    blocks.append({
                        'type': 'paragraph',
                        'tag': element.name,
                        'text': text
                    })

            elif element.name == 'table':
                # Tranh lay bang nam trong bang khac
                if element.find_parent('table'):
                    continue
                table_md = table_to_clean_text(element)
                if table_md:
                    blocks.append({
                        'type': 'table',
                        'tag': 'table',
                        'text': table_md
                    })

        return blocks

    def parse_document(self, doc_id: Any, title: str, html_content: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Phan tach toan bo tai lieu HTML thanh danh sach cac Chunk co cau truc phan cap.
        Moi chunk bao gom:
          - chunk_id: ma dinh danh duy nhat
          - doc_id: lien ket ve Document goc
          - parent_id: ma dinh danh cua chunk cha truc tiep (None neu la top-level)
          - level: cap do ('preamble', 'chuong', 'muc', 'dieu', 'khoan', 'doan', 'table')
          - heading: tieu de cua chunk (VD: 'Điều 1. Phạm vi điều chỉnh')
          - text: noi dung van ban sach cua chunk
          - seq_order: so thu tu de tao quan he NEXT
        """
        blocks = self.extract_blocks_from_html(html_content)
        chunks: List[Dict[str, Any]] = []

        current_chuong_id = None
        current_chuong_title = None

        current_muc_id = None
        current_muc_title = None

        current_dieu_id = None
        current_dieu_title = None

        seq = 0

        # Khoi phan doan mo dau (Preamble / Can cu ban hanh) truoc khi vao Dieu 1
        preamble_texts = []

        for block in blocks:
            text = block['text']
            b_type = block['type']

            # 1. Kiem tra CHUONG
            chuong_match = self.RE_CHUONG.match(text)
            if chuong_match and len(text) < 200:
                # Flush preamble neu co
                if preamble_texts and not current_dieu_id and not current_chuong_id:
                    p_id = f"{doc_id}_preamble"
                    chunks.append({
                        'chunk_id': p_id,
                        'doc_id': str(doc_id),
                        'doc_title': title,
                        'parent_id': None,
                        'level': 'preamble',
                        'heading': 'Căn cứ và Thẩm quyền ban hành',
                        'text': '\n\n'.join(preamble_texts),
                        'seq_order': seq
                    })
                    seq += 1
                    preamble_texts = []

                chuong_num = chuong_match.group(2)
                current_chuong_title = text
                current_chuong_id = f"{doc_id}_c_{chuong_num}"
                current_muc_id = None
                current_muc_title = None
                current_dieu_id = None
                current_dieu_title = None

                chunks.append({
                    'chunk_id': current_chuong_id,
                    'doc_id': str(doc_id),
                    'doc_title': title,
                    'parent_id': None,
                    'level': 'chuong',
                    'heading': current_chuong_title,
                    'text': current_chuong_title,
                    'seq_order': seq
                })
                seq += 1
                continue

            # 2. Kiem tra MUC
            muc_match = self.RE_MUC.match(text)
            if muc_match and len(text) < 200:
                muc_num = muc_match.group(2)
                current_muc_title = text
                parent_for_muc = current_chuong_id
                current_muc_id = f"{doc_id}_m_{muc_num}" if not current_chuong_id else f"{current_chuong_id}_m_{muc_num}"
                current_dieu_id = None
                current_dieu_title = None

                chunks.append({
                    'chunk_id': current_muc_id,
                    'doc_id': str(doc_id),
                    'doc_title': title,
                    'parent_id': parent_for_muc,
                    'level': 'muc',
                    'heading': current_muc_title,
                    'text': current_muc_title,
                    'seq_order': seq
                })
                seq += 1
                continue

            # 3. Kiem tra DIEU
            dieu_match = self.RE_DIEU.match(text)
            if dieu_match:
                # Flush preamble neu chua vao chuong nao ma gap ngay Dieu 1
                if preamble_texts and not current_dieu_id:
                    p_id = f"{doc_id}_preamble"
                    chunks.append({
                        'chunk_id': p_id,
                        'doc_id': str(doc_id),
                        'doc_title': title,
                        'parent_id': None,
                        'level': 'preamble',
                        'heading': 'Căn cứ và Thẩm quyền ban hành',
                        'text': '\n\n'.join(preamble_texts),
                        'seq_order': seq
                    })
                    seq += 1
                    preamble_texts = []

                dieu_num = dieu_match.group(2)
                current_dieu_title = text
                parent_for_dieu = current_muc_id if current_muc_id else current_chuong_id
                current_dieu_id = f"{doc_id}_d_{dieu_num}"

                chunks.append({
                    'chunk_id': current_dieu_id,
                    'doc_id': str(doc_id),
                    'doc_title': title,
                    'parent_id': parent_for_dieu,
                    'level': 'dieu',
                    'heading': current_dieu_title,
                    'text': current_dieu_title,
                    'seq_order': seq
                })
                seq += 1
                continue

            # 4. Noi dung ben trong Dieu hoac Preamble
            if not current_dieu_id:
                # Dang o phan dau tai lieu (Quoc hieu, can cu...)
                preamble_texts.append(text)
            else:
                # Dang o trong 1 Dieu -> Tao Child Chunk (Khoan / Doan / Bang bieu)
                parent_for_content = current_dieu_id
                khoan_match = self.RE_KHOAN.match(text)
                
                if khoan_match:
                    khoan_num = khoan_match.group(1)
                    child_id = f"{current_dieu_id}_k_{khoan_num}"
                    level = 'khoan'
                    heading = f"{current_dieu_title} - Khoản {khoan_num}"
                elif b_type == 'table':
                    child_id = f"{current_dieu_id}_tbl_{seq}"
                    level = 'table'
                    heading = f"{current_dieu_title} - Bảng biểu"
                else:
                    child_id = f"{current_dieu_id}_p_{seq}"
                    level = 'doan'
                    heading = f"{current_dieu_title} - Nội dung"

                chunks.append({
                    'chunk_id': child_id,
                    'doc_id': str(doc_id),
                    'doc_title': title,
                    'parent_id': parent_for_content,
                    'level': level,
                    'heading': heading,
                    'text': text,
                    'seq_order': seq
                })
                seq += 1

        # Truong hop dac biet: van ban rat ngan khong co Dieu nao
        if preamble_texts and not chunks:
            chunks.append({
                'chunk_id': f"{doc_id}_content",
                'doc_id': str(doc_id),
                'doc_title': title,
                'parent_id': None,
                'level': 'toan_van',
                'heading': title,
                'text': '\n\n'.join(preamble_texts),
                'seq_order': seq
            })

        return chunks


def build_next_relationships(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Tao cac quan he NEXT giua cac phan doan anh em hoac tuan tu lien ke.
    """
    next_rels = []
    for i in range(len(chunks) - 1):
        curr_chunk = chunks[i]
        next_chunk = chunks[i + 1]
        
        # Chi noi NEXT neu thuoc cung mot tai lieu Document
        if curr_chunk['doc_id'] == next_chunk['doc_id']:
            next_rels.append({
                'from_chunk_id': curr_chunk['chunk_id'],
                'to_chunk_id': next_chunk['chunk_id'],
                'doc_id': curr_chunk['doc_id'],
                'rel_type': 'NEXT'
            })
    return next_rels


# ==============================================================================
# RUN & DEMO BƯỚC 1
# ==============================================================================
if __name__ == "__main__":
    print("=" * 80)
    print(" BƯỚC 1: PHÂN TÍCH HTML, LÀM SẠCH VÀ PHÂN TÁCH CẤU TRÚC PHÂN CẤP (CHUNKING)")
    print("=" * 80)

    data_dir = Path(__file__).resolve().parent / "graph_rag_labs" / "kb+hops"
    metadata_path = data_dir / "metadata.csv"
    content_path = data_dir / "content.csv"

    if not metadata_path.exists() or not content_path.exists():
        print(f"Lỗi: Không tìm thấy dữ liệu tại {data_dir}")
        sys.exit(1)

    df_meta = pd.read_csv(metadata_path)
    df_content = pd.read_csv(content_path)

    chunker = HTMLHierarchicalChunker()

    all_chunks = []
    all_next_rels = []
    doc_stats = []

    print(f"\nĐang xử lý phân tách cho {len(df_meta)} tài liệu văn bản pháp luật...\n")

    for idx, row in df_content.iterrows():
        doc_id = str(row['id'])
        meta_match = df_meta[df_meta['id'].astype(str) == doc_id]
        doc_title = meta_match['title'].values[0] if not meta_match.empty else f"Document {doc_id}"
        html = row['content_html']

        doc_chunks = chunker.parse_document(doc_id=doc_id, title=doc_title, html_content=html)
        doc_nexts = build_next_relationships(doc_chunks)

        all_chunks.extend(doc_chunks)
        all_next_rels.extend(doc_nexts)

        # Thống kê phân cấp
        levels = {}
        for c in doc_chunks:
            lvl = c['level']
            levels[lvl] = levels.get(lvl, 0) + 1

        doc_stats.append({
            'doc_id': doc_id,
            'title': doc_title,
            'total_chunks': len(doc_chunks),
            'levels': levels
        })

    print("-" * 80)
    print(f"TỔNG KẾT PHÂN TÁCH TOÀN BỘ DỮ LIỆU:")
    print(f"- Tổng số Document: {len(df_meta)}")
    print(f"- Tổng số Chunk được tạo: {len(all_chunks)}")
    print(f"- Tổng số quan hệ NEXT tuần tự: {len(all_next_rels)}")
    print("-" * 80)

    # In mẫu phân tách trực quan cho 1 Document đại diện
    sample_doc = doc_stats[0]
    sample_doc_id = sample_doc['doc_id']
    sample_chunks = [c for c in all_chunks if c['doc_id'] == sample_doc_id]

    print(f"\nMINH HỌA TRỰC QUAN CẤU TRÚC PHÂN CẤP (DOCUMENT ID: {sample_doc_id}):")
    print(f"Tiêu đề: {sample_doc['title']}\n")

    for i, c in enumerate(sample_chunks[:15]):
        indent = "  "
        if c['level'] == 'chuong':
            indent = "  [Chương] 📁 "
        elif c['level'] == 'muc':
            indent = "    [Mục] 📂 "
        elif c['level'] == 'dieu':
            indent = "      [Điều] 📄 "
        elif c['level'] == 'khoan':
            indent = "        [Khoản] 🔹 "
        elif c['level'] == 'table':
            indent = "        [Bảng] 📊 "
        else:
            indent = "        [Đoạn] 🔸 "

        parent_info = f"(Parent: {c['parent_id']})" if c['parent_id'] else "(Parent: Root Document)"
        text_preview = c['text'].replace('\n', ' ')[:90]
        print(f"{indent}{c['chunk_id']} {parent_info}")
        print(f"       -> {text_preview}...")

    print(f"\n... và {len(sample_chunks) - 15} phân đoạn con khác.")

    print("\n" + "=" * 80)
    print("MINH HỌA QUAN HỆ TUẦN TỰ [:NEXT] GIỮA CÁC CHUNK LIỀN KỀ:")
    print("=" * 80)
    sample_nexts = [r for r in all_next_rels if r['doc_id'] == sample_doc_id][:5]
    for r in sample_nexts:
        print(f"  (:Chunk {{id: '{r['from_chunk_id']}'}}) -[:NEXT]-> (:Chunk {{id: '{r['to_chunk_id']}'}})")
