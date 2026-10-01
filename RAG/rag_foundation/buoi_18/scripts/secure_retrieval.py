"""
Module: secure_retrieval.py
Vị trí: buoi_17/scripts/secure_retrieval.py
Mục đích: Re-export và wrapper cho SecureRetrievalAdapter của Buổi 17.
"""

import sys
from pathlib import Path

BUOI_17_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUOI_17_DIR))

from scripts.secure_retrieval_adapter import SecureRetrievalAdapter, get_adapted_secure_retriever

__all__ = ["SecureRetrievalAdapter", "get_adapted_secure_retriever"]

if __name__ == "__main__":
    adapter = get_adapted_secure_retriever()
    res = adapter.retrieve(query="Thủ kho tiền", user_roles=["HR_Manager"], top_k=2)
    print("Retrieved Chunks:", len(res["results"]))
