"""
Script: load_secure_kg.py
Buổi 15: Cài đặt Kiểm soát Truy cập dựa trên Vai trò (RBAC) ở mức Dữ liệu
Nhiệm vụ:
1. Đọc dữ liệu bảo mật từ `buoi_14/data/processed/chunks_secure.csv`.
2. Cập nhật thuộc tính `allowed_roles` (List of Strings) lên các node (:DieuKhoan) và (:VanBan).
3. Gắn nhãn cập nhật `lab_session = "buoi_15"`, tuyệt đối không DETACH DELETE các node cũ.
4. Chạy các truy vấn kiểm thử xác thực dữ liệu phân quyền trên Neo4j.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Set
import pandas as pd
from neo4j import Driver

# Đảm bảo UTF-8 trên Windows console
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Thêm buoi_14 vào sys.path để import cấu hình
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.config import (
    get_neo4j_driver,
    get_neo4j_config,
    CHUNKS_SECURE_PATH,
    VALID_ROLES,
    ROLE_ADMIN,
    ROLE_HR_MANAGER,
    ROLE_RISK_OFFICER,
    ROLE_EMPLOYEE,
    ROLE_GUEST,
)


def load_and_prepare_records(csv_path: Path) -> tuple[List[Dict[str, Any]], Dict[str, Set[str]]]:
    """
    Đọc chunks_secure.csv và chuẩn bị danh sách record nạp vào Neo4j:
    - Mỗi DieuKhoan có `allowed_roles` dạng List[str]
    - Mỗi VanBan có `allowed_roles` là hợp nhất (Union) các vai trò của tất cả Điều khoản con.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file {csv_path}. Hãy chạy assign_security_tags.py trước!")

    df = pd.read_csv(csv_path)
    print(f"[*] Đọc thành công {len(df)} dòng dữ liệu từ {csv_path.name}")

    dieukhoan_records = []
    doc_roles_map: Dict[str, Set[str]] = {}

    for _, row in df.iterrows():
        chunk_id = str(row["chunk_id"]).strip()
        doc_id = str(row["document_id"]).strip()
        
        # Parse allowed_roles từ JSON string sang List[str]
        raw_roles = row.get("allowed_roles", "[]")
        if isinstance(raw_roles, str):
            try:
                roles_list = json.loads(raw_roles)
            except Exception:
                roles_list = [r.strip() for r in raw_roles.strip("[]").replace('"', '').replace("'", '').split(",") if r.strip()]
        elif isinstance(raw_roles, list):
            roles_list = raw_roles
        else:
            roles_list = [ROLE_GUEST]

        dieukhoan_records.append({
            "id": chunk_id,
            "document_id": doc_id,
            "allowed_roles": roles_list,
            "lab_session": "buoi_15",
        })

        if doc_id not in doc_roles_map:
            doc_roles_map[doc_id] = set()
        for r in roles_list:
            doc_roles_map[doc_id].add(r)

    return dieukhoan_records, doc_roles_map


def update_dieukhoan_security_nodes(driver: Driver, database: str, records: List[Dict[str, Any]]) -> int:
    """Cập nhật thuộc tính allowed_roles trên các Node (:DieuKhoan) bằng MERGE."""
    print(f"\n[*] Đang cập nhật allowed_roles cho {len(records)} Node (:DieuKhoan)...")
    
    query = """
    UNWIND $batch AS row
    MERGE (d:DieuKhoan {id: row.id})
    SET d.allowed_roles = row.allowed_roles,
        d.lab_session = row.lab_session,
        d.security_tagged = true
    """
    
    batch_size = 100
    total = len(records)
    with driver.session(database=database) as session:
        for i in range(0, total, batch_size):
            batch = records[i : i + batch_size]
            session.run(query, batch=batch)
            print(f"    -> Đã cập nhật xong batch {i + 1} - {min(i + batch_size, total)}/{total}")

    print(f"[+] Hoàn tất cập nhật {total} Node (:DieuKhoan) thành công.")
    return total


def update_vanban_security_nodes(driver: Driver, database: str, doc_roles_map: Dict[str, Set[str]]) -> int:
    """Cập nhật thuộc tính allowed_roles trên các Node (:VanBan) bằng MERGE."""
    print(f"\n[*] Đang cập nhật allowed_roles cho {len(doc_roles_map)} Node (:VanBan)...")
    
    vanban_records = []
    for doc_id, roles_set in doc_roles_map.items():
        vanban_records.append({
            "id": doc_id,
            "allowed_roles": sorted(list(roles_set)),
            "lab_session": "buoi_15",
        })

    query = """
    UNWIND $batch AS row
    MERGE (v:VanBan {id: row.id})
    SET v.allowed_roles = row.allowed_roles,
        v.lab_session = row.lab_session,
        v.security_tagged = true
    """

    with driver.session(database=database) as session:
        session.run(query, batch=vanban_records)

    print(f"[+] Hoàn tất cập nhật {len(vanban_records)} Node (:VanBan) thành công.")
    return len(vanban_records)


