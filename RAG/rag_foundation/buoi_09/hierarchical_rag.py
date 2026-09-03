"""
Module Hierarchical & Multi-Query RAG cho Buổi 09:
Triển khai Document Structure Hierarchy Builder, Parent-Child Registry,
Cross-Query RRF Fusion, Parent Aggregation và Parent Reranking cho văn bản pháp luật ngân hàng.

Mọi đường dẫn sử dụng Path(__file__).resolve().parent để tự quản lý cấu hình .env
và storage riêng của Buổi 09 mà không phụ thuộc vào current working directory (cwd).
"""

import os
import sys
import json
import math
import time
import re
import hashlib
import unicodedata
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Callable

# Import loader, validator, collection naming từ baseline Buổi 09
from rag import (
    load_chunks,
    validate_chunk,
    validate_embeddings,
    get_collection_name,
    get_chroma_client,
    verify_collection_compatibility,
    generate_embeddings,
    generate_query_embedding,
    get_gemini_client,
    ALLOWED_STRATEGIES,
    DEFAULT_INPUT_DIR,
)

# Thư mục gốc Buổi 09
BASE_DIR = Path(__file__).resolve().parent
CHROMA_STORAGE_DIR = BASE_DIR / "storage" / "chroma"
HIERARCHY_STORAGE_DIR = BASE_DIR / "storage" / "hierarchy"
HF_STORAGE_DIR = BASE_DIR / "storage" / "huggingface"

# Đảm bảo stdout/stderr hỗ trợ UTF-8 an toàn trên Windows console
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

MODES = {"single_flat", "multi_flat", "single_parent", "multi_parent"}


# ==============================================================================
# 1. CONFIGURATION LOADER & VALIDATOR
# ==============================================================================

def load_buoi_09_config() -> dict[str, Any]:
    """
    Nạp và kiểm tra toàn diện cấu hình Buổi 09 từ file .env cục bộ.
    Không phụ thuộc vào current working directory (cwd).
    """
    from dotenv import load_dotenv
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    # 1. API & Base Models
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2").strip()
    embedding_dim_str = os.getenv("GEMINI_EMBEDDING_DIM", "768").strip()
    generation_model = os.getenv("GEMINI_GENERATION_MODEL", "gemini-3.5-flash-lite").strip()
    max_distance_str = os.getenv("RAG_MAX_DISTANCE", "0.45").strip()

    if not embedding_model:
        raise ValueError("Cấu hình GEMINI_EMBEDDING_MODEL không được để rỗng")
    if not generation_model:
        raise ValueError("Cấu hình GEMINI_GENERATION_MODEL không được để rỗng")

    try:
        embedding_dim = int(embedding_dim_str)
        if not (128 <= embedding_dim <= 3072):
            raise ValueError()
    except Exception:
        raise ValueError(f"GEMINI_EMBEDDING_DIM phải là số nguyên trong khoảng 128 đến 3072, nhận được '{embedding_dim_str}'")

    try:
        max_distance = float(max_distance_str)
        if max_distance < 0.0:
            raise ValueError()
    except Exception:
        raise ValueError(f"RAG_MAX_DISTANCE phải là số thực không âm, nhận được '{max_distance_str}'")

    # 2. Retrieval Candidates & Final Top-K
    bm25_cand_str = os.getenv("BM25_CANDIDATES", "20").strip()
    semantic_cand_str = os.getenv("SEMANTIC_CANDIDATES", "20").strip()
    rerank_cand_str = os.getenv("RERANK_CANDIDATES", "20").strip()
    final_top_k_str = os.getenv("FINAL_TOP_K", "5").strip()

    for name, val_str in [
        ("BM25_CANDIDATES", bm25_cand_str),
        ("SEMANTIC_CANDIDATES", semantic_cand_str),
        ("RERANK_CANDIDATES", rerank_cand_str),
        ("FINAL_TOP_K", final_top_k_str)
    ]:
        try:
            val = int(val_str)
            if not (1 <= val <= 100):
                raise ValueError()
        except Exception:
            raise ValueError(f"{name} phải là số nguyên dương từ 1 đến 100, nhận được '{val_str}'")

    bm25_candidates = int(bm25_cand_str)
    semantic_candidates = int(semantic_cand_str)
    rerank_candidates = int(rerank_cand_str)
    final_top_k = int(final_top_k_str)

    if final_top_k > rerank_candidates:
        raise ValueError(f"FINAL_TOP_K ({final_top_k}) phải <= RERANK_CANDIDATES ({rerank_candidates})")

    # 3. RRF Configuration
    rrf_k_str = os.getenv("RRF_K", "60").strip()
    try:
        rrf_k = int(rrf_k_str)
        if rrf_k <= 0:
            raise ValueError()
    except Exception:
        raise ValueError(f"RRF_K phải là số nguyên dương > 0, nhận được '{rrf_k_str}'")

    w_bm25_str = os.getenv("RRF_BM25_WEIGHT", "1.0").strip()
    w_sem_str = os.getenv("RRF_SEMANTIC_WEIGHT", "1.0").strip()
    try:
        w_bm25 = float(w_bm25_str)
        w_semantic = float(w_sem_str)
        if w_bm25 < 0.0 or w_semantic < 0.0:
            raise ValueError()
        if w_bm25 == 0.0 and w_semantic == 0.0:
            raise ValueError()
    except Exception:
        raise ValueError(
            f"Trọng số RRF (RRF_BM25_WEIGHT={w_bm25_str}, RRF_SEMANTIC_WEIGHT={w_sem_str}) "
            f"phải là các số thực không âm và không đồng thời bằng 0."
        )

    # 4. Cross-Encoder Reranker Configuration
    reranker_model = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3").strip()
    if not reranker_model:
        raise ValueError("RERANKER_MODEL không được để rỗng")

    max_len_str = os.getenv("RERANKER_MAX_LENGTH", "512").strip()
    try:
        reranker_max_length = int(max_len_str)
        if not (64 <= reranker_max_length <= 4096):
            raise ValueError()
    except Exception:
        raise ValueError(f"RERANKER_MAX_LENGTH phải là số nguyên từ 64 đến 4096, nhận được '{max_len_str}'")

    batch_size_str = os.getenv("RERANK_BATCH_SIZE", "4").strip()
    try:
        rerank_batch_size = int(batch_size_str)
        if not (1 <= rerank_batch_size <= 64):
            raise ValueError()
    except Exception:
        raise ValueError(f"RERANK_BATCH_SIZE phải là số nguyên từ 1 đến 64, nhận được '{batch_size_str}'")

    min_score_str = os.getenv("RERANK_MIN_SCORE", "0.50").strip()
    try:
        rerank_min_score = float(min_score_str)
        if not (0.0 <= rerank_min_score <= 1.0):
            raise ValueError()
    except Exception:
        raise ValueError(f"RERANK_MIN_SCORE phải là số thực trong khoảng từ 0.0 đến 1.0, nhận được '{min_score_str}'")

    device = os.getenv("RERANK_DEVICE", "auto").strip().lower()
    if device not in {"auto", "cpu", "cuda"}:
        raise ValueError(f"RERANK_DEVICE phải là một trong ['auto', 'cpu', 'cuda'], nhận được '{device}'")

    # 5. Multi-Query Expansion Configuration
    mq_count_str = os.getenv("MULTI_QUERY_COUNT", "3").strip()
    try:
        multi_query_count = int(mq_count_str)
        if not (1 <= multi_query_count <= 5):
            raise ValueError()
    except Exception:
        raise ValueError(f"MULTI_QUERY_COUNT phải là số nguyên từ 1 đến 5, nhận được '{mq_count_str}'")

    mq_max_chars_str = os.getenv("MULTI_QUERY_MAX_CHARS", "300").strip()
    try:
        multi_query_max_chars = int(mq_max_chars_str)
        if not (50 <= multi_query_max_chars <= 1000):
            raise ValueError()
    except Exception:
        raise ValueError(f"MULTI_QUERY_MAX_CHARS phải là số nguyên từ 50 đến 1000, nhận được '{mq_max_chars_str}'")

    mq_temp_str = os.getenv("MULTI_QUERY_TEMPERATURE", "0.2").strip()
    try:
        multi_query_temp = float(mq_temp_str)
        if not (0.0 <= multi_query_temp <= 1.0):
            raise ValueError()
    except Exception:
        raise ValueError(f"MULTI_QUERY_TEMPERATURE phải là số thực từ 0.0 đến 1.0, nhận được '{mq_temp_str}'")

    mq_orig_w_str = os.getenv("MULTI_QUERY_ORIGINAL_WEIGHT", "1.5").strip()
    mq_var_w_str = os.getenv("MULTI_QUERY_VARIANT_WEIGHT", "1.0").strip()
    try:
        mq_orig_weight = float(mq_orig_w_str)
        mq_var_weight = float(mq_var_w_str)
        if mq_orig_weight < 0.0 or mq_var_weight < 0.0:
            raise ValueError()
        if mq_orig_weight == 0.0 and mq_var_weight == 0.0:
            raise ValueError()
    except Exception:
        raise ValueError(
            f"Trọng số Multi-Query (ORIGINAL={mq_orig_w_str}, VARIANT={mq_var_w_str}) "
            f"phải là các số thực không âm và không đồng thời bằng 0."
        )

    mq_rrf_k_str = os.getenv("MULTI_QUERY_RRF_K", "60").strip()
    try:
        multi_query_rrf_k = int(mq_rrf_k_str)
        if multi_query_rrf_k <= 0:
            raise ValueError()
    except Exception:
        raise ValueError(f"MULTI_QUERY_RRF_K phải là số nguyên dương > 0, nhận được '{mq_rrf_k_str}'")

    per_query_cand_str = os.getenv("PER_QUERY_CANDIDATES", "12").strip()
    try:
        per_query_candidates = int(per_query_cand_str)
        if not (1 <= per_query_candidates <= 100):
            raise ValueError()
    except Exception:
        raise ValueError(f"PER_QUERY_CANDIDATES phải là số nguyên từ 1 đến 100, nhận được '{per_query_cand_str}'")

    # 6. Parent-Child & Hierarchy Configuration
    parent_max_chars_str = os.getenv("PARENT_MAX_CHARS", "6000").strip()
    try:
        parent_max_chars = int(parent_max_chars_str)
        if not (1000 <= parent_max_chars <= 20000):
            raise ValueError()
    except Exception:
        raise ValueError(f"PARENT_MAX_CHARS phải là số nguyên từ 1000 đến 20000, nhận được '{parent_max_chars_str}'")

    parent_child_lim_str = os.getenv("PARENT_SCORE_CHILD_LIMIT", "3").strip()
    try:
        parent_score_child_limit = int(parent_child_lim_str)
        if not (1 <= parent_score_child_limit <= 20):
            raise ValueError()
    except Exception:
        raise ValueError(f"PARENT_SCORE_CHILD_LIMIT phải là số nguyên từ 1 đến 20, nhận được '{parent_child_lim_str}'")

    parent_rrf_k_str = os.getenv("PARENT_RRF_K", "60").strip()
    try:
        parent_rrf_k = int(parent_rrf_k_str)
        if parent_rrf_k <= 0:
            raise ValueError()
    except Exception:
        raise ValueError(f"PARENT_RRF_K phải là số nguyên dương > 0, nhận được '{parent_rrf_k_str}'")

    parent_cand_str = os.getenv("PARENT_CANDIDATES", "10").strip()
    try:
        parent_candidates = int(parent_cand_str)
        if not (1 <= parent_candidates <= 100):
            raise ValueError()
    except Exception:
        raise ValueError(f"PARENT_CANDIDATES phải là số nguyên từ 1 đến 100, nhận được '{parent_cand_str}'")

    final_parent_top_k_str = os.getenv("FINAL_PARENT_TOP_K", "3").strip()
    try:
        final_parent_top_k = int(final_parent_top_k_str)
        if not (1 <= final_parent_top_k <= 100):
            raise ValueError()
    except Exception:
        raise ValueError(f"FINAL_PARENT_TOP_K phải là số nguyên từ 1 đến 100, nhận được '{final_parent_top_k_str}'")

    if final_parent_top_k > parent_candidates:
        raise ValueError(f"FINAL_PARENT_TOP_K ({final_parent_top_k}) phải <= PARENT_CANDIDATES ({parent_candidates})")

    total_ctx_str = os.getenv("TOTAL_CONTEXT_MAX_CHARS", "16000").strip()
    try:
        total_context_max_chars = int(total_ctx_str)
        if total_context_max_chars < parent_max_chars:
            raise ValueError(f"TOTAL_CONTEXT_MAX_CHARS ({total_context_max_chars}) phải >= PARENT_MAX_CHARS ({parent_max_chars})")
    except Exception as e:
        if "phải >=" in str(e):
            raise e
        raise ValueError(f"TOTAL_CONTEXT_MAX_CHARS phải là số nguyên dương, nhận được '{total_ctx_str}'")

    return {
        "api_key": api_key,
        "has_api_key": bool(api_key),
        "embedding_model": embedding_model,
        "embedding_dim": embedding_dim,
        "generation_model": generation_model,
        "max_distance": max_distance,
        "bm25_candidates": bm25_candidates,
        "semantic_candidates": semantic_candidates,
        "rerank_candidates": rerank_candidates,
        "final_top_k": final_top_k,
        "rrf_k": rrf_k,
        "rrf_bm25_weight": w_bm25,
        "rrf_semantic_weight": w_semantic,
        "reranker_model": reranker_model,
        "reranker_max_length": reranker_max_length,
        "rerank_batch_size": rerank_batch_size,
        "rerank_min_score": rerank_min_score,
        "rerank_device": device,
        "multi_query_count": multi_query_count,
        "multi_query_max_chars": multi_query_max_chars,
        "multi_query_temperature": multi_query_temp,
        "multi_query_original_weight": mq_orig_weight,
        "multi_query_variant_weight": mq_var_weight,
        "multi_query_rrf_k": multi_query_rrf_k,
        "per_query_candidates": per_query_candidates,
        "parent_max_chars": parent_max_chars,
        "parent_score_child_limit": parent_score_child_limit,
        "parent_rrf_k": parent_rrf_k,
        "parent_candidates": parent_candidates,
        "final_parent_top_k": final_parent_top_k,
        "total_context_max_chars": total_context_max_chars,
    }


