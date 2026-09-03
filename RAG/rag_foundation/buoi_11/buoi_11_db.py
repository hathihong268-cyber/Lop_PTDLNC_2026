"""
Module Bước 1: Cấu hình và Kết nối Cơ sở dữ liệu Đồ thị Neo4j (kb-hops)
Bài thực hành 2 - Buổi 11: Multi-hop Graph RAG và Ứng dụng Hỏi Đáp (QA)
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver, exceptions

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)


def get_db_config() -> dict:
    """Lấy thông tin cấu hình kết nối Neo4j từ biến môi trường hoặc .env."""
    return {
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687").strip(),
        "http_port": os.getenv("NEO4J_HTTP_PORT", "7474").strip(),
        "user": os.getenv("NEO4J_USER", "neo4j").strip(),
        "password": os.getenv("NEO4J_PASSWORD", "abcd1234").strip(),
        "database": os.getenv("NEO4J_DATABASE", "kb-hops").strip(),
    }


def get_neo4j_driver() -> Driver:
    """Khởi tạo và trả về Neo4j Driver."""
    cfg = get_db_config()
    return GraphDatabase.driver(
        cfg["uri"],
        auth=(cfg["user"], cfg["password"]),
        connection_timeout=5.0
    )


def verify_connection() -> bool:
    """Kiểm tra kết nối tới Neo4j và kiểm tra dữ liệu trong database kb-hops."""
    cfg = get_db_config()
    print("=" * 80)
    print(" BƯỚC 1: KẾT NỐI VÀ KIỂM TRA CƠ SỞ DỮ LIỆU NEO4J (KB-HOPS)")
    print("=" * 80)
    print(f"[*] Đang kết nối tới Neo4j URL : {cfg['uri']}")
    print(f"[*] Tài khoản                 : {cfg['user']}")
    print(f"[*] Database đích             : {cfg['database']}")

    driver = get_neo4j_driver()
    try:
        driver.verify_connectivity()
        print(f"[+] Kết nối thành công tới máy chủ Neo4j qua giao thức Bolt!")

        # Kiểm tra database kb-hops
        with driver.session(database=cfg["database"]) as session:
            doc_count = session.run("MATCH (d:Document) RETURN count(d) AS cnt").single()["cnt"]
            chunk_count = session.run("MATCH (c:Chunk) RETURN count(c) AS cnt").single()["cnt"]
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt").single()["cnt"]
            doc_rel_count = session.run("MATCH (d1:Document)-[r]->(d2:Document) RETURN count(r) AS cnt").single()["cnt"]

            print(f"\n[+] TRẠNG THÁI CƠ SỞ DỮ LIỆU `{cfg['database']}`:")
            print(f"    • Số lượng Document           : {doc_count}")
            print(f"    • Số lượng Chunk              : {chunk_count:,}")
            print(f"    • Tổng số liên kết/quan hệ     : {rel_count:,}")
            print(f"    • Quan hệ liên văn bản (Doc-Doc): {doc_rel_count}")

            # Kiểm tra Vector Index
            try:
                indexes = session.run("SHOW VECTOR INDEXES").data()
                print(f"    • Vector Indexes              : {[idx['name'] for idx in indexes]}")
            except Exception:
                pass

        print("\n" + "=" * 80)
        print("[SUCCESS] Bước 1 hoàn thành: Kết nối CSDL Neo4j `kb-hops` sẵn sàng!")
        print("=" * 80)
        return True

    except exceptions.AuthError:
        print(f"\n[!] Lỗi xác thực: Sai tài khoản hoặc mật khẩu (User: '{cfg['user']}').")
        return False
    except exceptions.ServiceUnavailable as e:
        print(f"\n[!] Lỗi kết nối: Neo4j chưa được bật hoặc không thể truy cập tại {cfg['uri']} ({e}).")
        return False
    except Exception as e:
        print(f"\n[!] Lỗi: {e}")
        return False
    finally:
        driver.close()


if __name__ == "__main__":
    verify_connection()
