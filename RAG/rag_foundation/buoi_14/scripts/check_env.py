"""
Script kiểm tra môi trường và cấu hình RBAC Buổi 15
"""
import sys
from pathlib import Path

# Đảm bảo UTF-8 trên Windows console
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Thêm buoi_14 vào sys.path để import src
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

print("=" * 60)
print("KIỂM TRA MÔI TRƯỜNG & DEPENDENCIES (BUỔI 15 - RBAC)")
print("=" * 60)

print("[1/4] Kiểm tra pandas...")
import pandas as pd
print(f"      ✓ pandas: {pd.__version__}")

print("[2/4] Kiểm tra neo4j driver...")
import neo4j
print(f"      ✓ neo4j: {neo4j.__version__}")

print("[3/4] Kiểm tra sentence-transformers & transformers...")
import sentence_transformers
import transformers
import torch
print(f"      ✓ sentence-transformers: {sentence_transformers.__version__}")
print(f"      ✓ transformers: {transformers.__version__}")
print(f"      ✓ torch: {torch.__version__} (CUDA available: {torch.cuda.is_available()})")

print("[4/4] Kiểm tra streamlit...")
import streamlit as st
print(f"      ✓ streamlit: {st.__version__}")

print("\n" + "=" * 60)
print("KIỂM TRA CẤU HÌNH RBAC & DATABASE")
print("=" * 60)

from src.config import VALID_ROLES, ROLE_DESCRIPTIONS, get_neo4j_config, load_environment, validate_roles

env_file = load_environment()
cfg = get_neo4j_config()

print(f"Thư mục làm việc (BASE_DIR) : {BASE_DIR}")
print(f"File cấu hình .env           : {env_file}")
print(f"Neo4j URI                   : {cfg['uri']}")
print(f"Neo4j User                  : {cfg['user']}")
print(f"Neo4j Database              : {cfg['database']}")
print("\nDanh sách Vai trò (Roles) đã định nghĩa:")
for role in VALID_ROLES:
    print(f"  • {role:<15} : {ROLE_DESCRIPTIONS.get(role, '')}")

print("\nTest hàm validate_roles:")
test_input = ["Admin", "HR_Manager", "Invalid_Role", "Guest"]
print(f"  Input : {test_input}")
print(f"  Output: {validate_roles(test_input)}")
print("=" * 60)