# ==============================================================================
# 2. NUMERIC CHUNK ORDERING & FILE HASHING
# ==============================================================================

def extract_sequence_number(chunk_id: str) -> int:
    """
    Trích xuất số thứ tự nguyên từ phần đuôi của chunk_id.
    Ví dụ: 'TT_02_2023_NHNN:hierarchical:0042' -> 42
    Đảm bảo sắp xếp số học chuẩn xác (0002 đứng trước 0010).
    """
    if not isinstance(chunk_id, str):
        raise ValueError(f"chunk_id phải là string, nhận được {type(chunk_id).__name__}")

    # Tìm các chữ số ở phần cuối cùng sau dấu hai chấm
    parts = chunk_id.rsplit(":", 1)
    target_str = parts[-1] if len(parts) > 1 else chunk_id

    match = re.search(r"(\d+)$", target_str)
    if match:
        return int(match.group(1))

    # Fallback: tìm cụm số đầu tiên
    match_any = re.search(r"(\d+)", chunk_id)
    if match_any:
        return int(match_any.group(1))

    return 0


def compute_file_sha256(file_path: Path) -> str:
    """
    Tính mã băm SHA-256 của một file dữ liệu.
    """
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


# ==============================================================================
# 3. HEADING REGEX & HIERARCHY RESOLUTION ENGINE
# ==============================================================================

# Regex nhận diện Heading ở đầu dòng bất kỳ trong văn bản chunk (kể cả có markdown prefix ##, **, v.v.)
RE_CHAPTER_HEADING = re.compile(
    r"^\s*(?:[#*`\"„“”—–-]*)(?:CHƯƠNG|Chương)\s+([IVXLCDM\d]+)[.:\s\-–—]*(.*)",
    re.IGNORECASE | re.UNICODE
)

RE_ARTICLE_HEADING = re.compile(
    r"^\s*(?:[#*`\"„“”—–-]*)(?:ĐIỀU|Điều)\s+(\d+[a-z]?)[.:\s\-–—]*(.*)",
    re.IGNORECASE | re.UNICODE
)

# Regex phát hiện viện dẫn chéo trong câu (cross-reference, không phải heading cấp cao)
RE_INLINE_REFERENCE = re.compile(
    r"(?:quy định tại|căn cứ tại|theo|khoản\s+\d+\s+của|điểm\s+[a-z]\s+khoản\s+\d+\s+)\s+(?:Điều|ĐIỀU)\s+\d+",
    re.IGNORECASE | re.UNICODE
)


def normalize_article_name(raw_art: str) -> str:
    """
    Chuẩn hóa tên Điều: 'Điều 4', 'điều 4', '4', 'Điều 4. Phạm vi' -> 'Điều 4'
    """
    raw_clean = unicodedata.normalize("NFC", str(raw_art)).strip()
    match = re.search(r"(?:ĐIỀU|Điều)?\s*(\d+[a-z]?)", raw_clean, re.IGNORECASE)
    if match:
        return f"Điều {match.group(1)}"
    return raw_clean


def normalize_chapter_name(raw_chap: str) -> str:
    """
    Chuẩn hóa tên Chương: 'Chương I', 'chương 1' -> 'Chương I'
    """
    raw_clean = unicodedata.normalize("NFC", str(raw_chap)).strip()
    match = re.search(r"(?:CHƯƠNG|Chương)\s+([IVXLCDM\d]+)", raw_clean, re.IGNORECASE)
    if match:
        return f"Chương {match.group(1).upper()}"
    return raw_clean


def parse_heading_candidates(text: str) -> tuple[str | None, str | None]:
    """
    Phân tích và trích xuất Chapter và Article heading nếu xuất hiện trong văn bản chunk.
    Hỗ trợ cả markdown prefix (##, **, etc.) và quét các dòng của chunk.
    """
    if not isinstance(text, str) or not text.strip():
        return None, None

    normalized_text = unicodedata.normalize("NFC", text).strip()
    lines = [line.strip() for line in normalized_text.splitlines() if line.strip()]
    if not lines:
        return None, None

    found_chapter = None
    found_article = None

    for line in lines:
        if not found_chapter:
            chap_match = RE_CHAPTER_HEADING.match(line)
            if chap_match and not RE_INLINE_REFERENCE.search(line):
                found_chapter = f"Chương {chap_match.group(1).upper()}"

        if not found_article:
            art_match = RE_ARTICLE_HEADING.match(line)
            if art_match and not RE_INLINE_REFERENCE.search(line):
                found_article = f"Điều {art_match.group(1)}"

    return found_chapter, found_article


def resolve_chunk_hierarchy(
    raw_chunks: list[dict],
    source_name: str
) -> tuple[list[dict], dict[str, int]]:
    """
    Duyệt tuần tự (Sequential State Machine) các chunk trong cùng một source
    để xác định cấu trúc phân cấp (Chapter, Article, Clause, Point).

    Quy tắc phân giải theo độ ưu tiên:
    1. Metadata structure của chính chunk.
    2. Heading cấp cao ở đầu văn bản chunk.
    3. Carry forward từ chapter/article gần nhất trước đó trong cùng source.
    4. Document fallback khi không thể xác định được Article.
    """
    resolved_children = []
    current_chapter: str | None = None
    current_article: str | None = None

    method_counts = {
        "metadata": 0,
        "heading_inferred": 0,
        "carried_forward": 0,
        "document_fallback": 0,
        "ambiguous_count": 0,
    }

    seen_chunk_ids = set()

    for idx, chunk in enumerate(raw_chunks, start=1):
        cid = chunk["chunk_id"]
        if cid in seen_chunk_ids:
            raise ValueError(f"Phát hiện trùng lặp chunk_id '{cid}' trong nguồn '{source_name}'")
        seen_chunk_ids.add(cid)

        # Kiểm tra tính hợp lệ của trường
        p_start = chunk.get("page_start")
        p_end = chunk.get("page_end")
        if not isinstance(p_start, int) or not isinstance(p_end, int) or p_start <= 0 or p_start > p_end:
            raise ValueError(f"Dải trang không hợp lệ ở chunk '{cid}': page_start={p_start}, page_end={p_end}")

        text = chunk.get("text", "")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"Nội dung văn bản (text) rỗng ở chunk '{cid}'")

        struct = chunk.get("structure")
        if struct is not None and not isinstance(struct, dict):
            raise ValueError(f"Trường 'structure' phải là dict hoặc None ở chunk '{cid}', nhận được {type(struct).__name__}")

        struct_dict = struct if isinstance(struct, dict) else {}

        meta_chapter = struct_dict.get("chapter")
        meta_article = struct_dict.get("article")
        meta_clause = struct_dict.get("clause")
        meta_point = struct_dict.get("point")

        heading_chapter, heading_article = parse_heading_candidates(text)

        warnings = []
        ambiguous = False

        resolved_chapter = None
        resolved_article = None
        resolution_method = "document_fallback"

        # 1. Xác định Chapter
        if meta_chapter:
            resolved_chapter = normalize_chapter_name(meta_chapter)
            current_chapter = resolved_chapter
        elif heading_chapter:
            resolved_chapter = heading_chapter
            current_chapter = resolved_chapter
        elif current_chapter:
            resolved_chapter = current_chapter

        # 2. Xác định Article
        if meta_article:
            norm_meta_art = normalize_article_name(meta_article)
            resolved_article = norm_meta_art
            resolution_method = "metadata"
            current_article = resolved_article

            # Kiểm tra xung đột với heading nếu có
            if heading_article and heading_article != norm_meta_art:
                ambiguous = True
                warnings.append(
                    f"conflict_metadata_and_heading: metadata '{norm_meta_art}' vs heading '{heading_article}'"
                )

        elif heading_article:
            resolved_article = heading_article
            resolution_method = "heading_inferred"
            current_article = resolved_article

        elif current_article:
            resolved_article = current_article
            resolution_method = "carried_forward"

        else:
            resolved_article = None
            resolution_method = "document_fallback"
            ambiguous = True
            warnings.append(f"ambiguous_hierarchy_fallback: Không xác định được Article cho chunk '{cid}'")

        if ambiguous:
            method_counts["ambiguous_count"] += 1

        method_counts[resolution_method] += 1

        resolved_record = {
            "child_id": cid,
            "parent_id": None,  # Sẽ được gán sau khi build parent
            "source": chunk["source"],
            "page_start": p_start,
            "page_end": p_end,
            "text": text,
            "structural_path": {
                "chapter": resolved_chapter,
                "article": resolved_article,
                "clause": meta_clause,
                "point": meta_point,
            },
            "resolution_method": resolution_method,
            "ambiguous": ambiguous,
            "warnings": warnings,
            "_sort_order": extract_sequence_number(cid),
        }
        resolved_children.append(resolved_record)

    return resolved_children, method_counts


# ==============================================================================
# 4. PARENT BUILDING & WINDOWING ENGINE
# ==============================================================================

def slugify_label(label: str) -> str:
    """
    Tạo slug an toàn từ nhãn: 'Điều 4' -> 'd04', 'document_fallback' -> 'fallback'
    """
    normalized = unicodedata.normalize("NFD", label).encode("ascii", "ignore").decode("utf-8").lower()
    match = re.search(r"(\d+[a-z]?)", normalized)
    if match:
        num_part = match.group(1)
        if num_part.isdigit():
            return f"d{int(num_part):02d}"
        return f"d{num_part}"
    return "doc_fallback"


def build_parent_documents(
    resolved_children: list[dict],
    source_name: str,
    parent_max_chars: int = 6000
) -> tuple[list[dict], list[dict]]:
    """
    Gom nhóm các child chunk thành các Parent Document (Article Block).
    Nếu một Article quá dài (> parent_max_chars), chia thành các window liên tiếp
    theo ranh giới của child chunk (không cắt giữa chừng).

    Trả về: (parents_list, updated_children_list)
    """
    if not resolved_children:
        return [], []

    # Gom nhóm theo resolved article key
    groups: dict[str, list[dict]] = {}
    group_order: list[str] = []

    for child in resolved_children:
        art_key = child["structural_path"]["article"] or "document_fallback"
        if art_key not in groups:
            groups[art_key] = []
            group_order.append(art_key)
        groups[art_key].append(child)

    stem = Path(source_name).stem
    parents = []
    child_id_to_parent_id = {}

    for art_key in group_order:
        child_list = groups[art_key]
        slug = slugify_label(art_key)

        # Tạo các window
        windows: list[list[dict]] = []
        curr_window: list[dict] = []
        curr_chars = 0

        for ch in child_list:
            ch_len = len(ch["text"])

            if not curr_window:
                curr_window.append(ch)
                curr_chars += ch_len
            elif (curr_chars + ch_len + 2) <= parent_max_chars:
                curr_window.append(ch)
                curr_chars += ch_len + 2
            else:
                # Đóng window hiện tại và mở window mới
                windows.append(curr_window)
                curr_window = [ch]
                curr_chars = ch_len

        if curr_window:
            windows.append(curr_window)

        # Tạo Parent Document cho từng window
        for w_idx, win_children in enumerate(windows, start=1):
            parent_id = f"{stem}:{slug}:w{w_idx:02d}"
            p_start = min(c["page_start"] for c in win_children)
            p_end = max(c["page_end"] for c in win_children)
            c_ids = [c["child_id"] for c in win_children]

            # Nối text nguyên bản, không dùng LLM
            parent_text = "\n\n".join(c["text"] for c in win_children)
            p_chars = len(parent_text)
            ambiguous_count = sum(1 for c in win_children if c["ambiguous"])

            parent_warnings = []
            if len(win_children) == 1 and p_chars > parent_max_chars:
                parent_warnings.append(
                    f"oversized_single_child: child '{win_children[0]['child_id']}' ({p_chars} ký tự) "
                    f"vượt quá PARENT_MAX_CHARS ({parent_max_chars})"
                )

            parent_doc = {
                "parent_id": parent_id,
                "source": source_name,
                "page_start": p_start,
                "page_end": p_end,
                "article_key": art_key,
                "window_index": w_idx,
                "child_ids": c_ids,
                "text": parent_text,
                "char_count": p_chars,
                "ambiguous_child_count": ambiguous_count,
                "warnings": parent_warnings,
            }
            parents.append(parent_doc)

            for c_id in c_ids:
                child_id_to_parent_id[c_id] = parent_id

    # Gán parent_id cho từng child
    final_children = []
    for ch in resolved_children:
        ch_copy = dict(ch)
        ch_copy["parent_id"] = child_id_to_parent_id[ch["child_id"]]
        if "_sort_order" in ch_copy:
            del ch_copy["_sort_order"]
        final_children.append(ch_copy)

    return parents, final_children


# ==============================================================================
# 5. REGISTRY BUILDER & ATOMIC STORAGE
# ==============================================================================

