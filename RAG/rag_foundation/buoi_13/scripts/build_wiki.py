#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/build_wiki.py
Sinh hệ thống Wiki Markdown (Obsidian Vault) từ:
- outputs/entities.csv
- outputs/relations.csv

Cấu trúc:
wiki/
├── Home.md
├── risks/
├── controls/
└── events/
"""

import csv
import re
import sys
from pathlib import Path
from collections import defaultdict

# Đảm bảo in Unicode tiếng Việt mượt mà trên Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def find_directories():
    """Tự động tìm thư mục outputs và tạo thư mục wiki."""
    candidates = [
        Path(__file__).resolve().parent.parent / "outputs",
        Path.cwd() / "outputs",
        Path.cwd() / "Rag_thuchanh" / "RAG" / "rag_foundation" / "buoi_13" / "outputs",
        Path(__file__).resolve().parent.parent / "Rag_thuchanh" / "RAG" / "rag_foundation" / "buoi_13" / "outputs",
    ]
    outputs_dir = None
    for p in candidates:
        if (p / "entities.csv").exists() and (p / "relations.csv").exists():
            outputs_dir = p
            break

    if not outputs_dir:
        raise FileNotFoundError("Không tìm thấy thư mục outputs chứa entities.csv và relations.csv! Hãy chạy build_entities.py trước.")

    wiki_dir = outputs_dir.parent / "wiki"
    return outputs_dir, wiki_dir


def sanitize_filename(name: str) -> str:
    """Loại bỏ ký tự không hợp lệ trên hệ thống tệp Windows/Linux."""
    invalid_chars = r'\/:*?"<>|'
    clean = "".join(c for c in name if c not in invalid_chars)
    clean = " ".join(clean.split()).strip()
    return clean


def read_csv(file_path: Path):
    with open(file_path, mode="r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def build_wiki():
    outputs_dir, wiki_dir = find_directories()
    print("=" * 80)
    print("BƯỚC 3: SINH WIKI MARKDOWN (OBSIDIAN VAULT)")
    print(f"Outputs directory: {outputs_dir}")
    print(f"Wiki directory:    {wiki_dir}")
    print("=" * 80)

    # 1. Đọc entities và relations
    entities = read_csv(outputs_dir / "entities.csv")
    relations = read_csv(outputs_dir / "relations.csv")

    # Tạo các thư mục con trong wiki/
    risks_dir = wiki_dir / "risks"
    controls_dir = wiki_dir / "controls"
    events_dir = wiki_dir / "events"

    for d in [wiki_dir, risks_dir, controls_dir, events_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # 2. Xây dựng bản đồ Tra cứu Entity và File Name (Base Name)
    entity_by_id = {}
    basename_by_id = {}
    file_path_by_id = {}

    for e in entities:
        eid = e["id"]
        etype = e["type"]
        name = e["name"]
        
        entity_by_id[eid] = e
        # Tên file: <ID> - <Tên an toàn>
        clean_name = sanitize_filename(name)
        base_name = f"{eid} - {clean_name}" if clean_name else eid
        basename_by_id[eid] = base_name

        if etype == "RuiRo":
            file_path_by_id[eid] = risks_dir / f"{base_name}.md"
        elif etype == "KiemSoat":
            file_path_by_id[eid] = controls_dir / f"{base_name}.md"
        elif etype == "SuKienRuiRo":
            file_path_by_id[eid] = events_dir / f"{base_name}.md"

    # 3. Phân loại relations theo Source và Target
    # incoming_relations[target_id] = [relation, ...]
    # outgoing_relations[source_id] = [relation, ...]
    incoming_relations = defaultdict(list)
    outgoing_relations = defaultdict(list)

    for rel in relations:
        s_id = rel["source_id"]
        t_id = rel["target_id"]
        outgoing_relations[s_id].append(rel)
        incoming_relations[t_id].append(rel)

    created_pages = []

    # 4. Sinh trang RuiRo (wiki/risks/)
    for e in entities:
        if e["type"] != "RuiRo":
            continue
        eid = e["id"]
        file_path = file_path_by_id[eid]
        
        # Các kiểm soát giảm thiểu rủi ro này (incoming MITIGATES từ KiemSoat)
        mitigations = [r for r in incoming_relations[eid] if r["relationship_type"] == "MITIGATES"]
        # Các sự kiện quan sát của rủi ro này (outgoing OBSERVED_AS tới SuKienRuiRo)
        observations = [r for r in outgoing_relations[eid] if r["relationship_type"] == "OBSERVED_AS"]

        mitigations_md = ""
        if mitigations:
            for r in mitigations:
                ctrl_id = r["source_id"]
                ctrl_base = basename_by_id.get(ctrl_id, ctrl_id)
                mitigations_md += f"- [[{ctrl_base}]]\n"
                mitigations_md += f"  - **Mối quan hệ:** `{r['relationship_type']}`\n"
                mitigations_md += f"  - **Trích dẫn bằng chứng:** {r['evidence_quote']}\n"
                mitigations_md += f"  - **Độ tin cậy:** {r['confidence']} | **Trạng thái:** `{r['verification_status']}`\n"
        else:
            mitigations_md = "_Chưa có chốt kiểm soát trực tiếp nào được ghi nhận trong dữ liệu seed._\n"

        observations_md = ""
        if observations:
            for r in observations:
                evt_id = r["target_id"]
                evt_base = basename_by_id.get(evt_id, evt_id)
                observations_md += f"- [[{evt_base}]]\n"
                observations_md += f"  - **Mối quan hệ:** `{r['relationship_type']}`\n"
                observations_md += f"  - **Trích dẫn bằng chứng:** {r['evidence_quote']}\n"
                observations_md += f"  - **Độ tin cậy:** {r['confidence']} | **Trạng thái:** `{r['verification_status']}`\n"
        else:
            observations_md = "_Chưa ghi nhận sự kiện rủi ro nào liên quan._\n"

        content = f"""---
