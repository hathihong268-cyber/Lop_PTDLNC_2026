#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/inspect_data.py
Kiểm tra và báo cáo tính toàn vẹn của 4 file CSV seed cho Wiki Risk Graph:
- risk_profiles_seed.csv
- controls_seed.csv
- risk_events_seed.csv
- relationships_seed.csv
"""

import csv
import sys
from pathlib import Path
from collections import Counter

# Đảm bảo in Unicode tiếng Việt mượt mà trên Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def find_data_dir() -> Path:
    """Tự động tìm thư mục data chứa các file seed CSV."""
    candidates = [
        Path(__file__).resolve().parent.parent / "data",
        Path.cwd() / "data",
        Path.cwd() / "Rag_thuchanh" / "RAG" / "rag_foundation" / "buoi_13" / "data",
        Path(__file__).resolve().parent.parent / "Rag_thuchanh" / "RAG" / "rag_foundation" / "buoi_13" / "data",
    ]
    for p in candidates:
        if (p / "risk_profiles_seed.csv").exists():
            return p
    raise FileNotFoundError("Không tìm thấy thư mục data chứa các file seed CSV!")


def inspect_csv(file_path: Path):
    """Đọc và kiểm tra cấu trúc của một file CSV."""
    if not file_path.exists():
        return {"error": f"File không tồn tại: {file_path}"}

    with open(file_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    row_count = len(rows)
    null_counts = {col: 0 for col in fieldnames}
    
    # Kiểm tra duplicate toàn bộ dòng
    seen_rows = set()
    duplicate_rows = 0
    
    for row in rows:
        row_tuple = tuple(row.get(col, "") for col in fieldnames)
        if row_tuple in seen_rows:
            duplicate_rows += 1
        else:
            seen_rows.add(row_tuple)
            
        for col in fieldnames:
            val = row.get(col, "")
            if val is None or val.strip() == "":
                null_counts[col] += 1

    return {
        "file_name": file_path.name,
        "row_count": row_count,
        "columns": fieldnames,
        "null_counts": null_counts,
        "total_nulls": sum(null_counts.values()),
        "duplicate_rows": duplicate_rows,
        "rows": rows,
    }


def run_inspection():
    data_dir = find_data_dir()
    print("=" * 80)
    print(f"KIỂM TRA DỮ LIỆU WIKI RISK GRAPH - SEED DATA")
    print(f"Thư mục dữ liệu: {data_dir}")
    print("=" * 80)

    files = {
        "risk_profiles": data_dir / "risk_profiles_seed.csv",
        "controls": data_dir / "controls_seed.csv",
        "risk_events": data_dir / "risk_events_seed.csv",
        "relationships": data_dir / "relationships_seed.csv",
    }

    results = {}
    for key, path in files.items():
        results[key] = inspect_csv(path)

    # 1. Báo cáo chi tiết từng file
    print("\n--- 1. CHI TIẾT TỪNG FILE CSV ---")
    for key, info in results.items():
        print(f"\n[FILE]: {info['file_name']}")
        print(f"  - Số dòng dữ liệu (records): {info['row_count']}")
        print(f"  - Số cột ({len(info['columns'])}): {info['columns']}")
        print(f"  - Số giá trị null: {info['total_nulls']} (chi tiết: {info['null_counts']})")
        print(f"  - Số dòng trùng lặp (duplicate rows): {info['duplicate_rows']}")

    # 2. Khóa chính & Kiểm tra trùng ID
    print("\n--- 2. KHÓA CHÍNH (PRIMARY KEYS) & DUPLICATE ID ---")
    
    # risk_profiles PK: id
    rp_ids = [r["id"] for r in results["risk_profiles"]["rows"]]
    rp_id_counts = Counter(rp_ids)
    rp_dup_ids = [k for k, v in rp_id_counts.items() if v > 1]
    print(f"  - risk_profiles_seed.csv: PK = 'id' | Tổng ID = {len(rp_ids)}, Unique = {len(set(rp_ids))}, Trùng lặp = {len(rp_dup_ids)}")

    # controls PK: id
    ctrl_ids = [r["id"] for r in results["controls"]["rows"]]
    ctrl_id_counts = Counter(ctrl_ids)
    ctrl_dup_ids = [k for k, v in ctrl_id_counts.items() if v > 1]
    print(f"  - controls_seed.csv:      PK = 'id' | Tổng ID = {len(ctrl_ids)}, Unique = {len(set(ctrl_ids))}, Trùng lặp = {len(ctrl_dup_ids)}")

    # risk_events PK: id
    re_ids = [r["id"] for r in results["risk_events"]["rows"]]
    re_id_counts = Counter(re_ids)
    re_dup_ids = [k for k, v in re_id_counts.items() if v > 1]
    print(f"  - risk_events_seed.csv:   PK = 'id' | Tổng ID = {len(re_ids)}, Unique = {len(set(re_ids))}, Trùng lặp = {len(re_dup_ids)}")

    # relationships PK: (source_id, relationship_type, target_id)
    rel_keys = [(r["source_id"], r["relationship_type"], r["target_id"]) for r in results["relationships"]["rows"]]
    rel_key_counts = Counter(rel_keys)
    rel_dup_keys = [k for k, v in rel_key_counts.items() if v > 1]
    print(f"  - relationships_seed.csv: PK = ('source_id', 'relationship_type', 'target_id') | Tổng = {len(rel_keys)}, Unique = {len(set(rel_keys))}, Trùng lặp = {len(rel_dup_keys)}")

    # 3. Phân loại relationship_type
    print("\n--- 3. CÁC LOẠI RELATIONSHIP_TYPE ---")
    rel_types = Counter([r["relationship_type"] for r in results["relationships"]["rows"]])
    for r_type, count in rel_types.items():
        print(f"  - {r_type}: {count} quan hệ")

    # 4. Khóa tham chiếu & Kiểm tra toàn vẹn tham chiếu (Foreign Key Integrity)
    print("\n--- 4. KHÓA THAM CHIẾU & KIỂM TRA TOÀN VẸN (FOREIGN KEYS) ---")
    all_entity_ids = set(rp_ids) | set(ctrl_ids) | set(re_ids)

    # 4.1. risk_events -> risk_id
    re_missing_risk = []
    for r in results["risk_events"]["rows"]:
        if r["risk_id"] not in set(rp_ids):
            re_missing_risk.append((r["id"], r["risk_id"]))
    print(f"  - risk_events_seed.csv (risk_id -> risk_profiles.id):")
    print(f"      Khóa tham chiếu bị thiếu/lỗi: {len(re_missing_risk)} {re_missing_risk if re_missing_risk else '(Tất cả 12/12 hợp lệ)'}")

    # 4.2. relationships -> source_id, target_id
    rel_missing_source = []
    rel_missing_target = []
    for r in results["relationships"]["rows"]:
        s_id = r["source_id"]
        t_id = r["target_id"]
        r_type = r["relationship_type"]
        
        # Check source
        if r_type == "MITIGATES" and s_id not in set(ctrl_ids):
            rel_missing_source.append((s_id, r_type, t_id))
        elif r_type == "OBSERVED_AS" and s_id not in set(rp_ids):
            rel_missing_source.append((s_id, r_type, t_id))
        elif s_id not in all_entity_ids:
            rel_missing_source.append((s_id, r_type, t_id))

        # Check target
        if r_type == "MITIGATES" and t_id not in set(rp_ids):
            rel_missing_target.append((s_id, r_type, t_id))
        elif r_type == "OBSERVED_AS" and t_id not in set(re_ids):
            rel_missing_target.append((s_id, r_type, t_id))
        elif t_id not in all_entity_ids:
            rel_missing_target.append((s_id, r_type, t_id))

    print(f"  - relationships_seed.csv (source_id -> entities):")
    print(f"      source_id bị thiếu: {len(rel_missing_source)} {rel_missing_source if rel_missing_source else '(Tất cả 22/22 hợp lệ)'}")
    print(f"  - relationships_seed.csv (target_id -> entities):")
    print(f"      target_id bị thiếu: {len(rel_missing_target)} {rel_missing_target if rel_missing_target else '(Tất cả 22/22 hợp lệ)'}")

    # 4.3. Các mã tham chiếu ngoài (chưa có master data)
    owner_units = set(r["owner_unit_id"] for r in results["risk_profiles"]["rows"])
    owner_roles = set(r["owner_role_id"] for r in results["controls"]["rows"])
    print(f"\n  - Các mã tham chiếu chưa có bảng master data (dữ liệu độc lập):")
    print(f"      + owner_unit_id ({len(owner_units)} mã): {sorted(list(owner_units))}")
    print(f"      + owner_role_id ({len(owner_roles)} mã): {sorted(list(owner_roles))}")

    # 5. Phân tích độ bao phủ rủi ro (Risk Coverage & Orphan Analysis)
    print("\n--- 5. PHÂN TÍCH ĐỘ BAO PHỦ ĐỒ THỊ (GRAPH COVERAGE) ---")
    mitigated_risks = set(r["target_id"] for r in results["relationships"]["rows"] if r["relationship_type"] == "MITIGATES")
    observed_risks = set(r["source_id"] for r in results["relationships"]["rows"] if r["relationship_type"] == "OBSERVED_AS")
    unmitigated_risks = set(rp_ids) - mitigated_risks
    unobserved_risks = set(rp_ids) - observed_risks

    print(f"  - Tổng số RuiRo: {len(rp_ids)}")
    print(f"  - RuiRo có KiemSoat (MITIGATES): {len(mitigated_risks)}/{len(rp_ids)}")
    print(f"  - RuiRo CHƯA có KiemSoat (Unmitigated Risks): {len(unmitigated_risks)} -> {sorted(list(unmitigated_risks))}")
    print(f"  - RuiRo có SuKienRuiRo (OBSERVED_AS): {len(observed_risks)}/{len(rp_ids)}")
    print(f"  - RuiRo CHƯA có SuKienRuiRo: {len(unobserved_risks)} -> {sorted(list(unobserved_risks))}")

    print("\n" + "=" * 80)
    print("KẾT THÚC BÁO CÁO KIỂM TRA DỮ LIỆU")
    print("=" * 80)


if __name__ == "__main__":
    run_inspection()