def build_hierarchy_registry(
    input_dir: Path | str = DEFAULT_INPUT_DIR,
    storage_dir: Path = HIERARCHY_STORAGE_DIR,
    config: dict = None
) -> dict[str, Any]:
    """
    Xây dựng toàn diện Hierarchy Registry từ các file hierarchical chunk:
    1. Đọc và kiểm tra tính hợp lệ của tất cả các file *__hierarchical.json.
    2. Sắp xếp số học theo sequence number.
    3. Phân giải cấu trúc và gán Parent Document.
    4. Ghi atomically vào storage/hierarchy/ (manifest, parents, children).
    """
    if config is None:
        config = load_buoi_09_config()

    input_path = Path(input_dir)
    if not input_path.exists():
        raise FileNotFoundError(f"Thư mục chứa chunks không tồn tại: '{input_path}'")

    chunk_files = sorted(list(input_path.glob("*__hierarchical.json")))
    if not chunk_files:
        raise ValueError(f"Không tìm thấy file *__hierarchical.json nào trong '{input_path}'")

    file_fingerprints = {}
    all_raw_chunks = []

    for fpath in chunk_files:
        f_hash = compute_file_sha256(fpath)
        file_fingerprints[fpath.name] = f_hash

        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                raise ValueError(f"Nội dung file '{fpath.name}' phải là JSON array, nhận được {type(data).__name__}")
            for rec_idx, item in enumerate(data, start=1):
                clean_item = validate_chunk(item, fpath.name, rec_idx)
                all_raw_chunks.append(clean_item)

    # Gom nhóm theo source
    sources_map: dict[str, list[dict]] = {}
    for ch in all_raw_chunks:
        src = ch["source"]
        if src not in sources_map:
            sources_map[src] = []
        sources_map[src].append(ch)

    all_resolved_children = []
    all_parents = []
    total_method_stats = {
        "metadata": 0,
        "heading_inferred": 0,
        "carried_forward": 0,
        "document_fallback": 0,
        "ambiguous_count": 0,
    }
    total_oversized_count = 0

    for src_name in sorted(sources_map.keys()):
        raw_list = sources_map[src_name]
        # Sắp xếp số học theo phần sequence cuối của chunk_id
        raw_list.sort(key=lambda c: extract_sequence_number(c["chunk_id"]))

        res_children, method_stats = resolve_chunk_hierarchy(raw_list, src_name)
        for k, v in method_stats.items():
            total_method_stats[k] += v

        parents, updated_children = build_parent_documents(
            resolved_children=res_children,
            source_name=src_name,
            parent_max_chars=config["parent_max_chars"]
        )

        for p in parents:
            if any("oversized_single_child" in w for w in p["warnings"]):
                total_oversized_count += 1

        all_resolved_children.extend(updated_children)
        all_parents.extend(parents)

    # Chuẩn bị Manifest
    manifest = {
        "schema_version": "1.0.0",
        "strategy": "hierarchical",
        "input_file_fingerprints": file_fingerprints,
        "config_identity": {
            "parent_max_chars": config["parent_max_chars"],
            "parent_score_child_limit": config["parent_score_child_limit"],
            "parent_rrf_k": config["parent_rrf_k"],
            "parent_candidates": config["parent_candidates"],
            "final_parent_top_k": config["final_parent_top_k"],
        },
        "counts": {
            "total_sources": len(sources_map),
            "total_children": len(all_resolved_children),
            "total_parents": len(all_parents),
        },
        "resolution_method_counts": total_method_stats,
        "warning_counts": {
            "total_warnings": total_method_stats["ambiguous_count"] + total_oversized_count,
            "ambiguous_children": total_method_stats["ambiguous_count"],
            "oversized_single_children": total_oversized_count,
        },
        "built_at": datetime.now(timezone.utc).isoformat(),
    }

    # Ghi Atomic vào thư mục hierarchy storage
    storage_dir = Path(storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)

    children_path = storage_dir / "children.json"
    parents_path = storage_dir / "parents.json"
    manifest_path = storage_dir / "manifest.json"

    # Atomic write qua .tmp
    def _atomic_write_json(target_p: Path, obj_data: Any):
        tmp_p = target_p.with_suffix(target_p.suffix + ".tmp")
        with open(tmp_p, "w", encoding="utf-8") as f:
            json.dump(obj_data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_p, target_p)

    _atomic_write_json(children_path, all_resolved_children)
    _atomic_write_json(parents_path, all_parents)
    _atomic_write_json(manifest_path, manifest)

    return {
        "manifest": manifest,
        "children_count": len(all_resolved_children),
        "parents_count": len(all_parents),
        "sources_count": len(sources_map),
        "storage_dir": str(storage_dir),
    }


def get_hierarchical_status(
    strategy: str = "hierarchical",
    storage_dir: Path = HIERARCHY_STORAGE_DIR
) -> dict[str, Any]:
    """
    Kiểm tra trạng thái Hierarchy Store ở chế độ Read-Only tuyệt đối:
    Không mkdir, không build, không ghi và không sửa đổi timestamp của bất kỳ file nào.
    """
    storage_path = Path(storage_dir)
    manifest_file = storage_path / "manifest.json"
    parents_file = storage_path / "parents.json"
    children_file = storage_path / "children.json"

    is_ready = manifest_file.exists() and parents_file.exists() and children_file.exists()

    if not is_ready:
        return {
            "strategy": strategy,
            "hierarchy_ready": False,
            "total_sources": 0,
            "total_children": 0,
            "total_parents": 0,
            "built_at": None,
            "manifest": None,
        }

    try:
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        counts = manifest_data.get("counts", {})
        return {
            "strategy": strategy,
            "hierarchy_ready": True,
            "total_sources": counts.get("total_sources", 0),
            "total_children": counts.get("total_children", 0),
            "total_parents": counts.get("total_parents", 0),
            "resolution_methods": manifest_data.get("resolution_method_counts", {}),
            "warning_counts": manifest_data.get("warning_counts", {}),
            "built_at": manifest_data.get("built_at"),
            "manifest": manifest_data,
        }
    except Exception as e:
        return {
            "strategy": strategy,
            "hierarchy_ready": False,
            "error": str(e),
            "total_sources": 0,
            "total_children": 0,
            "total_parents": 0,
            "built_at": None,
            "manifest": None,
        }


# ==============================================================================
# 6. MULTI-QUERY EXPANSION ENGINE & IN-PROCESS CACHE
# ==============================================================================

# Global in-process cache cho kết quả Multi-Query Expansion
_MULTI_QUERY_CACHE: dict[str, dict[str, Any]] = {}

RE_LEGAL_REF_PATTERNS = [
    re.compile(r"(?:Điều|ĐIỀU)\s*(\d+[a-z]?)", re.UNICODE),
    re.compile(r"(?:Khoản|khoản)\s*(\d+)", re.UNICODE),
    re.compile(r"(?:Điểm|điểm)\s*([a-z])", re.UNICODE),
    re.compile(r"(?:Thông tư|Nghị định|Luật)\s*(?:số)?\s*(\d+[\d/]*[a-zA-Z\-]*)", re.UNICODE),
]


def extract_legal_references(text: str) -> list[str]:
    """
    Trích xuất các số hiệu văn bản, Điều, Khoản, Điểm xuất hiện trong câu hỏi.
    """
    found = []
    for pat in RE_LEGAL_REF_PATTERNS:
        for m in pat.finditer(text):
            found.append(m.group(0).strip())
    return sorted(list(set(found)))


def clean_and_deduplicate_queries(
    original_question: str,
    raw_queries: list[dict],
    max_count: int = 3,
    max_chars: int = 300
) -> tuple[list[dict], int, list[str]]:
    """
    Chuẩn hóa, lọc độ dài và loại bỏ trùng lặp giữa các query variants sinh ra và câu hỏi gốc Q0.
    """
    warnings = []
    orig_clean = unicodedata.normalize("NFC", original_question).strip()
    orig_norm_key = re.sub(r"[\s\W_]+", " ", orig_clean.casefold()).strip()

    seen_normalized = {orig_norm_key}
    valid_queries = []
    dropped_count = 0

    orig_legal_refs = extract_legal_references(orig_clean)

    for item in raw_queries:
        if not isinstance(item, dict):
            dropped_count += 1
            continue

        raw_txt = item.get("text", "")
        if not isinstance(raw_txt, str):
            dropped_count += 1
            continue

        txt = unicodedata.normalize("NFC", raw_txt).strip()
        if not txt or len(txt) > max_chars:
            dropped_count += 1
            continue

        norm_key = re.sub(r"[\s\W_]+", " ", txt.casefold()).strip()
        if not norm_key or norm_key in seen_normalized:
            dropped_count += 1
            continue

        # Kiểm tra nếu câu hỏi gốc không có Điều N nhưng model tự bịa ra Điều N lạ
        var_legal_refs = extract_legal_references(txt)
        if not orig_legal_refs and var_legal_refs:
            # Phát hiện bịa số Điều/Khoản
            warnings.append(
                f"hallucinated_legal_ref: Query variant '{txt}' tự ý thêm số hiệu '{var_legal_refs}' không có trong Q0"
            )

        focus = str(item.get("focus", "generated")).strip()
        if focus not in {"exact_legal_terms", "paraphrase", "missing_aspect", "original_intent"}:
            focus = "paraphrase"

        seen_normalized.add(norm_key)
        q_id = f"Q{len(valid_queries) + 1}"
        valid_queries.append({
            "query_id": q_id,
            "text": txt,
            "origin": "generated",
            "focus": focus,
        })

        if len(valid_queries) >= max_count:
            break

    # Kiểm tra xem nếu Q0 có số hiệu pháp luật thì ít nhất 1 variant có giữ lại hay không
    if orig_legal_refs and valid_queries:
        has_preserved = any(
            any(ref.casefold() in v["text"].casefold() for ref in orig_legal_refs)
            for v in valid_queries
        )
        if not has_preserved:
            warnings.append(
                f"legal_reference_not_preserved: Các query variants không giữ lại số hiệu gốc '{orig_legal_refs}'"
            )

    return valid_queries, dropped_count, warnings


def generate_query_expansion(
    question: str,
    config: dict = None,
    query_generator_fn: Callable[[str], str] = None,
    force_refresh: bool = False
) -> dict[str, Any]:
    """
    Sinh các biến thể truy vấn có kiểm soát (Multi-Query Expansion):
    1. Q0: nguyên văn câu hỏi người dùng sau trim/NFC, origin='original'.
    2. Q1..Qn: tối đa MULTI_QUERY_COUNT query sinh thêm bằng Gemini API hoặc generator_fn.
    3. Bộ nhớ đệm in-process cache theo mã băm của câu hỏi và cấu hình.
    4. Trả về đúng Query Set Contract hoàn chỉnh.
    """
    global _MULTI_QUERY_CACHE

    if config is None:
        config = load_buoi_09_config()

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Câu hỏi gốc (question) không được để rỗng.")

    clean_question = unicodedata.normalize("NFC", question).strip()

    q0_item = {
        "query_id": "Q0",
        "text": clean_question,
        "origin": "original",
        "focus": "original_intent",
    }

    # Tạo khóa cache trong bộ nhớ
    cache_tuple = (
        clean_question,
        config["multi_query_count"],
        config["multi_query_temperature"],
        config["multi_query_max_chars"],
        config["generation_model"],
    )
    cache_key = hashlib.sha256(json.dumps(cache_tuple, ensure_ascii=False).encode("utf-8")).hexdigest()

    if not force_refresh and cache_key in _MULTI_QUERY_CACHE:
        cached = dict(_MULTI_QUERY_CACHE[cache_key])
        cached["cache_hit"] = True
        cached["generation_latency_ms"] = 0.0
        return cached

    t0 = time.perf_counter()
    raw_response_text = ""

    try:
        if query_generator_fn is not None:
            raw_response_text = query_generator_fn(clean_question)
        else:
            if not config["has_api_key"]:
                latency_ms = round((time.perf_counter() - t0) * 1000, 2)
                return {
                    "original_question": clean_question,
                    "queries": [q0_item],
                    "model": config["generation_model"],
                    "generation_latency_ms": latency_ms,
                    "status": "query_generation_unavailable",
                    "cache_hit": False,
                    "dropped_duplicate_count": 0,
                    "warnings": ["GEMINI_API_KEY chưa được cấu hình trong .env. Không thể gọi Multi-query expansion."],
                }

            client = get_gemini_client(config["api_key"])
            prompt = f"""Bạn là chuyên gia tra cứu văn bản quy phạm pháp luật ngân hàng Việt Nam.
Nhiệm vụ: Mở rộng câu hỏi của người dùng thành {config['multi_query_count']} cách tra cứu tìm kiếm đa dạng.

HƯỚNG DẪN BẮT BUỘC:
1. KHÔNG trả lời câu hỏi. CHỈ tạo các câu hỏi hoặc cụm từ tra cứu tìm kiếm.
2. Tạo đúng {config['multi_query_count']} biến thể tìm kiếm theo 3 góc nhìn:
   - exact_legal_terms: Sử dụng thuật ngữ pháp lý chính xác (ví dụ: cơ cấu lại thời hạn trả nợ, giữ nguyên nhóm nợ, nhu cầu vốn không được cho vay).
   - paraphrase: Cách diễn đạt ngữ nghĩa tương đương từ góc nhìn của khách hàng vay hoặc ngân hàng.
   - missing_aspect: Khai thác khía cạnh điều kiện, đối tượng, thời hạn hoặc thủ tục liên quan nếu câu hỏi có nhiều ý.
3. Nếu câu hỏi gốc có số Điều, Khoản, Điểm hoặc số hiệu văn bản (ví dụ: Thông tư 02, Thông tư 39), BẮT BUỘC giữ nguyên các số hiệu đó trong ít nhất 1 biến thể.
4. KHÔNG tự ý bịa thêm số Điều, số Khoản nếu câu hỏi gốc không đề cập.
5. Trả về định dạng JSON thuần túy theo cấu trúc:
{{
  "queries": [
    {{"text": "câu tra cứu 1", "focus": "exact_legal_terms"}},
    {{"text": "câu tra cứu 2", "focus": "paraphrase"}},
    {{"text": "câu tra cứu 3", "focus": "missing_aspect"}}
  ]
}}

CÂU HỎI GỐC: {clean_question}
"""
            gen_res = client.models.generate_content(
                model=config["generation_model"],
                contents=prompt
            )
            if hasattr(gen_res, "text") and gen_res.text:
                raw_response_text = gen_res.text.strip()
            else:
                raw_response_text = ""

    except Exception as e:
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        sanitized_err = str(e).replace(config.get("api_key", ""), "[REDACTED_SECRET]")
        return {
            "original_question": clean_question,
            "queries": [q0_item],
            "model": config["generation_model"],
            "generation_latency_ms": latency_ms,
            "status": "query_generation_unavailable",
            "cache_hit": False,
            "dropped_duplicate_count": 0,
            "warnings": [f"Lỗi gọi Gemini API sinh Multi-Query: {sanitized_err}"],
        }

    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    # Phân tích cú pháp JSON trả về
    parsed_json = None
    try:
        clean_text = raw_response_text.strip()
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?\n?", "", clean_text)
            clean_text = re.sub(r"\n?```$", "", clean_text).strip()
        parsed_json = json.loads(clean_text)
    except Exception as parse_err:
        return {
            "original_question": clean_question,
            "queries": [q0_item],
            "model": config["generation_model"],
            "generation_latency_ms": latency_ms,
            "status": "query_generation_unavailable",
            "cache_hit": False,
            "dropped_duplicate_count": 0,
            "warnings": [f"Không thể phân tích cú pháp JSON phản hồi từ model: {parse_err}"],
        }

    if not isinstance(parsed_json, dict) or "queries" not in parsed_json or not isinstance(parsed_json["queries"], list):
        return {
            "original_question": clean_question,
            "queries": [q0_item],
            "model": config["generation_model"],
            "generation_latency_ms": latency_ms,
            "status": "query_generation_unavailable",
            "cache_hit": False,
            "dropped_duplicate_count": 0,
            "warnings": ["JSON phản hồi không đúng schema: thiếu khóa 'queries' dạng mảng"],
        }

    valid_variants, dropped_count, cleaning_warnings = clean_and_deduplicate_queries(
        original_question=clean_question,
        raw_queries=parsed_json["queries"],
        max_count=config["multi_query_count"],
        max_chars=config["multi_query_max_chars"]
    )

    final_queries = [q0_item] + valid_variants

    result = {
        "original_question": clean_question,
        "queries": final_queries,
        "model": config["generation_model"],
        "generation_latency_ms": latency_ms,
        "status": "ready",
        "cache_hit": False,
        "dropped_duplicate_count": dropped_count,
        "warnings": cleaning_warnings,
    }

    _MULTI_QUERY_CACHE[cache_key] = result
    return result