id: {eid}
type: {e['type']}
verification_status: {e['verification_status']}
data_origin: {e['data_origin']}
category: {e['category']}
inherent_level: {e['inherent_level']}
residual_level: {e['residual_level']}
owner_unit_id: {e['owner_unit_id']}
---

# {eid} - {e['name']}

## 1. Thông tin rủi ro
- **Mã hồ sơ rủi ro:** `{eid}`
- **Phân loại (Category):** {e['category']}
- **Mức độ rủi ro vốn có (Inherent Level):** {e['inherent_level']}
- **Mức độ rủi ro còn lại (Residual Level):** {e['residual_level']}
- **Đơn vị quản lý (Owner Unit ID):** `{e['owner_unit_id']}`
- **Nguồn gốc dữ liệu:** {e['data_origin']}
- **Trạng thái xác minh:** {e['verification_status']}

## 2. Diễn biến cấu trúc rủi ro
- **Mô tả chung:** {e['description']}
- **Nguyên nhân (Cause):** {e['cause']}
- **Sự kiện rủi ro (Event):** {e['event']}
- **Tác động / Hậu quả (Impact):** {e['impact']}

## 3. Kiểm soát liên quan (Mitigating Controls)
{mitigations_md}
## 4. Sự kiện rủi ro liên quan (Observed Risk Events)
{observations_md}
---
[[Home| Trang chủ Wiki]]
"""
        with open(file_path, mode="w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        created_pages.append(file_path)

    # 5. Sinh trang KiemSoat (wiki/controls/)
    for e in entities:
        if e["type"] != "KiemSoat":
            continue
        eid = e["id"]
        file_path = file_path_by_id[eid]

        # Kiểm soát này MITIGATES rủi ro nào (outgoing MITIGATES tới RuiRo)
        mitigates_rels = [r for r in outgoing_relations[eid] if r["relationship_type"] == "MITIGATES"]
        mitigates_md = ""
        if mitigates_rels:
            for r in mitigates_rels:
                risk_id = r["target_id"]
                risk_base = basename_by_id.get(risk_id, risk_id)
                mitigates_md += f"- [[{risk_base}]]\n"
                mitigates_md += f"  - **Mối quan hệ:** `{r['relationship_type']}`\n"
                mitigates_md += f"  - **Trích dẫn bằng chứng:** {r['evidence_quote']}\n"
                mitigates_md += f"  - **Độ tin cậy:** {r['confidence']} | **Trạng thái:** `{r['verification_status']}`\n"
        else:
            mitigates_md = "_Chưa liên kết với hồ sơ rủi ro nào._\n"

        content = f"""---
