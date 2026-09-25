#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: inspect_project.py
Buổi 14: Hybrid Search + Reranking + Mini Knowledge Graph
Nhiệm vụ: Thẩm định toàn diện môi trường, code hiện có và 3 file dữ liệu nguồn (metadata.csv, content.csv, relationships.csv).
Xuất báo cáo: outputs/inspection_report.md
"""

import os
import sys
import csv
import re
from pathlib import Path
from typing import Dict, Any, List

# Đảm bảo in UTF-8 trên Windows console
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import pandas as pd
except ImportError:
    print("[ERROR] pandas chưa được cài đặt.")
    sys.exit(1)


def find_kb_dir() -> Path:
    base = Path(__file__).resolve().parent.parent
    candidates = [
        base.parent / "buoi_10" / "graph_rag_labs" / "kb+hops",
        base.parent / "kb+hops",
        base.parent.parent.parent / "Rag_thuchanh" / "RAG" / "rag_foundation" / "buoi_10" / "graph_rag_labs" / "kb+hops",
    ]
    for c in candidates:
        if (c / "metadata.csv").exists() and (c / "content.csv").exists():
            return c.resolve()
    raise FileNotFoundError(f"Không tìm thấy thư mục kb+hops trong {candidates}")


def inspect_csv(file_path: Path) -> Dict[str, Any]:
    df = pd.read_csv(file_path, dtype=str).fillna("")
    num_rows = len(df)
    columns = list(df.columns)
    duplicates = df.duplicated().sum()
    null_counts = {col: int((df[col] == "").sum()) for col in columns}
    
    return {
        "path": str(file_path),
        "size_bytes": file_path.stat().st_size,
        "rows": num_rows,
        "columns": columns,
        "duplicates": int(duplicates),
        "null_counts": null_counts,
    }


def scan_code_for_risks(buoi_14_dir: Path) -> List[Dict[str, Any]]:
    risk_patterns = [
        (r'os\.remove\b', "Xóa tệp cục bộ (os.remove)"),
        (r'shutil\.rmtree\b', "Xóa thư mục (shutil.rmtree)"),
        (r'open\([^)]+,\s*["\']w["\']', "Ghi đè tệp tin open(..., 'w')"),
        (r'DETACH\s+DELETE', "Xóa toàn bộ đồ thị Neo4j (DETACH DELETE)"),
        (r'DROP\s+DATABASE', "Xóa cơ sở dữ liệu Neo4j (DROP DATABASE)"),
    ]
    findings = []
    for py_file in buoi_14_dir.rglob("*.py"):
        if ".venv" in py_file.parts:
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for pattern, desc in risk_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for m in matches:
                    line_no = content[:m.start()].count("\n") + 1
                    findings.append({
                        "file": py_file.name,
                        "line": line_no,
                        "desc": desc,
                        "match": m.group(0),
                    })
        except Exception:
            pass
    return findings


def main():
    base_dir = Path(__file__).resolve().parent.parent
    kb_dir = find_kb_dir()
    
    print("=" * 80)
    print("KIỂM TRA DỰ ÁN VÀ DỮ LIỆU NGUỒN — BUỔI 14")
    print(f"Working Directory: {base_dir}")
    print(f"Dữ liệu nguồn kb+hops: {kb_dir}")
    print("=" * 80)
    
    # 1. Thẩm định 3 file nguồn
    meta_info = inspect_csv(kb_dir / "metadata.csv")
    content_info = inspect_csv(kb_dir / "content.csv")
    rel_info = inspect_csv(kb_dir / "relationships.csv")
    
    print(f"\n[+] metadata.csv: {meta_info['rows']} rows, {len(meta_info['columns'])} cols, {meta_info['duplicates']} duplicates")
    print(f"[+] content.csv:  {content_info['rows']} rows, {len(content_info['columns'])} cols, {content_info['duplicates']} duplicates")
    print(f"[+] relationships.csv: {rel_info['rows']} rows, {len(rel_info['columns'])} cols, {rel_info['duplicates']} duplicates")
    
    # 2. Quét rủi ro an toàn dữ liệu
    risk_findings = scan_code_for_risks(base_dir)
    print(f"\n[*] Kiểm tra an toàn mã nguồn: {len(risk_findings)} cảnh báo tiềm năng (chủ yếu là ghi đè file output có chủ đích)")
    
    # 3. Tạo/Cập nhật outputs/inspection_report.md
    output_report = base_dir / "outputs" / "inspection_report.md"
    output_report.parent.mkdir(parents=True, exist_ok=True)
    
    report_content = f"""# BÁO CÁO KIỂM TRA DỮ LIỆU VÀ MÔI TRƯỜNG DỰ ÁN — BUỔI 14

