"""
Script: secure_search_demo.py
Buổi 15: Cài đặt Kiểm soát Truy cập dựa trên Vai trò (RBAC) ở mức Dữ liệu
Nhiệm vụ: Giao diện CLI tương tác demo tìm kiếm bảo mật với các tham số --query, --roles, --method, --top-k.
"""

import sys
import argparse
from pathlib import Path
from typing import List

# Đảm bảo UTF-8 trên Windows console
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.config import VALID_ROLES, ROLE_GUEST, validate_roles
from src.secure_retriever import secure_retrieve


def main():
    parser = argparse.ArgumentParser(description="Demo Tìm kiếm An toàn (Secure Retrieval Pipeline) - Buổi 15")
    parser.add_argument(
        "--query",
        type=str,
        default="Tiêu chuẩn bổ nhiệm chức danh thủ kho tiền, thủ quỹ, kiểm ngân",
        help="Câu hỏi truy vấn"
    )
    parser.add_argument(
        "--roles",
        type=str,
        nargs="+",
        default=[ROLE_GUEST],
        help=f"Danh sách vai trò của người dùng. Hợp lệ: {VALID_ROLES}"
    )
    parser.add_argument(
        "--method",
        type=str,
        choices=["bm25", "dense", "hybrid", "hybrid_rerank"],
        default="hybrid_rerank",
        help="Phương pháp tìm kiếm"
    )
    parser.add_argument("--top-k", type=int, default=5, help="Số lượng kết quả cần lấy")
    parser.add_argument("--candidate-k", type=int, default=20, help="Số lượng ứng viên trước khi rerank")
    parser.add_argument("--no-graph", action="store_true", help="Không trích xuất Graph Hints từ Neo4j")

    args = parser.parse_args()

    user_roles = validate_roles(args.roles)

    print("=" * 80)
    print("DEMO TRUY VẤN AN TOÀN (SECURE RETRIEVAL PIPELINE)")
    print("=" * 80)
    print(f"• Câu hỏi (Query)        : {args.query}")
    print(f"• Vai trò người dùng     : {user_roles}")
    print(f"• Phương pháp (Method)   : {args.method.upper()}")
    print(f"• Top-K / Candidate-K    : {args.top_k} / {args.candidate_k}")
    print("=" * 80)

    res = secure_retrieve(
        query=args.query,
        user_roles=user_roles,
        method=args.method,
        top_k=args.top_k,
        candidate_k=args.candidate_k,
        include_graph_hints=not args.no_graph
    )

    print(f"\n[+] Thời gian thực thi  : {res['elapsed_ms']} ms")
    print(f"[+] Số kết quả trả về   : {res['results_count']}")
    print(f"[!] Đã lọc bỏ do cấm    : {res['filtered_out_count']} chunks không có quyền truy cập\n")

    print("-" * 80)
    print("DANH SÁCH KẾT QUẢ TOP-K ĐƯỢC PHÉP TRUY CẬP:")
    print("-" * 80)

    for item in res["results"]:
        rank = item["rank"]
        cid = item["chunk_id"]
        score = item["score"]
        allowed = item["allowed_roles"]
        citation = item["citation"]
        text_snippet = item["text"].replace("\n", " ")[:140]

        print(f"\n[TOP {rank}] {citation}")
        print(f"       Chunk ID      : {cid}")
        print(f"       Điểm số       : {score}")
        print(f"       Quyền xem     : {allowed}")
        print(f"       Vai trò khớp  : {item.get('matched_roles', [])}")
        print(f"       Nội dung      : {text_snippet}...")

    hints = res.get("graph_hints")
    if hints and hints.get("connected"):
        print("\n" + "-" * 80)
        print("SECURE GRAPH HINTS (GỢI Ý ĐỒ THỊ NEO4J ĐÃ LỌC QUYỀN):")
        print("-" * 80)
        if hints.get("document_relations"):
            print("• Quan hệ giữa các văn bản:")
            for r in hints["document_relations"]:
                print(f"   -> {r}")
        else:
            print("• Không có quan hệ liên văn bản phù hợp với quyền truy cập.")

        if hints.get("adjacent_chunks"):
            print("\n• Các điều khoản liền kề [:NEXT] được phép xem:")
            for n in hints["adjacent_chunks"]:
                print(f"   -> {n}")
        else:
            print("• Không có điều khoản liền kề hợp lệ với quyền truy cập.")
    elif hints and hints.get("error_message"):
        print(f"\n[!] Graph Hints Info: {hints['error_message']}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
