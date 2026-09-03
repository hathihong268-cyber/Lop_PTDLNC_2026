"""
Script: baseline_retrieval.py
Buổi 14: Hybrid Search + Reranking + Mini Knowledge Graph
Nhiệm vụ: Chạy thử nghiệm và so sánh kết quả giữa 2 Baseline độc lập:
1. BM25-only retrieval (Lexical)
2. Dense-only retrieval (Semantic Embedding)
"""

import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Đảm bảo UTF-8 trên Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Thêm thư mục gốc buoi_14 vào sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.bm25_retriever import BM25Retriever
from src.dense_retriever import DenseRetriever


def print_results(method_name: str, results: List[Dict[str, Any]], query: str):
    """In kết quả retrieval theo định dạng rõ ràng."""
    print("\n" + "=" * 75)
    print(f"{method_name.upper()} RESULTS (Top-{len(results)})")
    print(f"Câu hỏi: \"{query}\"")
    print("=" * 75)

    if not results:
        print("[!] Không tìm thấy kết quả nào phù hợp.")
        return

    for item in results:
        print(f"\n[Rank {item['rank']}] Score: {item['retrieval_score']:.4f} | Method: {item['retrieval_method']}")
        print(f"  • Trích dẫn (Citation): {item['citation']}")
        print(f"  • Chunk ID:             {item['chunk_id']}")
        print(f"  • Document ID:          {item['document_id']}")
        
        text_preview = item['text'].replace('\n', ' ')
        if len(text_preview) > 200:
            text_preview = text_preview[:200] + "..."
        print(f"  • Nội dung (Snippet):   {text_preview}")


def run_comparison(query: str, top_k: int = 5):
    """Khởi tạo và thực thi cả BM25 và Dense Retriever cho cùng 1 câu hỏi."""
    corpus_path = BASE_DIR / "data" / "processed" / "chunks_normalized.csv"
    if not corpus_path.exists():
        print(f"[ERROR] Không tìm thấy {corpus_path}. Hãy chạy `python scripts/prepare_corpus.py` trước.")
        sys.exit(1)

    print(f"[*] Đang nạp dữ liệu corpus từ: {corpus_path}")
    
    # 1. Khởi tạo BM25 Retriever
    print("[*] Đang khởi tạo BM25 Retriever...")
    bm25 = BM25Retriever(corpus_path)

    # 2. Khởi tạo Dense Retriever
    print("[*] Đang khởi tạo Dense Retriever...")
    dense = DenseRetriever(corpus_path, cache_dir=BASE_DIR / "cache")

    # 3. Thực thi tìm kiếm
    print(f"\n[>] Đang thực thi truy vấn: \"{query}\" (Top-k: {top_k})")
    bm25_results = bm25.search(query, top_k=top_k)
    dense_results = dense.search(query, top_k=top_k)

    # 4. In kết quả riêng biệt
    print_results("BM25", bm25_results, query)
    print_results("DENSE", dense_results, query)

    return bm25_results, dense_results


def main():
    parser = argparse.ArgumentParser(description="Chạy thử nghiệm Baseline Retrieval: BM25 vs Dense")
    parser.add_argument("--query", "--question", "-q", type=str, default="Quy định về vận chuyển và áp tải tiền mặt trong ngành ngân hàng", help="Câu hỏi truy vấn")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Số lượng kết quả lấy ra (mặc định: 5)")

    args = parser.parse_args()
    run_comparison(args.query, args.top_k)


if __name__ == "__main__":
    main()
