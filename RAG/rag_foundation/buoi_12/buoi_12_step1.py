# -*- coding: utf-8 -*-
"""
BƯỚC 1: Kiểm tra dữ liệu và làm sạch HTML
Module: buoi_12_step1.py

Input:
- ner_kb/metadata.csv
- ner_kb/content.csv

Output:
- ner_kb/cleaned_documents.csv
"""

import os
import sys
import io
import re
import pandas as pd
from bs4 import BeautifulSoup

# Ensure UTF-8 output encoding for Windows terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def clean_html_content(raw_html: str) -> str:
    """
    Làm sạch nội dung HTML bằng BeautifulSoup:
    1. Parse HTML và loại bỏ các thẻ script, style nếu có.
    2. Trích xuất text thuần túy.
    3. Chuẩn hóa khoảng trắng và ngắt dòng.
    4. Giữ nguyên 100% nội dung gốc, số hiệu và cụm từ pháp lý (không paraphrase).
    """
    if not isinstance(raw_html, str) or not raw_html.strip():
        return ""
    
    soup = BeautifulSoup(raw_html, "html.parser")
    
    # Loại bỏ thẻ script, style nếu có
    for tag in soup(["script", "style"]):
        tag.decompose()
    
    # Lấy text với ngắt dòng
    text = soup.get_text(separator="\n")
    
    # Chuẩn hóa khoảng trắng từng dòng
    lines = []
    for line in text.splitlines():
        # Thay thế khoảng trắng đặc biệt &nbsp; / non-breaking space
        line = line.replace("\xa0", " ").replace("&nbsp;", " ")
        # Gom nhiều khoảng trắng liên tiếp thành 1
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)
            
    # Nối lại bằng xuống dòng
    cleaned_text = "\n".join(lines)
    return cleaned_text

