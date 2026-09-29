"""
Module Evaluation Benchmark - Buổi 09:
Đánh giá định lượng hiệu năng truy xuất và chất lượng của 4 chế độ:
single_flat, multi_flat, single_parent, multi_parent trên tập eval/questions.json.

LƯU Ý: Đây là skeleton placeholder được tạo trong Bước 02.
Chưa triển khai logic chạy benchmark; an toàn để import, không có side effects.
"""

from pathlib import Path
import sys
from typing import Dict, List, Any, Optional

BASE_DIR = Path(__file__).resolve().parent


def evaluate_hierarchical_system(
    questions_file: Optional[Path] = None,
    modes: Optional[List[str]] = None,
    k_list: Optional[List[int]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Placeholder hàm đánh giá benchmark 4 chế độ cho Buổi 09.
    TODO: Triển khai ở Bước tiếp theo.
    """
    raise NotImplementedError("Chưa triển khai trong Bước 02 (Skeleton).")


def main():
    """CLI Placeholder cho evaluate.py."""
    print("=== BUỔI 09: EVALUATION BENCHMARK (SKELETON BƯỚC 02) ===")
    print("Mã nguồn đang ở trạng thái skeleton. Vui lòng triển khai các bước kế tiếp theo SPEC_buoi_09.md.")


if __name__ == "__main__":
    main()