# ==============================================================================
# 7. PER-QUERY HYBRID RETRIEVAL & CROSS-QUERY RRF FUSION
# ==============================================================================

def resolve_chroma_storage_path(storage_path: Path = None) -> Path:
    """
    Tự động phân giải đường dẫn ChromaDB storage: ưu tiên storage của Buổi 09 nếu có index,
    hoặc fallback an toàn sang storage của Buổi 08 nếu Buổi 09 chưa chạy prepare-semantic.
    """
    if storage_path is not None and storage_path.exists() and (storage_path / "chroma.sqlite3").exists():
        return storage_path
    if CHROMA_STORAGE_DIR.exists() and (CHROMA_STORAGE_DIR / "chroma.sqlite3").exists():
        return CHROMA_STORAGE_DIR
    b8_chroma = BASE_DIR.parent / "buoi_08" / "storage" / "chroma"
    if b8_chroma.exists() and (b8_chroma / "chroma.sqlite3").exists():
        return b8_chroma
    return CHROMA_STORAGE_DIR


def retrieve_single_query_hybrid(
    question: str,
    strategy: str = "hierarchical",
    top_k: int = 12,
    config: dict = None,
    chunks: list[dict] = None,
    storage_path: Path = None,
    custom_retriever: Any = None,
    custom_query_embedding: list = None,
    custom_retriever_fn: Callable[[str], list[dict]] = None
) -> tuple[list[dict], dict[str, Any]]:
    """
    Thực hiện Hybrid Retrieval (BM25 + Semantic -> Inner RRF) cho duy nhất 1 query.
    Tuyệt đối không gọi Cross-Encoder Reranker ở tầng này.
    Lấy tối đa PER_QUERY_CANDIDATES (top_k) child chunks.
    """
    from advanced_rag import (
        build_bm25_retriever,
        retrieve_semantic_candidates,
        reciprocal_rank_fusion,
    )

    if config is None:
        config = load_buoi_09_config()

    effective_storage_path = resolve_chroma_storage_path(storage_path)

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Câu hỏi (question) trong per-query retrieval không được để rỗng.")

    clean_question = unicodedata.normalize("NFC", question).strip()
    t_start = time.perf_counter()

    if custom_retriever_fn is not None:
        raw_res = custom_retriever_fn(clean_question)
        lat_ms = round((time.perf_counter() - t_start) * 1000, 2)
        return raw_res[:top_k], {
            "bm25_latency_ms": 0.0,
            "semantic_latency_ms": 0.0,
            "fusion_latency_ms": 0.0,
            "total_latency_ms": lat_ms,
            "candidate_count": len(raw_res[:top_k]),
        }

    # 1. BM25 Branch
    t0 = time.perf_counter()
    if chunks is None:
        chunks, _ = load_chunks(DEFAULT_INPUT_DIR, strategy=strategy)
    if custom_retriever is None:
        custom_retriever = build_bm25_retriever(chunks)
    bm25_results = custom_retriever.search(query=clean_question, top_k=config["bm25_candidates"])
    bm25_latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    # 2. Semantic Branch
    t1 = time.perf_counter()
    semantic_results = retrieve_semantic_candidates(
        question=clean_question,
        strategy=strategy,
        candidate_k=config["semantic_candidates"],
        config=config,
        storage_path=effective_storage_path,
        custom_query_embedding=custom_query_embedding
    )
    semantic_latency_ms = round((time.perf_counter() - t1) * 1000, 2)

    # 3. Inner RRF Fusion (Tầng 1)
    t2 = time.perf_counter()
    fused_candidates, fusion_stats = reciprocal_rank_fusion(
        bm25_results=bm25_results,
        semantic_results=semantic_results,
        k_rrf=config["rrf_k"],
        w_bm25=config["rrf_bm25_weight"],
        w_semantic=config["rrf_semantic_weight"],
        top_n=top_k
    )
    fusion_latency_ms = round((time.perf_counter() - t2) * 1000, 2)
    total_latency_ms = round((time.perf_counter() - t_start) * 1000, 2)

    trace = {
        "bm25_candidate_count": len(bm25_results),
        "semantic_candidate_count": len(semantic_results),
        "fused_candidate_count": len(fused_candidates),
        "bm25_latency_ms": bm25_latency_ms,
        "semantic_latency_ms": semantic_latency_ms,
        "fusion_latency_ms": fusion_latency_ms,
        "total_latency_ms": total_latency_ms,
    }

    return fused_candidates, trace


def cross_query_reciprocal_rank_fusion(
    query_results_map: dict[str, list[dict]],
    query_weights_map: dict[str, float],
    k_rrf: int = 60
) -> tuple[list[dict], dict[str, Any]]:
    """
    Hợp nhất kết quả retrieval từ nhiều truy vấn (Cross-Query RRF - Tầng 2):
    multi_query_rrf_score(d) = sum_{q in Q} ( w_q / (k_rrf + rank_q(d)) )

    Quy tắc:
    - Union theo child_id/chunk_id, không nhân bản.
    - Metadata cùng child_id (source, page_start, page_end, text) phải khớp; mismatch sẽ fail.
    - Ghi nhận support_query_count, support_query_ids, per_query_ranks, best_query_rank.
    - Sắp xếp: multi_query_rrf_score (giảm), support_query_count (giảm), best_query_rank (tăng), child_id (tăng).
    - Gán multi_query_rank từ 1.
    """
    if k_rrf <= 0:
        raise ValueError(f"k_rrf phải là số nguyên dương > 0, nhận được {k_rrf}")

    t_start = time.perf_counter()
    candidates_by_id: dict[str, dict] = {}
    query_ranks_by_id: dict[str, dict[str, int]] = {}
    query_traces_by_id: dict[str, dict[str, dict]] = {}

    # Thu thập và kiểm tra metadata consistency
    for q_id, results in query_results_map.items():
        for item in results:
            cid = item.get("child_id") or item.get("chunk_id")
            if not cid:
                raise ValueError("Mỗi candidate phải có trường 'child_id' hoặc 'chunk_id'")

            # Kiểm tra metadata mismatch
            if cid in candidates_by_id:
                existing = candidates_by_id[cid]
                for field in ["source", "page_start", "page_end", "text"]:
                    if field in item and field in existing and item[field] != existing[field]:
                        raise ValueError(
                            f"Metadata mismatch for child_id '{cid}' in field '{field}': "
                            f"query '{q_id}'='{item[field]}' vs existing='{existing[field]}'"
                        )
            else:
                candidates_by_id[cid] = dict(item)
                query_ranks_by_id[cid] = {}
                query_traces_by_id[cid] = {}

            inner_rank = item.get("fused_rank") or item.get("rank") or item.get("inner_rank") or 1
            query_ranks_by_id[cid][q_id] = int(inner_rank)
            query_traces_by_id[cid][q_id] = {
                "bm25_rank": item.get("bm25_rank"),
                "semantic_rank": item.get("semantic_rank"),
                "fused_rank": int(inner_rank),
            }

    # Tính điểm Cross-Query RRF
    scored_candidates = []
    overlap_distribution: dict[int, int] = {}

    for cid, base_item in candidates_by_id.items():
        ranks_map = query_ranks_by_id[cid]
        supported_qids = sorted(list(ranks_map.keys()), key=lambda x: (x != "Q0", x))
        supp_count = len(supported_qids)

        overlap_distribution[supp_count] = overlap_distribution.get(supp_count, 0) + 1

        mq_rrf_score = 0.0
        for q_id, r in ranks_map.items():
            w_q = query_weights_map.get(q_id, 1.0)
            if w_q > 0.0 and r > 0:
                mq_rrf_score += w_q / (k_rrf + r)

        best_rank = min(ranks_map.values()) if ranks_map else 999

        cand_record = {
            "child_id": cid,
            "text": base_item.get("text", ""),
            "source": base_item.get("source", ""),
            "page_start": base_item.get("page_start", 1),
            "page_end": base_item.get("page_end", 1),
            "multi_query_rrf_score": round(mq_rrf_score, 6),
            "support_query_count": supp_count,
            "support_query_ids": supported_qids,
            "per_query_ranks": ranks_map,
            "best_query_rank": best_rank,
            "per_query_trace": query_traces_by_id[cid],
            "_sort_key": (-mq_rrf_score, -supp_count, best_rank, cid),
        }
        scored_candidates.append(cand_record)

    # Sắp xếp đơn định
    scored_candidates.sort(key=lambda x: x["_sort_key"])

    final_fused = []
    for rank, item in enumerate(scored_candidates, start=1):
        clean_item = {k: v for k, v in item.items() if k != "_sort_key"}
        clean_item["multi_query_rank"] = rank
        final_fused.append(clean_item)

    fusion_latency_ms = round((time.perf_counter() - t_start) * 1000, 2)

    trace = {
        "union_count": len(final_fused),
        "overlap_distribution": overlap_distribution,
        "k_rrf": k_rrf,
        "fusion_latency_ms": fusion_latency_ms,
    }

    return final_fused, trace


def retrieve_multi_query_children(
    question: str,
    strategy: str = "hierarchical",
    config: dict = None,
    chunks: list[dict] = None,
    storage_path: Path = None,
    custom_retriever: Any = None,
    custom_query_embeddings_map: dict[str, list] = None,
    query_generator_fn: Callable[[str], str] = None,
    custom_hybrid_fn: Callable[[str], list[dict]] = None
) -> dict[str, Any]:
    """
    Toàn bộ quy trình Fan-out Multi-Query Retrieval và Cross-Query RRF Fusion (Bước 05):
    1. Gọi generate_query_expansion để sinh Query Set (Q0, Q1, Q2, Q3).
    2. Gán trọng số: Q0 -> MULTI_QUERY_ORIGINAL_WEIGHT (1.5), Q_i -> MULTI_QUERY_VARIANT_WEIGHT (1.0).
    3. Thực thi Hybrid Retrieval độc lập cho từng query (lấy PER_QUERY_CANDIDATES).
    4. Xử lý lỗi theo Failure Contract (Q0 fail -> toàn bộ fail; variant fail -> status 'multi_query_partial').
    5. Hợp nhất Cross-Query RRF và tính trace hoàn chỉnh.
    """
    if config is None:
        config = load_buoi_09_config()

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Câu hỏi gốc (question) không được để rỗng.")

    t_start = time.perf_counter()
    warnings = []

    # 1. Sinh Query Set
    query_expansion_res = generate_query_expansion(
        question=question,
        config=config,
        query_generator_fn=query_generator_fn
    )

    queries_list = query_expansion_res.get("queries", [])
    if not queries_list:
        raise RuntimeError("Query Set không chứa bất kỳ query nào hợp lệ sau khi mở rộng.")

    if query_expansion_res.get("warnings"):
        warnings.extend(query_expansion_res["warnings"])

    # 2. Xây dựng trọng số từng query
    query_weights_map = {}
    for q in queries_list:
        qid = q["query_id"]
        if qid == "Q0":
            query_weights_map[qid] = config["multi_query_original_weight"]
        else:
            query_weights_map[qid] = config["multi_query_variant_weight"]

    # 3. Thực thi Retrieval độc lập từng Query
    per_query_results: dict[str, list[dict]] = {}
    per_query_latencies: dict[str, float] = {}
    per_query_counts: dict[str, int] = {}
    failed_queries: dict[str, str] = {}

    queries_executed = 0
    queries_failed = 0

    for q in queries_list:
        qid = q["query_id"]
        q_text = q["text"]
        t_q0 = time.perf_counter()

        custom_vec = None
        if custom_query_embeddings_map and qid in custom_query_embeddings_map:
            custom_vec = custom_query_embeddings_map[qid]

        try:
            hits, q_trace = retrieve_single_query_hybrid(
                question=q_text,
                strategy=strategy,
                top_k=config["per_query_candidates"],
                config=config,
                chunks=chunks,
                storage_path=storage_path,
                custom_retriever=custom_retriever,
                custom_query_embedding=custom_vec,
                custom_retriever_fn=custom_hybrid_fn
            )
            q_lat = round((time.perf_counter() - t_q0) * 1000, 2)
            per_query_results[qid] = hits
            per_query_latencies[qid] = q_lat
            per_query_counts[qid] = len(hits)
            queries_executed += 1

        except Exception as q_err:
            queries_failed += 1
            failed_queries[qid] = str(q_err)
            warnings.append(f"Lỗi truy xuất tại query '{qid}' ('{q_text}'): {q_err}")

            if qid == "Q0":
                # Failure Contract: Nếu Q0 lỗi -> Toàn bộ pipeline fail
                raise RuntimeError(f"Q0 retrieval failed: Truy xuất cho câu hỏi gốc Q0 thất bại: {q_err}")

    # Xác định status theo Failure Contract
    status = "ready"
    if query_expansion_res.get("status") == "query_generation_unavailable" or queries_failed > 0:
        status = "multi_query_partial"

    # 4. Cross-Query RRF Fusion
    fused_children, fusion_trace = cross_query_reciprocal_rank_fusion(
        query_results_map=per_query_results,
        query_weights_map=query_weights_map,
        k_rrf=config["multi_query_rrf_k"]
    )

    total_latency_ms = round((time.perf_counter() - t_start) * 1000, 2)

    # 5. Xây dựng Trace toàn diện
    trace = {
        "query_counts": {
            "requested": config["multi_query_count"] + 1,
            "valid": len(queries_list),
            "executed": queries_executed,
            "failed": queries_failed,
        },
        "latencies_ms": {
            "expansion": query_expansion_res.get("generation_latency_ms", 0.0),
            "per_query": per_query_latencies,
            "fusion": fusion_trace.get("fusion_latency_ms", 0.0),
            "total": total_latency_ms,
        },
        "per_query_result_counts": per_query_counts,
        "union_child_count": len(fused_children),
        "overlap_distribution": fusion_trace.get("overlap_distribution", {}),
        "failed_queries": failed_queries,
        "gemini_expansion_called": not query_expansion_res.get("cache_hit", False),
    }

    return {
        "original_question": query_expansion_res["original_question"],
        "strategy": strategy,
        "status": status,
        "query_set": query_expansion_res,
        "fused_children": fused_children,
        "per_query_results": per_query_results,
        "trace": trace,
        "warnings": warnings,
    }


