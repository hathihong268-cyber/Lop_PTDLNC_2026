"""
Module: rbac.py
Vị trí: buoi_17/scripts/rbac.py
Mục đích: Module kiểm tra và quản lý chính sách phân quyền RBAC cho Buổi 17.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

BUOI_17_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BUOI_17_DIR / "config" / "rbac_policy.json"


class RBACManager:
    def __init__(self, config_file: Path = CONFIG_PATH):
        self.config_file = config_file
        self.policy = self._load_policy()

    def _load_policy(self) -> Dict[str, Any]:
        if self.config_file.exists():
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "valid_roles": ["Admin", "HR_Manager", "Risk_Officer", "Employee", "Guest"],
            "default_role": "Guest",
            "default_policy": "DEFAULT_DENY"
        }

    def validate_roles(self, roles: List[str]) -> List[str]:
        valid = self.policy.get("valid_roles", ["Guest"])
        if not roles or not isinstance(roles, list):
            return ["Guest"]
        
        filtered = [r for r in roles if r in valid]
        if not filtered:
            print(f"[CẢNH BÁO RBAC] Không tìm thấy role hợp lệ trong {roles}. Mặc định Deny -> Guest.")
            return ["Guest"]
        return filtered

    def is_chunk_allowed(self, chunk_allowed_roles: List[str], user_roles: List[str]) -> bool:
        user_roles = self.validate_roles(user_roles)
        if "Admin" in user_roles:
            return True
        return any(r in chunk_allowed_roles for r in user_roles)


_rbac_manager = None

def get_rbac_manager() -> RBACManager:
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager


if __name__ == "__main__":
    mgr = get_rbac_manager()
    print("Valid Roles:", mgr.policy.get("valid_roles"))
    print("Check Admin:", mgr.is_chunk_allowed(["HR_Manager"], ["Admin"]))
    print("Check Guest:", mgr.is_chunk_allowed(["HR_Manager"], ["Guest"]))
