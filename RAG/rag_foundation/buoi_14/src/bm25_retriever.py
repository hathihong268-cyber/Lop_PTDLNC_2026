"""
Module: bm25_retriever.py
Buổi 14: Hybrid Search + Reranking + Mini Knowledge Graph
Nhiệm vụ: Bộ truy xuất Lexical BM25 tối ưu hóa cho văn bản quy phạm pháp luật tiếng Việt.
"""

import re
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from rank_bm25 import BM25Okapi

from src.citation import format_citation


def tokenize_vietnamese_legal(text: str) -> List[str]:
    """
    Hàm tách từ (tokenization) chuyên dụng cho văn bản pháp lý tiếng Việt:
    - Bảo toàn mã/số hiệu văn bản: 46/2023/NĐ-CP, 01/2014/TT-NHNN, 17/2023/QH15...
    - Bảo toàn số hiệu điều khoản: Điều 1, Điều 73, Khoản 2, Điểm a...
    - Chuẩn hóa chữ thường và phân tách các từ tiếng Việt chuẩn xác.
    """
    if not text:
        return []
    
    text_lower = text.lower()
    
    # Pattern nhận diện token:
    # 1. Mã văn bản chứa dấu gạch chéo / gạch ngang / số: [a-z0-9à-ỹ\/\.\-_]+
    # 2. Các từ tiếng Việt có dấu và số
    tokens = re.findall(r'[a-z0-9àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ\/\.\-_]+', text_lower)
    
    # Loại bỏ các token thuần ký tự dấu nếu có
    cleaned_tokens = [t.strip("/.-_") for t in tokens if len(t.strip("/.-_")) > 0]
    return cleaned_tokens


class BM25Retriever:
    """
    Bộ truy xuất từ khóa BM25 cho Corpus quy phạm pháp luật.
    """

    def __init__(self, corpus_csv_path: Optional[Path] = None):
        if corpus_csv_path is None:
            base_dir = Path(__file__).resolve().parent.parent
            corpus_csv_path = base_dir / "data" / "processed" / "chunks_normalized.csv"
            
        self.corpus_csv_path = Path(corpus_csv_path)
        if not self.corpus_csv_path.exists():
            raise FileNotFoundError(f"Không tìm thấy file corpus tại: {self.corpus_csv_path}")

        # Đọc dữ liệu chunks đã chuẩn hóa
        self.df = pd.read_csv(self.corpus_csv_path, dtype=str).fillna("")
        self.chunks: List[Dict[str, Any]] = self.df.to_dict(orient="records")

        # Tokenize toàn bộ corpus
        self.tokenized_corpus = [
            tokenize_vietnamese_legal(str(c.get("text", ""))) for c in self.chunks
        ]
        
        # Khởi tạo mô hình BM25Okapi
        self.bm25 = BM25Okapi(self.tokenized_corpus)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Tìm kiếm top_k chunks có điểm BM25 cao nhất cho query.
        Trả về danh sách dict theo đúng schema chuẩn.
        """
        tokenized_query = tokenize_vietnamese_legal(query)
        if not tokenized_query:
            return []

        scores = self.bm25.get_scores(tokenized_query)
        
        # Lấy top_k chỉ số có điểm cao nhất
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

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
                "retrieval_method": "bm25",
                "citation": format_citation(row),
            })

        return results