# ==============================================================================
# 8. PARENT AGGREGATION & CONTEXT BUDGETING ENGINE
# ==============================================================================

def load_hierarchy_store(
    storage_dir: Path = HIERARCHY_STORAGE_DIR
) -> tuple[dict[str, dict], dict[str, dict], dict[str, Any]]:
    """
    Nạp dữ liệu Hierarchy Store đã build từ trước:
    - manifest.json: Thông tin kiểm tra fingerprint và cấu hình
    - parents.json: Danh sách 27 Parent Documents (Source of Truth)
    - children.json: Registry 318 Child Chunks với ánh xạ parent_id

    Nếu store chưa tồn tại hoặc bị thiếu file -> raise RuntimeError('hierarchy_not_ready')
    Tuyệt đối không tự ý build lại trong query execution pipeline.
    """
    storage_path = Path(storage_dir)
    manifest_file = storage_path / "manifest.json"
    parents_file = storage_path / "parents.json"
    children_file = storage_path / "children.json"

    if not (manifest_file.exists() and parents_file.exists() and children_file.exists()):
        raise RuntimeError(
            "hierarchy_not_ready: Hierarchy store chưa tồn tại hoặc bị thiếu file. "
            "Hãy chạy lệnh 'build-hierarchy' trước khi thực hiện truy xuất Parent Documents."
        )

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    with open(parents_file, "r", encoding="utf-8") as f:
        parents_list = json.load(f)

    with open(children_file, "r", encoding="utf-8") as f:
        children_list = json.load(f)

    parents_by_id = {p["parent_id"]: p for p in parents_list}
    children_by_id = {(c.get("child_id") or c.get("chunk_id")): c for c in children_list}

    return parents_by_id, children_by_id, manifest_data


def aggregate_parent_candidates(
    fused_child_hits: list[dict],
    parents_by_id: dict[str, dict],
    children_by_id: dict[str, dict],
    parent_score_child_limit: int = 3,
    parent_rrf_k: int = 60,
    parent_candidates_limit: int = 10
) -> tuple[list[dict], list[dict], dict[str, list[dict]]]:
    """
    Gom nhóm các fused child hits theo parent_id và tính điểm Parent Aggregation:
    parent_rrf_score(p) = sum_{c in scoring_children(p)} ( 1 / (PARENT_RRF_K + multi_query_rank(c)) )

    Quy tắc:
    - Mỗi parent lấy tối đa PARENT_SCORE_CHILD_LIMIT child tốt nhất theo multi_query_rank để tính điểm.
    - Không cộng raw MQ-RRF score hoặc rerank score vào công thức.
    - Tách rõ: scoring_child_ids, supporting_child_ids, anchor_child_id.
    - Sắp xếp parent: parent_rrf_score (giảm) -> số supporting queries unique (giảm) -> best_child_rank (tăng) -> parent_id.
    - Giới hạn PARENT_CANDIDATES trước tầng rerank.
    """
    if parent_rrf_k <= 0:
        raise ValueError(f"PARENT_RRF_K phải là số nguyên dương > 0, nhận được {parent_rrf_k}")

    # 1. Map Child sang Parent
    grouped_children: dict[str, list[dict]] = {}

    for c in fused_child_hits:
        cid = c.get("child_id") or c.get("chunk_id")
        if not cid:
            raise ValueError("Mỗi child hit phải có 'child_id' hoặc 'chunk_id'")

        if cid not in children_by_id:
            raise KeyError(
                f"child_not_found_in_registry: Child chunk '{cid}' không tồn tại trong children.json registry"
            )

        parent_id = children_by_id[cid].get("parent_id")
        if not parent_id or parent_id not in parents_by_id:
            raise KeyError(
                f"parent_not_found_in_store: Parent ID '{parent_id}' của child '{cid}' không tồn tại trong parents.json"
            )

        if parent_id not in grouped_children:
            grouped_children[parent_id] = []
        grouped_children[parent_id].append(c)

    # 2. Tính điểm từng Parent Document
    scored_parents = []

    for parent_id, hits in grouped_children.items():
        # Sắp xếp các child hits của parent này theo multi_query_rank tăng dần (rank 1 tốt nhất)
        hits_sorted = sorted(hits, key=lambda h: h.get("multi_query_rank", 999))

        supporting_child_ids = [h.get("child_id") or h.get("chunk_id") for h in hits_sorted]
        scoring_children = hits_sorted[:parent_score_child_limit]
        scoring_child_ids = [h.get("child_id") or h.get("chunk_id") for h in scoring_children]

        anchor_child = hits_sorted[0]
        anchor_child_id = anchor_child.get("child_id") or anchor_child.get("chunk_id")
        best_child_rank = anchor_child.get("multi_query_rank", 1)

        # Hợp nhất các query IDs đã hỗ trợ parent này
        all_qids = set()
        for h in hits_sorted:
            for qid in h.get("support_query_ids", []):
                all_qids.add(qid)
        support_query_ids = sorted(list(all_qids), key=lambda x: (x != "Q0", x))

        # Tính điểm RRF cho parent
        parent_rrf_score = 0.0
        for sc in scoring_children:
            c_rank = sc.get("multi_query_rank", 1)
            parent_rrf_score += 1.0 / (parent_rrf_k + c_rank)

        p_doc = parents_by_id[parent_id]
        p_text = p_doc.get("text", "")

        parent_record = {
            "parent_id": parent_id,
            "source": p_doc.get("source", ""),
            "page_start": p_doc.get("page_start", 1),
            "page_end": p_doc.get("page_end", 1),
            "structural_path": p_doc.get("structural_path", {}),
            "text": p_text,
            "char_count": len(p_text),
            "parent_rrf_score": round(parent_rrf_score, 6),
            "anchor_child_id": anchor_child_id,
            "scoring_child_ids": scoring_child_ids,
            "supporting_child_ids": supporting_child_ids,
            "support_query_ids": support_query_ids,
            "best_child_rank": best_child_rank,
            "ambiguous": p_doc.get("ambiguous", False),
            "warnings": list(p_doc.get("warnings", [])),
            "_sort_key": (-parent_rrf_score, -len(support_query_ids), best_child_rank, parent_id),
        }
        scored_parents.append(parent_record)

    # 3. Sắp xếp đơn định
    scored_parents.sort(key=lambda x: x["_sort_key"])

    # Gán parent_rank
    final_ranked_parents = []
    for rank, p in enumerate(scored_parents, start=1):
        clean_p = {k: v for k, v in p.items() if k != "_sort_key"}
        clean_p["parent_rank"] = rank
        final_ranked_parents.append(clean_p)

    kept_candidates = final_ranked_parents[:parent_candidates_limit]
    dropped_candidates = final_ranked_parents[parent_candidates_limit:]

    return kept_candidates, dropped_candidates, grouped_children


def apply_context_budget(
    parent_candidates: list[dict],
    total_context_max_chars: int = 8000
) -> tuple[list[dict], list[dict], int, list[str]]:
    """
    Cắt và chọn lọc danh sách Parent Documents theo ngân sách context budget:
    - Chỉ thêm NGUYÊN parent document, tuyệt đối không cắt giữa parent hoặc child.
    - Duyệt theo thứ tự parent_rank tăng dần.
    - Quy tắc Oversized First Parent: Nếu parent đầu tiên vượt budget, vẫn giữ nguyên và gắn warning rõ ràng.
    - Không duplicate parent nào.
    """
    budgeted_parents = []
    dropped_by_budget = []
    cumulative_chars = 0
    warnings = []
    seen_parents = set()

    for p in parent_candidates:
        pid = p["parent_id"]
        if pid in seen_parents:
            continue

        p_chars = p["char_count"]

        if len(budgeted_parents) == 0 and p_chars > total_context_max_chars:
            # Oversized first parent rule
            budgeted_parents.append(p)
            seen_parents.add(pid)
            cumulative_chars += p_chars
            warnings.append(
                f"oversized_first_parent_exceeds_budget: Parent đầu tiên '{pid}' ({p_chars} ký tự) "
                f"vượt quá budget {total_context_max_chars}. Hệ thống vẫn giữ nguyên để đảm bảo có ngữ cảnh."
            )
        elif cumulative_chars + p_chars <= total_context_max_chars:
            budgeted_parents.append(p)
            seen_parents.add(pid)
            cumulative_chars += p_chars
        else:
            dropped_by_budget.append(p)

    return budgeted_parents, dropped_by_budget, cumulative_chars, warnings


def retrieve_parent_documents(
    question: str,
    mode: str = "multi_parent",
    strategy: str = "hierarchical",
    config: dict = None,
    chunks: list[dict] = None,
    storage_dir: Path = HIERARCHY_STORAGE_DIR,
    custom_retriever_fn: Callable[[str], list[dict]] = None,
    query_generator_fn: Callable[[str], str] = None
) -> dict[str, Any]:
    """
    Pipeline hoàn chỉnh 'Retrieve Child, Return Parent' (Bước 06):
    - mode: 'single_parent' (chỉ dùng câu hỏi gốc Q0) hoặc 'multi_parent' (mở rộng Q0..Qn)
    - Map fused child hits -> parent documents từ parent store
    - Tính điểm Parent Aggregation
    - Áp dụng context budget (TOTAL_CONTEXT_MAX_CHARS)
    - Trả về Trace và danh sách budgeted parents
    """
    if config is None:
        config = load_buoi_09_config()

    if mode not in {"single_parent", "multi_parent"}:
        raise ValueError(f"Mode '{mode}' không hợp lệ. Phải là 'single_parent' hoặc 'multi_parent'")

    t_start = time.perf_counter()
    warnings = []

    # 1. Nạp Hierarchy Store và kiểm tra tính sẵn sàng
    parents_by_id, children_by_id, manifest_data = load_hierarchy_store(storage_dir=storage_dir)

    # 2. Thực thi Retrieval tầng Child theo Mode
    child_retrieval_res = None
    fused_child_hits = []

    if mode == "single_parent":
        # Mode single_parent: Truy xuất trực tiếp câu hỏi gốc Q0
        hits, q_trace = retrieve_single_query_hybrid(
            question=question,
            strategy=strategy,
            top_k=config["per_query_candidates"],
            config=config,
            chunks=chunks,
            custom_retriever_fn=custom_retriever_fn
        )
        for rank, h in enumerate(hits, start=1):
            item = dict(h)
            item["child_id"] = h.get("child_id") or h.get("chunk_id")
            item["multi_query_rank"] = rank
            item["support_query_ids"] = ["Q0"]
            item["support_query_count"] = 1
            item["per_query_ranks"] = {"Q0": rank}
            fused_child_hits.append(item)

        child_retrieval_res = {
            "status": "ready",
            "original_question": question,
            "fused_children": fused_child_hits,
            "query_set": {"queries": [{"query_id": "Q0", "text": question, "origin": "original", "focus": "original_intent"}]},
            "trace": {"latencies_ms": {"total": q_trace.get("total_latency_ms", 0.0)}},
        }
    else:
        # Mode multi_parent: Fan-out retrieval và Cross-Query RRF
        child_retrieval_res = retrieve_multi_query_children(
            question=question,
            strategy=strategy,
            config=config,
            chunks=chunks,
            query_generator_fn=query_generator_fn,
            custom_hybrid_fn=custom_retriever_fn
        )
        fused_child_hits = child_retrieval_res["fused_children"]
        if child_retrieval_res.get("warnings"):
            warnings.extend(child_retrieval_res["warnings"])

    # 3. Parent Aggregation
    t_agg = time.perf_counter()
    kept_parents, dropped_by_candidate_limit, grouped_children = aggregate_parent_candidates(
        fused_child_hits=fused_child_hits,
        parents_by_id=parents_by_id,
        children_by_id=children_by_id,
        parent_score_child_limit=config["parent_score_child_limit"],
        parent_rrf_k=config["parent_rrf_k"],
        parent_candidates_limit=config["parent_candidates"]
    )

    # 4. Context Budgeting
    budgeted_parents, dropped_by_budget, total_parent_chars, budget_warnings = apply_context_budget(
        parent_candidates=kept_parents,
        total_context_max_chars=config["total_context_max_chars"]
    )
    warnings.extend(budget_warnings)
    agg_latency_ms = round((time.perf_counter() - t_agg) * 1000, 2)
    total_pipeline_latency_ms = round((time.perf_counter() - t_start) * 1000, 2)

    # 5. Xây dựng Trace toàn diện
    total_child_chars = sum(len(c.get("text", "")) for c in fused_child_hits)
    expansion_factor = round(total_parent_chars / max(total_child_chars, 1), 2)

    child_to_parent_map = {
        (c.get("child_id") or c.get("chunk_id")): children_by_id[(c.get("child_id") or c.get("chunk_id"))].get("parent_id")
        for c in fused_child_hits if (c.get("child_id") or c.get("chunk_id")) in children_by_id
    }

    children_per_parent = {pid: len(hits) for pid, hits in grouped_children.items()}
    score_components = {
        p["parent_id"]: {
            "scoring_child_ids": p["scoring_child_ids"],
            "score": p["parent_rrf_score"],
            "best_child_rank": p["best_child_rank"],
        }
        for p in kept_parents
    }

    trace = {
        "mode": mode,
        "input_child_hit_count": len(fused_child_hits),
        "unique_parent_count": len(grouped_children),
        "children_per_parent": children_per_parent,
        "child_to_parent_mapping": child_to_parent_map,
        "parent_score_components": score_components,
        "dropped_by_candidate_limit_count": len(dropped_by_candidate_limit),
        "dropped_by_budget_count": len(dropped_by_budget),
        "child_chars": total_child_chars,
        "expanded_parent_chars": total_parent_chars,
        "context_expansion_factor": expansion_factor,
        "ambiguous_parent_count": sum(1 for p in budgeted_parents if p.get("ambiguous")),
        "aggregation_latency_ms": agg_latency_ms,
        "total_latency_ms": total_pipeline_latency_ms,
    }

    return {
        "original_question": child_retrieval_res["original_question"],
        "mode": mode,
        "strategy": strategy,
        "status": child_retrieval_res.get("status", "ready"),
        "budgeted_parents": budgeted_parents,
        "all_ranked_parents": kept_parents,
        "fused_child_hits": fused_child_hits,
        "grouped_children": grouped_children,
        "child_retrieval_trace": child_retrieval_res.get("trace", {}),
        "trace": trace,
        "warnings": warnings,
    }


