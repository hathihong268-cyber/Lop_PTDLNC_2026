"""
Module: dense_retriever.py
Buổi 14: Hybrid Search + Reranking + Mini Knowledge Graph
Nhiệm vụ: Bộ truy xuất Vector ngữ nghĩa (Dense Retrieval) tối ưu cho tiếng Việt với cơ chế Cache Embeddings.
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel

from src.citation import format_citation

MODEL_NAME = "thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5"
EMBEDDING_DIM = 384


class DenseRetriever:
    """
    Bộ truy xuất Vector Dense Retrieval sử dụng mô hình embedding tiếng Việt,
    kết hợp lưu cache cục bộ trong buoi_14/cache/ để tái sử dụng tức thì.
    """

    def __init__(self, corpus_csv_path: Optional[Path] = None, cache_dir: Optional[Path] = None):
        base_dir = Path(__file__).resolve().parent.parent
        
        if corpus_csv_path is None:
            corpus_csv_path = base_dir / "data" / "processed" / "chunks_normalized.csv"
        if cache_dir is None:
            cache_dir = base_dir / "cache"

        self.corpus_csv_path = Path(corpus_csv_path)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "dense_embeddings_cache.npz"

        if not self.corpus_csv_path.exists():
            raise FileNotFoundError(f"Không tìm thấy file corpus tại: {self.corpus_csv_path}")

        # Đọc dữ liệu corpus
        self.df = pd.read_csv(self.corpus_csv_path, dtype=str).fillna("")
        self.chunks: List[Dict[str, Any]] = self.df.to_dict(orient="records")
        self.chunk_ids = [c["chunk_id"] for c in self.chunks]

        # Quản lý Model & Tokenizer (Lazy loading)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._tokenizer = None
        self._model = None

        # Tải hoặc tạo Embeddings
        self.doc_embeddings = self._get_or_compute_embeddings()

    def _load_model(self):
        """Khởi tạo mô hình và tokenizer nếu chưa tải."""
        if self._model is None or self._tokenizer is None:
            print(f"[*] Đang tải mô hình nhúng '{MODEL_NAME}' trên {self.device.type.upper()}...")
            start_t = time.time()
            self._tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            self._model = AutoModel.from_pretrained(MODEL_NAME)
            self._model.to(self.device)
            self._model.eval()
            print(f"[+] Mô hình đã sẵn sàng ({time.time() - start_t:.2f}s).")

    @staticmethod
    def _mean_pooling(model_output, attention_mask):
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        return sum_embeddings / sum_mask

    def _embed_texts_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Sinh vector embedding theo lô (batch)."""
        self._load_model()
        all_embeddings = []

        total = len(texts)
        for i in range(0, total, batch_size):
            batch_texts = texts[i : i + batch_size]
            encoded = self._tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            ).to(self.device)

            with torch.no_grad():
                model_output = self._model(**encoded)
                sentence_embeddings = self._mean_pooling(model_output, encoded["attention_mask"])
                sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)

            all_embeddings.append(sentence_embeddings.cpu().numpy())

        return np.vstack(all_embeddings)

    def _get_or_compute_embeddings(self) -> np.ndarray:
        """Kiểm tra cache; nếu hợp lệ thì load, nếu chưa có thì tính toán và lưu cache."""
        if self.cache_file.exists():
            try:
                data = np.load(self.cache_file, allow_pickle=True)
                cached_ids = list(data["chunk_ids"])
                cached_embs = data["embeddings"]
                if cached_ids == self.chunk_ids and cached_embs.shape[0] == len(self.chunk_ids):
                    print(f"[+] Đã tải Embeddings từ Cache ({len(cached_ids)} chunks): {self.cache_file}")
                    return cached_embs
                else:
                    print("[!] Cache không khớp với corpus hiện tại. Tiến hành tạo mới...")
            except Exception as e:
                print(f"[!] Lỗi đọc cache ({e}). Tiến hành tạo mới...")

        print(f"[*] Bắt đầu tạo Dense Embeddings cho {len(self.chunks)} chunks...")
        texts = [c["text"] for c in self.chunks]
        t0 = time.time()
        embs = self._embed_texts_batch(texts, batch_size=32)
        print(f"[+] Hoàn thành sinh Embeddings ({time.time() - t0:.2f}s). Shape: {embs.shape}")

        # Lưu cache
        np.savez_compressed(self.cache_file, chunk_ids=self.chunk_ids, embeddings=embs)
        print(f"[+] Đã lưu Cache vào: {self.cache_file}")
        return embs

    def embed_query(self, query: str) -> np.ndarray:
        """Sinh vector embedding chuẩn hóa cho câu truy vấn."""
        self._load_model()
        encoded = self._tokenizer(
            [query],
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        ).to(self.device)

        with torch.no_grad():
            model_output = self._model(**encoded)
            sentence_embedding = self._mean_pooling(model_output, encoded["attention_mask"])
            sentence_embedding = F.normalize(sentence_embedding, p=2, dim=1)

        return sentence_embedding.cpu().numpy()[0]

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Tìm kiếm top_k chunks có độ tương đồng Cosine cao nhất với query vector.
        """
        query_vec = self.embed_query(query)
        # Cosine similarity do các vector đã được L2 normalized
        scores = np.dot(self.doc_embeddings, query_vec)

        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for rank, idx in enumerate(top_indices, 1):
            row = self.chunks[idx]
            score = float(scores[idx])

            results.append({
                "rank": rank,
                "chunk_id": row["chunk_id"],
                "document_id": row["document_id"],
                "text": row["text"],
                "retrieval_score": round(score, 4),
                "retrieval_method": "dense",
                "citation": format_citation(row),
            })

        return results