def run_security_verification_queries(driver: Driver, database: str) -> None:
    """Chạy các truy vấn kiểm thử nhanh nhằm xác thực tính chính xác của dữ liệu phân quyền trong Neo4j."""
    print("\n" + "=" * 70)
    print("KIỂM TRA VÀ XÁC THỰC CƠ SỞ DỮ LIỆU NEO4J (SECURE GRAPH VERIFICATION)")
    print("=" * 70)

    with driver.session(database=database) as session:
        # 1. Đếm số lượng Node đã được gắn allowed_roles
        count_dieukhoan_res = session.run("""
            MATCH (d:DieuKhoan)
            WHERE d.allowed_roles IS NOT NULL
            RETURN count(d) AS cnt
        """).single()
        cnt_d = count_dieukhoan_res["cnt"]

        count_vanban_res = session.run("""
            MATCH (v:VanBan)
            WHERE v.allowed_roles IS NOT NULL
            RETURN count(v) AS cnt
        """).single()
        cnt_v = count_vanban_res["cnt"]

        print(f"1. Tổng số Node đã được gắn thuộc tính 'allowed_roles':")
        print(f"   • Node (:DieuKhoan) : {cnt_d} nodes")
        print(f"   • Node (:VanBan)    : {cnt_v} nodes")

        # 2. Truy vấn lấy thử 1 node VanBan và 3 node DieuKhoan liên kết
        print(f"\n2. Truy vấn mẫu 1 Văn bản và các Điều khoản liên kết kèm phân quyền:")
        sample_query = """
        MATCH (v:VanBan)-[:CONTAINS]->(d:DieuKhoan)
        WHERE v.id = '44209'
        RETURN v.id AS vanban_id, v.so_ky_hieu AS so_ky_hieu, v.title AS vanban_title,
               v.allowed_roles AS vanban_roles,
               d.id AS dieukhoan_id, d.article AS article, d.allowed_roles AS dieukhoan_roles
        ORDER BY d.id
        LIMIT 3
        """
        sample_results = session.run(sample_query).data()
        for idx, row in enumerate(sample_results, 1):
            if idx == 1:
                print(f"   [VĂN BẢN] ID: {row['vanban_id']} | Số ký hiệu: {row['so_ky_hieu']}")
                print(f"             Tiêu đề : {row['vanban_title']}")
                print(f"             Allowed Roles Văn bản: {row['vanban_roles']}")
                print(f"   [CÁC ĐIỀU KHOẢN TRỰC THUỘC]")
            print(f"     -> [{row['dieukhoan_id']}] {row['article']}")
            print(f"        Allowed Roles: {row['dieukhoan_roles']}")

        # 3. Kiểm thử lọc theo vai trò người dùng (Access Filtering Test)
        print(f"\n3. Kiểm thử logic Lọc quyền truy cập (Cypher Access Filtering):")
        
        test_roles_list = [
            ("Guest", [ROLE_GUEST]),
            ("HR_Manager", [ROLE_HR_MANAGER]),
            ("Risk_Officer", [ROLE_RISK_OFFICER]),
            ("Admin", [ROLE_ADMIN]),
        ]

        for role_label, user_roles in test_roles_list:
            filter_query = """
            MATCH (d:DieuKhoan)
            WHERE any(role IN d.allowed_roles WHERE role IN $user_roles)
            RETURN count(d) AS accessible_count
            """
            res = session.run(filter_query, user_roles=user_roles).single()
            accessible = res["accessible_count"]
            pct = (accessible / 720) * 100
            print(f"   • Vai trò: {role_label:<12} (user_roles={str(user_roles):<25}) -> Xem được: {accessible:3d}/720 chunks ({pct:5.1f}%)")

    print("=" * 70)


def main():
    print("=" * 70)
    print("NẠP THÔNG TIN PHÂN QUYỀN RBAC VÀO NEO4J (BUỔI 15)")
    print("=" * 70)
    
    cfg = get_neo4j_config()
    print(f"Cấu hình kết nối: URI={cfg['uri']}, User={cfg['user']}, DB={cfg['database']}")
    
    driver, database = get_neo4j_driver()
    try:
        driver.verify_connectivity()
        print("✓ Đã kết nối thành công tới Neo4j!")

        start_time = time.time()
        dieukhoan_records, doc_roles_map = load_and_prepare_records(CHUNKS_SECURE_PATH)
        
        update_dieukhoan_security_nodes(driver, database, dieukhoan_records)
        update_vanban_security_nodes(driver, database, doc_roles_map)
        
        elapsed = time.time() - start_time
        print(f"\n[+] Tổng thời gian cập nhật Neo4j: {elapsed:.2f} giây.")

        # Kiểm tra sau khi nạp
        run_security_verification_queries(driver, database)

    finally:
        driver.close()
        print("\n[*] Đã đóng kết nối Neo4j.")


if __name__ == "__main__":
    main()
