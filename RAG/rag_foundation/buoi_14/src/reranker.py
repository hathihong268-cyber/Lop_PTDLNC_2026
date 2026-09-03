"""
Module: reranker.py
Buổi 14: Hybrid Search + Reranking + Mini Knowledge Graph
Nhiệm vụ: Tầng Reranking sử dụng mô hình Cross-Encoder đa ngôn ngữ (BAAI/bge-reranker-base)
để đánh giá tương quan ngữ cảnh trực tiếp giữa (Câu hỏi, Ứng viên).
"""

import math
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

MODEL_NAME = "BAAI/bge-reranker-base"


class CrossEncoderReranker:
    """
    Mô hình Cross-Encoder Reranker chấm điểm cặp (Query, Passage).
    Chỉ rerank trên danh sách ứng viên (candidate_k) từ Hybrid Search,
    tuyệt đối không rerank trên toàn bộ corpus để tối ưu hiệu năng.
    """

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        device: str = "auto",
        max_length: int = 512,
        batch_size: int = 4
    ):
        self.model_name = model_name
        self.max_length = max_length
        self.batch_size = batch_size

        if device == "auto":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self._tokenizer = None
        self._model = None

    def _load_model(self):
        """Lazy loading: Chỉ tải mô hình vào RAM khi thực sự bắt đầu rerank."""
        if self._tokenizer is None or self._model is None:
            print(f"[*] [RERANKER] Đang tải mô hình Cross-Encoder '{self.model_name}' trên {self.device.type.upper()}...")
            t0 = time.time()
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self._model.to(self.device)
            self._model.eval()
            print(f"[+] [RERANKER] Mô hình Cross-Encoder sẵn sàng ({time.time() - t0:.2f}s).")

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Đánh giá lại danh sách candidates từ Hybrid Search:
        1. Tạo cặp (query, chunk_text)
        2. Chạy qua Cross-Encoder
        3. Chuẩn hóa Sigmoid: 1 / (1 + exp(-logit))
        4. Sắp xếp lại và trả về top_k theo schema chuẩn
        """
        if not candidates:
            return []

        if not query or not query.strip():
            raise ValueError("Câu hỏi query không được để trống khi Rerank.")

        self._load_model()

        texts = [c["text"] for c in candidates]
        pairs = [[query, txt] for txt in texts]

        all_scores = []
        for i in range(0, len(pairs), self.batch_size):
            batch_pairs = pairs[i : i + self.batch_size]
            inputs = self._tokenizer(
                batch_pairs,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt"
            ).to(self.device)

            with torch.no_grad():
                outputs = self._model(**inputs)
                logits = outputs.logits
                if logits.dim() == 2 and logits.size(1) == 1:
                    logits = logits.squeeze(-1)
                elif logits.dim() == 2 and logits.size(1) > 1:
                    logits = logits[:, 0]

                logits_list = logits.cpu().tolist()
                if isinstance(logits_list, float):
                    logits_list = [logits_list]

                for logit in logits_list:
                    sig = 1.0 / (1.0 + math.exp(-float(logit)))
                    all_scores.append((float(logit), float(sig)))

        # Gán điểm và thông tin thứ hạng trước/sau rerank
        scored_candidates = []
        for cand, (raw_logit, sig_score) in zip(candidates, all_scores):
            item = dict(cand)
            item["hybrid_rank"] = cand.get("final_rank", None)
            item["hybrid_score"] = cand.get("rrf_score", None)
            item["rerank_raw_logit"] = round(raw_logit, 4)
            item["rerank_score"] = round(sig_score, 4)
            scored_candidates.append(item)

        # Sắp xếp giảm dần theo rerank_score (Sigmoid)
        scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)

        # Gán final_rank mới sau khi Rerank
        reranked_results = []
        for rank, item in enumerate(scored_candidates[:top_k], 1):
            item["final_rank"] = rank
            h_rank = item["hybrid_rank"]
            item["rank_shift"] = (h_rank - rank) if h_rank is not None else 0
            reranked_results.append(item)

        return reranked_results
