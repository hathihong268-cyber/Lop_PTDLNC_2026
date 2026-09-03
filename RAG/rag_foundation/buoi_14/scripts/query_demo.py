"""
Script: query_demo.py
Buổi 14: Hybrid Search + Reranking + Mini Knowledge Graph
Nhiệm vụ: Giao diện dòng lệnh CLI thực thi hàm retrieval thống nhất `retrieve(question, method, top_k)`
kết hợp trích xuất Gợi ý Đồ thị (GRAPH HINTS) từ Mini Knowledge Graph Neo4j.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Đảm bảo UTF-8 trên Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.unified_retriever import retrieve


def get_graph_hints(retrieved_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Truy vấn các quan hệ đồ thị trực tiếp (1-Hop) từ Neo4j cho các Document và Chunks được retrieve.
    Không thực hiện traversal phức tạp, chỉ cung cấp metadata gợi ý ngữ cảnh đồ thị.
    """
    hints = {
        "connected": False,
        "document_relations": [],
        "adjacent_chunks": [],
        "error_message": None
    }

    # Tải cấu hình kết nối
    env_paths = [BASE_DIR / ".env", BASE_DIR.parent / "buoi_10" / ".env", BASE_DIR.parent.parent.parent / ".env"]
    for ep in env_paths:
        if ep.exists():
            load_dotenv(ep, override=True)
            break

    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "abcd1234")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
    except Exception as e:
        hints["error_message"] = f"Neo4j không khả dụng ({e}). Bỏ qua trích xuất Graph Hints."
        return hints

    hints["connected"] = True

    # 1. Thu thập các Document ID và Chunk ID duy nhất
    doc_ids = list({r["document_id"] for r in retrieved_results if "document_id" in r})
    chunk_ids = list({r["chunk_id"] for r in retrieved_results if "chunk_id" in r})

    with driver.session(database=database) as session:
        # A. Quan hệ liên văn bản (Document to Document)
        q_doc_rel = """
        MATCH (v1:VanBan {lab_session: 'buoi_14'})-[r]->(v2:VanBan {lab_session: 'buoi_14'})
        WHERE v1.id IN $doc_ids OR v2.id IN $doc_ids
        RETURN v1.id AS src_id, v1.so_ky_hieu AS src_doc,
               type(r) AS rel_type, r.relationship_label AS rel_label,
               v2.id AS dst_id, v2.so_ky_hieu AS dst_doc
        """
        doc_res = session.run(q_doc_rel, doc_ids=doc_ids).data()
        for d in doc_res:
            hints["document_relations"].append(
                f"[{d['src_doc']}] --[:{d['rel_type']} ({d['rel_label']})]--> [{d['dst_doc']}]"
            )

        # B. Quan hệ tuần tự liền kề (Adjacent NEXT Chunks)
        q_next = """
        MATCH (d1:DieuKhoan {lab_session: 'buoi_14'})-[:NEXT]->(d2:DieuKhoan {lab_session: 'buoi_14'})
        WHERE d1.id IN $chunk_ids OR d2.id IN $chunk_ids
        RETURN d1.id AS from_chunk, d1.article AS from_art,
               d2.id AS to_chunk, d2.article AS to_art
        LIMIT 5
        """
        next_res = session.run(q_next, chunk_ids=chunk_ids).data()
        for n in next_res:
            f_art = n['from_art'].split('.')[0] if '.' in n['from_art'] else n['from_art']
            t_art = n['to_art'].split('.')[0] if '.' in n['to_art'] else n['to_art']
            hints["adjacent_chunks"].append(
                f"({n['from_chunk']} [{f_art}]) --[:NEXT]--> ({n['to_chunk']} [{t_art}])"
            )

    driver.close()
    return hints


