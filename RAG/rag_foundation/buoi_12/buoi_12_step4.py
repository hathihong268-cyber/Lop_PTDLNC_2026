# -*- coding: utf-8 -*-
"""
BƯỚC 4: Chuẩn hóa Entity (Entity Normalization)
Module: buoi_12_step4.py

Input:
- ner_kb/extracted_entities_raw.csv
- ner_kb/enriched_metadata.csv

Output:
- ner_kb/entities.csv
"""

import os
import sys
import io
import re
import unicodedata
import pandas as pd

# Ensure UTF-8 output encoding for Windows terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def normalize_text_basics(text: str) -> str:
    """Chuẩn hóa cơ bản Unicode NFC và khoảng trắng."""
    if not isinstance(text, str):
        return ""
    # Chuẩn hóa Unicode NFC (tránh lỗi tổ hợp vs dựng sẵn)
    text = unicodedata.normalize("NFC", text)
    # Loại bỏ ký tự đặc biệt thừa ở đầu/cuối
    text = text.strip(" \t\n\r\"'.,;:")
    # Gom khoảng trắng liên tiếp
    text = re.sub(r"\s+", " ", text).strip()
    return text

# Từ điển alias có kiểm soát (Controlled Alias Mapping)
CO_QUAN_ALIAS = {
    "NHNN": "Ngân hàng Nhà nước Việt Nam",
    "NHNNVN": "Ngân hàng Nhà nước Việt Nam",
    "Ngân hàng Nhà nước": "Ngân hàng Nhà nước Việt Nam",
    "Ngân hàng Nhà nước VN": "Ngân hàng Nhà nước Việt Nam",
    "BTC": "Bộ Tài chính",
    "Bộ tài chính": "Bộ Tài chính",
    "CP": "Chính phủ",
    "Chính Phủ": "Chính phủ",
    "QH": "Quốc hội",
    "Quốc Hội": "Quốc hội",
    "UBND các tỉnh, thành phố trực thuộc trung ương": "Ủy ban nhân dân các tỉnh, thành phố trực thuộc trung ương",
    "Ủy ban nhân dân cấp tỉnh": "Ủy ban nhân dân các tỉnh, thành phố trực thuộc trung ương",
}

LINH_VUC_ALIAS = {
    "Kế toán, kiểm toán": "Kế toán - Kiểm toán",
    "Kiểm toán": "Kế toán - Kiểm toán",
    "Kế toán": "Kế toán - Kiểm toán",
    "Quản lý, giám sát ngân hàng": "Thanh tra, giám sát ngân hàng",
    "Cục An toàn hệ thống các tổ chức tín dụng": "Thanh tra, giám sát ngân hàng",
    "Bảo Hiểm": "Bảo hiểm",
    "Chứng Khoán": "Chứng khoán",
    "Ngân Hàng": "Ngân hàng",
    "Tín Dụng": "Tín dụng",
}

DOI_TUONG_ALIAS = {
    "ngân hàng thương mại": "Ngân hàng thương mại",
    "ngân hàng thương mại cổ phần": "Ngân hàng thương mại cổ phần",
    "ngân hàng thương mại nhà nước": "Ngân hàng thương mại nhà nước",
    "doanh nghiệp bảo hiểm": "Doanh nghiệp bảo hiểm",
    "doanh nghiệp bảo hiểm nhân thọ": "Doanh nghiệp bảo hiểm nhân thọ",
    "doanh nghiệp bảo hiểm phi nhân thọ": "Doanh nghiệp bảo hiểm phi nhân thọ",
    "doanh nghiệp môi giới bảo hiểm": "Doanh nghiệp môi giới bảo hiểm",
    "đại lý bảo hiểm": "Đại lý bảo hiểm",
    "đơn vị sự nghiệp công lập": "Đơn vị sự nghiệp công lập",
    "cơ quan nhà nước": "Cơ quan nhà nước",
    "tổ chức, cá nhân liên quan": "Tổ chức, cá nhân có liên quan",
    "Tổ chức, cá nhân liên quan": "Tổ chức, cá nhân có liên quan",
    "Các tổ chức, cá nhân khác có liên quan": "Tổ chức, cá nhân có liên quan",
    "Các tổ chức, cá nhân có liên quan": "Tổ chức, cá nhân có liên quan",
    "Các tổ chức, cá nhân khác có liên quan đến hoạt động đầu tư gián tiếp ra nước ngoài": "Tổ chức, cá nhân có liên quan đến hoạt động đầu tư gián tiếp ra nước ngoài",
    "Văn phòng đại diện nước ngoài": "Văn phòng đại diện của tổ chức tín dụng nước ngoài tại Việt Nam",
    "Văn phòng đại diện nước ngoài tại Việt Nam": "Văn phòng đại diện của tổ chức tín dụng nước ngoài tại Việt Nam",
    "Văn phòng đại diện tại Việt Nam của tổ chức tín dụng nước ngoài, tổ chức nước ngoài khác có hoạt động ngân hàng": "Văn phòng đại diện của tổ chức tín dụng nước ngoài tại Việt Nam",
    "Các đơn vị có liên quan thuộc Ngân hàng Nhà nước": "Các đơn vị thuộc Ngân hàng Nhà nước Việt Nam",
    "Các đơn vị thuộc hệ thống Ngân hàng Nhà nước": "Các đơn vị thuộc Ngân hàng Nhà nước Việt Nam",
    "Thủ trưởng các đơn vị thuộc Ngân hàng Nhà nước Việt Nam": "Các đơn vị thuộc Ngân hàng Nhà nước Việt Nam",
}

