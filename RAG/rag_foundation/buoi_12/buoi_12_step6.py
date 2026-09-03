# -*- coding: utf-8 -*-
"""
BƯỚC 6: Validate Relationship và tạo output chính thức
Module: buoi_12_step6.py

Input:
- ner_kb/relationships_raw.csv
- ner_kb/cleaned_documents.csv
- ner_kb/entities.csv

Output:
- ner_kb/relationships.csv
- ner_kb/validation_report.csv
"""

import os
import sys
import io
import re
import pandas as pd

# Ensure UTF-8 output encoding for Windows terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

VALID_REL_TYPES = {
    "THAM_CHIEU",
    "SUA_DOI_BO_SUNG",
    "THAY_THE_BOI",
    "BAN_HANH_BOI",
    "KY_BOI",
    "AP_DUNG_CHO",
    "THUOC_LINH_VUC"
}

def run_step_6():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ner_kb_dir = os.path.join(base_dir, "ner_kb")
    
    raw_rel_path = os.path.join(ner_kb_dir, "relationships_raw.csv")
    cleaned_doc_path = os.path.join(ner_kb_dir, "cleaned_documents.csv")
    entities_path = os.path.join(ner_kb_dir, "entities.csv")
    
    out_valid_rel_path = os.path.join(ner_kb_dir, "relationships.csv")
    out_report_path = os.path.join(ner_kb_dir, "validation_report.csv")
    
    print("=" * 70)
    print("          BƯỚC 6: VALIDATE RELATIONSHIP VÀ TẠO OUTPUT CHÍNH THỨC      ")
    print("=" * 70)
    
    if not os.path.exists(raw_rel_path):
        print(f"LỖI: Không tìm thấy {raw_rel_path}")
        return False
        
    df_raw_rel = pd.read_csv(raw_rel_path, dtype=str)
    df_docs = pd.read_csv(cleaned_doc_path, dtype=str)
    df_entities = pd.read_csv(entities_path, dtype=str)
    
    print(f"\n[1] Đọc dữ liệu đầu vào:")
    print(f"  - relationships_raw.csv : {len(df_raw_rel)} quan hệ")
    print(f"  - cleaned_documents.csv : {len(df_docs)} documents")
    print(f"  - entities.csv            : {len(df_entities)} entities")
    
    # Tập hợp các danh mục chuẩn
    corpus_docs = set(df_docs["so_ky_hieu"].dropna().str.strip().tolist())
    entity_canonicals = set(df_entities["canonical_name"].dropna().str.strip().tolist())
    
    validation_records = []
    seen_edges = set()
    
    pass_count = 0
    fail_count = 0
    fail_reasons = {}
    
    for idx, row in df_raw_rel.iterrows():
        src = str(row.get("source", "")).strip()
        tgt = str(row.get("target", "")).strip()
        rel_type = str(row.get("relationship_type", "")).strip()
        src_type = str(row.get("source_type", "")).strip()
        tgt_type = str(row.get("target_type", "")).strip()
        method = str(row.get("method", "")).strip()
        conf = row.get("confidence", "0.95")
        evidence = str(row.get("evidence", "")).strip()
        
        is_pass = True
        reasons = []
        
        # 1. Kiểm tra Missing field
        if not src:
            is_pass = False
            reasons.append("Source bị rỗng")
        if not tgt:
            is_pass = False
            reasons.append("Target bị rỗng")
        if not rel_type:
            is_pass = False
            reasons.append("Relationship type bị rỗng")
            
        # 2. Kiểm tra Relationship type hợp lệ
        if rel_type not in VALID_REL_TYPES:
            is_pass = False
            reasons.append(f"Relationship type không hợp lệ: '{rel_type}'")
            
        # 3. Kiểm tra Self-loop (Source == Target)
        if src and tgt and src.upper() == tgt.upper():
            is_pass = False
            reasons.append("Self-loop: Source trùng Target")
            
        # 4. Kiểm tra Missing Evidence
        if not evidence or len(evidence.strip()) == 0 or evidence.lower() in ["nan", "null", "none"]:
            is_pass = False
            reasons.append("Missing evidence (Bằng chứng rỗng)")
            
        # 5. Kiểm tra tính hợp lệ của Entity Target đối với quan hệ Doc -> Entity
        if rel_type in ["BAN_HANH_BOI", "KY_BOI", "AP_DUNG_CHO", "THUOC_LINH_VUC"]:
            if tgt not in entity_canonicals:
                is_pass = False
                reasons.append(f"Target entity '{tgt}' không tìm thấy trong entities.csv")
                
        # 6. Kiểm tra Duplicate Edge
        edge_key = (src, tgt, rel_type)
        if edge_key in seen_edges:
            is_pass = False
            reasons.append("Duplicate edge (Quan hệ đã xuất hiện trước đó)")
        else:
            if is_pass:
                seen_edges.add(edge_key)
                
        # Ghi nhận kết quả
        status_str = "PASS" if is_pass else "FAIL"
        reason_str = "; ".join(reasons) if reasons else "OK"
        
        if is_pass:
            pass_count += 1
        else:
            fail_count += 1
            for r in reasons:
                fail_reasons[r] = fail_reasons.get(r, 0) + 1
                
        validation_records.append({
            "source": src,
            "target": tgt,
            "relationship_type": rel_type,
            "source_type": src_type,
            "target_type": tgt_type,
            "method": method,
            "confidence": conf,
            "evidence": evidence,
            "validation_status": status_str,
            "fail_reason": reason_str
        })
        
    df_val = pd.DataFrame(validation_records)
    
    # 7. Lưu file validation_report.csv
    print(f"\n[2] Lưu báo cáo kiểm định: {out_report_path}")
    df_val.to_csv(out_report_path, index=False, encoding="utf-8-sig")
    print(f"  - Kích thước: {os.path.getsize(out_report_path):,} bytes ({len(df_val)} dòng)")
    
    # 8. Lưu file relationships.csv (chỉ chứa các relation đạt chuẩn PASS)
    df_pass = df_val[df_val["validation_status"] == "PASS"].copy()
    # Bỏ 2 cột validation để giữ đúng schema chính thức
    df_pass_final = df_pass[["source", "target", "relationship_type", "source_type", "target_type", "method", "confidence", "evidence"]]
    
    print(f"\n[3] Lưu quan hệ chính thức đạt chuẩn vào: {out_valid_rel_path}")
    df_pass_final.to_csv(out_valid_rel_path, index=False, encoding="utf-8-sig")
    print(f"  - Kích thước: {os.path.getsize(out_valid_rel_path):,} bytes ({len(df_pass_final)} dòng)")
    
    # 9. Báo cáo thống kê
    print("\n" + "=" * 70)
    print("                    BÁO CÁO THỐNG KÊ BƯỚC 6                      ")
    print("=" * 70)
    print(f"1. Tổng số relation raw đầu vào : {len(df_raw_rel)}")
    print(f"2. Số lượng relation PASS       : {pass_count} ({pass_count/len(df_raw_rel)*100:.1f}%)")
    print(f"3. Số lượng relation FAIL       : {fail_count} ({fail_count/len(df_raw_rel)*100:.1f}%)")
    
    print(f"\n4. Số lượng relation PASS theo loại quan hệ:")
    pass_type_counts = df_pass_final["relationship_type"].value_counts()
    for rtype, cnt in pass_type_counts.items():
        stype = "Doc -> Doc" if rtype in ["THAM_CHIEU", "SUA_DOI_BO_SUNG", "THAY_THE_BOI"] else "Doc -> Entity"
        print(f"  - {rtype:<18} ({stype:<12}): {cnt:>3} relations")
    print(f"  -------------------------------------------------------------")
    print(f"  - TỔNG RELATION CHÍNH THỨC       : {len(df_pass_final):>3} relations")
    
    print(f"\n5. Phân tích nguyên nhân FAIL phổ biến (nếu có):")
    if fail_reasons:
        for r, cnt in fail_reasons.items():
            print(f"  - [FAIL] {r}: {cnt} trường hợp")
    else:
        print("  - Không có lỗi nào (0 FAIL)")
        
    # 10. In 10 relation PASS mẫu
    print("\n" + "=" * 70)
    print("                      10 RELATION PASS MẪU                       ")
    print("=" * 70)
    
    sample_indices = []
    types_seen = set()
    for idx, r in df_pass_final.iterrows():
        t = r["relationship_type"]
        if t not in types_seen or len(sample_indices) < 10:
            sample_indices.append(idx)
            types_seen.add(t)
        if len(sample_indices) >= 10:
            break
            
    sample_df = df_pass_final.loc[sample_indices]
    for idx, (_, r) in enumerate(sample_df.iterrows(), 1):
        print(f"[{idx:02d}] ({r['source']}) --[:{r['relationship_type']}]--> ({r['target']})")
        print(f"     Type: {r['source_type']} -> {r['target_type']} | Method: {r['method']} (Conf: {r['confidence']})")
        print(f"     Evidence: {r['evidence'][:130]}...")
        print("-" * 70)
        
    # 11. Đánh giá điều kiện PASS
    pass_conditions = [
        ("Tập tin relationships.csv tồn tại", os.path.exists(out_valid_rel_path) and os.path.getsize(out_valid_rel_path) > 0),
        ("Tập tin validation_report.csv tồn tại", os.path.exists(out_report_path) and os.path.getsize(out_report_path) > 0),
        ("Mọi edge trong relationships.csv có source, target và type", (df_pass_final["source"].str.len() > 0).all() and (df_pass_final["target"].str.len() > 0).all()),
        ("FAIL nghiêm trọng = 0 trong file xuất", (df_pass_final["evidence"].str.len() > 0).all()),
        ("Không có duplicate edge trong relationships.csv", len(df_pass_final) == len(df_pass_final.drop_duplicates(subset=["source", "target", "relationship_type"])))
    ]
    
    all_pass = all(cond[1] for cond in pass_conditions)
    
    print("\n" + "=" * 70)
    print("                 ĐIỀU KIỆN PASS BƯỚC 6                    ")
    print("=" * 70)
    for desc, is_ok in pass_conditions:
        status = "PASS" if is_ok else "FAIL"
        print(f"[{status}] {desc}")
        
    print(f"\nKẾT QUẢ CUỐI CÙNG BƯỚC 6: {'[PASS]' if all_pass else '[FAIL]'}")
    print("=" * 70)
    
    return all_pass

if __name__ == "__main__":
    run_step_6()
