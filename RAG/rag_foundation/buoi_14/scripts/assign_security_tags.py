"""
Script: assign_security_tags.py
Buổi 15: Cài đặt Kiểm soát Truy cập dựa trên Vai trò (RBAC) ở mức Dữ liệu
Nhiệm vụ:
1. Đọc corpus đã chuẩn hóa từ `data/processed/chunks_normalized.csv`.
2. Phân loại nội dung theo quy tắc nghiệp vụ và gán nhãn quyền truy cập (`allowed_roles`).
3. Ghi dữ liệu đã gắn thẻ bảo mật ra `data/processed/chunks_secure.csv`.
4. Kiểm tra tính toàn vẹn (không null/empty, thống kê phân bổ quyền, in mẫu 3 cấp độ).
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

# Đảm bảo hiển thị Unicode tiếng Việt trên Windows console
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
    ROLE_ADMIN,
    ROLE_HR_MANAGER,
    ROLE_RISK_OFFICER,
    ROLE_EMPLOYEE,
    ROLE_GUEST,
    VALID_ROLES,
    CHUNKS_NORMALIZED_PATH,
    CHUNKS_SECURE_PATH,
)

# ==============================================================================
# QUY TẮC PHÂN LOẠI QUYỀN TRUY CẬP (SECURITY CLASSIFICATION RULES)
# ==============================================================================
# Nhóm 1: Tài liệu Nhân sự / Lương thưởng / Bổ nhiệm / Quản trị nội bộ
HR_KEYWORDS = [
    "nhân sự", "lương", "thưởng", "tuyển dụng", "bổ nhiệm", "miễn nhiệm",
    "kỷ luật", "tiền lương", "chức danh", "người đại diện theo pháp luật",
    "thành viên hội đồng", "ban kiểm soát", "tiêu chuẩn người quản lý",
    "bãi nhiệm", "hợp đồng lao động", "thôi việc", "cán bộ",
]

# Nhóm 2: Tài liệu Quản trị Rủi ro / Tín dụng / Hạn mức / Ngoại hối / Vận chuyển tiền
RISK_KEYWORDS = [
    "tín dụng", "rủi ro", "hạn mức", "phê duyệt", "cho vay", "vay vốn",
    "an toàn vốn", "dự trữ ngoại hối", "đầu tư gián tiếp", "vận chuyển tiền",
    "áp tải tiền", "bảo quản tiền", "tài sản quý", "thẩm định", "thanh khoản",
    "trích nộp", "quỹ bảo đảm an toàn", "nợ xấu", "tài sản bảo đảm",
]

ROLES_HR: List[str] = [ROLE_ADMIN, ROLE_HR_MANAGER]
ROLES_RISK: List[str] = [ROLE_ADMIN, ROLE_RISK_OFFICER, ROLE_EMPLOYEE]
ROLES_PUBLIC: List[str] = [ROLE_ADMIN, ROLE_HR_MANAGER, ROLE_RISK_OFFICER, ROLE_EMPLOYEE, ROLE_GUEST]


def classify_chunk(row: pd.Series) -> List[str]:
    """
    Phân loại quyền truy cập cho một chunk dữ liệu dựa trên title, article, chapter và text.
    Thứ tự ưu tiên:
    1. Nếu chứa từ khóa Nhân sự -> [Admin, HR_Manager]
    2. Nếu chứa từ khóa Rủi ro / Tín dụng -> [Admin, Risk_Officer, Employee]
    3. Các quy định pháp luật và thông tin chung khác -> [Admin, HR_Manager, Risk_Officer, Employee, Guest]
    """
    text_content = str(row.get("text", "")).lower()
    title_content = str(row.get("title", "")).lower()
    article_content = str(row.get("article", "")).lower()
    chapter_content = str(row.get("chapter", "")).lower()
    
    combined_search_text = f"{title_content} {chapter_content} {article_content} {text_content}"

    # 1. Kiểm tra nhóm Nhân sự (HR)
    for kw in HR_KEYWORDS:
        if kw in combined_search_text:
            return ROLES_HR

    # 2. Kiểm tra nhóm Rủi ro / Tín dụng (Risk & Credit)
    for kw in RISK_KEYWORDS:
        if kw in combined_search_text:
            return ROLES_RISK

    # 3. Mặc định là tài liệu công khai chung
    return ROLES_PUBLIC


def process_and_assign_tags() -> pd.DataFrame:
    """Đọc dữ liệu, gán allowed_roles và lưu file chunks_secure.csv."""
    print("=" * 70)
    print("BẮT ĐẦU PHÂN LOẠI BẢO MẬT & GÁN THẺ QUYỀN (SECURITY TAGGING)")
    print("=" * 70)
    
    if not CHUNKS_NORMALIZED_PATH.exists():
        raise FileNotFoundError(f"Không tìm thấy file dữ liệu gốc tại: {CHUNKS_NORMALIZED_PATH}")

    df = pd.read_csv(CHUNKS_NORMALIZED_PATH)
    print(f"✓ Đã đọc thành công {len(df)} dòng dữ liệu từ: {CHUNKS_NORMALIZED_PATH.name}")

    # Áp dụng logic phân quyền
    print("→ Đang phân loại và gán allowed_roles cho từng chunk...")
    assigned_roles_list = []
    for _, row in df.iterrows():
        roles = classify_chunk(row)
        assigned_roles_list.append(json.dumps(roles, ensure_ascii=False))

    df["allowed_roles"] = assigned_roles_list

    # Lưu file mới
    CHUNKS_SECURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CHUNKS_SECURE_PATH, index=False, encoding="utf-8")
    print(f"✓ Đã lưu tập dữ liệu bảo mật ({len(df)} dòng) ra: {CHUNKS_SECURE_PATH}")

    return df


def verify_security_dataset(df: pd.DataFrame) -> None:
    """Kiểm tra tính hợp lệ và toàn vẹn của tập dữ liệu sau khi phân quyền."""
    print("\n" + "=" * 70)
    print("KIỂM THỬ TÍNH TOÀN VẸN & THỐNG KÊ PHÂN BỔ BẢO MẬT")
    print("=" * 70)

    # 1. Kiểm tra null/empty
    null_count = df["allowed_roles"].isna().sum()
    empty_count = (df["allowed_roles"].str.len() == 0).sum()
    print(f"1. Kiểm tra tính toàn vẹn:")
    print(f"   • Dòng bị null: {null_count}")
    print(f"   • Dòng bị rỗng: {empty_count}")
    assert null_count == 0, "LỖI: Tồn tại dòng có allowed_roles là Null!"
    assert empty_count == 0, "LỖI: Tồn tại dòng có allowed_roles bị Rỗng!"
    print("   -> TẤT CẢ các dòng đều được phân quyền hợp lệ (100% Complete) ✅")

    # 2. Thống kê theo nhóm quyền
    print(f"\n2. Thống kê phân bổ theo nhóm quyền:")
    role_group_counts = df["allowed_roles"].value_counts()
    for role_group, count in role_group_counts.items():
        pct = (count / len(df)) * 100
        parsed_roles = json.loads(role_group)
        print(f"   • {str(parsed_roles):<65} : {count:4d} chunks ({pct:5.1f}%)")

    # 3. Hiển thị 3 mẫu dòng dữ liệu đại diện cho 3 cấp độ
    print(f"\n3. Mẫu dữ liệu đại diện cho 3 cấp độ bảo mật:")
    
    sample_hr = df[df["allowed_roles"] == json.dumps(ROLES_HR, ensure_ascii=False)].iloc[0]
    sample_risk = df[df["allowed_roles"] == json.dumps(ROLES_RISK, ensure_ascii=False)].iloc[0]
    sample_pub = df[df["allowed_roles"] == json.dumps(ROLES_PUBLIC, ensure_ascii=False)].iloc[0]

    samples = [
        ("CẤP ĐỘ 1: NHÂN SỰ & QUẢN TRỊ NỘI BỘ (Chỉ Admin & HR_Manager)", sample_hr),
        ("CẤP ĐỘ 2: RỦI RO & TÍN DỤNG (Admin, Risk_Officer, Employee)", sample_risk),
        ("CẤP ĐỘ 3: QUY ĐỊNH CHUNG & CÔNG KHAI (Tất cả vai trò kể cả Guest)", sample_pub),
    ]

    for title_sec, s in samples:
        print("\n" + "-" * 70)
        print(f"[{title_sec}]")
        print(f"• Chunk ID     : {s['chunk_id']}")
        print(f"• Văn bản      : {s['so_ky_hieu']} - {s['title'][:70]}...")
        print(f"• Điều khoản   : {s.get('article', '')}")
        print(f"• Allowed Roles: {s['allowed_roles']}")
        snippet = str(s['text']).replace('\n', ' ')[:130]
        print(f"• Trích đoạn   : {snippet}...")
    print("=" * 70)


if __name__ == "__main__":
    secure_df = process_and_assign_tags()
    verify_security_dataset(secure_df)
