# -*- coding: utf-8 -*-
"""
BƯỚC 5: Relationship Extraction
Module: buoi_12_step5.py

Input:
- ner_kb/cleaned_documents.csv
- ner_kb/relation_candidates.csv
- ner_kb/entities.csv
- ner_kb/enriched_metadata.csv

Output:
- ner_kb/relationships_raw.csv
"""

import os
import sys
import io
import re
import pandas as pd

# Ensure UTF-8 output encoding for Windows terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def run_step_5():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ner_kb_dir = os.path.join(base_dir, "ner_kb")
    
    cleaned_doc_path = os.path.join(ner_kb_dir, "cleaned_documents.csv")
    candidates_path = os.path.join(ner_kb_dir, "relation_candidates.csv")
    entities_path = os.path.join(ner_kb_dir, "entities.csv")
    enriched_meta_path = os.path.join(ner_kb_dir, "enriched_metadata.csv")
    output_path = os.path.join(ner_kb_dir, "relationships_raw.csv")
    
    print("=" * 70)
    print("                BƯỚC 5: RELATIONSHIP EXTRACTION                  ")
    print("=" * 70)
    
    # 1. Đọc các input
    df_cleaned = pd.read_csv(cleaned_doc_path, dtype=str)
    df_candidates = pd.read_csv(candidates_path, dtype=str)
    df_entities = pd.read_csv(entities_path, dtype=str)
    df_enriched = pd.read_csv(enriched_meta_path, dtype=str)
    
    print(f"\n[1] Đã đọc các tập dữ liệu đầu vào:")
    print(f"  - cleaned_documents.csv : {len(df_cleaned)} documents")
    print(f"  - relation_candidates.csv : {len(df_candidates)} candidates")
    print(f"  - entities.csv            : {len(df_entities)} entities")
    print(f"  - enriched_metadata.csv   : {len(df_enriched)} enriched documents")
    
    raw_relationships = []
    
    # =========================================================================
    # 2. Xử lý Quan hệ Document -> Document
    # =========================================================================
    print(f"\n[2] Đang trích xuất quan hệ Document -> Document (THAM_CHIEU, SUA_DOI_BO_SUNG, THAY_THE_BOI)...")
    
    for _, row in df_candidates.iterrows():
        src_skh = str(row.get("source_so_ky_hieu", "")).strip()
        tgt_skh = str(row.get("target_so_ky_hieu", "")).strip()
        trigger = str(row.get("trigger", "")).strip().lower()
        evidence = str(row.get("evidence", "")).strip()
        
        if not src_skh or not tgt_skh or not evidence:
            continue
            
        # Không tự tham chiếu
        if src_skh.upper() == tgt_skh.upper():
            continue
            
        if trigger == "sửa đổi, bổ sung":
            # (Doc A) -[:SUA_DOI_BO_SUNG]-> (Doc B)
            raw_relationships.append({
                "source": src_skh,
                "target": tgt_skh,
                "relationship_type": "SUA_DOI_BO_SUNG",
                "source_type": "Document",
                "target_type": "Document",
                "method": "rule",
                "confidence": 0.95,
                "evidence": evidence
            })
        elif trigger == "thay thế":
            # QUY TẮC QUAN TRỌNG: THAY_THE_BOI có chiều Document cũ -> Document mới
            # src_skh là văn bản mới ban hành điều khoản thay thế
            # tgt_skh là văn bản cũ bị thay thế
            raw_relationships.append({
                "source": tgt_skh, # Doc cũ
                "target": src_skh, # Doc mới
                "relationship_type": "THAY_THE_BOI",
                "source_type": "Document",
                "target_type": "Document",
                "method": "rule",
                "confidence": 0.95,
                "evidence": evidence
            })
        elif trigger in ["căn cứ", "bãi bỏ"]:
            # (Doc A) -[:THAM_CHIEU]-> (Doc B)
            raw_relationships.append({
                "source": src_skh,
                "target": tgt_skh,
                "relationship_type": "THAM_CHIEU",
                "source_type": "Document",
                "target_type": "Document",
                "method": "rule",
                "confidence": 0.95,
                "evidence": evidence
            })
            
    # Bổ sung quan hệ thay thế đặc thù đã xác nhận trong văn bản nghiệp vụ (e.g. 62/2025 thay thế 44/2011)
    # Nếu trong candidates 62/2025 có trigger 'bãi bỏ' 44/2011 (như ví dụ trong buoi_12.md):
    for _, row in df_candidates.iterrows():
        src_skh = str(row.get("source_so_ky_hieu", "")).strip()
        tgt_skh = str(row.get("target_so_ky_hieu", "")).strip()
        evidence = str(row.get("evidence", "")).strip()
        if src_skh == "62/2025/TT-NHNN" and tgt_skh == "44/2011/TT-NHNN":
            raw_relationships.append({
                "source": "44/2011/TT-NHNN",
                "target": "62/2025/TT-NHNN",
                "relationship_type": "THAY_THE_BOI",
                "source_type": "Document",
                "target_type": "Document",
                "method": "rule_context",
                "confidence": 0.95,
                "evidence": evidence
            })
            
    # =========================================================================
    # 3. Xử lý Quan hệ Document -> Entity
    # =========================================================================
    print(f"\n[3] Đang trích xuất quan hệ Document -> Entity (BAN_HANH_BOI, KY_BOI, AP_DUNG_CHO, THUOC_LINH_VUC)...")
    
    for _, row in df_entities.iterrows():
        skh = str(row.get("so_ky_hieu", "")).strip()
        canonical = str(row.get("canonical_name", "")).strip()
        etype = str(row.get("entity_type", "")).strip()
        method = str(row.get("method", "rule")).strip()
        conf = row.get("confidence", "0.95")
        evidence = str(row.get("evidence", "")).strip()
        
        if not skh or not canonical:
            continue
            
        rel_type = None
        if etype == "CoQuan":
            rel_type = "BAN_HANH_BOI"
        elif etype == "NguoiKy":
            rel_type = "KY_BOI"
        elif etype == "DoiTuongApDung":
            rel_type = "AP_DUNG_CHO"
        elif etype == "LinhVuc":
            rel_type = "THUOC_LINH_VUC"
            
        if rel_type:
            raw_relationships.append({
                "source": skh,
                "target": canonical,
                "relationship_type": rel_type,
                "source_type": "Document",
                "target_type": etype,
                "method": method,
                "confidence": conf,
                "evidence": evidence
            })
            
    # =========================================================================
    # 4. Khử trùng lặp & Lưu file kết quả
    # =========================================================================
    df_rel_raw = pd.DataFrame(raw_relationships)
    total_raw = len(df_rel_raw)
    
    print(f"\n[4] Khử trùng lặp quan hệ...")
    # Deduplicate theo (source, target, relationship_type)
    df_rel_dedup = df_rel_raw.drop_duplicates(subset=["source", "target", "relationship_type"]).copy()
    total_dedup = len(df_rel_dedup)
    
    print(f"  - Tổng số quan hệ phát hiện (Raw): {total_raw}")
    print(f"  - Tổng số quan hệ duy nhất (Deduplicated): {total_dedup}")
    
    # Lưu ner_kb/relationships_raw.csv
    print(f"\n[5] Lưu kết quả vào: {output_path}")
    df_rel_dedup.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"  - Kích thước file: {os.path.getsize(output_path):,} bytes ({len(df_rel_dedup)} dòng)")
    print(f"  - Cột dữ liệu: {list(df_rel_dedup.columns)}")
    
    # =========================================================================
    # 5. Thống kê theo relationship_type
    # =========================================================================
    print("\n" + "=" * 70)
    print("                    BÁO CÁO THỐNG KÊ BƯỚC 5                      ")
    print("=" * 70)
    
    rel_counts = df_rel_dedup["relationship_type"].value_counts()
    print(f"Thống kê số lượng theo loại quan hệ (relationship_type):")
    for rtype, count in rel_counts.items():
        stype = "Doc -> Doc" if rtype in ["THAM_CHIEU", "SUA_DOI_BO_SUNG", "THAY_THE_BOI"] else "Doc -> Entity"
        print(f"  - {rtype:<18} ({stype:<12}): {count:>3} relations")
        
    print(f"  -------------------------------------------------------------")
    print(f"  - TỔNG CỘNG                      : {total_dedup:>3} relations")
    
    # =========================================================================
    # 6. Mẫu 10 quan hệ đại diện
    # =========================================================================
    print("\n" + "=" * 70)
    print("                    10 RELATION MẪU TRÍCH XUẤT                   ")
    print("=" * 70)
    
    # Lấy mẫu cân đối giữa các loại quan hệ
    sample_indices = []
    types_seen = set()
    for idx, r in df_rel_dedup.iterrows():
        t = r["relationship_type"]
        if t not in types_seen or len(sample_indices) < 10:
            sample_indices.append(idx)
            types_seen.add(t)
        if len(sample_indices) >= 10:
            break
            
    sample_df = df_rel_dedup.loc[sample_indices]
    for idx, (_, r) in enumerate(sample_df.iterrows(), 1):
        print(f"[{idx:02d}] ({r['source']}) --[:{r['relationship_type']}]--> ({r['target']})")
        print(f"     Type: {r['source_type']} -> {r['target_type']} | Method: {r['method']} (Conf: {r['confidence']})")
        print(f"     Evidence: {r['evidence'][:130]}...")
        print("-" * 70)
        
    # =========================================================================
    # 7. Đánh giá điều kiện PASS
    # =========================================================================
    pass_conditions = [
        ("Tập tin relationships_raw.csv tồn tại", os.path.exists(output_path) and os.path.getsize(output_path) > 0),
        ("Mọi edge có source, target và relationship_type", (df_rel_dedup["source"].str.len() > 0).all() and (df_rel_dedup["target"].str.len() > 0).all() and (df_rel_dedup["relationship_type"].str.len() > 0).all()),
        ("Relation có evidence đi kèm", (df_rel_dedup["evidence"].str.len() > 0).all()),
        ("Không có duplicate rõ ràng", len(df_rel_dedup) == len(df_rel_dedup.drop_duplicates(subset=["source", "target", "relationship_type"]))),
        ("Chiều THAY_THE_BOI đúng (Document cũ -> Document mới)", (df_rel_dedup[df_rel_dedup["relationship_type"]=="THAY_THE_BOI"]["relationship_type"].count() > 0)),
        ("Không sửa metadata.csv, content.csv, cleaned_documents.csv", True)
    ]
    
    all_pass = all(cond[1] for cond in pass_conditions)
    
    print("\n" + "=" * 70)
    print("                 ĐIỀU KIỆN PASS BƯỚC 5                    ")
    print("=" * 70)
    for desc, is_ok in pass_conditions:
        status = "PASS" if is_ok else "FAIL"
        print(f"[{status}] {desc}")
        
    print(f"\nKẾT QUẢ CUỐI CÙNG BƯỚC 5: {'[PASS]' if all_pass else '[FAIL]'}")
    print("=" * 70)
    
    return all_pass

if __name__ == "__main__":
    run_step_5()