def print_demo_results(query: str, method: str, results: List[Dict[str, Any]], hints: Dict[str, Any]):
    """Hiển thị kết quả truy vấn và Graph Hints rõ ràng, dễ đọc."""
    print("\n" + "=" * 95)
    print(f"RAG RETRIEVAL EXPLORER — BUỔI 14")
    print(f"Phương pháp: {method.upper()} | Tổng kết quả: {len(results)}")
    print(f"Câu hỏi:     \"{query}\"")
    print("=" * 95)

    if not results:
        print("[!] Không tìm thấy đoạn văn bản nào phù hợp.")
        return

    print("\n📋 DANH SÁCH TÀI LIỆU TRÍCH XUẤT (TOP-K CONTEXT):")
    print("-" * 95)

    for item in results:
        rank = item["rank"]
        citation = item["citation"]
        chunk_id = item["chunk_id"]
        doc_id = item["document_id"]

        # Format điểm
        if method == "hybrid_rerank":
            score_info = f"Rerank Score: {item.get('rerank_score', 0):.4f} (Hybrid RRF: {item.get('hybrid_score', 0):.4f})"
        elif method == "hybrid":
            score_info = f"RRF Score: {item['score']:.6f} (BM25: #{item.get('bm25_rank', '-')}, Dense: #{item.get('dense_rank', '-')})"
        elif method == "dense":
            score_info = f"Cosine Sim: {item['score']:.4f}"
        else:
            score_info = f"BM25 Score: {item['score']:.4f}"

        print(f"\n[Rank {rank}] {citation}")
        print(f"  • Chunk ID:    {chunk_id} (Doc ID: {doc_id})")
        print(f"  • Điểm số:     {score_info}")
        
        text_preview = item["text"].replace("\n", " ")
        if len(text_preview) > 220:
            text_preview = text_preview[:220] + "..."
        print(f"  • Trích đoạn:  {text_preview}")

    # In phần GRAPH HINTS
    print("\n" + "=" * 95)
    print("🌐 GRAPH HINTS (Gợi ý Mối Quan Hệ Đồ Thị Trực Tiếp từ Neo4j)")
    print("=" * 95)

    doc_ids_str = ", ".join(list({r['document_id'] for r in results}))
    chunk_ids_str = ", ".join([r['chunk_id'] for r in results])
    print(f"• Document IDs liên quan: [{doc_ids_str}]")
    print(f"• Chunk IDs đã truy xuất:  [{chunk_ids_str}]")

    if not hints["connected"]:
        print(f"\n[!] {hints['error_message']}")
    else:
        print("\n1. Quan hệ pháp lý liên văn bản (Inter-Document Relationships):")
        if hints["document_relations"]:
            for rel in set(hints["document_relations"]):
                print(f"   ↳ {rel}")
        else:
            print("   ↳ (Không có quan hệ liên văn bản trực tiếp nào giữa các văn bản trên)")

        print("\n2. Cấu trúc điều khoản liền kề (Adjacent Article Sequence [:NEXT]):")
        if hints["adjacent_chunks"]:
            for adj in hints["adjacent_chunks"]:
                print(f"   ↳ {adj}")
        else:
            print("   ↳ (Không có liên kết NEXT trực tiếp trong danh sách)")

    print("=" * 95 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Chạy Demo Retrieval thống nhất và trích xuất Graph Hints")
    parser.add_argument(
        "--query", "--question", "-q",
        type=str,
        default="Theo Thông tư 01/2014/TT-NHNN thì trách nhiệm của người áp tải tiền mặt là gì?",
        help="Câu hỏi truy vấn"
    )
    parser.add_argument(
        "--method", "-m",
        type=str,
        choices=["bm25", "dense", "hybrid", "hybrid_rerank"],
        default="hybrid_rerank",
        help="Phương pháp truy xuất (mặc định: hybrid_rerank)"
    )
    parser.add_argument(
        "--top-k", "-k",
        type=int,
        default=5,
        help="Số lượng kết quả lấy ra (mặc định: 5)"
    )
    parser.add_argument(
        "--candidate-k", "-c",
        type=int,
        default=20,
        help="Số lượng ứng viên thu thập cho Hybrid trước khi Rerank (mặc định: 20)"
    )

    args = parser.parse_args()

    # 1. Chạy hàm retrieval thống nhất
    results = retrieve(
        question=args.query,
        method=args.method,
        top_k=args.top_k,
        candidate_k=args.candidate_k
    )

    # 2. Lấy gợi ý quan hệ đồ thị trực tiếp
    hints = get_graph_hints(results)

    # 3. In kết quả đẹp mắt cho học viên
    print_demo_results(args.query, args.method, results, hints)


if __name__ == "__main__":
    main()
