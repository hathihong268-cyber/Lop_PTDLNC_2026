#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/build_entities.py
Chuẩn hóa 4 file CSV seed thành 2 bảng chuẩn:
- outputs/entities.csv
- outputs/relations.csv
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


def find_directories():
    """Tự động tìm thư mục data và thư mục outputs."""
    candidates = [
        Path(__file__).resolve().parent.parent / "data",
        Path.cwd() / "data",
        Path.cwd() / "Rag_thuchanh" / "RAG" / "rag_foundation" / "buoi_13" / "data",
        Path(__file__).resolve().parent.parent / "Rag_thuchanh" / "RAG" / "rag_foundation" / "buoi_13" / "data",
    ]
    data_dir = None
    for p in candidates:
        if (p / "risk_profiles_seed.csv").exists():
            data_dir = p
            break
            
    if not data_dir:
        raise FileNotFoundError("Không tìm thấy thư mục data chứa các file seed CSV!")

    # outputs_dir nằm cùng cấp với data_dir
    outputs_dir = data_dir.parent / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    return data_dir, outputs_dir


def read_csv(file_path: Path):
    """Đọc dữ liệu từ file CSV."""
    with open(file_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def build_entities_and_relations():
    data_dir, outputs_dir = find_directories()
    print("=" * 80)
    print("BƯỚC 2: CHUẨN HÓA DỮ LIỆU THÀNH ENTITIES & RELATIONS")
    print(f"Data directory:   {data_dir}")
    print(f"Outputs directory: {outputs_dir}")
    print("=" * 80)

    # 1. Đọc 4 file CSV seed
    risk_profiles = read_csv(data_dir / "risk_profiles_seed.csv")
    controls = read_csv(data_dir / "controls_seed.csv")
    risk_events = read_csv(data_dir / "risk_events_seed.csv")
    relationships = read_csv(data_dir / "relationships_seed.csv")

    entities = []

    # 2. Mapping risk_profiles_seed.csv -> type = RuiRo
    for r in risk_profiles:
        entity = {
            "id": r["id"],
            "type": "RuiRo",
            "name": r["name"],
            "description": r.get("description", ""),
            "source_file": "risk_profiles_seed.csv",
            "data_origin": r.get("data_origin", "SYNTHETIC"),
            "verification_status": r.get("verification_status", "VERIFIED"),
            # Thuộc tính nghiệp vụ riêng của RuiRo
            "category": r.get("category", ""),
            "cause": r.get("cause", ""),
            "event": r.get("event", ""),
            "impact": r.get("impact", ""),
            "inherent_level": r.get("inherent_level", ""),
            "residual_level": r.get("residual_level", ""),
            "owner_unit_id": r.get("owner_unit_id", ""),
            # Các thuộc tính của type khác để trống
            "control_type": "",
            "frequency": "",
            "owner_role_id": "",
            "effectiveness": "",
            "risk_id": "",
            "occurred_at": "",
            "discovered_at": "",
            "severity": "",
            "loss_amount_vnd": "",
        }
        entities.append(entity)

    # 3. Mapping controls_seed.csv -> type = KiemSoat
    for c in controls:
        entity = {
            "id": c["id"],
            "type": "KiemSoat",
            "name": c["name"],
            "description": f"Kiểm soát {c.get('control_type', '')} tần suất {c.get('frequency', '')} - Hiệu quả: {c.get('effectiveness', '')}",
            "source_file": "controls_seed.csv",
            "data_origin": c.get("data_origin", "SYNTHETIC"),
            "verification_status": c.get("verification_status", "VERIFIED"),
            # Thuộc tính nghiệp vụ riêng của KiemSoat
            "category": "",
            "cause": "",
            "event": "",
            "impact": "",
            "inherent_level": "",
            "residual_level": "",
            "owner_unit_id": "",
            "control_type": c.get("control_type", ""),
            "frequency": c.get("frequency", ""),
            "owner_role_id": c.get("owner_role_id", ""),
            "effectiveness": c.get("effectiveness", ""),
            "risk_id": "",
            "occurred_at": "",
            "discovered_at": "",
            "severity": "",
            "loss_amount_vnd": "",
        }
        entities.append(entity)

    # 4. Mapping risk_events_seed.csv -> type = SuKienRuiRo
    for e in risk_events:
        entity = {
            "id": e["id"],
            "type": "SuKienRuiRo",
            "name": e.get("description", f"Sự kiện rủi ro {e['id']}"),
            "description": e.get("description", ""),
            "source_file": "risk_events_seed.csv",
            "data_origin": e.get("data_origin", "SYNTHETIC"),
            "verification_status": e.get("verification_status", "VERIFIED"),
            # Thuộc tính nghiệp vụ riêng của SuKienRuiRo
            "category": "",
            "cause": "",
            "event": "",
            "impact": "",
            "inherent_level": "",
            "residual_level": "",
            "owner_unit_id": "",
            "control_type": "",
            "frequency": "",
            "owner_role_id": "",
            "effectiveness": "",
            "risk_id": e.get("risk_id", ""),
            "occurred_at": e.get("occurred_at", ""),
            "discovered_at": e.get("discovered_at", ""),
            "severity": e.get("severity", ""),
            "loss_amount_vnd": e.get("loss_amount_vnd", "0"),
        }
        entities.append(entity)

    # 5. Xuất outputs/entities.csv
    entities_file = outputs_dir / "entities.csv"
    entity_fieldnames = [
        "id",
        "type",
        "name",
        "description",
        "source_file",
        "data_origin",
        "verification_status",
        "category",
        "cause",
        "event",
        "impact",
        "inherent_level",
        "residual_level",
        "owner_unit_id",
        "control_type",
        "frequency",
        "owner_role_id",
        "effectiveness",
        "risk_id",
        "occurred_at",
        "discovered_at",
        "severity",
        "loss_amount_vnd",
    ]

    with open(entities_file, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=entity_fieldnames)
        writer.writeheader()
        writer.writerows(entities)

    print(f"\n[OK] Đã tạo thành công: {entities_file} ({len(entities)} entities)")

    # 6. Chuẩn hóa relations.csv từ relationships_seed.csv
    entity_ids = {e["id"] for e in entities}
    relations = []
    orphan_references = []

    for idx, r in enumerate(relationships, start=1):
        source_id = r["source_id"].strip()
        target_id = r["target_id"].strip()
        rel_type = r["relationship_type"].strip()
        status = r.get("verification_status", "PROPOSED").strip()
        origin = r.get("data_origin", "SYNTHETIC").strip()

        # Kiểm tra source_id và target_id có tồn tại trong entities.csv không
        is_orphan = False
        if source_id not in entity_ids:
            orphan_references.append(f"Dòng {idx}: source_id '{source_id}' không tồn tại trong entities.csv")
            is_orphan = True
        if target_id not in entity_ids:
            orphan_references.append(f"Dòng {idx}: target_id '{target_id}' không tồn tại trong entities.csv")
            is_orphan = True

        relation = {
            "source_id": source_id,
            "relationship_type": rel_type,
            "target_id": target_id,
            "source": r.get("source", "LAB_SEED"),
            "evidence_quote": r.get("evidence_quote", ""),
            "confidence": r.get("confidence", "1.0"),
            "verification_status": status,
            "data_origin": origin,
        }
        relations.append(relation)

    # 7. Xuất outputs/relations.csv
    relations_file = outputs_dir / "relations.csv"
    relation_fieldnames = [
        "source_id",
        "relationship_type",
        "target_id",
        "source",
        "evidence_quote",
        "confidence",
        "verification_status",
        "data_origin",
    ]

    with open(relations_file, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=relation_fieldnames)
        writer.writeheader()
        writer.writerows(relations)

    print(f"[OK] Đã tạo thành công: {relations_file} ({len(relations)} relations)")

    # 8. Báo cáo thống kê
    print("\n--- BÁO CÁO THỐNG KÊ ---")
    type_counts = Counter(e["type"] for e in entities)
    print("1. Số entity theo từng type:")
    for etype, count in type_counts.items():
        print(f"   - {etype}: {count}")
    print(f"   => Tổng cộng: {len(entities)} entities")

    rel_type_counts = Counter(r["relationship_type"] for r in relations)
    print("\n2. Số relation theo từng relationship_type:")
    for rtype, count in rel_type_counts.items():
        print(f"   - {rtype}: {count}")
    print(f"   => Tổng cộng: {len(relations)} relations")

    print("\n3. Kiểm tra Orphan References:")
    if orphan_references:
        print(f"   [CẢNH BÁO / LỖI] Phát hiện {len(orphan_references)} orphan reference(s):")
        for err in orphan_references:
            print(f"     * {err}")
    else:
        print("   [HOÀN HẢO] 0 orphan reference. Tất cả source_id và target_id đều tồn tại hợp lệ trong entities.csv.")

    print("\n" + "=" * 80)
    print("HOÀN TẤT CHUẨN HÓA DỮ LIỆU BƯỚC 2")
    print("=" * 80)


if __name__ == "__main__":
    build_entities_and_relations()
