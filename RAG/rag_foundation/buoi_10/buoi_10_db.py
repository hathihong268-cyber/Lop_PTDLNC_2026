"""
Module Buoc 3: Cau hinh va Ket noi Co so du lieu Neo4j cuc bo
Bai thuc hanh 1 - Buoi 10: Graph RAG Foundation
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver, Session, exceptions

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)


def get_db_config() -> dict:
    """Lay cau hinh ket noi Neo4j tu file .env."""
    return {
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687").strip(),
        "http_port": os.getenv("NEO4J_HTTP_PORT", "7474").strip(),
        "user": os.getenv("NEO4J_USER", "neo4j").strip(),
        "password": os.getenv("NEO4J_PASSWORD", "abcd1234").strip(),
        "database": os.getenv("NEO4J_DATABASE", "kb-hops").strip(),
    }


def get_neo4j_driver() -> Driver:
    """Khoi tao va tra ve driver ket noi toi Neo4j."""
    cfg = get_db_config()
    driver = GraphDatabase.driver(
        cfg["uri"],
        auth=(cfg["user"], cfg["password"]),
        connection_timeout=5.0
    )
    return driver


def verify_connection() -> bool:
    """Kiem tra ket noi va trang thai cua co so du lieu target."""
    cfg = get_db_config()
    print(f"[*] Dang kiem tra ket noi toi Neo4j tai: {cfg['uri']}...")
    print(f"    - User: {cfg['user']}")
    print(f"    - Target Database: '{cfg['database']}'")

    driver = get_neo4j_driver()
    try:
        driver.verify_connectivity()
        print(f"[+] Ket noi thanh cong toi giao thuc Bolt (Port {cfg['uri'].split(':')[-1]})!")

        # Kiem tra database kb-hops
        with driver.session(database="system") as session:
            # Tu dong tao database neu chua co
            session.run(f"CREATE DATABASE `{cfg['database']}` IF NOT EXISTS")
            
            res = session.run("SHOW DATABASES")
            db_info = {r["name"]: r.get("currentStatus", "N/A") for r in res}
            print(f"[+] Danh sach cac Database hien co:")
            for db_name, status in db_info.items():
                is_target = " (Target DB)" if db_name == cfg["database"] else ""
                print(f"    - {db_name}: {status}{is_target}")

        return True
    except exceptions.AuthError:
        print(f"[!] Loi xac thuc: Sai tai khoan hoac mat khau (User: '{cfg['user']}').")
        return False
    except exceptions.ServiceUnavailable as e:
        print(f"[!] Loi ket noi: Neo4j chua duoc bat hoac sai cong mang ({e}).")
        return False
    except Exception as e:
        print(f"[!] Loi: {e}")
        return False
    finally:
        driver.close()


if __name__ == "__main__":
    print("=" * 80)
    print(" BƯỚC 3: CẤU HÌNH VÀ KIỂM TRA KẾT NỐI CƠ SỞ DỮ LIỆU NEO4J")
    print("=" * 80)
    success = verify_connection()
    if success:
        print("\n[SUCCESS] Cấu hình kết nối Neo4j sẵn sàng cho Bước 4 (Nạp dữ liệu)!")
    else:
        print("\n[FAIL] Vui lòng kiểm tra lại trạng thái Neo4j Desktop hoặc mật khẩu trong file .env.")
