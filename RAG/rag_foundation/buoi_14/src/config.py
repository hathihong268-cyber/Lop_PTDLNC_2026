"""
Module: config.py
Buổi 15: Cài đặt Kiểm soát Truy cập dựa trên Vai trò (RBAC) ở mức Dữ liệu & Retrieval Pipeline
Nhiệm vụ: Cấu hình tập trung danh sách vai trò (Roles), thông số kết nối Database từ .env, và đường dẫn thư mục.
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver

# Đảm bảo UTF-8 trên Windows console
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ==============================================================================
# 1. ĐƯỜNG DẪN THƯ MỤC HỆ THỐNG
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
CHUNKS_NORMALIZED_PATH = PROCESSED_DATA_DIR / "chunks_normalized.csv"
CHUNKS_SECURE_PATH = PROCESSED_DATA_DIR / "chunks_secure.csv"
CACHE_DIR = BASE_DIR / "cache"
OUTPUTS_DIR = BASE_DIR / "outputs"
ROLES_CONFIG_PATH = BASE_DIR / "roles.json"
ENV_PATH = BASE_DIR / ".env"

# Đảm bảo các thư mục cần thiết luôn tồn tại
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# 2. ĐỊNH NGHĨA VAI TRÒ (RBAC ROLES CONFIGURATION)
# ==============================================================================
ROLE_ADMIN = "Admin"
ROLE_HR_MANAGER = "HR_Manager"
ROLE_RISK_OFFICER = "Risk_Officer"
ROLE_EMPLOYEE = "Employee"
ROLE_GUEST = "Guest"

VALID_ROLES: List[str] = [
    ROLE_ADMIN,
    ROLE_HR_MANAGER,
    ROLE_RISK_OFFICER,
    ROLE_EMPLOYEE,
    ROLE_GUEST,
]

VALID_ROLES_SET: Set[str] = set(VALID_ROLES)

ROLE_DESCRIPTIONS: Dict[str, str] = {
    ROLE_ADMIN: "Quản trị viên toàn quyền hệ thống (truy cập mọi văn bản)",
    ROLE_HR_MANAGER: "Cán bộ nhân sự (truy cập tài liệu nhân sự, lương thưởng, quy chế & tài liệu chung)",
    ROLE_RISK_OFFICER: "Cán bộ quản trị rủi ro / tín dụng (truy cập tài liệu tín dụng, hạn mức, bảo mật & tài liệu chung)",
    ROLE_EMPLOYEE: "Nhân viên chính thức (truy cập quy định nghiệp vụ, nội quy & tài liệu công khai)",
    ROLE_GUEST: "Khách vãng lai / đối tác ngoài (chỉ truy cập văn bản công khai chung)",
}


def validate_roles(roles: List[str]) -> List[str]:
    """
    Kiểm tra tính hợp lệ của danh sách vai trò người dùng truyền vào.
    Loại bỏ vai trò trùng lặp và cảnh báo/loại bỏ vai trò không hợp lệ.
    """
    if not roles:
        return [ROLE_GUEST]
    
    clean_roles = []
    for r in roles:
        r_str = str(r).strip()
        if r_str in VALID_ROLES_SET and r_str not in clean_roles:
            clean_roles.append(r_str)
        elif r_str not in VALID_ROLES_SET:
            print(f"[CẢNH BÁO RBAC] Vai trò '{r_str}' không hợp lệ. Bỏ qua.")
    
    return clean_roles if clean_roles else [ROLE_GUEST]


# ==============================================================================
# 3. CẤU HÌNH KẾT NỐI DATABASE NEO4J
# ==============================================================================
def load_environment(override: bool = True) -> Path:
    """Tải biến môi trường từ file .env cục bộ tại buoi_14/.env."""
    env_candidate_paths = [
        ENV_PATH,
        BASE_DIR.parent.parent.parent / ".env",
        BASE_DIR.parent / "buoi_10" / ".env",
    ]
    
    for path in env_candidate_paths:
        if path.exists():
            load_dotenv(dotenv_path=path, override=override)
            return path
    
    # Mặc định trả về ENV_PATH
    load_dotenv(dotenv_path=ENV_PATH, override=override)
    return ENV_PATH


def get_neo4j_config() -> Dict[str, str]:
    """Đọc thông tin cấu hình Neo4j từ biến môi trường."""
    load_environment()
    return {
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("NEO4J_PASSWORD", "abcd1234"),
        "database": os.getenv("NEO4J_DATABASE", "neo4j"),
    }


def get_neo4j_driver() -> Tuple[Driver, str]:
    """Khởi tạo và trả về Neo4j Driver và tên database."""
    cfg = get_neo4j_config()
    driver = GraphDatabase.driver(
        cfg["uri"],
        auth=(cfg["user"], cfg["password"]),
    )
    return driver, cfg["database"]


if __name__ == "__main__":
    print("=" * 60)
    print("RBAC CONFIGURATION TEST (BUOI_15)")
    print("=" * 60)
    print(f"Base Directory       : {BASE_DIR}")
    print(f"Roles Defined        : {VALID_ROLES}")
    env_file = load_environment()
    print(f"Loaded Env File      : {env_file}")
    db_cfg = get_neo4j_config()
    print(f"Neo4j URI            : {db_cfg['uri']}")
    print(f"Neo4j User           : {db_cfg['user']}")
    print(f"Neo4j Database       : {db_cfg['database']}")
    print("Validation Test      :", validate_roles(["Admin", "HR_Manager", "InvalidRole"]))
    print("=" * 60)
