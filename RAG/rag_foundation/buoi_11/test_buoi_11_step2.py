"""
Script Kiểm thử Toàn diện Bước 2: Truy vấn Vector và Mở rộng Đồ thị Đa bước (Multi-hop)
Bài thực hành 2 - Buổi 11: Multi-hop Graph RAG và Ứng dụng Hỏi Đáp (QA)

Kiểm tra:
- So sánh kết quả khi tìm kiếm với 0 hop (chỉ Vector), 1 hop và 2 hops.
- Kiểm thử trên 5 câu hỏi thực tế trong đề bài Buổi 11 Bước 4.
"""

import sys
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
from buoi_11_retrieval import search_graph_rag_context, print_search_results
from buoi_11_db import get_neo4j_driver, get_db_config

TEST_QUERIES = [
    {
        "id": 1,
        "question": "Nghị định 46/2023/NĐ-CP thay thế cho nghị định nào, và nghị định bị thay thế đó có nội dung gì nổi bật về kinh doanh bảo hiểm?",
        "expected_rel": "THAY_THE",
        "description": "Truy vấn quan hệ thay thế giữa Nghị định 46/2023 và Nghị định 73/2016"
    },
    {
        "id": 2,
        "question": "Văn bản hợp nhất số 52/VBHN-NHNN được hợp nhất từ văn bản nào, và quy định về hồ sơ, thủ tục cấp giấy phép lần đầu của ngân hàng thương mại gồm những tài liệu gì?",
        "expected_rel": "HOP_NHAT",
        "description": "Truy vấn quan hệ hợp nhất của Văn bản 52/VBHN-NHNN"
    },
    {
        "id": 3,
        "question": "Thông tư số 01/2025/TT-NHNN quy định về cấp giấy phép quỹ tín dụng nhân dân được sửa đổi, bổ sung bởi văn bản nào, và những nội dung sửa đổi bổ sung chính là gì?",
        "expected_rel": "SUA_DOI_BO_SUNG",
        "description": "Truy vấn quan hệ sửa đổi bổ sung của Thông tư 01/2025"
    },
    {
        "id": 4,
        "question": "Thông tư số 41/2016/TT-NHNN về tỷ lệ an toàn vốn của ngân hàng căn cứ vào luật nào, và luật đó quy định chức năng nhiệm vụ của cơ quan nào?",
        "expected_rel": "CAN_CU",
        "description": "Truy vấn quan hệ căn cứ pháp lý của Thông tư 41/2016"
    },
    {
        "id": 5,
        "question": "Hoạt động giao nhận, vận chuyển tiền mặt và tài sản quý của Ngân hàng Nhà nước được điều chỉnh bởi Thông tư nào, và Thông tư đó có được sửa đổi bổ sung bởi văn bản nào không?",
        "expected_rel": "SUA_DOI_BO_SUNG / VAN_BAN_BO_SUNG",
        "description": "Truy vấn điều chỉnh và sửa đổi bổ sung văn bản tiền tệ"
    }
]


def test_comparison_hops(question: str):
    """So sánh kết quả giữa 0 bước nhảy (chỉ vector) và 1 bước nhảy (đa bước)."""
    print("\n" + "=" * 90)
    print(f"🔬 SO SÁNH HIỆU QUẢ CỦA NGỮ CẢNH ĐA BƯỚC (MULTI-HOP)")
    print(f"❓ Câu hỏi: {question}")
    print("=" * 90)

    driver = get_neo4j_driver()
    try:
        # 1. Chạy với 0 hop (Chỉ Vector Search)
        print("\n🔹 [THỬ NGHIỆM 1] Cấu hình 0 HOP (Chỉ Vector Search truyền thống):")
        res_0 = search_graph_rag_context(query=question, top_k=3, num_hops=0, driver=driver)
        print(f"  • Số chunk trực tiếp      : {len(res_0['initial_chunks'])}")
        print(f"  • Số tài liệu hạt nhân    : {len(res_0['seed_doc_ids'])}")
        print(f"  • Quan hệ liên kết đồ thị : {len(res_0['traversal_paths'])} (Không mở rộng)")
        print(f"  • Tài liệu liên quan thu được : 0")

        # 2. Chạy với 1 hop (Vector Search + 1-hop Graph Traversal)
        print("\n🔸 [THỬ NGHIỆM 2] Cấu hình 1 HOP (Vector Search + Mở rộng Đồ thị 1 bước):")
        res_1 = search_graph_rag_context(query=question, top_k=3, num_hops=1, driver=driver)
        print(f"  • Số chunk trực tiếp      : {len(res_1['initial_chunks'])}")
        print(f"  • Số liên kết đồ thị tìm thấy: {len(res_1['traversal_paths'])}")
        print(f"  • Số tài liệu liên quan   : {len(res_1['related_documents'])}")
        print(f"  • Số chunk mở rộng bổ sung: {len(res_1['hop_chunks'])}")
        print(f"  • Tổng số chunk ngữ cảnh  : {len(res_1['all_chunks'])}")

        if res_1["traversal_paths"]:
            print(f"\n  👉 CÁC ĐƯỜNG DẪN QUAN HỆ KHÁM PHÁ ĐƯỢC:")
            for p in res_1["traversal_paths"]:
                rels = " -> ".join([f"[:{r['type']} ({r.get('relationship','')})]" for r in p["relationships"]])
                print(f"     • {p['seed_so_ky_hieu']} --{rels}--> {p['target_so_ky_hieu']} ({p['target_title'][:50]}...)")

        print("\n" + "=" * 90)
    finally:
        driver.close()


def run_all_test_questions():
    """Chạy kiểm thử trên tất cả 5 câu hỏi của đề bài."""
    driver = get_neo4j_driver()
    try:
        for item in TEST_QUERIES:
            print("\n" + "#" * 90)
            print(f"# CÂU HỎI {item['id']}: {item['question']}")
            print(f"# Mô tả: {item['description']} | Kỳ vọng quan hệ: {item['expected_rel']}")
            print("#" * 90)

            res = search_graph_rag_context(
                query=item["question"],
                top_k=3,
                num_hops=1,
                driver=driver
            )
            print_search_results(res)
    finally:
        driver.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        run_all_test_questions()
    else:
        # Chạy so sánh trên câu hỏi 1
        test_comparison_hops(TEST_QUERIES[0]["question"])