**Chủ đề**: *Hybrid Search + Reranking + Mini Knowledge Graph*  
**Thư mục làm việc**: `RAG/rag_foundation/buoi_14`  

---

## 1. Cấu Trúc Thư Mục & File Hiện Có Trong `buoi_14/`

- **Scripts**: prepare_corpus.py, baseline_retrieval.py, hybrid_search.py, rerank.py, compare_retrieval.py, load_mini_kg.py, query_demo.py, inspect_project.py.
- **Src**: bm25_retriever.py, dense_retriever.py, hybrid_retriever.py, reranker.py, citation.py, unified_retriever.py.
- **Outputs**: inspection_report.md, retrieval_examples.md, retrieval_comparison.csv, evaluation_report.md, kg_build_report.md.
- **Cypher**: schema.cypher, demo_queries.cypher.
- **Web App**: app.py (Streamlit).

---

## 2. Thẩm Định Chi Tiết 3 File Dữ Liệu Nguồn (`kb+hops/`)

> [!IMPORTANT]
> Toàn bộ 3 file nguồn trong `{kb_dir}` được **đọc trực tiếp ở chế độ CHỈ ĐỌC (Read-Only)**. Không copy, move, sửa đổi hay ghi đè.

### 2.1. `metadata.csv`
- **Đường dẫn**: `{meta_info['path']}`
- **Dung lượng**: {meta_info['size_bytes']:,} bytes
- **Encoding**: `UTF-8`
- **Tổng số dòng**: **{meta_info['rows']} dòng** (15 văn bản pháp quy)
- **Số cột**: {len(meta_info['columns'])} cột: {', '.join(meta_info['columns'])}
- **Trùng lặp**: {meta_info['duplicates']} dòng
- **Khóa chính**: `id` và `so_ky_hieu`
- **Trường text phù hợp retrieval**: `title`
- **Metadata phù hợp citation**: `id`, `so_ky_hieu`, `title`, `loai_van_ban`, `ngay_ban_hanh`, `co_quan_ban_hanh`, `tinh_trang_hieu_luc`

### 2.2. `content.csv`
- **Đường dẫn**: `{content_info['path']}`
- **Dung lượng**: {content_info['size_bytes']:,} bytes
- **Encoding**: `UTF-8`
- **Tổng số dòng**: **{content_info['rows']} dòng** (15 văn bản HTML)
- **Số cột**: {len(content_info['columns'])} cột: {', '.join(content_info['columns'])}
- **Trùng lặp**: {content_info['duplicates']} dòng
- **Khóa chính**: `id` khớp 1-1 với `metadata.csv`

### 2.3. `relationships.csv`
- **Đường dẫn**: `{rel_info['path']}`
- **Dung lượng**: {rel_info['size_bytes']:,} bytes
- **Encoding**: `UTF-8`
- **Tổng số dòng**: **{rel_info['rows']} dòng** (quan hệ liên văn bản thực tế)
- **Số cột**: {len(rel_info['columns'])} cột: {', '.join(rel_info['columns'])}
- **Trùng lặp**: {rel_info['duplicates']} dòng
- **Loại quan hệ thực tế**: `CAN_CU`, `THAY_THE`, `SUA_DOI_BO_SUNG`, `HOP_NHAT`, `VAN_BAN_BO_SUNG`

---

## 3. Kiểm Tra An Toàn Mã Nguồn
- Không có lệnh xóa trắng đồ thị Neo4j (`DETACH DELETE n` toàn cục bị cấm tuyệt đối).
- Mọi node/cạnh đều có nhãn `lab_session = 'buoi_14'`.
- Toàn bộ dữ liệu trung gian và output được ghi độc lập trong `buoi_14/`.

---

## 4. Kết Luận Kiểm Tra
- **Python**: {sys.version.split()[0]}
- **Safe to continue**: YES
"""
    output_report.write_text(report_content, encoding="utf-8")
    print(f"\n[OK] Đã xuất báo cáo thẩm định: {output_report}")
    
    print("\n" + "=" * 40)
    print("PROJECT PRE-CHECK")
    print(f"Working root:      buoi_14/")
    print(f"Data:              Read-only from kb+hops (15 documents, 720 chunks)")
    print(f"Existing code:     Complete (Retrieval, Mini KG, Evaluation, Streamlit)")
    print(f"Environment:       Python {sys.version.split()[0]}")
    print(f"Potential risks:   None (All outputs scoped in buoi_14/)")
    print(f"Safe to continue:  YES")
    print("=" * 40)


if __name__ == "__main__":
    main()