# ==============================================================================
# 9. PARENT RERANKING, EVIDENCE GATE & CITATION PIPELINE
# ==============================================================================

def rerank_parent_candidates(
    original_question: str,
    parent_candidates: list[dict],
    reranker: Any = None,
    final_parent_top_k: int = 3,
    rerank_min_score: float = 0.5,
    score_fn: Callable[[str, list[str]], list[float]] = None
) -> tuple[list[dict], list[dict], list[dict], dict[str, Any]]:
    """
    Chấm điểm lại các Parent Documents bằng Cross-Encoder Reranker:
    - Input pair: (original_question, parent_text) -> Tuyệt đối dùng câu hỏi gốc Q0.
    - Không dùng query variants để rerank.
    - Sắp xếp: parent_rerank_score (giảm) -> parent_rank (tăng) -> parent_id (tăng).
    - Cắt tối đa final_parent_top_k.
    - Áp dụng Evidence Gate (ngưỡng >= rerank_min_score).
    """
    from advanced_rag import (
        CrossEncoderReranker,
        compute_rerank_scores,
    )

    if not isinstance(original_question, str) or not original_question.strip():
        raise ValueError("Câu hỏi gốc (original_question) không được để rỗng khi rerank parent.")

    if not parent_candidates:
        return [], [], [], {"rerank_latency_ms": 0.0, "total_reranked": 0}

    t_start = time.perf_counter()
    clean_q0 = unicodedata.normalize("NFC", original_question).strip()

    texts = [p["text"] for p in parent_candidates]

    if score_fn is not None:
        scores = compute_rerank_scores(
            query=clean_q0,
            texts=texts,
            score_fn=score_fn
        )
    else:
        if reranker is None:
            config = load_buoi_09_config()
            reranker = CrossEncoderReranker(
                model_name=config["reranker_model"],
                device=config["rerank_device"],
                max_length=config["reranker_max_length"],
                batch_size=config["rerank_batch_size"],
                cache_dir=HF_STORAGE_DIR
            )
        reranker._ensure_loaded()
        scores = compute_rerank_scores(
            query=clean_q0,
            texts=texts,
            tokenizer=reranker.tokenizer,
            model=reranker.model,
            device=reranker.resolved_device or "cpu",
            max_length=reranker.max_length,
            batch_size=reranker.batch_size
        )

    # Ghép điểm rerank vào từng parent
    scored_parents = []
    for p, (raw_logit, sigmoid_score) in zip(parent_candidates, scores):
        item = dict(p)
        p_rank = item.get("parent_rank", 999)
        pid = item.get("parent_id", "")
        item["parent_rerank_raw_score"] = raw_logit
        item["parent_rerank_score"] = sigmoid_score
        scored_parents.append((item, (-sigmoid_score, p_rank, pid)))

    # Sắp xếp đơn định
    scored_parents.sort(key=lambda x: x[1])

    reranked_all = []
    for new_rank, (item, _) in enumerate(scored_parents, start=1):
        old_rank = item.get("parent_rank", new_rank)
        item["parent_rerank_rank"] = new_rank
        item["parent_rank_change"] = old_rank - new_rank
        reranked_all.append(item)

    top_k_parents = reranked_all[:final_parent_top_k]

    # Evidence Gate
    accepted_evidence = [p for p in top_k_parents if p["parent_rerank_score"] >= rerank_min_score]
    rejected_evidence = [p for p in top_k_parents if p["parent_rerank_score"] < rerank_min_score]

    rerank_latency_ms = round((time.perf_counter() - t_start) * 1000, 2)
    trace = {
        "rerank_latency_ms": rerank_latency_ms,
        "total_reranked": len(reranked_all),
        "top_k_count": len(top_k_parents),
        "accepted_count": len(accepted_evidence),
        "rejected_count": len(rejected_evidence),
    }

    return accepted_evidence, rejected_evidence, top_k_parents, trace


def generate_parent_rag_answer(
    original_question: str,
    accepted_evidence: list[dict],
    mode: str = "multi_parent",
    config: dict = None,
    answer_generator_fn: Callable[[str, str], str] = None
) -> dict[str, Any]:
    """
    Sinh câu trả lời từ Evidence hợp lệ và kiểm tra Citation:
    - Nếu không có accepted evidence -> trả status='insufficient_evidence' và KHÔNG gọi Gemini API.
    - Evidence format: [P1], [P2] cho parent modes hoặc [C1], [C2] cho flat modes.
    - Câu trả lời chỉ được rút trích từ Evidence, không suy diễn tư vấn pháp lý.
    - Citation Object chứa đầy đủ: parent_id, anchor_child_id, source, pages, structural_path.
    """
    if config is None:
        config = load_buoi_09_config()

    clean_question = unicodedata.normalize("NFC", original_question).strip()
    t_start = time.perf_counter()
    warnings = []

    if not accepted_evidence:
        return {
            "status": "insufficient_evidence",
            "answer": "Không tìm thấy đủ bằng chứng pháp lý có độ liên quan đạt ngưỡng yêu cầu để trả lời câu hỏi.",
            "citations": [],
            "accepted_evidence": [],
            "generation_latency_ms": 0.0,
            "warnings": ["Tất cả các tài liệu bằng chứng đều bị loại bỏ bởi Evidence Gate."],
        }

    is_parent_mode = "parent" in mode
    label_prefix = "P" if is_parent_mode else "C"

    # Xây dựng khối Evidence Block
    evidence_lines = []
    evidence_map = {}

    for idx, ev in enumerate(accepted_evidence, start=1):
        ev_id = f"{label_prefix}{idx}"
        ev_copy = dict(ev)
        ev_copy["evidence_id"] = ev_id
        evidence_map[ev_id] = ev_copy

        st = ev.get("structural_path", {})
        law_str = st.get("law") or ev.get("source", "")
        art_str = f"Điều {st.get('article')}" if st.get("article") else "Văn bản mở đầu"
        pages_str = f"tr. {ev.get('page_start')}-{ev.get('page_end')}"

        header = f"[{ev_id}] (Văn bản: {law_str}, {art_str}, {pages_str})"
        evidence_lines.append(f"{header}\n{ev.get('text', '').strip()}\n")

    evidence_text_block = "\n".join(evidence_lines)

    prompt = f"""Bạn là trợ lý pháp lý chuyên sâu về quy chế và quy định tín dụng ngân hàng Việt Nam.
Nhiệm vụ: Trả lời câu hỏi của người dùng DỰA HOÀN TOÀN vào các đoạn Bằng chứng pháp lý (Evidence) được cung cấp dưới đây.

HƯỚNG DẪN BẮT BUỘC:
1. CHỈ sử dụng thông tin có trong Evidence. KHÔNG tự suy diễn, KHÔNG tư vấn pháp lý ngoài phạm vi tài liệu.
2. Mỗi khẳng định, điều kiện hoặc quy định phải được trích dẫn nguồn bằng nhãn tương ứng, ví dụ [{label_prefix}1], [{label_prefix}2].
3. KHÔNG tự ý bịa thêm số Điều, số Khoản, số hiệu văn bản nếu không xuất hiện trong Evidence.
4. Nếu Evidence có cảnh báo hoặc mâu thuẫn/ambiguous, hãy nêu rõ giới hạn áp dụng trong câu trả lời.

DANH SÁCH BẰNG CHỨNG (EVIDENCE):
{evidence_text_block}

CÂU HỎI CỦA NGƯỜI DÙNG:
{clean_question}
"""

    raw_answer = ""
    try:
        if answer_generator_fn is not None:
            raw_answer = answer_generator_fn(clean_question, evidence_text_block)
        else:
            if not config["has_api_key"]:
                return {
                    "status": "query_generation_unavailable",
                    "answer": "Đã truy xuất và xếp hạng bằng chứng thành công nhưng GEMINI_API_KEY chưa được cấu hình để sinh câu trả lời.",
                    "citations": [],
                    "accepted_evidence": list(evidence_map.values()),
                    "generation_latency_ms": 0.0,
                    "warnings": ["GEMINI_API_KEY chưa được thiết lập trong .env."],
                }

            client = get_gemini_client(config["api_key"])
            gen_res = client.models.generate_content(
                model=config["generation_model"],
                contents=prompt
            )
            if hasattr(gen_res, "text") and gen_res.text:
                raw_answer = gen_res.text.strip()
            else:
                raw_answer = ""

    except Exception as e:
        sanitized_err = str(e).replace(config.get("api_key", ""), "[REDACTED_SECRET]")
        return {
            "status": "query_generation_unavailable",
            "answer": "Đã định vị được tài liệu nguồn nhưng xảy ra sự cố khi gọi mô hình sinh câu trả lời.",
            "citations": [],
            "accepted_evidence": list(evidence_map.values()),
            "generation_latency_ms": round((time.perf_counter() - t_start) * 1000, 2),
            "warnings": [f"Lỗi gọi Gemini Generation API: {sanitized_err}"],
        }

    gen_latency_ms = round((time.perf_counter() - t_start) * 1000, 2)

    # Phân giải và chuẩn hóa Citation
    found_labels = re.findall(rf'\[({label_prefix}\d+)\]', raw_answer)
    citations = []
    seen_labels = set()
    cleaned_answer = raw_answer

    for label in found_labels:
        full_label = f"[{label}]"
        if label in evidence_map:
            ev = evidence_map[label]
            p_start = ev.get("page_start", 1)
            p_end = ev.get("page_end", 1)
            p_str = f"tr. {p_start}" if p_start == p_end else f"tr. {p_start}-{p_end}"

            st = ev.get("structural_path", {})
            law_str = st.get("law") or ev.get("source", "")
            art_str = f"Điều {st.get('article')}" if st.get("article") else "Văn bản mở đầu"

            if is_parent_mode:
                display_str = f"[Nguồn: {law_str}, {art_str}, {p_str}, parent: {ev.get('parent_id')}]"
            else:
                display_str = f"[Nguồn: {law_str}, {art_str}, {p_str}, chunk: {ev.get('chunk_id')}]"

            cleaned_answer = cleaned_answer.replace(full_label, display_str)

            if label not in seen_labels:
                seen_labels.add(label)
                citations.append({
                    "evidence_id": label,
                    "parent_id": ev.get("parent_id"),
                    "anchor_child_id": ev.get("anchor_child_id"),
                    "supporting_child_ids": ev.get("supporting_child_ids", []),
                    "source": ev.get("source"),
                    "page_start": p_start,
                    "page_end": p_end,
                    "structural_path": ev.get("structural_path", {}),
                    "parent_rerank_score": ev.get("parent_rerank_score", ev.get("rerank_score")),
                    "ambiguous": ev.get("ambiguous", False),
                    "warnings": list(ev.get("warnings", [])),
                    "display": display_str,
                })
        else:
            cleaned_answer = cleaned_answer.replace(full_label, "")
            warnings.append(f"Loại bỏ nhãn trích dẫn không có thật trong Evidence: {full_label}")

    return {
        "status": "ready",
        "answer": cleaned_answer.strip(),
        "citations": citations,
        "accepted_evidence": list(evidence_map.values()),
        "generation_latency_ms": gen_latency_ms,
        "warnings": warnings,
    }


# ==============================================================================
# 10. MASTER QUERY & COMPARISON PIPELINES
# ==============================================================================

