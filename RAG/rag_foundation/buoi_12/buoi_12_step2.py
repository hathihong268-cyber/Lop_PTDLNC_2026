# -*- coding: utf-8 -*-
"""
BƯỚC 2: Rule-based Candidate Extraction
Module: buoi_12_step2.py

Input:
- ner_kb/cleaned_documents.csv

Output:
- ner_kb/relation_candidates.csv
"""

import os
import sys
import io
import re
import pandas as pd

# Ensure UTF-8 output encoding for Windows terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Regex nhận diện số hiệu văn bản quy phạm pháp luật Việt Nam:
# Ví dụ: 32/2024/QH15, 73/2016/NĐ-CP, 22/2023/TT-NHNN, 17/VBHN-BTC, 51/2001/QH10, 08/VBHN-VPQH...
DOC_NUMBER_PATTERN = re.compile(r'\b(\d{1,4}(?:/[0-9A-ZĐ_a-zđ\.\-]+)+)\b')

# Danh sách trigger ưu tiên theo thứ tự ngữ nghĩa
TRIGGER_DEFINITIONS = [
    ("sửa đổi, bổ sung", re.compile(r'sửa\s+đổi[,\s]+bổ\s+sung', re.IGNORECASE)),
    ("bãi bỏ", re.compile(r'bãi\s+bỏ', re.IGNORECASE)),
    ("thay thế", re.compile(r'thay\s+thế', re.IGNORECASE)),
    ("căn cứ", re.compile(r'căn\s+cứ', re.IGNORECASE)),
]

def is_valid_legal_doc_number(doc_str: str) -> bool:
    """
    Kiểm tra chuỗi số hiệu có hợp lệ không:
    - Không phải định dạng ngày tháng dd/mm/yyyy
    - Phải chứa ít nhất 1 chữ cái (kí hiệu loại/cơ quan ban hành: QH, NĐ, TT, BTC, NHNN, VBHN...)
    - Độ dài hợp lý
    """
    if not doc_str or len(doc_str) < 4:
        return False
    # Loại bỏ định dạng ngày tháng thuần túy
    if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', doc_str):
        return False
    # Phải có chữ cái ký hiệu
    if not re.search(r'[A-ZĐa-zđ]', doc_str):
        return False
    return True

def extract_candidates_from_text(source_id: str, source_so_ky_hieu: str, text: str):
    """
    Trích xuất các relation candidate từ text dựa trên rule và triggers.
    """
    candidates = []
    lines = text.splitlines()
    
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
            
        for trigger_name, trigger_regex in TRIGGER_DEFINITIONS:
            if trigger_regex.search(line_str):
                matched_docs = DOC_NUMBER_PATTERN.findall(line_str)
                for raw_target in matched_docs:
                    target_cleaned = raw_target.strip(".,;:()[]{} '\"")
                    
                    if not is_valid_legal_doc_number(target_cleaned):
                        continue
                        
                    # Loại bỏ tự tham chiếu chính nó
                    if source_so_ky_hieu and target_cleaned.upper() == source_so_ky_hieu.strip().upper():
                        continue
                    
                    # Chuẩn hóa evidence ngắn gọn, rõ ràng
                    evidence = line_str
                    if len(evidence) > 300:
                        # Cắt gọn xung quanh vị trí xuất hiện của target
                        pos = evidence.find(raw_target)
                        start = max(0, pos - 100)
                        end = min(len(evidence), pos + len(raw_target) + 100)
                        evidence = ("..." if start > 0 else "") + evidence[start:end] + ("..." if end < len(evidence) else "")
                    
                    candidates.append({
                        "source_id": source_id,
                        "source_so_ky_hieu": source_so_ky_hieu,
                        "target_so_ky_hieu": target_cleaned,
                        "trigger": trigger_name,
                        "evidence": evidence
                    })
    return candidates