id: {eid}
type: {e['type']}
verification_status: {e['verification_status']}
data_origin: {e['data_origin']}
control_type: {e['control_type']}
frequency: {e['frequency']}
owner_role_id: {e['owner_role_id']}
effectiveness: {e['effectiveness']}
---

# {eid} - {e['name']}

## 1. Thông tin chốt kiểm soát
- **Mã kiểm soát:** `{eid}`
- **Loại kiểm soát (Control Type):** {e['control_type']}
- **Tần suất thực hiện (Frequency):** {e['frequency']}
- **Hiệu quả kiểm soát (Effectiveness):** {e['effectiveness']}
- **Vai trò phụ trách (Owner Role ID):** `{e['owner_role_id']}`
- **Mô tả kiểm soát:** {e['description']}
- **Nguồn gốc dữ liệu:** {e['data_origin']}
- **Trạng thái xác minh:** {e['verification_status']}

## 2. Rủi ro được giảm thiểu (Mitigated Risks)
{mitigates_md}
---
[[Home| Trang chủ Wiki]]
"""
        with open(file_path, mode="w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        created_pages.append(file_path)

    # 6. Sinh trang SuKienRuiRo (wiki/events/)
    for e in entities:
        if e["type"] != "SuKienRuiRo":
            continue
        eid = e["id"]
        file_path = file_path_by_id[eid]

        # Sự kiện này OBSERVED_AS từ rủi ro nào (incoming OBSERVED_AS từ RuiRo)
        observed_rels = [r for r in incoming_relations[eid] if r["relationship_type"] == "OBSERVED_AS"]
        observed_md = ""
        if observed_rels:
            for r in observed_rels:
                risk_id = r["source_id"]
                risk_base = basename_by_id.get(risk_id, risk_id)
                observed_md += f"- [[{risk_base}]]\n"
                observed_md += f"  - **Mối quan hệ:** `{r['relationship_type']}`\n"
                observed_md += f"  - **Trích dẫn bằng chứng:** {r['evidence_quote']}\n"
                observed_md += f"  - **Độ tin cậy:** {r['confidence']} | **Trạng thái:** `{r['verification_status']}`\n"
        elif e.get("risk_id"):
            # Fallback nếu có risk_id trong entity
            risk_id = e["risk_id"]
            risk_base = basename_by_id.get(risk_id, risk_id)
            observed_md += f"- [[{risk_base}]]\n"
        else:
            observed_md = "_Chưa liên kết với hồ sơ rủi ro nào._\n"

        # Định dạng tiền tệ VND đẹp mắt
        loss_val = e.get("loss_amount_vnd", "0")
        try:
            loss_formatted = f"{int(float(loss_val)):,} VND"
        except Exception:
            loss_formatted = f"{loss_val} VND"

        content = f"""---
id: {eid}
type: {e['type']}
verification_status: {e['verification_status']}
data_origin: {e['data_origin']}
risk_id: {e['risk_id']}
occurred_at: {e['occurred_at']}
discovered_at: {e['discovered_at']}
severity: {e['severity']}
loss_amount_vnd: {e['loss_amount_vnd']}
---

# {eid} - {e['name']}

## 1. Thông tin sự kiện rủi ro
- **Mã sự kiện:** `{eid}`
- **Mô tả chi tiết:** {e['description']}
- **Ngày xảy ra (Occurred At):** {e['occurred_at']}
- **Ngày phát hiện (Discovered At):** {e['discovered_at']}
- **Mức độ nghiêm trọng (Severity):** {e['severity']}
- **Tổn thất tài chính ước tính:** {loss_formatted}
- **Nguồn gốc dữ liệu:** {e['data_origin']}
- **Trạng thái xác minh:** {e['verification_status']}

## 2. Hồ sơ rủi ro liên quan (Associated Risk Profile)
{observed_md}
---
[[Home| Trang chủ Wiki]]
"""
        with open(file_path, mode="w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        created_pages.append(file_path)

    # 7. Sinh trang wiki/Home.md
    home_file = wiki_dir / "Home.md"
    
    # Danh sách links
    risk_links = "\n".join([f"{idx}. [[{basename_by_id[e['id']]}]]" for idx, e in enumerate(entities, 1) if e["type"] == "RuiRo"])
    control_links = "\n".join([f"{idx}. [[{basename_by_id[e['id']]}]]" for idx, e in enumerate([e for e in entities if e["type"] == "KiemSoat"], 1)])
    event_links = "\n".join([f"{idx}. [[{basename_by_id[e['id']]}]]" for idx, e in enumerate([e for e in entities if e["type"] == "SuKienRuiRo"], 1)])

    home_content = f"""---