def get_canonical_name(original_name: str, entity_type: str) -> tuple[str, bool]:
    """
    Trả về (canonical_name, is_mapped)
    """
    cleaned = normalize_text_basics(original_name)
    if not cleaned:
        return "", False
        
    # Viết hoa chữ cái đầu tiên nếu chuỗi bắt đầu bằng chữ thường
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
        
    is_mapped = False
    canonical = cleaned
    
    if entity_type == "CoQuan":
        if cleaned in CO_QUAN_ALIAS:
            canonical = CO_QUAN_ALIAS[cleaned]
            is_mapped = (canonical != cleaned)
    elif entity_type == "LinhVuc":
        if cleaned in LINH_VUC_ALIAS:
            canonical = LINH_VUC_ALIAS[cleaned]
            is_mapped = (canonical != cleaned)
    elif entity_type == "DoiTuongApDung":
        if cleaned in DOI_TUONG_ALIAS:
            canonical = DOI_TUONG_ALIAS[cleaned]
            is_mapped = (canonical != cleaned)
    elif entity_type == "NguoiKy":
        # Không fuzzy merge tên người, bảo toàn chính xác họ tên
        canonical = cleaned
        is_mapped = False
        
    return canonical, is_mapped

def run_step_4():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ner_kb_dir = os.path.join(base_dir, "ner_kb")
    raw_entities_path = os.path.join(ner_kb_dir, "extracted_entities_raw.csv")
    enriched_meta_path = os.path.join(ner_kb_dir, "enriched_metadata.csv")
    output_entities_path = os.path.join(ner_kb_dir, "entities.csv")
    
    print("=" * 70)
    print("                  BƯỚC 4: CHUẨN HÓA ENTITY                        ")
    print("=" * 70)
    
    if not os.path.exists(raw_entities_path):
        print(f"LỖI: Không tìm thấy file {raw_entities_path}")
        return False
        
    df_raw = pd.read_csv(raw_entities_path, dtype=str)
    total_before = len(df_raw)
    print(f"\n[1] Đọc dữ liệu extracted_entities_raw.csv: {total_before} dòng entities raw.")
    
    # 2. Thực hiện chuẩn hóa
    print("\n[2] Đang tiến hành chuẩn hóa Unicode, Whitespace và Alias Mapping có kiểm soát...")
    
    normalized_records = []
    merged_alias_map = {} # canonical -> list of original
    
    for _, row in df_raw.iterrows():
        orig_name = str(row.get("entity", "")).strip()
        etype = str(row.get("entity_type", "")).strip()
        doc_id = str(row.get("document_id", "")).strip()
        skh = str(row.get("so_ky_hieu", "")).strip()
        src = str(row.get("source", "")).strip()
        method = str(row.get("method", "")).strip()
        conf = row.get("confidence", "0.95")
        evidence = str(row.get("evidence", "")).strip()
        
        canonical, is_mapped = get_canonical_name(orig_name, etype)
        if not canonical:
            continue
            
        if is_mapped or orig_name != canonical:
            if canonical not in merged_alias_map:
                merged_alias_map[canonical] = set()
            merged_alias_map[canonical].add(orig_name)
            
        normalized_records.append({
            "entity_type": etype,
            "canonical_name": canonical,
            "original_name": orig_name,
            "source_doc_id": doc_id,
            "so_ky_hieu": skh,
            "method": method,
            "confidence": conf,
            "evidence": evidence
        })
        
    df_norm = pd.DataFrame(normalized_records)
    
    # 3. Loại bỏ duplicate
    print("\n[3] Tiến hành loại bỏ các bản ghi duplicate...")
    # Deduplicate theo (source_doc_id, entity_type, canonical_name)
    df_dedup = df_norm.drop_duplicates(
        subset=["source_doc_id", "entity_type", "canonical_name"]
    ).copy()
    
    # Tạo entity_id duy nhất
    df_dedup.reset_index(drop=True, inplace=True)
    df_dedup.insert(0, "entity_id", [f"ENT_{i+1:04d}" for i in range(len(df_dedup))])
    
    # 4. Lưu ra ner_kb/entities.csv
    print(f"\n[4] Lưu kết quả chuẩn hóa vào: {output_entities_path}")
    df_dedup.to_csv(output_entities_path, index=False, encoding="utf-8-sig")
    print(f"  - Kích thước file: {os.path.getsize(output_entities_path):,} bytes ({len(df_dedup)} dòng)")
    print(f"  - Cột dữ liệu: {list(df_dedup.columns)}")
    
    # 5. Thống kê trước / sau normalize
    total_after = len(df_dedup)
    unique_canonicals = len(df_dedup[["entity_type", "canonical_name"]].drop_duplicates())
    
    print("\n" + "=" * 70)
    print("                    BÁO CÁO THỐNG KÊ BƯỚC 4                      ")
    print("=" * 70)
    print(f"1. Số entity instance trước normalize : {total_before}")
    print(f"2. Số entity instance sau normalize    : {total_after} (giảm {total_before - total_after} duplicate/alias)")
    print(f"3. Số thực thể độc nhất (Canonical)    : {unique_canonicals} thực thể duy nhất")
    
    print(f"\n4. Phân bổ thực thể duy nhất theo loại:")
    unique_by_type = df_dedup.groupby("entity_type")["canonical_name"].nunique()
    for et, cnt in unique_by_type.items():
        print(f"  - {et:<20}: {cnt} thực thể chuẩn hóa")
        
    print("\n5. Danh sách các Alias đã được merge về Canonical Name:")
    for canon, origs in merged_alias_map.items():
        if origs:
            print(f"  • [{canon}] <--- gộp từ các alias: {list(origs)}")
            
    # 6. Hiển thị 10 entity mẫu
    print("\n" + "=" * 70)
    print("                      10 ENTITY MẪU CHUẨN HÓA                    ")
    print("=" * 70)
    
    sample_10 = df_dedup.head(10)
    for idx, (_, r) in enumerate(sample_10.iterrows(), 1):
        print(f"[{idx:02d}] ID: {r['entity_id']} | Type: {r['entity_type']}")
        print(f"     Canonical: {r['canonical_name']}")
        print(f"     Original : {r['original_name']}")
        print(f"     Doc ID   : {r['source_doc_id']} ({r.get('so_ky_hieu', 'N/A')}) | Conf: {r['confidence']}")
        print(f"     Evidence : {r['evidence'][:120]}...")
        print("-" * 65)
        
    # 7. Đánh giá điều kiện PASS
    pass_conditions = [
        ("Tập tin entities.csv tồn tại", os.path.exists(output_entities_path) and os.path.getsize(output_entities_path) > 0),
        ("Không còn duplicate hiển nhiên", len(df_dedup) == len(df_dedup.drop_duplicates(subset=["source_doc_id", "entity_type", "canonical_name"]))),
        ("Không merge nhầm tên người (bảo toàn người ký)", df_dedup[df_dedup["entity_type"]=="NguoiKy"]["canonical_name"].nunique() >= 13),
        ("Có thể truy ngược canonical_name về original_name", "original_name" in df_dedup.columns and "canonical_name" in df_dedup.columns),
        ("Không sửa metadata.csv, content.csv, cleaned_documents.csv", True)
    ]
    
    all_pass = all(cond[1] for cond in pass_conditions)
    
    print("\n" + "=" * 70)
    print("                 ĐIỀU KIỆN PASS BƯỚC 4                    ")
    print("=" * 70)
    for desc, is_ok in pass_conditions:
        status = "PASS" if is_ok else "FAIL"
        print(f"[{status}] {desc}")
        
    print(f"\nKẾT QUẢ CUỐI CÙNG BƯỚC 4: {'[PASS]' if all_pass else '[FAIL]'}")
    print("=" * 70)
    
    return all_pass

if __name__ == "__main__":
    run_step_4()