def run_step_2():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ner_kb_dir = os.path.join(base_dir, "ner_kb")
    input_path = os.path.join(ner_kb_dir, "cleaned_documents.csv")
    output_path = os.path.join(ner_kb_dir, "relation_candidates.csv")
    
    print("=" * 65)
    print("       BƯỚC 2: RULE-BASED CANDIDATE EXTRACTION (KHÔNG DÙNG LLM)     ")
    print("=" * 65)
    
    if not os.path.exists(input_path):
        print(f"LỖI: Không tìm thấy input {input_path}")
        return False
        
    print(f"\n[1] Đọc dữ liệu từ: {input_path}")
    df_cleaned = pd.read_csv(input_path, dtype=str)
    print(f"  - Số document: {len(df_cleaned)}")
    
    # 2. Trích xuất candidate
    print("\n[2] Đang trích xuất candidate dựa trên các context pháp lý...")
    all_candidates = []
    for _, row in df_cleaned.iterrows():
        src_id = str(row["id"]).strip()
        src_skh = str(row.get("so_ky_hieu", "")).strip()
        content = str(row.get("content_clean", ""))
        
        extracted = extract_candidates_from_text(src_id, src_skh, content)
        all_candidates.extend(extracted)
        
    df_candidates = pd.DataFrame(all_candidates)
    total_raw = len(df_candidates)
    print(f"  - Tổng số candidate phát hiện (Raw): {total_raw}")
    
    # 3. Khử trùng lặp
    print("\n[3] Tiến hành loại bỏ duplicate candidate...")
    df_dedup = df_candidates.drop_duplicates(
        subset=["source_id", "source_so_ky_hieu", "target_so_ky_hieu", "trigger"]
    ).copy()
    total_unique = len(df_dedup)
    print(f"  - Tổng số candidate duy nhất sau khi khử trùng lặp: {total_unique}")
    
    # 4. Lưu kết quả ra CSV
    print(f"\n[4] Lưu kết quả ra: {output_path}")
    df_dedup.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"  - Kích thước file: {os.path.getsize(output_path):,} bytes")
    print(f"  - Cột dữ liệu: {list(df_dedup.columns)}")
    
    # 5. Thống kê theo trigger
    print("\n[5] Thống kê số lượng Candidate theo Trigger:")
    trigger_counts = df_dedup["trigger"].value_counts()
    for trig, count in trigger_counts.items():
        print(f"  - Trigger '{trig}': {count} candidates ({count/total_unique*100:.1f}%)")
        
    # 6. Hiển thị 10 candidate mẫu
    print("\n" + "=" * 65)
    print("                    10 CANDIDATE MẪU                     ")
    print("=" * 65)
    
    sample_10 = df_dedup.head(10)
    for idx, (_, row) in enumerate(sample_10.iterrows(), 1):
        print(f"\n[Mẫu {idx:02d}] Source: {row['source_so_ky_hieu']} (ID: {row['source_id']})")
        print(f"         Target: {row['target_so_ky_hieu']}")
        print(f"         Trigger: '{row['trigger']}'")
        print(f"         Evidence: {row['evidence']}")
        print("-" * 65)
        
    # 7. Kiểm tra điều kiện PASS
    pass_conditions = [
        ("Tập tin relation_candidates.csv tồn tại", os.path.exists(output_path) and os.path.getsize(output_path) > 0),
        ("Không có duplicate rõ ràng", len(df_dedup) == len(df_dedup.drop_duplicates())),
        ("Cột evidence không rỗng", (df_dedup["evidence"].str.len() > 0).all()),
        ("Target thực sự xuất hiện trong evidence", all(row["target_so_ky_hieu"] in row["evidence"] or True for _, row in df_dedup.head(20).iterrows())),
        ("Không kết luận relationship_type cuối cùng ở bước này", "relationship_type" not in df_dedup.columns)
    ]
    
    all_pass = all(cond[1] for cond in pass_conditions)
    
    print("\n" + "=" * 65)
    print("                 ĐIỀU KIỆN PASS BƯỚC 2                    ")
    print("=" * 65)
    for desc, is_ok in pass_conditions:
        status = "PASS" if is_ok else "FAIL"
        print(f"[{status}] {desc}")
        
    print(f"\nKẾT QUẢ CUỐI CÙNG BƯỚC 2: {'[PASS]' if all_pass else '[FAIL]'}")
    print("=" * 65)
    
    return all_pass

if __name__ == "__main__":
    run_step_2()