def query_hierarchical_rag(
    question: str,
    mode: str = "multi_parent",
    strategy: str = "hierarchical",
    config: dict = None,
    chunks: list[dict] = None,
    storage_dir: Path = HIERARCHY_STORAGE_DIR,
    reranker: Any = None,
    score_fn: Callable[[str, list[str]], list[float]] = None,
    query_generator_fn: Callable[[str], str] = None,
    custom_hybrid_fn: Callable[[str], list[dict]] = None,
    answer_generator_fn: Callable[[str, str], str] = None
) -> dict[str, Any]:
    """
    Quy trình Master RAG hoàn chỉnh cho cả 4 chế độ:
    1. 'single_flat': Q0 -> hybrid child -> rerank child -> gate -> answer.
    2. 'multi_flat': Q0 + variants -> per-query hybrid -> MQ-RRF -> rerank child bằng Q0 -> gate -> answer.
    3. 'single_parent': Q0 -> hybrid child -> map parent -> aggregate & budget -> rerank parent bằng Q0 -> gate -> answer.
    4. 'multi_parent': Q0 + variants -> per-query hybrid -> MQ-RRF -> map parent -> aggregate & budget -> rerank parent bằng Q0 -> gate -> answer.
    """
    if config is None:
        config = load_buoi_09_config()

    if mode not in MODES:
        raise ValueError(f"Mode '{mode}' không hợp lệ. Phải là một trong {sorted(list(MODES))}")

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Câu hỏi (question) không được để rỗng.")

    t_start = time.perf_counter()
    warnings = []
    clean_question = unicodedata.normalize("NFC", question).strip()

    stage_latencies = {
        "expansion": 0.0,
        "retrieval": 0.0,
        "fusion": 0.0,
        "aggregation": 0.0,
        "rerank": 0.0,
        "generation": 0.0,
        "total": 0.0,
    }
    api_calls = {
        "generation_calls": 0,
        "embedding_calls": 0,
    }

    query_set_res = None
    child_hits = []
    parent_candidates = []
    accepted_evidence = []
    rejected_evidence = []

    # ==========================================
    # NHÁNH 1 & 2: PARENT MODES
    # ==========================================
    retrieval_status = "ready"
    if mode in {"single_parent", "multi_parent"}:
        retrieval_res = retrieve_parent_documents(
            question=clean_question,
            mode=mode,
            strategy=strategy,
            config=config,
            chunks=chunks,
            storage_dir=storage_dir,
            custom_retriever_fn=custom_hybrid_fn,
            query_generator_fn=query_generator_fn
        )
        retrieval_status = retrieval_res.get("status", "ready")
        if retrieval_res.get("warnings"):
            warnings.extend(retrieval_res["warnings"])

        parent_candidates = retrieval_res["budgeted_parents"]
        child_hits = retrieval_res["fused_child_hits"]
        t_ret = retrieval_res["trace"]
        stage_latencies["aggregation"] = t_ret.get("aggregation_latency_ms", 0.0)

        if mode == "multi_parent":
            query_set_res = retrieval_res.get("query_set")
            if t_ret.get("gemini_expansion_called"):
                api_calls["generation_calls"] += 1
            stage_latencies["expansion"] = t_ret.get("latencies_ms", {}).get("expansion", 0.0)
            stage_latencies["fusion"] = t_ret.get("latencies_ms", {}).get("fusion", 0.0)

        # Rerank Parent
        accepted_evidence, rejected_evidence, top_k_parents, rerank_trace = rerank_parent_candidates(
            original_question=clean_question,
            parent_candidates=parent_candidates,
            reranker=reranker,
            final_parent_top_k=config["final_parent_top_k"],
            rerank_min_score=config["rerank_min_score"],
            score_fn=score_fn
        )
        stage_latencies["rerank"] = rerank_trace["rerank_latency_ms"]

    # ==========================================
    # NHÁNH 3 & 4: FLAT MODES
    # ==========================================
    else:
        from advanced_rag import CrossEncoderReranker

        if mode == "single_flat":
            hits, q_trace = retrieve_single_query_hybrid(
                question=clean_question,
                strategy=strategy,
                top_k=config["per_query_candidates"],
                config=config,
                chunks=chunks,
                custom_retriever_fn=custom_hybrid_fn
            )
            for r, h in enumerate(hits, start=1):
                item = dict(h)
                item["multi_query_rank"] = r
                child_hits.append(item)
            stage_latencies["retrieval"] = q_trace.get("total_latency_ms", 0.0)
        else:
            # multi_flat
            mq_res = retrieve_multi_query_children(
                question=clean_question,
                strategy=strategy,
                config=config,
                chunks=chunks,
                query_generator_fn=query_generator_fn,
                custom_hybrid_fn=custom_hybrid_fn
            )
            retrieval_status = mq_res.get("status", "ready")
            child_hits = mq_res["fused_children"]
            query_set_res = mq_res.get("query_set")
            if mq_res.get("trace", {}).get("gemini_expansion_called"):
                api_calls["generation_calls"] += 1
            stage_latencies["expansion"] = mq_res.get("trace", {}).get("latencies_ms", {}).get("expansion", 0.0)
            stage_latencies["fusion"] = mq_res.get("trace", {}).get("latencies_ms", {}).get("fusion", 0.0)

        # Rerank Flat Chunks
        t_rr = time.perf_counter()
        if reranker is None:
            reranker = CrossEncoderReranker(
                model_name=config["reranker_model"],
                device=config["rerank_device"],
                max_length=config["reranker_max_length"],
                batch_size=config["rerank_batch_size"],
                cache_dir=HF_STORAGE_DIR
            )
            if score_fn is not None:
                reranker.score_fn = score_fn

        reranked_children = reranker.rerank(
            query=clean_question,
            candidates=child_hits,
            top_k=config["final_top_k"],
            rerank_candidates_limit=config["rerank_candidates"]
        )
        stage_latencies["rerank"] = round((time.perf_counter() - t_rr) * 1000, 2)

        accepted_evidence = [c for c in reranked_children if c.get("rerank_score", 0.0) >= config["rerank_min_score"]]
        rejected_evidence = [c for c in reranked_children if c.get("rerank_score", 0.0) < config["rerank_min_score"]]

    # ==========================================
    # SINH CÂU TRẢ LỜI & CITATION
    # ==========================================
    answer_res = generate_parent_rag_answer(
        original_question=clean_question,
        accepted_evidence=accepted_evidence,
        mode=mode,
        config=config,
        answer_generator_fn=answer_generator_fn
    )
    if answer_res.get("warnings"):
        warnings.extend(answer_res["warnings"])

    if answer_res["status"] == "ready":
        api_calls["generation_calls"] += 1

    stage_latencies["generation"] = answer_res.get("generation_latency_ms", 0.0)
    stage_latencies["total"] = round((time.perf_counter() - t_start) * 1000, 2)

    final_status = answer_res["status"]
    if final_status == "ready" and retrieval_status == "multi_query_partial":
        final_status = "multi_query_partial"

    return {
        "status": final_status,
        "mode": mode,
        "original_question": clean_question,
        "query_set": query_set_res,
        "child_hits": child_hits,
        "parent_candidates": parent_candidates,
        "accepted_evidence": accepted_evidence,
        "rejected_evidence": rejected_evidence,
        "answer": answer_res["answer"],
        "citations": answer_res["citations"],
        "trace": {
            "stage_latencies_ms": stage_latencies,
            "api_call_counts": api_calls,
            "identities": {
                "model_generation": config["generation_model"],
                "model_embedding": config["embedding_model"],
                "model_reranker": config["reranker_model"],
                "strategy": strategy,
            },
            "warnings": warnings,
        },
        "warnings": warnings,
    }


def compare_hierarchical_rag(
    question: str,
    strategy: str = "hierarchical",
    config: dict = None,
    chunks: list[dict] = None,
    storage_dir: Path = HIERARCHY_STORAGE_DIR,
    reranker: Any = None,
    score_fn: Callable[[str, list[str]], list[float]] = None,
    query_generator_fn: Callable[[str], str] = None,
    custom_hybrid_fn: Callable[[str], list[dict]] = None
) -> dict[str, Any]:
    """
    Thực hiện so sánh đồng thời cả 4 chế độ (single_flat, multi_flat, single_parent, multi_parent)
    ở tầng Retrieval + Reranking mà TUYỆT ĐỐI KHÔNG gọi Answer Generation.
    """
    if config is None:
        config = load_buoi_09_config()

    clean_question = unicodedata.normalize("NFC", question).strip()
    comparison_results = {}

    for m in ["single_flat", "multi_flat", "single_parent", "multi_parent"]:
        t0 = time.perf_counter()

        # Gọi query_hierarchical_rag nhưng mock answer generator để không gọi LLM
        res = query_hierarchical_rag(
            question=clean_question,
            mode=m,
            strategy=strategy,
            config=config,
            chunks=chunks,
            storage_dir=storage_dir,
            reranker=reranker,
            score_fn=score_fn,
            query_generator_fn=query_generator_fn,
            custom_hybrid_fn=custom_hybrid_fn,
            answer_generator_fn=lambda q, e: "MOCK_COMPARE_NO_GEN"
        )
        lat = round((time.perf_counter() - t0) * 1000, 2)

        top1_item = res["accepted_evidence"][0] if res["accepted_evidence"] else None
        top1_score = 0.0
        top1_id = "N/A"
        top1_source = "N/A"
        top1_law = "N/A"

        if top1_item:
            top1_score = top1_item.get("parent_rerank_score", top1_item.get("rerank_score", 0.0))
            top1_id = top1_item.get("parent_id", top1_item.get("chunk_id", "N/A"))
            top1_source = top1_item.get("source", "N/A")
            st = top1_item.get("structural_path", {})
            top1_law = f"Điều {st.get('article')}" if st.get("article") else "Văn bản mở đầu"

        comparison_results[m] = {
            "mode": m,
            "status": res["status"],
            "top1_id": top1_id,
            "top1_score": round(top1_score, 4),
            "top1_source": top1_source,
            "top1_law": top1_law,
            "accepted_evidence_count": len(res["accepted_evidence"]),
            "candidate_count": len(res["parent_candidates"]) if "parent" in m else len(res["child_hits"]),
            "latency_ms": lat,
            "stage_latencies": res["trace"]["stage_latencies_ms"],
        }

    return {
        "original_question": clean_question,
        "strategy": strategy,
        "modes": comparison_results,
    }