id: HOME
type: Dashboard
title: Trang Chủ Wiki Tri Thức Rủi Ro
---

# 🛡️ Wiki Tri Thức Rủi Ro (Wiki Risk Graph)

Hệ thống cơ sở tri thức đồ thị rủi ro phục vụ đào tạo và tra cứu.

---

## 📊 1. Thống kê Đồ thị Tri thức
- **Tổng số thực thể (Nodes):** **{len(entities)}**
  - 🔴 Hồ sơ Rủi ro (`:RuiRo`): **12**
  - 🟢 Chốt Kiểm soát (`:KiemSoat`): **10**
  - 🟡 Sự kiện Rủi ro (`:SuKienRuiRo`): **12**
- **Tổng số liên kết (Edges):** **{len(relations)}**
  - 🛡️ Giảm thiểu rủi ro (`MITIGATES`): **10**
  - ⚠️ Biểu hiện thành sự kiện (`OBSERVED_AS`): **12**

---

## 🎯 2. Mô hình Luồng Quan hệ MVP
```
[KiemSoat] ──(MITIGATES)──► [RuiRo] ──(OBSERVED_AS)──► [SuKienRuiRo]
```

---

## 🔴 3. Danh mục Hồ sơ Rủi ro (RuiRo)
{risk_links}

---

## 🟢 4. Danh mục Chốt Kiểm soát (KiemSoat)
{control_links}

---

## 🟡 5. Danh mục Sự kiện Rủi ro (SuKienRuiRo)
{event_links}
"""
    with open(home_file, mode="w", encoding="utf-8") as f:
        f.write(home_content.strip() + "\n")
    created_pages.append(home_file)

    # 8. Đếm tổng số wikilinks được tạo trong toàn bộ vault
    total_wikilinks = 0
    wikilink_pattern = re.compile(r"\[\[(.*?)\]\]")
    for p in created_pages:
        with open(p, mode="r", encoding="utf-8") as f:
            text = f.read()
            matches = wikilink_pattern.findall(text)
            total_wikilinks += len(matches)

    # 9. Tìm các đường đi ví dụ: KiemSoat -> RuiRo -> SuKienRuiRo
    sample_paths = []
    for rel_m in [r for r in relations if r["relationship_type"] == "MITIGATES"]:
        ctrl_id = rel_m["source_id"]
        risk_id = rel_m["target_id"]
        # Tìm các sự kiện của risk_id
        for rel_o in [r for r in relations if r["relationship_type"] == "OBSERVED_AS" and r["source_id"] == risk_id]:
            evt_id = rel_o["target_id"]
            ctrl_name = basename_by_id[ctrl_id]
            risk_name = basename_by_id[risk_id]
            evt_name = basename_by_id[evt_id]
            sample_paths.append((ctrl_name, risk_name, evt_name))

    print("\n--- BÁO CÁO KẾT QUẢ SINH WIKI ---")
    print(f"1. Tổng số trang Wiki đã tạo: {len(created_pages)} trang")
    print(f"   - wiki/Home.md: 1")
    print(f"   - wiki/risks/:    {len(list(risks_dir.glob('*.md')))}")
    print(f"   - wiki/controls/: {len(list(controls_dir.glob('*.md')))}")
    print(f"   - wiki/events/:   {len(list(events_dir.glob('*.md')))}")
    print(f"2. Tổng số wikilink ([[...]]) trong toàn bộ Vault: {total_wikilinks} wikilinks")
    
    print("\n3. Ví dụ đường đi: KiemSoat -> RuiRo -> SuKienRuiRo:")
    for idx, (c, r, e) in enumerate(sample_paths[:5], 1):
        print(f"   Ví dụ {idx}:")
        print(f"     [[{c}]]")
        print(f"       └── [MITIGATES] ──► [[{r}]]")
        print(f"                             └── [OBSERVED_AS] ──► [[{e}]]")

    print("\n" + "=" * 80)
    print("HOÀN TẤT SINH WIKI MARKDOWN BƯỚC 3")
    print("=" * 80)


if __name__ == "__main__":
    build_wiki()