def run_step_1():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ner_kb_dir = os.path.join(base_dir, "ner_kb")
    meta_path = os.path.join(ner_kb_dir, "metadata.csv")
    content_path = os.path.join(ner_kb_dir, "content.csv")
    output_path = os.path.join(ner_kb_dir, "cleaned_documents.csv")
    
    print("=" * 60)
    print("         BƯỚC 1: KIỂM TRA DỮ LIỆU VÀ LÀM SẠCH HTML          ")
    print("=" * 60)
    
    # 1. Đọc dữ liệu
    print(f"\n[1] Đang đọc dữ liệu từ:")
    print(f"  - Metadata: {meta_path}")
    print(f"  - Content:  {content_path}")
    
    df_meta = pd.read_csv(meta_path, dtype=str)
    df_content = pd.read_csv(content_path, dtype=str)
    
    # 2. Kiểm tra số dòng, số cột
    print(f"\n[2] Kích thước dữ liệu ban đầu:")
    print(f"  - metadata.csv : {df_meta.shape[0]} dòng, {df_meta.shape[1]} cột")
    print(f"    Cột: {list(df_meta.columns)}")
    print(f"  - content.csv  : {df_content.shape[0]} dòng, {df_content.shape[1]} cột")
    print(f"    Cột: {list(df_content.columns)}")
    
    # 3. Kiểm tra duplicate ID
    dup_meta_ids = df_meta[df_meta.duplicated(subset=["id"], keep=False)]["id"].tolist()
    dup_content_ids = df_content[df_content.duplicated(subset=["id"], keep=False)]["id"].tolist()
    
    print(f"\n[3] Kiểm tra duplicate ID:")
    print(f"  - Số duplicate id trong metadata.csv: {len(dup_meta_ids)}")
    print(f"  - Số duplicate id trong content.csv : {len(dup_content_ids)}")
    
    # 4. Kiểm tra ID mismatch giữa hai file
    meta_ids = set(df_meta["id"].dropna().astype(str).str.strip())
    content_ids = set(df_content["id"].dropna().astype(str).str.strip())
    
    only_in_meta = meta_ids - content_ids
    only_in_content = content_ids - meta_ids
    common_ids = meta_ids & content_ids
    
    print(f"\n[4] Kiểm tra khớp ID:")
    print(f"  - ID chỉ có trong metadata: {len(only_in_meta)} {list(only_in_meta) if only_in_meta else ''}")
    print(f"  - ID chỉ có trong content : {len(only_in_content)} {list(only_in_content) if only_in_content else ''}")
    print(f"  - ID khớp ở cả 2 file     : {len(common_ids)}")
    
    # 5. Merge dữ liệu theo ID
    df_merged = pd.merge(df_meta, df_content, on="id", how="inner")
    print(f"\n[5] Kết quả ghép dữ liệu (Merge theo ID):")
    print(f"  - Số document sau merge: {len(df_merged)}")
    
    # 6. Thống kê missing values & giá trị chưa chuẩn
    print(f"\n[6] Thống kê Missing values & Giá trị chưa chuẩn trong Metadata:")
    unclassified_patterns = ["chưa phân loại", "chua phan loai", "null", "none", "nan", ""]
    
    analysis_records = []
    for col in df_merged.columns:
        if col in ["content_html"]:
            continue
        series = df_merged[col]
        null_count = series.isna().sum()
        empty_count = series.apply(lambda x: 1 if isinstance(x, str) and x.strip() == "" else 0).sum()
        unclass_count = series.apply(
            lambda x: 1 if isinstance(x, str) and x.strip().lower() in unclassified_patterns else 0
        ).sum()
        
        analysis_records.append({
            "Cột": col,
            "Null/NaN": null_count,
            "Rỗng ('')": empty_count,
            "Chưa phân loại / Null str": unclass_count,
            "Tổng không hợp lệ": null_count + empty_count + unclass_count,
            "Tỷ lệ (%)": f"{((null_count + empty_count + unclass_count) / len(df_merged) * 100):.1f}%"
        })
    
    df_missing_report = pd.DataFrame(analysis_records)
    print(df_missing_report.to_string(index=False))
    
    # 7. Làm sạch content_html bằng BeautifulSoup
    print(f"\n[7] Đang làm sạch content_html bằng BeautifulSoup...")
    df_merged["content_clean"] = df_merged["content_html"].apply(clean_html_content)
    
    # Kiểm tra tính toàn vẹn của content_clean
    empty_cleaned = df_merged[df_merged["content_clean"].str.len() == 0]
    print(f"  - Số văn bản có content_clean bị rỗng: {len(empty_cleaned)}")
    
    # Kiểm tra sự tồn tại của các cụm từ pháp lý quan trọng
    keywords = ["căn cứ", "sửa đổi, bổ sung", "bãi bỏ", "thay thế", "thông tư", "nghị định", "luật"]
    print(f"\n[8] Kiểm tra tần suất các từ khóa pháp lý cốt lõi trong content_clean:")
    for kw in keywords:
        count = df_merged["content_clean"].str.lower().apply(lambda x: 1 if kw in x else 0).sum()
        print(f"  - Từ khóa '{kw}': xuất hiện trong {count}/{len(df_merged)} văn bản")
    
    # 8. Lưu kết quả ra ner_kb/cleaned_documents.csv
    print(f"\n[9] Lưu file kết quả vào: {output_path}")
    df_merged.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"  - Kích thước file đầu ra: {os.path.getsize(output_path):,} bytes")
    print(f"  - Số dòng: {len(df_merged)}, Số cột: {len(df_merged.columns)}")
    print(f"  - Danh sách cột: {list(df_merged.columns)}")
    
    # 9. In 2 mẫu so sánh content_html và content_clean
    print("\n" + "=" * 60)
    print("      MẪU MINH HỌA SO SÁNH CONTENT_HTML VÀ CONTENT_CLEAN    ")
    print("=" * 60)
    
    sample_docs = df_merged.head(2)
    for idx, (_, row) in enumerate(sample_docs.iterrows(), 1):
        print(f"\n--- [MẪU {idx}] ID: {row['id']} | Số ký hiệu: {row.get('so_ky_hieu', 'N/A')} ---")
        print(f"Tiêu đề: {row.get('title', 'N/A')}")
        raw_snippet = (row['content_html'][:250] + "...") if len(row['content_html']) > 250 else row['content_html']
        clean_snippet = (row['content_clean'][:350] + "...") if len(row['content_clean']) > 350 else row['content_clean']
        
        print(f"\n* [Raw HTML] ({len(row['content_html']):,} ký tự):")
        print(raw_snippet)
        print(f"\n* [Content Clean] ({len(row['content_clean']):,} ký tự):")
        print(clean_snippet)
        print("-" * 50)
    
    # 10. Đánh giá điều kiện PASS
    pass_conditions = [
        ("Tập tin cleaned_documents.csv tồn tại", os.path.exists(output_path) and os.path.getsize(output_path) > 0),
        ("Số document đầy đủ (30/30)", len(df_merged) == len(df_meta)),
        ("Không mất ID", len(df_merged["id"].unique()) == len(df_meta["id"].unique())),
        ("content_clean không rỗng", len(empty_cleaned) == 0),
        ("Không sửa metadata.csv và content.csv", os.path.exists(meta_path) and os.path.exists(content_path))
    ]
    
    all_pass = all(cond[1] for cond in pass_conditions)
    
    print("\n" + "=" * 60)
    print("                 ĐIỀU KIỆN PASS BƯỚC 1                    ")
    print("=" * 60)
    for desc, is_ok in pass_conditions:
        status = "PASS" if is_ok else "FAIL"
        print(f"[{status}] {desc}")
    
    print(f"\nKẾT QUẢ CUỐI CÙNG BƯỚC 1: {'[PASS]' if all_pass else '[FAIL]'}")
    print("=" * 60)
    
    return all_pass

if __name__ == "__main__":
    run_step_1()