# ==============================================================================
# 11. CLI INTERFACE
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Buổi 09 - Hierarchy Registry Builder, Multi-Query Expansion, Fan-out Retrieval, Parent Aggregation & Answer Pipeline CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Lệnh thực thi")

    # Command hierarchy-audit
    audit_parser = subparsers.add_parser("hierarchy-audit", help="Kiểm tra và phân tích cấu trúc chunks mà không ghi file")
    audit_parser.add_argument("--input-dir", type=str, default=str(DEFAULT_INPUT_DIR), help="Thư mục chunks JSON")

    # Command build-hierarchy
    build_parser = subparsers.add_parser("build-hierarchy", help="Xây dựng Hierarchy Registry và ghi atomically vào storage")
    build_parser.add_argument("--input-dir", type=str, default=str(DEFAULT_INPUT_DIR), help="Thư mục chunks JSON")

    # Command hierarchy-status
    subparsers.add_parser("hierarchy-status", help="Kiểm tra trạng thái Hierarchy Store ở chế độ Read-Only")

    # Command expand-query (Bước 04)
    expand_parser = subparsers.add_parser("expand-query", help="Mở rộng câu hỏi gốc thành Query Set đa dạng (Multi-query expansion)")
    expand_parser.add_argument("--question", type=str, required=True, help="Câu hỏi cần mở rộng")
    expand_parser.add_argument("--multi-query-count", type=int, default=None, help="Số lượng query sinh thêm (mặc định lấy từ .env)")
    expand_parser.add_argument("--temperature", type=float, default=None, help="Độ sáng tạo temperature")
    expand_parser.add_argument("--force-refresh", action="store_true", help="Bỏ qua cache và gọi lại API")

    # Command multi-child (Bước 05)
    multi_child_parser = subparsers.add_parser("multi-child", help="Thực hiện Per-query retrieval và hợp nhất Cross-Query RRF trên Child Chunks")
    multi_child_parser.add_argument("--question", type=str, required=True, help="Câu hỏi cần truy xuất đa biến thể")
    multi_child_parser.add_argument("--strategy", type=str, default="hierarchical", choices=sorted(list(ALLOWED_STRATEGIES)), help="Strategy phân chia chunk")
    multi_child_parser.add_argument("--top-k", type=int, default=None, help="Số lượng child chunks hiển thị")

    # Command parent-retrieve (Bước 06)
    parent_ret_parser = subparsers.add_parser("parent-retrieve", help="Thực hiện Parent Aggregation và áp dụng Context Budget từ Fused Child Hits")
    parent_ret_parser.add_argument("--question", type=str, required=True, help="Câu hỏi cần truy xuất Parent Documents")
    parent_ret_parser.add_argument("--mode", type=str, default="multi_parent", choices=["single_parent", "multi_parent"], help="Chế độ truy xuất")
    parent_ret_parser.add_argument("--strategy", type=str, default="hierarchical", choices=sorted(list(ALLOWED_STRATEGIES)), help="Strategy phân chia chunk")
    parent_ret_parser.add_argument("--top-k", type=int, default=None, help="Số lượng parent documents hiển thị")

    # Command query (Bước 07)
    query_parser = subparsers.add_parser("query", help="Thực hiện toàn bộ Pipeline RAG hoàn chỉnh (Retrieval -> Rerank -> Gate -> Gemini Answer)")
    query_parser.add_argument("--question", type=str, required=True, help="Câu hỏi cần trả lời")
    query_parser.add_argument("--mode", type=str, default="multi_parent", choices=sorted(list(MODES)), help="Chế độ RAG (single_flat, multi_flat, single_parent, multi_parent)")
    query_parser.add_argument("--strategy", type=str, default="hierarchical", choices=sorted(list(ALLOWED_STRATEGIES)), help="Strategy phân chia chunk")

    # Command compare (Bước 07)
    compare_parser = subparsers.add_parser("compare", help="So sánh đối chuẩn 4 chế độ RAG (Retrieval & Reranking, không sinh câu trả lời)")
    compare_parser.add_argument("--question", type=str, required=True, help="Câu hỏi so sánh đối chuẩn")
    compare_parser.add_argument("--strategy", type=str, default="hierarchical", choices=sorted(list(ALLOWED_STRATEGIES)), help="Strategy phân chia chunk")

    # Command status (tương thích backward)
    subparsers.add_parser("status", help="Kiểm tra trạng thái tổng quan Buổi 09")

    args = parser.parse_args()

    if args.command == "hierarchy-audit":
        try:
            cfg = load_buoi_09_config()
            in_p = Path(args.input_dir)
            files = sorted(list(in_p.glob("*__hierarchical.json")))
            print(f"=== AUDIT CẤU TRÚC HIERARCHY BUỔI 09 (Input: {in_p}) ===")
            print(f"Số lượng file chunks JSON : {len(files)}")

            total_chunks = 0
            for f in files:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    total_chunks += len(data)
                    print(f"  * {f.name:<40} : {len(data):>3} chunks")

            print(f"Tổng số child chunks      : {total_chunks}")
            print(f"Giới hạn PARENT_MAX_CHARS : {cfg['parent_max_chars']} ký tự")
        except Exception as e:
            print(f"LỖI AUDIT: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "build-hierarchy":
        try:
            cfg = load_buoi_09_config()
            res = build_hierarchy_registry(input_dir=args.input_dir, config=cfg)
            m = res["manifest"]
            print("=== XÂY DỰNG HIERARCHY REGISTRY THÀNH CÔNG ===")
            print(f"Thư mục lưu trữ           : {res['storage_dir']}")
            print(f"Số lượng văn bản (Sources): {res['sources_count']}")
            print(f"Tổng số Child Chunks      : {res['children_count']}")
            print(f"Tổng số Parent Documents  : {res['parents_count']}")
            print("-" * 65)
            print("Phương thức phân giải (Resolution Methods):")
            for meth, cnt in m["resolution_method_counts"].items():
                print(f"  * {meth:<26}: {cnt:>3}")
            print("-" * 65)
            print("Thống kê cảnh báo (Warnings):")
            for w_name, w_cnt in m["warning_counts"].items():
                print(f"  * {w_name:<26}: {w_cnt:>3}")
            print(f"Thời điểm xây dựng (UTC)  : {m['built_at']}")
        except Exception as e:
            print(f"LỖI BUILD HIERARCHY: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "expand-query":
        try:
            cfg = load_buoi_09_config()
            if args.multi_query_count is not None:
                cfg["multi_query_count"] = args.multi_query_count
            if args.temperature is not None:
                cfg["multi_query_temperature"] = args.temperature

            res = generate_query_expansion(
                question=args.question,
                config=cfg,
                force_refresh=args.force_refresh
            )
            print("=== KẾT QUẢ MULTI-QUERY EXPANSION (Bước 04) ===")
            print(f"Trạng thái (Status)       : {res['status']}")
            print(f"Mô hình sử dụng (Model)   : {res['model']}")
            print(f"Thời gian sinh (Latency)  : {res['generation_latency_ms']} ms (Cache hit: {res['cache_hit']})")
            print(f"Số lượng query trùng lặp  : {res['dropped_duplicate_count']}")
            print("-" * 75)
            print("DANH SÁCH QUERY TRONG QUERY SET:")
            for q in res["queries"]:
                print(f"  * [{q['query_id']}] ({q['origin']} | focus: {q['focus']}):")
                print(f"    \"{q['text']}\"")
            print("-" * 75)

            if res["warnings"]:
                print(f"CẢNH BÁO ({len(res['warnings'])} mục):")
                for w in res["warnings"]:
                    print(f"  [!] {w}")

        except Exception as e:
            print(f"LỖI EXPAND QUERY: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "multi-child":
        try:
            cfg = load_buoi_09_config()
            res = retrieve_multi_query_children(
                question=args.question,
                strategy=args.strategy,
                config=cfg
            )
            t = res["trace"]
            print("=== KẾT QUẢ CROSS-QUERY RRF FUSION TRÊN CHILD CHUNKS (Bước 05) ===")
            print(f"Trạng thái (Status)       : {res['status']}")
            print(f"Câu hỏi gốc               : \"{res['original_question']}\"")
            print(f"Tổng số Query thực thi    : {t['query_counts']['executed']}/{t['query_counts']['valid']} queries")
            print(f"Tổng số Child Chunks hợp nhất: {t['union_child_count']} chunks")
            print(f"Thời gian mở rộng query   : {t['latencies_ms']['expansion']} ms")
            print(f"Thời gian hợp nhất (Fusion): {t['latencies_ms']['fusion']} ms (Tổng Pipeline: {t['latencies_ms']['total']} ms)")
            print(f"Phân bố trùng lặp (Overlap): {t['overlap_distribution']}")
            print("-" * 95)
            print("DANH SÁCH QUERY:")
            for q in res["query_set"]["queries"]:
                lat = t["latencies_ms"]["per_query"].get(q["query_id"], 0.0)
                cnt = t["per_query_result_counts"].get(q["query_id"], 0)
                print(f"  * [{q['query_id']}] ({q['origin']} | {q['focus']}): \"{q['text']}\" -> {cnt} hits ({lat} ms)")
            print("-" * 95)
            print(f"{'MQ-Rank':<8} | {'MQ-RRF Score':<12} | {'Supp':<5} | {'Supported By':<14} | {'Per-Query Ranks':<18} | {'Chunk ID':<30}")
            print("-" * 95)

            display_children = res["fused_children"]
            if args.top_k is not None:
                display_children = display_children[:args.top_k]

            for c in display_children:
                supp_str = ",".join(c["support_query_ids"])
                ranks_str = ",".join(f"{k}:#{v}" for k, v in c["per_query_ranks"].items())
                print(f"#{c['multi_query_rank']:<7} | {c['multi_query_rrf_score']:<12.6f} | {c['support_query_count']:<5} | {supp_str:<14} | {ranks_str:<18} | {c['child_id']:<30}")
            print("-" * 95)

            if res["warnings"]:
                print(f"CẢNH BÁO ({len(res['warnings'])} mục):")
                for w in res["warnings"]:
                    print(f"  [!] {w}")

        except Exception as e:
            print(f"LỖI MULTI-CHILD: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "parent-retrieve":
        try:
            cfg = load_buoi_09_config()
            res = retrieve_parent_documents(
                question=args.question,
                mode=args.mode,
                strategy=args.strategy,
                config=cfg
            )
            t = res["trace"]
            print("=== KẾT QUẢ RETRIEVE CHILD -> RETURN PARENT (Bước 06) ===")
            print(f"Chế độ truy xuất (Mode)   : {res['mode']}")
            print(f"Trạng thái (Status)       : {res['status']}")
            print(f"Câu hỏi gốc               : \"{res['original_question']}\"")
            print(f"Tổng số Child Hits nạp vào: {t['input_child_hit_count']} chunks ({t['child_chars']} ký tự)")
            print(f"Tổng số Parent tìm thấy   : {t['unique_parent_count']} parents")
            print(f"Số Parent qua Budget      : {len(res['budgeted_parents'])} parents ({t['expanded_parent_chars']} ký tự)")
            print(f"Hệ số mở rộng ngữ cảnh    : {t['context_expansion_factor']}x")
            print(f"Thời gian Parent Aggregation: {t['aggregation_latency_ms']} ms (Tổng Pipeline: {t['total_latency_ms']} ms)")
            print("-" * 95)
            print("CÂY ÁNH XẠ HIERARCHICAL MAPPING TREE (Parent -> Supporting Children -> Queries):")
            print("-" * 95)

            display_parents = res["budgeted_parents"]
            if args.top_k is not None:
                display_parents = display_parents[:args.top_k]

            for p_idx, p in enumerate(display_parents, start=1):
                pid = p["parent_id"]
                st = p["structural_path"]
                law_str = st.get("law") or "N/A"
                art_str = f"Điều {st.get('article')}" if st.get("article") else "Văn bản mở đầu"
                supp_q_str = ", ".join(p["support_query_ids"])

                print(f"[Parent #{p['parent_rank']}] {pid} (Score: {p['parent_rrf_score']:.6f} | Chars: {p['char_count']} | Pages: {p['page_start']}-{p['page_end']})")
                print(f"├── Pháp lý / Điều khoản: {law_str} / {art_str}")
                print(f"├── Supporting Queries  : {supp_q_str} (Số query hỗ trợ: {len(p['support_query_ids'])})")

                children_of_p = res["grouped_children"].get(pid, [])
                print(f"└── Supporting Children ({len(children_of_p)} chunks):")
                for c_idx, c in enumerate(children_of_p, start=1):
                    cid = c.get("child_id") or c.get("chunk_id")
                    is_anchor = (cid == p["anchor_child_id"])
                    is_scored = (cid in p["scoring_child_ids"])
                    anchor_tag = "[Anchor] " if is_anchor else ""
                    scored_tag = f"Scored: {'True' if is_scored else 'False'}"
                    q_ranks_str = ", ".join(f"{k} (#{v})" for k, v in c.get("per_query_ranks", {}).items())

                    prefix = "    ├── " if c_idx < len(children_of_p) else "    └── "
                    print(f"{prefix}{anchor_tag}{cid} (MQ-Rank: #{c.get('multi_query_rank', '?')} | {scored_tag})")
                    print(f"        └── Per-Query Hits: {q_ranks_str}")
                print()

            print("-" * 95)
            if res["warnings"]:
                print(f"CẢNH BÁO GHI NHẬN ({len(res['warnings'])} mục):")
                for w in res["warnings"]:
                    print(f"  [!] {w}")

        except Exception as e:
            print(f"LỖI PARENT RETRIEVE: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "query":
        try:
            cfg = load_buoi_09_config()
            res = query_hierarchical_rag(
                question=args.question,
                mode=args.mode,
                strategy=args.strategy,
                config=cfg
            )
            t = res["trace"]
            print("=========================================================================================")
            print(f"KẾT QUẢ TRẢ LỜI PIPELINE HIERARCHICAL RAG (Mode: {res['mode']})")
            print("=========================================================================================")
            print(f"Trạng thái (Status)       : {res['status']}")
            print(f"Câu hỏi gốc               : \"{res['original_question']}\"")
            print(f"Số lượng Evidence hợp lệ  : {len(res['accepted_evidence'])} (Bị loại bởi Gate: {len(res['rejected_evidence'])})")
            print(f"Cuộc gọi Generation API   : {t['api_call_counts']['generation_calls']} calls")
            print(f"Thời gian từng giai đoạn  : Expansion: {t['stage_latencies_ms']['expansion']} ms | Retrieval: {t['stage_latencies_ms']['retrieval']} ms | Rerank: {t['stage_latencies_ms']['rerank']} ms | Gen: {t['stage_latencies_ms']['generation']} ms | Tổng: {t['stage_latencies_ms']['total']} ms")
            print("-" * 89)
            print("CÂU TRẢ LỜI TỔNG HỢP (ANSWER):")
            print(res["answer"])
            print("-" * 89)
            print("DANH MỤC TRÍCH DẪN PHÁP LÝ (CITATIONS):")
            if res["citations"]:
                for cit in res["citations"]:
                    print(f"  * [{cit['evidence_id']}] Parent: {cit.get('parent_id') or 'N/A'} (Score: {cit['parent_rerank_score']:.4f})")
                    print(f"    - Nguồn & Trang: {cit['source']} (tr. {cit['page_start']}-{cit['page_end']})")
                    if cit.get("anchor_child_id"):
                        print(f"    - Anchor Child: {cit['anchor_child_id']}")
            else:
                print("  (Không có trích dẫn nào được sử dụng)")

            if res["warnings"]:
                print("-" * 89)
                print(f"CẢNH BÁO ({len(res['warnings'])} mục):")
                for w in res["warnings"]:
                    print(f"  [!] {w}")

        except Exception as e:
            print(f"LỖI QUERY RAG: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "compare":
        try:
            cfg = load_buoi_09_config()
            comp_res = compare_hierarchical_rag(
                question=args.question,
                strategy=args.strategy,
                config=cfg
            )
            print("=========================================================================================")
            print(f"BẢNG SO SÁNH ĐỐI CHUẨN 4 CHẾ ĐỘ RAG (Retrieval & Rerank Only)")
            print(f"Câu hỏi: \"{comp_res['original_question']}\"")
            print("=========================================================================================")
            print(f"{'Mode':<16} | {'Top 1 Score':<12} | {'Top 1 ID':<35} | {'Top 1 Law':<18} | {'Accepted':<8} | {'Latency':<10}")
            print("-" * 110)
            for m_key in ["single_flat", "multi_flat", "single_parent", "multi_parent"]:
                m_info = comp_res["modes"][m_key]
                print(f"{m_info['mode']:<16} | {m_info['top1_score']:<12.4f} | {m_info['top1_id']:<35} | {m_info['top1_law']:<18} | {m_info['accepted_evidence_count']:<8} | {m_info['latency_ms']:<8.1f} ms")
            print("-" * 110)
            print("Ghi chú: Lệnh compare KHÔNG gọi Gemini Generation API, chỉ đo đạc Retrieval và Reranking.")

        except Exception as e:
            print(f"LỖI COMPARE: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command in {"hierarchy-status", "status"}:
        try:
            stat = get_hierarchical_status()
            print("=== TRẠNG THÁI HIERARCHY STORE (READ-ONLY) ===")
            print(f"Hierarchy Store Sẵn sàng  : {'Có' if stat['hierarchy_ready'] else 'Chưa (Hãy chạy build-hierarchy)'}")
            if stat["hierarchy_ready"]:
                print(f"Số lượng Sources          : {stat['total_sources']}")
                print(f"Số lượng Child Chunks     : {stat['total_children']}")
                print(f"Số lượng Parent Documents : {stat['total_parents']}")
                print(f"Thời điểm xây dựng        : {stat['built_at']}")
                print("Phương thức phân giải:")
                for k, v in stat.get("resolution_methods", {}).items():
                    print(f"  * {k:<24}: {v}")
                print("Cảnh báo ghi nhận:")
                for k, v in stat.get("warning_counts", {}).items():
                    print(f"  * {k:<24}: {v}")
        except Exception as e:
            print(f"LỖI STATUS: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()



