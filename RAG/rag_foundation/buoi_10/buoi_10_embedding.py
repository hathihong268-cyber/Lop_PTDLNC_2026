"""
Module Buoc 2: Tao Vector Nhung (Dense Embeddings) bang mo hinh Tieng Viet tren CPU
Mo hinh: thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5
Bai thuc hanh 1 - Buoi 10: Graph RAG Foundation
"""

import os
import sys
import time
import json
import torch
import torch.nn.functional as F
from pathlib import Path
from typing import List, Dict, Any, Union
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModel

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


MODEL_NAME = "thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5"
EMBEDDING_DIM = 384


class VietnameseEmbeddingModel:
    """
    Mo hinh tao Vector Nhung Tieng Viet toi uu hoa chay tren CPU voi PyTorch.
    Su dung co che Mean Pooling va L2-Normalization.
    """

    def __init__(self, model_name: str = MODEL_NAME, device: str = "cpu"):
        self.device = torch.device(device)
        self.model_name = model_name
        
        print(f"[*] Dang tai mo hinh nhung '{model_name}' tren thiet bi: {self.device.type.upper()}...")
        start_t = time.time()
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()
        print(f"[+] Mo hinh da san sang ({time.time() - start_t:.2f}s). Kich thuoc Vector: {EMBEDDING_DIM} dims")

    @staticmethod
    def _mean_pooling(model_output, attention_mask):
        """
        Thuc hien Mean Pooling ket hop voi Attention Mask de tinh toan
        vector dai dien cho toan bo cau/doan van ban.
        """
        token_embeddings = model_output[0]  # First element chua token embeddings (batch_size, seq_len, hidden_dim)
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        return sum_embeddings / sum_mask

    def embed_texts(self, texts: List[str], batch_size: int = 64, show_progress: bool = True) -> List[List[float]]:
        """
        Tao vector nhung cho danh sach van ban theo Batch tren CPU.
        Ket qua tra ve da duoc chuan hoa L2 (Cosine similarity san sang).
        """
        if not texts:
            return []

        all_embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size
        
        iterator = range(0, len(texts), batch_size)
        if show_progress:
            iterator = tqdm(iterator, total=total_batches, desc="[Embeddings CPU]", unit="batch")

        for i in iterator:
            batch = texts[i:i + batch_size]
            
            # Tokenize & Padding
            encoded_input = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            ).to(self.device)

            with torch.no_grad():
                model_output = self.model(**encoded_input)
                # Mean pooling
                sentence_embeddings = self._mean_pooling(model_output, encoded_input["attention_mask"])
                # L2 Normalization (Cosine Similarity)
                sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)

            all_embeddings.extend(sentence_embeddings.cpu().tolist())

        return all_embeddings

    def embed_query(self, query: str) -> List[float]:
        """Tao vector nhung cho 1 cau truy van don le."""
        return self.embed_texts([query], batch_size=1, show_progress=False)[0]


def embed_chunks_pipeline(chunks: List[Dict[str, Any]], batch_size: int = 64) -> List[Dict[str, Any]]:
    """
    Nhan danh sach cac Chunk tu Buoc 1, tao vector nhung cho truong `text` cua moi chunk
    va gan vao truong `embedding`.
    """
    model = VietnameseEmbeddingModel()
    
    # Lay danh sach van ban can nhung (ket hop heading + text de gia tang tinh ngu canh)
    texts_to_embed = []
    for c in chunks:
        heading = c.get('heading', '')
        text = c.get('text', '')
        if heading and heading != text:
            full_text = f"{heading}\n{text}"
        else:
            full_text = text
        texts_to_embed.append(full_text)

    print(f"\n[*] Bat dau tao Vector Nhung cho tong cong {len(chunks)} Chunks...")
    start_time = time.time()
    embeddings = model.embed_texts(texts_to_embed, batch_size=batch_size, show_progress=True)
    elapsed = time.time() - start_time
    
    print(f"[+] Hoan thanh tao Vector Nhung trong {elapsed:.2f}s ({len(chunks)/elapsed:.1f} chunks/giay)!")

    # Gan embedding vao chunk
    for i, c in enumerate(chunks):
        c['embedding'] = embeddings[i]

    return chunks


if __name__ == "__main__":
    print("=" * 80)
    print(" BƯỚC 2: TẠO VECTOR NHÚNG (EMBEDDING) BẰNG MÔ HÌNH TIẾNG VIỆT TRÊN CPU")
    print("=" * 80)
    
    # Import chunker từ Bước 1 để lấy dữ liệu mẫu
    from buoi_10_chunking import HTMLHierarchicalChunker, build_next_relationships
    import pandas as pd

    data_dir = Path(__file__).resolve().parent / "graph_rag_labs" / "kb+hops"
    metadata_path = data_dir / "metadata.csv"
    content_path = data_dir / "content.csv"

    df_meta = pd.read_csv(metadata_path)
    df_content = pd.read_csv(content_path)

    chunker = HTMLHierarchicalChunker()

    # Thử nghiệm trên 1 Document đầu tiên làm mẫu minh họa
    sample_row = df_content.iloc[0]
    sample_id = str(sample_row['id'])
    sample_title = df_meta[df_meta['id'].astype(str) == sample_id]['title'].values[0]
    sample_html = sample_row['content_html']

    print(f"\n1. Phân tách tài liệu mẫu ID: {sample_id} ({sample_title[:60]}...)")
    sample_chunks = chunker.parse_document(doc_id=sample_id, title=sample_title, html_content=sample_html)
    print(f"   -> Đã tạo {len(sample_chunks)} chunks.")

    print(f"\n2. Thực hiện Embedding cho các chunks mẫu:")
    embedded_chunks = embed_chunks_pipeline(sample_chunks, batch_size=64)

    print(f"\n3. Kết quả minh họa mẫu Vector nhúng:")
    for c in embedded_chunks[:3]:
        vec = c['embedding']
        print(f"   - Chunk ID: {c['chunk_id']}")
        print(f"     Heading : {c['heading']}")
        print(f"     Vector  : [{vec[0]:.4f}, {vec[1]:.4f}, {vec[2]:.4f}, ..., {vec[-1]:.4f}] (Độ dài: {len(vec)})")
