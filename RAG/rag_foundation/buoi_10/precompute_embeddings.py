"""
Script tiền xử lý và lưu cache Embedding cho toàn bộ 7,654 Chunks của 15 văn bản pháp luật.
Giúp việc nạp vào Neo4j sau này diễn ra tức thì (chỉ mất vài giây thay vì phải đợi embed lại).
"""

import sys
import time
import json
import pandas as pd
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from buoi_10_chunking import HTMLHierarchicalChunker, build_next_relationships
from buoi_10_embedding import embed_chunks_pipeline
from buoi_10_loader import CACHE_FILE, load_chunks_cache, save_chunks_cache

def main():
    print("=" * 80)
    print(" TIỀN XỬ LÝ CHUNKING & EMBEDDING CHO TOÀN BỘ 15 VĂN BẢN (LƯU VÀO CACHE)")
    print("=" * 80)

    # Kiểm tra cache hiện có
    chunks, next_rels = load_chunks_cache()
    if chunks and len(chunks) > 0:
        print(f"[+] Cache đã tồn tại với {len(chunks)} chunks tại: {CACHE_FILE}")
        return

    data_dir = Path(__file__).resolve().parent / "graph_rag_labs" / "kb+hops"
    metadata_path = data_dir / "metadata.csv"
    content_path = data_dir / "content.csv"

    df_meta = pd.read_csv(metadata_path)
    df_content = pd.read_csv(content_path)

    print(f"[*] 1. Đang bóc tách HTML và phân cấp Cha-Con cho {len(df_meta)} tài liệu...")
    chunker = HTMLHierarchicalChunker()
    all_chunks = []
    all_next_rels = []

    for _, row in df_content.iterrows():
        d_id = str(row['id'])
        meta_match = df_meta[df_meta['id'].astype(str) == d_id]
        d_title = meta_match['title'].values[0] if not meta_match.empty else f"Document {d_id}"
        d_html = row['content_html']

        doc_chunks = chunker.parse_document(doc_id=d_id, title=d_title, html_content=d_html)
        doc_nexts = build_next_relationships(doc_chunks)

        all_chunks.extend(doc_chunks)
        all_next_rels.extend(doc_nexts)

    print(f"[+] Bóc tách hoàn tất: {len(all_chunks)} Chunks, {len(all_next_rels)} quan hệ NEXT.")

    print(f"\n[*] 2. Đang tạo Vector Embeddings (mô hình thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5 trên CPU)...")
    all_chunks = embed_chunks_pipeline(all_chunks, batch_size=64)

    print(f"\n[*] 3. Đang ghi dữ liệu vào Cache file...")
    save_chunks_cache(all_chunks, all_next_rels)
    print(f"🎉 [HOÀN TẤT] Cache đã sẵn sàng tại {CACHE_FILE}!")

if __name__ == "__main__":
    main()
