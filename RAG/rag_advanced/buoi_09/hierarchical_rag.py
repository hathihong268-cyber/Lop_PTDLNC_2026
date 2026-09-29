"""
Module Hierarchical & Multi-Query Advanced RAG - Buổi 09:
Triển khai Document Structure Hierarchy Builder, Parent-Child Registry,
Multi-Query Expansion, Cross-Query RRF Fusion, Parent Aggregation và Parent Reranking.

Bước 03: Triển khai Config Loader, Deterministic Hierarchy Builder,
Parent Document Store (Atomic Persistence), Read-Only Status và CLI.
"""

from pathlib import Path
import os
import sys
import json
import re
import math
import time
import copy
import hashlib
import unicodedata
from datetime import datetime, timezone
import argparse
from typing import Dict, List, Any, Optional, Tuple, Union, Callable, Set

# Đảm bảo UTF-8 an toàn trên Windows console
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import dotenv

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = (BASE_DIR / "storage").resolve()
CHROMA_STORAGE_DIR = (STORAGE_DIR / "chroma").resolve()
HIERARCHY_STORAGE_DIR = (STORAGE_DIR / "hierarchy").resolve()
HF_CACHE_DIR = (STORAGE_DIR / "huggingface").resolve()

# Tìm thư mục chunks Buổi 05 linh hoạt
DEFAULT_CHUNKS_DIR = (BASE_DIR.parent.parent / "rag_foundation" / "buoi_05" / "output" / "chunks").resolve()
if not DEFAULT_CHUNKS_DIR.exists():
    DEFAULT_CHUNKS_DIR = (BASE_DIR.parent / "buoi_05" / "output" / "chunks").resolve()

# 4 chế độ truy xuất chính thức của Buổi 09
ALLOWED_MODES = {"single_flat", "multi_flat", "single_parent", "multi_parent"}

# Regex mẫu tiêu đề và cấu trúc pháp lý
RE_HEADING_DIEU = re.compile(
    r"(?:^|\n)\s*(?:#+\s*|\*\*\s*|[\"“]\s*)?Điều\s+(\d+[\w\.]*)\b(?:\.?\s*([^\n\r]*))?",
    re.IGNORECASE
)
RE_HEADING_CHUONG = re.compile(
    r"(?:^|\n)\s*(?:#+\s*|\*\*\s*|[\"“]\s*)?Chương\s+([IVXLCDM\d]+)\b(?:\.?\s*([^\n\r]*))?",
    re.IGNORECASE
)
RE_CLAUSE_PREFIX = re.compile(r"^\s*(\d+)\.\s+([^\n\r]+)")
RE_POINT_PREFIX = re.compile(r"^\s*([a-zđ])\)\s+([^\n\r]+)", re.IGNORECASE)
RE_AMENDING_KEYWORDS = re.compile(r"(sửa đổi|bổ sung)\s+(?:một số điều|khoản|điểm|Điều)", re.IGNORECASE)
RE_INLINE_DIEU_CITED = re.compile(r"(?:sửa đổi|bổ sung|khoản \d+)\s+Điều\s+(\d+)", re.IGNORECASE)


# ==============================================================================
# 1. CONFIGURATION LOADER & VALIDATOR
# ==============================================================================

def load_buoi_09_config(env_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Nạp và kiểm tra tính hợp lệ của cấu hình Buổi 09 từ tệp .env.
    Đường dẫn nạp độc lập với current working directory (cwd).
    """
    target_env = Path(env_path).resolve() if env_path else (BASE_DIR / ".env").resolve()
    if target_env.exists() and target_env.is_file():
        dotenv.load_dotenv(dotenv_path=target_env, override=True)
    else:
        # Fallback thử nạp .env.example làm giá trị mặc định nếu .env chưa tạo
        example_env = (BASE_DIR / ".env.example").resolve()
        if example_env.exists() and example_env.is_file():
            dotenv.load_dotenv(dotenv_path=example_env, override=False)

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2").strip()
    embedding_dim_str = os.getenv("GEMINI_EMBEDDING_DIM", "768").strip()
    generation_model = os.getenv("GEMINI_GENERATION_MODEL", "gemini-3.5-flash-lite").strip()
    reranker_model = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3").strip()
    rerank_device = os.getenv("RERANK_DEVICE", "auto").strip()

    # Kiểm tra model names không được rỗng
    if not embedding_model:
        raise ValueError("GEMINI_EMBEDDING_MODEL không được để rỗng.")
    if not generation_model:
        raise ValueError("GEMINI_GENERATION_MODEL không được để rỗng.")
    if not reranker_model:
        raise ValueError("RERANKER_MODEL không được để rỗng.")

    try:
        embedding_dim = int(embedding_dim_str)
        if not (128 <= embedding_dim <= 3072):
            raise ValueError()
    except Exception:
        raise ValueError(f"GEMINI_EMBEDDING_DIM phải là số nguyên trong [128, 3072], nhận được: '{embedding_dim_str}'")

    # Baseline Buổi 08 params
    try:
        top_k = int(os.getenv("DEFAULT_TOP_K", "5"))
        if not (1 <= top_k <= 50):
            raise ValueError()
    except Exception:
        raise ValueError("DEFAULT_TOP_K phải là số nguyên từ 1 đến 50.")

    try:
        max_distance = float(os.getenv("RAG_MAX_DISTANCE", "0.45"))
        if max_distance < 0:
            raise ValueError()
    except Exception:
        raise ValueError("RAG_MAX_DISTANCE phải là số thực >= 0.")

    try:
        bm25_top_k = int(os.getenv("BM25_TOP_K", "10"))
        if not (1 <= bm25_top_k <= 100):
            raise ValueError()
    except Exception:
        raise ValueError("BM25_TOP_K phải là số nguyên từ 1 đến 100.")

    try:
        semantic_top_k = int(os.getenv("SEMANTIC_TOP_K", "10"))
        if not (1 <= semantic_top_k <= 100):
            raise ValueError()
    except Exception:
        raise ValueError("SEMANTIC_TOP_K phải là số nguyên từ 1 đến 100.")

    try:
        rerank_min_score = float(os.getenv("RERANK_MIN_SCORE", "0.50"))
        if not (0.0 <= rerank_min_score <= 1.0):
            raise ValueError()
    except Exception:
        raise ValueError("RERANK_MIN_SCORE phải là số thực trong khoảng [0.0, 1.0].")

    # Buổi 09: Multi-Query parameters
    try:
        mq_count = int(os.getenv("MULTI_QUERY_COUNT", "3"))
        if not (1 <= mq_count <= 5):
            raise ValueError()
    except Exception:
        raise ValueError("MULTI_QUERY_COUNT phải là số nguyên từ 1 đến 5.")

    try:
        mq_max_chars = int(os.getenv("MULTI_QUERY_MAX_CHARS", "300"))
        if not (50 <= mq_max_chars <= 1000):
            raise ValueError()
    except Exception:
        raise ValueError("MULTI_QUERY_MAX_CHARS phải là số nguyên từ 50 đến 1000.")

    try:
        mq_temperature = float(os.getenv("MULTI_QUERY_TEMPERATURE", "0.2"))
        if not (0.0 <= mq_temperature <= 1.0):
            raise ValueError()
    except Exception:
        raise ValueError("MULTI_QUERY_TEMPERATURE phải là số thực từ 0.0 đến 1.0.")

    try:
        orig_weight = float(os.getenv("MULTI_QUERY_ORIGINAL_WEIGHT", "1.5"))
        var_weight = float(os.getenv("MULTI_QUERY_VARIANT_WEIGHT", "1.0"))
        if orig_weight < 0 or var_weight < 0:
            raise ValueError("Weights không được là số âm.")
        if orig_weight == 0.0 and var_weight == 0.0:
            raise ValueError("MULTI_QUERY_ORIGINAL_WEIGHT và MULTI_QUERY_VARIANT_WEIGHT không được đồng thời bằng 0.")
    except Exception as e:
        raise ValueError(f"Lỗi cấu hình Multi-Query weights: {e}")

    try:
        mq_rrf_k = int(os.getenv("MULTI_QUERY_RRF_K", "60"))
        if mq_rrf_k <= 0:
            raise ValueError()
    except Exception:
        raise ValueError("MULTI_QUERY_RRF_K phải là số nguyên dương (> 0).")

    try:
        per_query_cands = int(os.getenv("PER_QUERY_CANDIDATES", "12"))
        if not (1 <= per_query_cands <= 100):
            raise ValueError()
    except Exception:
        raise ValueError("PER_QUERY_CANDIDATES phải là số nguyên dương từ 1 đến 100.")

    # Buổi 09: Parent-Child parameters
    try:
        parent_max_chars = int(os.getenv("PARENT_MAX_CHARS", "6000"))
        if not (1000 <= parent_max_chars <= 20000):
            raise ValueError()
    except Exception:
        raise ValueError("PARENT_MAX_CHARS phải là số nguyên từ 1000 đến 20000.")

    try:
        parent_score_child_limit = int(os.getenv("PARENT_SCORE_CHILD_LIMIT", "3"))
        if not (1 <= parent_score_child_limit <= 20):
            raise ValueError()
    except Exception:
        raise ValueError("PARENT_SCORE_CHILD_LIMIT phải là số nguyên từ 1 đến 20.")

    try:
        parent_rrf_k = int(os.getenv("PARENT_RRF_K", "60"))
        if parent_rrf_k <= 0:
            raise ValueError()
    except Exception:
        raise ValueError("PARENT_RRF_K phải là số nguyên dương (> 0).")

    try:
        parent_cands = int(os.getenv("PARENT_CANDIDATES", "10"))
        if not (1 <= parent_cands <= 100):
            raise ValueError()
    except Exception:
        raise ValueError("PARENT_CANDIDATES phải là số nguyên dương từ 1 đến 100.")

    try:
        final_parent_top_k = int(os.getenv("FINAL_PARENT_TOP_K", "3"))
        if not (1 <= final_parent_top_k <= 100):
            raise ValueError()
    except Exception:
        raise ValueError("FINAL_PARENT_TOP_K phải là số nguyên dương từ 1 đến 100.")

    if final_parent_top_k > parent_cands:
        raise ValueError(
            f"FINAL_PARENT_TOP_K ({final_parent_top_k}) không được lớn hơn PARENT_CANDIDATES ({parent_cands})."
        )

    try:
        total_context_max_chars = int(os.getenv("TOTAL_CONTEXT_MAX_CHARS", "16000"))
        if total_context_max_chars < parent_max_chars:
            raise ValueError(
                f"TOTAL_CONTEXT_MAX_CHARS ({total_context_max_chars}) phải >= PARENT_MAX_CHARS ({parent_max_chars})."
            )
    except Exception as e:
        raise ValueError(f"Lỗi cấu hình TOTAL_CONTEXT_MAX_CHARS: {e}")

    return {
        "api_key": api_key,
        "has_api_key": bool(api_key),
        "embedding_model": embedding_model,
        "embedding_dim": embedding_dim,
        "generation_model": generation_model,
        "reranker_model": reranker_model,
        "rerank_device": rerank_device,
        "rerank_min_score": rerank_min_score,
        "top_k": top_k,
        "max_distance": max_distance,
        "bm25_top_k": bm25_top_k,
        "semantic_top_k": semantic_top_k,
        "multi_query_count": mq_count,
        "multi_query_max_chars": mq_max_chars,
        "multi_query_temperature": mq_temperature,
        "multi_query_original_weight": orig_weight,
        "multi_query_variant_weight": var_weight,
        "multi_query_rrf_k": mq_rrf_k,
        "per_query_candidates": per_query_cands,
        "parent_max_chars": parent_max_chars,
        "parent_score_child_limit": parent_score_child_limit,
        "parent_rrf_k": parent_rrf_k,
        "parent_candidates": parent_cands,
        "final_parent_top_k": final_parent_top_k,
        "total_context_max_chars": total_context_max_chars,
    }


# ==============================================================================
# 2. CHUNKS LOADER, VALIDATOR & NUMERIC ORDERING
# ==============================================================================

def extract_chunk_number(chunk_id: str) -> int:
    """Trích xuất phần số cuối cùng của chunk_id để sắp xếp số học."""
    m = re.search(r":(\d+)$", chunk_id)
    if m:
        return int(m.group(1))
    m2 = re.search(r"_(\d+)$", chunk_id)
    if m2:
        return int(m2.group(1))
    return 0


def load_and_order_hierarchical_chunks(
    input_path: Optional[Union[str, Path]] = None,
    strategy: str = "hierarchical"
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Nạp dữ liệu chunks JSON, chỉ chấp nhận strategy 'hierarchical',
    validate schema 6 trường nghiêm ngặt, kiểm tra trùng lặp chunk_id
    và sắp xếp thứ tự số học (numeric) theo từng nguồn tài liệu.
    """
    if strategy != "hierarchical":
        raise ValueError(f"Strategy '{strategy}' không được hỗ trợ ở Buổi 09. Chỉ chấp nhận 'hierarchical'.")

    target_dir = Path(input_path).resolve() if input_path else DEFAULT_CHUNKS_DIR
    if not target_dir.exists():
        raise FileNotFoundError(f"Đường dẫn thư mục chunks không tồn tại: {target_dir}")

    if target_dir.is_file():
        files = [target_dir]
    elif target_dir.is_dir():
        # Lọc các file *__hierarchical.json
        files = sorted(list(target_dir.glob("*__hierarchical.json")))
        if not files:
            files = sorted([f for f in target_dir.glob("*.json") if "hierarchical" in f.name])
        if not files:
            raise FileNotFoundError(f"Không tìm thấy file hierarchical JSON nào trong: {target_dir}")
    else:
        raise ValueError(f"Đường dẫn input không hợp lệ: {target_dir}")

    raw_records: List[Dict[str, Any]] = []
    seen_chunk_ids: Dict[str, str] = {} # chunk_id -> file_name
    file_fingerprints: List[Dict[str, Any]] = []

    for f in files:
        file_bytes = f.read_bytes()
        f_hash = hashlib.sha256(file_bytes).hexdigest()
        file_fingerprints.append({
            "file_name": f.name,
            "file_path": str(f),
            "sha256": f_hash,
            "size_bytes": len(file_bytes)
        })

        try:
            content = json.loads(file_bytes.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Lỗi cú pháp JSON trong file '{f.name}': {e}")

        if not isinstance(content, list):
            raise ValueError(f"Nội dung file '{f.name}' phải là một JSON array (list).")

        for idx, rec in enumerate(content):
            loc = f"Record thứ {idx} trong file '{f.name}'"
            if not isinstance(rec, dict):
                raise ValueError(f"{loc}: Phải là một JSON object (dict).")

            # Validate 6 trường bắt buộc
            req_keys = {"chunk_id", "strategy", "source", "page_start", "page_end", "text"}
            missing = req_keys - rec.keys()
            if missing:
                raise ValueError(f"{loc}: Thiếu các trường bắt buộc: {sorted(list(missing))}")

            cid = str(rec["chunk_id"]).strip()
            if not cid:
                raise ValueError(f"{loc}: Trường 'chunk_id' không được rỗng.")

            if cid in seen_chunk_ids:
                prev_f = seen_chunk_ids[cid]
                raise ValueError(f"{loc}: Trùng lặp chunk_id '{cid}' (đã xuất hiện trước đó tại '{prev_f}').")
            seen_chunk_ids[cid] = f.name

            rec_strategy = str(rec["strategy"]).strip()
            if rec_strategy != "hierarchical":
                raise ValueError(f"{loc}: strategy '{rec_strategy}' không khớp với yêu cầu 'hierarchical'.")

            source = str(rec["source"]).strip()
            if not source:
                raise ValueError(f"{loc}: Trường 'source' không được rỗng.")

            p_start = rec["page_start"]
            p_end = rec["page_end"]
            if isinstance(p_start, bool) or not isinstance(p_start, int) or p_start < 1:
                raise ValueError(f"{loc}: 'page_start' phải là integer >= 1 (nhận được: {p_start}).")
            if isinstance(p_end, bool) or not isinstance(p_end, int) or p_end < 1:
                raise ValueError(f"{loc}: 'page_end' phải là integer >= 1 (nhận được: {p_end}).")
            if p_start > p_end:
                raise ValueError(f"{loc}: 'page_start' ({p_start}) không được lớn hơn 'page_end' ({p_end}).")

            text = rec["text"]
            if not isinstance(text, str):
                raise ValueError(f"{loc}: Trường 'text' phải là string.")
            text_clean = text.strip()
            if not text_clean:
                raise ValueError(f"{loc}: Trường 'text' sau khi trim không được rỗng.")

            chunk_copy = dict(rec)
            chunk_copy["chunk_id"] = cid
            chunk_copy["strategy"] = rec_strategy
            chunk_copy["source"] = source
            chunk_copy["page_start"] = p_start
            chunk_copy["page_end"] = p_end
            chunk_copy["text"] = text_clean
            raw_records.append(chunk_copy)

    # Nhóm theo source và sắp xếp numeric theo thứ tự số của chunk_id
    by_source: Dict[str, List[Dict[str, Any]]] = {}
    for r in raw_records:
        by_source.setdefault(r["source"], []).append(r)

    ordered_records: List[Dict[str, Any]] = []
    source_stats: Dict[str, Any] = {}

    for src in sorted(by_source.keys()):
        src_chunks = by_source[src]
        src_chunks.sort(key=lambda c: (extract_chunk_number(c["chunk_id"]), c["chunk_id"]))
        ordered_records.extend(src_chunks)
        source_stats[src] = {
            "chunk_count": len(src_chunks),
            "first_chunk_id": src_chunks[0]["chunk_id"],
            "last_chunk_id": src_chunks[-1]["chunk_id"]
        }

    stats = {
        "files_read": len(files),
        "total_records": len(ordered_records),
        "sources_count": len(source_stats),
        "sources": source_stats,
        "file_fingerprints": file_fingerprints
    }
    return ordered_records, stats


# ==============================================================================
# 3. DETERMINISTIC HIERARCHY RESOLUTION
# ==============================================================================

def clean_article_slug(label: str) -> str:
    """Tạo khóa slug chuẩn hóa từ tiêu đề Điều."""
    m = re.search(r"Điều\s+(\d+[\w\.]*)", label, re.IGNORECASE)
    if m:
        num = m.group(1).rstrip(".")
        return f"Dieu_{num}"
    cleaned = re.sub(r"[^\w]+", "_", label.strip()).strip("_")
    return cleaned[:30] if cleaned else "Dieu_Unknown"


def resolve_child_hierarchy(
    chunks: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Phân giải cấu trúc cấp bậc (Hierarchy Resolution) cho từng child chunk
    theo quy tắc deterministic 4 cấp ưu tiên:
    1. Metadata explicit của chính record.
    2. Heading cấp cao ở đầu chunk text.
    3. Carry forward Điều/Chương gần nhất trong cùng source.
    4. Document fallback khi chưa xác định được Điều.
    """
    resolved_children: List[Dict[str, Any]] = []
    current_context: Dict[str, Any] = {
        "active_source": None,
        "active_chapter": None,
        "active_article": None,
        "active_article_key": None,
    }

    res_counts = {
        "metadata": 0,
        "heading_inferred": 0,
        "carried_forward": 0,
        "document_fallback": 0
    }
    ambiguous_count = 0
    warning_type_counts: Dict[str, int] = {}

    for c in chunks:
        src = c["source"]
        # Không carry forward qua source khác
        if src != current_context["active_source"]:
            current_context = {
                "active_source": src,
                "active_chapter": None,
                "active_article": None,
                "active_article_key": None,
            }

        st = c.get("structure") or {}
        meta_chapter = st.get("chapter")
        meta_article = st.get("article")
        meta_clause = st.get("clause")
        meta_point = st.get("point")

        text = c["text"]
        warnings: List[str] = []
        ambiguous = False

        # Tìm kiếm các tiêu đề trong text
        dieu_headings = list(RE_HEADING_DIEU.finditer(text))
        chuong_headings = list(RE_HEADING_CHUONG.finditer(text))

        # Phân giải Chapter
        resolved_chapter = None
        if meta_chapter:
            resolved_chapter = meta_chapter
            current_context["active_chapter"] = meta_chapter
        elif chuong_headings:
            resolved_chapter = chuong_headings[-1].group(0).strip()
            current_context["active_chapter"] = resolved_chapter
        elif current_context["active_chapter"]:
            resolved_chapter = current_context["active_chapter"]

        # Phân giải Article theo 4 cấp ưu tiên
        resolved_article = None
        res_method = None

        if meta_article:
            res_method = "metadata"
            resolved_article = meta_article

            # Kiểm tra xung đột với heading trong text
            if dieu_headings:
                hd_art_str = dieu_headings[-1].group(0).strip()
                m1 = re.search(r"Điều\s+(\d+)", meta_article, re.IGNORECASE)
                m2 = re.search(r"Điều\s+(\d+)", hd_art_str, re.IGNORECASE)
                if m1 and m2 and m1.group(1) != m2.group(1):
                    ambiguous = True
                    w_msg = f"Xung đột giữa metadata article '{meta_article}' và text heading '{hd_art_str}'. Ưu tiên metadata."
                    warnings.append(w_msg)
                    warning_type_counts["metadata_heading_conflict"] = warning_type_counts.get("metadata_heading_conflict", 0) + 1

            current_context["active_article"] = resolved_article
            current_context["active_article_key"] = clean_article_slug(resolved_article)

        elif dieu_headings:
            # Có tiêu đề Điều trong text
            first_hd = dieu_headings[0]
            is_at_start = first_hd.start() <= 5

            if is_at_start:
                res_method = "heading_inferred"
                resolved_article = first_hd.group(0).strip()
                current_context["active_article"] = resolved_article
                current_context["active_article_key"] = clean_article_slug(resolved_article)
            else:
                # Tiêu đề xuất hiện ở giữa/cuối chunk (ranh giới chuyển giao Điều)
                ambiguous = True
                w_msg = f"Chunk chứa tiêu đề Điều mới ở giữa/cuối nội dung: '{dieu_headings[-1].group(0).strip()}'."
                warnings.append(w_msg)
                warning_type_counts["heading_at_chunk_end"] = warning_type_counts.get("heading_at_chunk_end", 0) + 1

                if current_context["active_article"]:
                    res_method = "carried_forward"
                    resolved_article = current_context["active_article"]
                else:
                    res_method = "heading_inferred"
                    resolved_article = dieu_headings[-1].group(0).strip()

                # Cập nhật context cho các chunk tiếp theo sau ranh giới này
                current_context["active_article"] = dieu_headings[-1].group(0).strip()
                current_context["active_article_key"] = clean_article_slug(dieu_headings[-1].group(0).strip())

            if len(dieu_headings) > 1:
                ambiguous = True
                w_msg = f"Chunk chứa nhiều tiêu đề Điều ({len(dieu_headings)} tiêu đề)."
                warnings.append(w_msg)
                warning_type_counts["multiple_headings_in_chunk"] = warning_type_counts.get("multiple_headings_in_chunk", 0) + 1

        elif current_context["active_article"]:
            res_method = "carried_forward"
            resolved_article = current_context["active_article"]

        else:
            res_method = "document_fallback"
            resolved_article = None

        # Kiểm tra văn bản sửa đổi / dẫn chiếu Điều
        if RE_AMENDING_KEYWORDS.search(text):
            m_cited = RE_INLINE_DIEU_CITED.search(text)
            if m_cited:
                ambiguous = True
                w_msg = f"Phát hiện trích dẫn sửa đổi/bổ sung Điều {m_cited.group(1)} của văn bản khác trong nội dung."
                warnings.append(w_msg)
                warning_type_counts["amending_cited_article"] = warning_type_counts.get("amending_cited_article", 0) + 1

        # Trích xuất clause/point bổ sung nếu metadata thiếu
        resolved_clause = meta_clause
        if not resolved_clause:
            m_cl = RE_CLAUSE_PREFIX.match(text)
            if m_cl:
                resolved_clause = f"{m_cl.group(1)}. {m_cl.group(2)[:100]}"

        resolved_point = meta_point
        if not resolved_point:
            m_pt = RE_POINT_PREFIX.match(text)
            if m_pt:
                resolved_point = f"{m_pt.group(1)}) {m_pt.group(2)[:100]}"

        res_counts[res_method] += 1
        if ambiguous:
            ambiguous_count += 1

        article_key = current_context["active_article_key"] or "Preamble"

        child_record = {
            "child_id": c["chunk_id"],
            "parent_id": None, # Sẽ được gán cụ thể khi build parent windows
            "source": src,
            "page_start": c["page_start"],
            "page_end": c["page_end"],
            "text": text,
            "structural_path": {
                "chapter": resolved_chapter,
                "article": resolved_article,
                "clause": resolved_clause,
                "point": resolved_point
            },
            "_article_key": article_key, # Field tạm phục vụ gom nhóm
            "resolution_method": res_method,
            "ambiguous": ambiguous,
            "warnings": warnings
        }
        resolved_children.append(child_record)

    resolution_stats = {
        "methods": res_counts,
        "ambiguous_children_count": ambiguous_count,
        "warning_breakdown": warning_type_counts,
        "total_warnings": sum(len(c["warnings"]) for c in resolved_children)
    }
    return resolved_children, resolution_stats


# ==============================================================================
# 4. PARENT BUILDING & WINDOW SPLITTING
# ==============================================================================

def build_parent_documents(
    children: List[Dict[str, Any]],
    parent_max_chars: int = 6000
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Gộp các child chunks thành các Parent Documents (khối Điều luật).
    Nếu một Điều quá dài vượt `parent_max_chars`, chia thành các window
    liên tiếp tại ranh giới child chunks, không cắt giữa chừng nội dung.
    Gán chính xác `parent_id` cho từng child record.
    """
    # Gom nhóm các children liên tiếp có cùng (source, _article_key)
    groups: List[Tuple[str, str, List[Dict[str, Any]]]] = []
    current_key: Optional[Tuple[str, str]] = None
    current_group: List[Dict[str, Any]] = []

    for c in children:
        key = (c["source"], c["_article_key"])
        if key == current_key:
            current_group.append(c)
        else:
            if current_group and current_key:
                groups.append((current_key[0], current_key[1], current_group))
            current_key = key
            current_group = [c]
    if current_group and current_key:
        groups.append((current_key[0], current_key[1], current_group))

    parents: List[Dict[str, Any]] = []
    split_article_count = 0
    oversized_children_count = 0

    for src, art_key, grp_children in groups:
        # Chia window tại ranh giới child
        windows: List[List[Dict[str, Any]]] = []
        curr_w: List[Dict[str, Any]] = []
        curr_chars = 0

        for c in grp_children:
            c_len = len(c["text"])
            sep_len = 2 if curr_w else 0 # tương ứng với '\n\n'

            if curr_chars + sep_len + c_len <= parent_max_chars:
                curr_w.append(c)
                curr_chars += sep_len + c_len
            else:
                if curr_w:
                    windows.append(curr_w)
                    curr_w = [c]
                    curr_chars = c_len
                else:
                    # Single child đơn lẻ vượt quá PARENT_MAX_CHARS
                    windows.append([c])
                    curr_w = []
                    curr_chars = 0

        if curr_w:
            windows.append(curr_w)

        if len(windows) > 1:
            split_article_count += 1

        for w_idx, w_children in enumerate(windows, start=1):
            parent_id = f"{src}::{art_key}::w{w_idx:02d}"
            p_warnings: List[str] = []

            if len(windows) > 1:
                p_warnings.append(f"article_split_into_{len(windows)}_windows (window {w_idx}/{len(windows)})")

            for c in w_children:
                c["parent_id"] = parent_id
                if len(c["text"]) > parent_max_chars:
                    oversized_msg = f"oversized_single_child: {len(c['text'])} > {parent_max_chars}"
                    if oversized_msg not in c["warnings"]:
                        c["warnings"].append(oversized_msg)
                    p_warnings.append(f"oversized_single_child (chunk {c['child_id']})")
                    oversized_children_count += 1

            parent_text = "\n\n".join(c["text"] for c in w_children)
            p_doc = {
                "parent_id": parent_id,
                "source": src,
                "page_start": min(c["page_start"] for c in w_children),
                "page_end": max(c["page_end"] for c in w_children),
                "article_key": art_key,
                "window_index": w_idx,
                "child_ids": [c["child_id"] for c in w_children],
                "text": parent_text,
                "char_count": len(parent_text),
                "ambiguous_child_count": sum(1 for c in w_children if c["ambiguous"]),
                "warnings": p_warnings
            }
            parents.append(p_doc)

    # Loại bỏ trường tạm '_article_key' khỏi children trước khi lưu/trả về
    for c in children:
        c.pop("_article_key", None)

    char_counts = [p["char_count"] for p in parents]
    sorted_counts = sorted(char_counts)
    p_len = len(sorted_counts)
    stats = {
        "total_parents": len(parents),
        "split_articles_count": split_article_count,
        "oversized_single_children_count": oversized_children_count,
        "parent_size_min": sorted_counts[0] if p_len > 0 else 0,
        "parent_size_median": sorted_counts[p_len // 2] if p_len > 0 else 0,
        "parent_size_p95": sorted_counts[int(p_len * 0.95)] if p_len > 0 else 0,
        "parent_size_max": sorted_counts[-1] if p_len > 0 else 0,
    }
    return children, parents, stats


# ==============================================================================
# 5. ATOMIC STORE & READ-ONLY STATUS
# ==============================================================================

def save_hierarchy_store(
    children: List[Dict[str, Any]],
    parents: List[Dict[str, Any]],
    manifest: Dict[str, Any],
    storage_dir: Optional[Union[str, Path]] = None
) -> Dict[str, Any]:
    """
    Lưu trữ cấu trúc hierarchy một cách Atomic:
    Ghi dữ liệu vào temporary file trên cùng thư mục rồi replace.
    Không xóa dữ liệu hợp lệ cũ trước khi build mới hoàn tất.
    """
    target_storage = Path(storage_dir).resolve() if storage_dir else HIERARCHY_STORAGE_DIR
    target_storage.mkdir(parents=True, exist_ok=True)

    files_to_save = {
        "children.json": children,
        "parents.json": parents,
        "manifest.json": manifest
    }

    pid = os.getpid()
    temp_files: List[Path] = []

    try:
        for fname, data in files_to_save.items():
            dest = target_storage / fname
            tmp = target_storage / f"{fname}.tmp.{pid}"
            temp_files.append(tmp)

            with open(tmp, "w", encoding="utf-8") as fp:
                json.dump(data, fp, ensure_ascii=False, indent=2)
                fp.flush()
                os.fsync(fp.fileno())

            os.replace(tmp, dest)

        return {
            "status": "success",
            "storage_dir": str(target_storage),
            "files_saved": list(files_to_save.keys())
        }
    except Exception as e:
        for tmp in temp_files:
            if tmp.exists():
                try:
                    tmp.unlink()
                except Exception:
                    pass
        raise IOError(f"Lỗi khi lưu trữ atomic hierarchy store: {e}")


def get_hierarchy_status(storage_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Kiểm tra trạng thái của Hierarchy Store (thao tác READ-ONLY tuyệt đối).
    Không mkdir, không build và không sửa timestamp.
    """
    target_storage = Path(storage_dir).resolve() if storage_dir else HIERARCHY_STORAGE_DIR

    if not target_storage.exists() or not target_storage.is_dir():
        return {
            "is_built": False,
            "storage_dir": str(target_storage),
            "reason": "Thư mục storage/hierarchy chưa tồn tại."
        }

    children_file = target_storage / "children.json"
    parents_file = target_storage / "parents.json"
    manifest_file = target_storage / "manifest.json"

    if not (children_file.exists() and parents_file.exists() and manifest_file.exists()):
        return {
            "is_built": False,
            "storage_dir": str(target_storage),
            "reason": "Thiếu ít nhất một trong các tệp: children.json, parents.json, manifest.json."
        }

    try:
        with open(manifest_file, "r", encoding="utf-8") as fp:
            manifest = json.load(fp)

        return {
            "is_built": True,
            "storage_dir": str(target_storage),
            "schema_version": manifest.get("schema_version"),
            "build_timestamp": manifest.get("build_timestamp"),
            "strategy": manifest.get("strategy"),
            "total_children": manifest.get("counts", {}).get("total_children"),
            "total_parents": manifest.get("counts", {}).get("total_parents"),
            "ambiguous_children": manifest.get("counts", {}).get("ambiguous_children"),
            "oversized_single_children": manifest.get("counts", {}).get("oversized_single_children"),
            "total_warnings": manifest.get("warning_counts", {}).get("total_warnings"),
            "config_identity": manifest.get("config_identity"),
        }
    except Exception as e:
        return {
            "is_built": False,
            "storage_dir": str(target_storage),
            "reason": f"Không thể đọc manifest.json: {e}"
        }


# ==============================================================================
# 6. MULTI-QUERY EXPANSION (BƯỚC 04)
# ==============================================================================

# In-process cache cho Query Expansion: cache_key -> deepcopy(result)
_QUERY_EXPANSION_CACHE: Dict[str, Dict[str, Any]] = {}


def clear_query_expansion_cache() -> None:
    """Xóa sạch cache query expansion trong process (phục vụ testing hoặc reset)."""
    _QUERY_EXPANSION_CACHE.clear()


def normalize_query_text(text: str) -> str:
    """Chuẩn hóa văn bản câu hỏi: Unicode NFC, trim, loại bỏ khoảng trắng thừa."""
    if not isinstance(text, str):
        raise TypeError(f"Câu hỏi phải là string, nhận được: {type(text).__name__}")
    nfc = unicodedata.normalize("NFC", text.strip())
    return re.sub(r"\s+", " ", nfc)


def normalize_for_dedup(text: str) -> str:
    """Chuẩn hóa để so khớp trùng lặp: lowercase, loại bỏ dấu câu/ký hiệu và khoảng trắng dư."""
    norm = unicodedata.normalize("NFC", text).casefold()
    return re.sub(r"[\W_]+", " ", norm).strip()


def find_legal_articles(text: str) -> Set[str]:
    """Trích xuất tập hợp số hiệu Điều trong câu hỏi/văn bản (ví dụ: {'7', '8', '16a'})."""
    matches = re.findall(r"Điều\s+(\d+[\w\.]*)", text, re.IGNORECASE)
    return set(m.rstrip(".").lower() for m in matches)


def extract_legal_references(text: str) -> Dict[str, Set[str]]:
    """Trích xuất chi tiết các tham chiếu pháp lý trong văn bản: Điều, Khoản, Điểm, Thông tư, Năm."""
    return {
        "articles": set(m.rstrip(".").lower() for m in re.findall(r"Điều\s+(\d+[\w\.]*)", text, re.IGNORECASE)),
        "clauses": set(m.lower() for m in re.findall(r"Khoản\s+(\d+)", text, re.IGNORECASE)),
        "points": set(m.lower() for m in re.findall(r"Điểm\s+([a-zđ])", text, re.IGNORECASE)),
        "circulars": set(m.lower() for m in re.findall(r"Thông tư\s+(?:số\s+)?(\d+(?:/\d+/[-\w]*)?)", text, re.IGNORECASE)),
        "years": set(re.findall(r"\b(20\d{2}|19\d{2})\b", text))
    }


def build_error_query_set(
    question: str,
    model: str,
    error_msg: str,
    start_time: float
) -> Dict[str, Any]:
    """Tạo Query Set với status 'query_generation_unavailable' khi gặp lỗi."""
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    q0_clean = normalize_query_text(question)
    return {
        "original_question": q0_clean,
        "queries": [
            {
                "query_id": "Q0",
                "text": q0_clean,
                "origin": "original",
                "focus": "original_intent"
            }
        ],
        "model": model,
        "generation_latency_ms": latency_ms,
        "status": "query_generation_unavailable",
        "error": error_msg,
        "dropped_duplicate_count": 0,
        "cache_hit": False
    }


def generate_query_variants(
    question: str,
    config: Optional[Dict[str, Any]] = None,
    query_generator_fn: Optional[Callable[[str, int, float, str], Dict[str, Any]]] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Sinh các biến thể truy vấn (Multi-Query Expansion) có kiểm soát cho câu hỏi pháp lý:
    - Q0: Luôn là câu hỏi gốc nguyên văn sau trim/NFC (origin='original', focus='original_intent').
    - Q1..Qn: Tối đa MULTI_QUERY_COUNT câu sinh thêm (origin='generated').
    - Hỗ trợ Dependency Injection thông qua `query_generator_fn`.
    - Cache in-process theo hash của câu hỏi + cấu hình + model.
    - Chống ảo giác: Loại bỏ query bịa thêm số Điều và query trùng lặp.
    - Nếu có lỗi: Trả status='query_generation_unavailable' với lỗi rõ, không crash.
    """
    if not isinstance(question, str):
        raise TypeError(f"Câu hỏi phải là string, nhận được: {type(question).__name__}")

    q0_clean = normalize_query_text(question)
    if not q0_clean:
        raise ValueError("Câu hỏi không được để rỗng hoặc chỉ chứa khoảng trắng.")
    if len(q0_clean) > 2000:
        raise ValueError("Độ dài câu hỏi vượt quá giới hạn 2000 ký tự.")

    cfg = config or load_buoi_09_config()
    model = cfg.get("generation_model", "gemini-3.5-flash-lite")
    count = int(cfg.get("multi_query_count", 3))
    temperature = float(cfg.get("multi_query_temperature", 0.2))
    max_chars = int(cfg.get("multi_query_max_chars", 300))

    cache_key = hashlib.sha256(
        f"{q0_clean}||{model}||{temperature:.2f}||{max_chars}||{count}".encode("utf-8")
    ).hexdigest()

    # Kiểm tra Cache trong process (chỉ dùng khi không inject generator_fn)
    if use_cache and query_generator_fn is None:
        if cache_key in _QUERY_EXPANSION_CACHE:
            cached = copy.deepcopy(_QUERY_EXPANSION_CACHE[cache_key])
            cached["cache_hit"] = True
            cached["generation_latency_ms"] = 0.0
            return cached

    start_time = time.perf_counter()

    # 1. Gọi Generator (qua Dependency Injection hoặc Gemini API thật)
    raw_response: Optional[Dict[str, Any]] = None

    if query_generator_fn is not None:
        try:
            raw_response = query_generator_fn(q0_clean, count, temperature, model)
        except Exception as e:
            return build_error_query_set(q0_clean, model, str(e), start_time)
    else:
        api_key = cfg.get("api_key", "").strip()
        if not api_key:
            return build_error_query_set(q0_clean, model, "Thiếu GEMINI_API_KEY trong cấu hình.", start_time)

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            system_instruction = (
                "Bạn là chuyên gia tra cứu văn bản pháp luật ngân hàng Việt Nam. "
                "Nhiệm vụ của bạn là mở rộng câu hỏi của người dùng thành các biến thể tìm kiếm đa dạng, "
                "phục vụ hệ thống truy xuất thông tin (Information Retrieval).\n"
                "Quy tắc tuyệt đối:\n"
                "1. KHÔNG trả lời câu hỏi, KHÔNG đưa ra kết luận pháp lý hay thông tin giải đáp.\n"
                "2. CHỈ sinh các câu hỏi hoặc cụm từ tìm kiếm tương đương phục vụ tìm kiếm.\n"
                "3. Biến thể cần bao phủ: (a) thuật ngữ pháp lý chính xác ('exact_legal_terms'), "
                "(b) cách diễn đạt tương đương/paraphrase ('paraphrase'), "
                "(c) khía cạnh còn thiếu nếu câu hỏi có nhiều ý ('missing_aspect').\n"
                "4. Nếu câu hỏi có chứa số Điều, Khoản, Điểm hoặc số hiệu Thông tư, PHẢI giữ nguyên số hiệu đó trong ít nhất một biến thể.\n"
                "5. TUYỆT ĐỐI KHÔNG tự phát minh thêm số Điều, Khoản, Thông tư không có trong câu hỏi gốc.\n"
                f"6. Độ dài mỗi biến thể không quá {max_chars} ký tự."
            )
            user_prompt = (
                f"Hãy tạo {count} biến thể tìm kiếm cho câu hỏi pháp lý sau:\n"
                f"Câu hỏi: \"{q0_clean}\"\n\n"
                "Trả về đúng định dạng JSON theo schema đã quy định."
            )
            schema = {
                "type": "OBJECT",
                "properties": {
                    "queries": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "text": {"type": "STRING"},
                                "focus": {"type": "STRING"}
                            },
                            "required": ["text", "focus"]
                        }
                    }
                },
                "required": ["queries"]
            }
            resp = client.models.generate_content(
                model=model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=temperature,
                )
            )
            raw_response = json.loads(resp.text)
        except Exception as e:
            return build_error_query_set(q0_clean, model, str(e), start_time)

    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    if not isinstance(raw_response, dict) or "queries" not in raw_response or not isinstance(raw_response["queries"], list):
        return build_error_query_set(
            q0_clean, model, "Phản hồi từ mô hình không đúng định dạng schema JSON (thiếu trường 'queries').", start_time
        )

    # 2. Xây dựng Q0 và kiểm tra tính hợp lệ của các generated variants
    q0_item = {
        "query_id": "Q0",
        "text": q0_clean,
        "origin": "original",
        "focus": "original_intent"
    }

    orig_dedup = normalize_for_dedup(q0_clean)
    seen_dedup = {orig_dedup}
    orig_articles = find_legal_articles(q0_clean)
    valid_generated: List[Dict[str, Any]] = []
    dropped_duplicate_count = 0
    allowed_focus = {"exact_legal_terms", "paraphrase", "missing_aspect"}

    for item in raw_response["queries"]:
        if not isinstance(item, dict):
            continue
        v_text = item.get("text")
        if not isinstance(v_text, str):
            continue
        v_clean = normalize_query_text(v_text)
        if not v_clean:
            continue
        if len(v_clean) > max_chars:
            v_clean = v_clean[:max_chars].strip()

        # Kiểm tra trùng lặp
        v_dedup = normalize_for_dedup(v_clean)
        if v_dedup in seen_dedup:
            dropped_duplicate_count += 1
            continue

        # Kiểm tra phát minh số Điều không có trong câu gốc
        v_articles = find_legal_articles(v_clean)
        invented = v_articles - orig_articles
        if invented:
            dropped_duplicate_count += 1
            continue

        seen_dedup.add(v_dedup)
        v_focus = str(item.get("focus", "paraphrase")).strip()
        if v_focus not in allowed_focus:
            v_focus = "paraphrase"

        valid_generated.append({"text": v_clean, "focus": v_focus})
        if len(valid_generated) >= count:
            break

    # Gán ID tuần tự deterministic: Q0, Q1, Q2, ...
    final_queries = [q0_item]
    for idx, g in enumerate(valid_generated, start=1):
        final_queries.append({
            "query_id": f"Q{idx}",
            "text": g["text"],
            "origin": "generated",
            "focus": g["focus"]
        })

    result = {
        "original_question": q0_clean,
        "queries": final_queries,
        "model": model,
        "generation_latency_ms": latency_ms,
        "status": "ready",
        "dropped_duplicate_count": dropped_duplicate_count,
        "cache_hit": False
    }

    if use_cache and query_generator_fn is None:
        _QUERY_EXPANSION_CACHE[cache_key] = copy.deepcopy(result)

    return result


# ==============================================================================
# 7. CROSS-QUERY RRF FUSION (BƯỚC 05)
# ==============================================================================

def cross_query_rrf_fusion(
    per_query_results: List[Dict[str, Any]],
    config: Optional[Dict[str, Any]] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Tầng RRF thứ hai: hợp nhất kết quả từ nhiều query thành union child_id.

    Công thức Multi-Query RRF score cho child d:
      mq_rrf_score(d) = Σ_q [ query_weight(q) / (MULTI_QUERY_RRF_K + inner_fused_rank_q(d)) ]

    Trong đó:
    - Q0 (origin='original') dùng MULTI_QUERY_ORIGINAL_WEIGHT
    - Q1..Qn (origin='generated') dùng MULTI_QUERY_VARIANT_WEIGHT
    - inner_fused_rank là fused_rank từ RRF nội bộ của từng query
    - KHÔNG dùng bm25_score, cosine distance, inner rrf_score hay rerank score

    per_query_results: list các dict:
      {
        "query_id": "Q0",
        "origin": "original" | "generated",
        "status": "ok" | "error",
        "error_msg": Optional[str],
        "candidates": List[child_hit_dict],  # đã có fused_rank
        "latency_ms": float,
        "result_count": int
      }
    """
    cfg = config or {}
    mq_rrf_k = float(cfg.get("multi_query_rrf_k", 60))
    orig_weight = float(cfg.get("multi_query_original_weight", 1.5))
    var_weight = float(cfg.get("multi_query_variant_weight", 1.0))

    t0 = time.perf_counter()

    # Lập bản đồ child_id → merged record
    union: Dict[str, Dict[str, Any]] = {}

    for qr in per_query_results:
        if qr["status"] != "ok":
            continue  # bỏ qua query lỗi; đã ghi rõ theo failure contract

        qid = qr["query_id"]
        origin = qr.get("origin", "generated")
        weight = orig_weight if origin == "original" else var_weight

        for hit in qr["candidates"]:
            # Xác định child_id (ưu tiên 'chunk_id', fallback 'child_id')
            cid = hit.get("child_id") or hit.get("chunk_id")
            if not cid:
                continue

            inner_rank = hit.get("fused_rank") or hit.get("inner_fused_rank") or hit.get("rank")
            if inner_rank is None:
                continue

            mq_contrib = weight / (mq_rrf_k + float(inner_rank))

            if cid not in union:
                # Chuẩn hóa trường metadata bắt buộc
                union[cid] = {
                    "child_id": cid,
                    "text": hit.get("text", ""),
                    "source": hit.get("source", ""),
                    "page_start": hit.get("page_start"),
                    "page_end": hit.get("page_end"),
                    # Tích lũy
                    "_mq_score": 0.0,
                    "_support_query_ids": [],
                    "_per_query_ranks": {},
                    "_per_query_trace": {},
                }
            else:
                # Kiểm tra metadata consistency
                rec = union[cid]
                mismatches = []
                for field in ("text", "source", "page_start", "page_end"):
                    if rec[field] != hit.get(field):
                        mismatches.append(
                            f"{field}: stored={rec[field]!r} vs {qid}={hit.get(field)!r}"
                        )
                if mismatches:
                    raise ValueError(
                        f"Metadata mismatch for child_id='{cid}' across queries: "
                        + "; ".join(mismatches)
                    )

            rec = union[cid]
            rec["_mq_score"] += mq_contrib
            if qid not in rec["_support_query_ids"]:
                rec["_support_query_ids"].append(qid)
            rec["_per_query_ranks"][qid] = inner_rank

            # Trace per-query: giữ bm25_rank, semantic_rank, inner fused_rank
            rec["_per_query_trace"][qid] = {
                "bm25_rank": hit.get("bm25_rank"),
                "semantic_rank": hit.get("semantic_rank"),
                "inner_fused_rank": inner_rank,
                "matched_by": hit.get("matched_by", []),
            }

    # Sắp xếp support_query_ids theo thứ tự Q0, Q1...
    def _qid_sort_key(qid: str) -> int:
        m = re.match(r"Q(\d+)$", qid)
        return int(m.group(1)) if m else 9999

    # Xây dựng danh sách final và sắp xếp
    fused: List[Dict[str, Any]] = []
    for cid, rec in union.items():
        support_ids_sorted = sorted(rec["_support_query_ids"], key=_qid_sort_key)
        per_query_ranks = rec["_per_query_ranks"]
        best_rank = min(per_query_ranks.values()) if per_query_ranks else 9999

        fused.append({
            "child_id": cid,
            "text": rec["text"],
            "source": rec["source"],
            "page_start": rec["page_start"],
            "page_end": rec["page_end"],
            "multi_query_rrf_score": round(rec["_mq_score"], 8),
            "multi_query_rank": 0,  # sẽ gán bên dưới
            "support_query_count": len(support_ids_sorted),
            "support_query_ids": support_ids_sorted,
            "per_query_ranks": per_query_ranks,
            "per_query_trace": rec["_per_query_trace"],
            "best_query_rank": best_rank,
        })

    # Sort: mq_rrf_score DESC, support_count DESC, best_rank ASC, child_id ASC
    fused.sort(key=lambda x: (
        -x["multi_query_rrf_score"],
        -x["support_query_count"],
        x["best_query_rank"],
        x["child_id"]
    ))

    # Gán multi_query_rank từ 1
    for rank, item in enumerate(fused, start=1):
        item["multi_query_rank"] = rank

    # Tính overlap distribution
    overlap_dist: Dict[int, int] = {}
    for item in fused:
        cnt = item["support_query_count"]
        overlap_dist[cnt] = overlap_dist.get(cnt, 0) + 1

    fusion_latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    fusion_stats = {
        "union_child_count": len(fused),
        "overlap_distribution": overlap_dist,
        "fusion_latency_ms": fusion_latency_ms,
        "config_used": {
            "multi_query_rrf_k": mq_rrf_k,
            "multi_query_original_weight": orig_weight,
            "multi_query_variant_weight": var_weight,
        }
    }

    return fused, fusion_stats


# ==============================================================================
# 8. FAN-OUT MULTI-QUERY HYBRID RETRIEVAL (BƯỚC 05)
# ==============================================================================

def fan_out_multi_query_retrieval(
    query_set: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None,
    hybrid_retriever_fn: Optional[Callable[..., Dict[str, Any]]] = None,
    query_generator_fn: Optional[Callable[..., Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Fan-out per-query hybrid retrieval + cross-query RRF fusion (Bước 05).

    Với mỗi query Q0..Qn:
      1. Gọi hybrid_retriever_fn (hoặc retrieve_hybrid_candidates từ advanced_rag)
         → BM25 + semantic → inner RRF.
      2. Mỗi query chỉ được gọi hybrid retriever đúng một lần.
      3. Không gọi cross-encoder.
      4. Lấy tối đa PER_QUERY_CANDIDATES child hits.

    Sau đó gọi cross_query_rrf_fusion để tổng hợp union.

    Failure contract:
    - Q0 lỗi → fail toàn pipeline (status='q0_retrieval_failed').
    - Generated query lỗi → ghi lỗi riêng, status='multi_query_partial'.
    - Tất cả generated lỗi nhưng Q0 OK → vẫn trả kết quả Q0, status='multi_query_partial'.

    hybrid_retriever_fn(question, top_n, config) -> {'candidates': [...], 'trace': {...}}
    """
    cfg = config or load_buoi_09_config()
    per_query_cands = int(cfg.get("per_query_candidates", 12))

    queries = query_set.get("queries", [])
    if not queries:
        return {
            "status": "error",
            "error": "Query set rỗng hoặc không có trường 'queries'.",
            "fused_children": [],
            "per_query_results": [],
            "trace": {}
        }

    per_query_results: List[Dict[str, Any]] = []
    q0_failed = False

    # --- Fan-out: gọi retriever cho từng query độc lập ---
    for q_item in queries:
        qid = q_item["query_id"]
        q_text = q_item["text"]
        origin = q_item.get("origin", "generated")

        t_ret_start = time.perf_counter()
        try:
            if hybrid_retriever_fn is not None:
                ret_result = hybrid_retriever_fn(q_text, top_n=per_query_cands, config=cfg)
            else:
                # Import lazy để tránh circular / module chưa có
                from advanced_rag import retrieve_hybrid_candidates
                ret_result = retrieve_hybrid_candidates(
                    question=q_text,
                    strategy="hierarchical",
                    top_n=per_query_cands,
                    config=cfg,
                )
            candidates = ret_result.get("candidates", [])
            ret_trace = ret_result.get("trace", {})
            latency_ms = round((time.perf_counter() - t_ret_start) * 1000, 2)

            per_query_results.append({
                "query_id": qid,
                "origin": origin,
                "text": q_text,
                "status": "ok",
                "error_msg": None,
                "candidates": candidates,
                "result_count": len(candidates),
                "latency_ms": latency_ms,
                "retrieval_trace": ret_trace,
            })

        except Exception as exc:
            latency_ms = round((time.perf_counter() - t_ret_start) * 1000, 2)
            err_msg = str(exc)

            per_query_results.append({
                "query_id": qid,
                "origin": origin,
                "text": q_text,
                "status": "error",
                "error_msg": err_msg,
                "candidates": [],
                "result_count": 0,
                "latency_ms": latency_ms,
                "retrieval_trace": {},
            })

            if qid == "Q0":
                q0_failed = True
                break  # Q0 lỗi → dừng ngay

    # --- Q0 failure: fail toàn pipeline ---
    if q0_failed:
        return {
            "status": "q0_retrieval_failed",
            "error": next(
                (r["error_msg"] for r in per_query_results if r["query_id"] == "Q0"),
                "Q0 retrieval failed"
            ),
            "fused_children": [],
            "per_query_results": per_query_results,
            "trace": _build_retrieval_trace(per_query_results, None, None, cfg),
        }

    # --- Kiểm tra partial status ---
    ok_count = sum(1 for r in per_query_results if r["status"] == "ok")
    err_count = sum(1 for r in per_query_results if r["status"] == "error")
    total_queries = len(queries)

    # --- Cross-query RRF fusion ---
    t_fusion_start = time.perf_counter()
    try:
        fused_children, fusion_stats = cross_query_rrf_fusion(
            per_query_results=per_query_results,
            config=cfg,
        )
    except ValueError as ve:
        # Metadata mismatch → fail với thông báo rõ
        return {
            "status": "metadata_mismatch_error",
            "error": str(ve),
            "fused_children": [],
            "per_query_results": per_query_results,
            "trace": _build_retrieval_trace(per_query_results, None, None, cfg),
        }
    fusion_latency_ms = round((time.perf_counter() - t_fusion_start) * 1000, 2)

    # Xác định status cuối
    if err_count == 0:
        final_status = "ok"
    else:
        final_status = "multi_query_partial"

    trace = _build_retrieval_trace(per_query_results, fusion_stats, fusion_latency_ms, cfg)
    trace["query_expansion_call_count"] = 0  # expansion đã xảy ra ở bước trước

    return {
        "status": final_status,
        "query_count_requested": total_queries,
        "query_count_valid": ok_count + err_count,
        "query_count_executed": ok_count + err_count,
        "query_count_failed": err_count,
        "fused_children": fused_children,
        "per_query_results": per_query_results,
        "fusion_stats": fusion_stats,
        "trace": trace,
    }


def _build_retrieval_trace(
    per_query_results: List[Dict[str, Any]],
    fusion_stats: Optional[Dict[str, Any]],
    fusion_latency_ms: Optional[float],
    cfg: Dict[str, Any]
) -> Dict[str, Any]:
    """Xây dựng trace tổng hợp cho toàn bộ fan-out retrieval."""
    per_query_summary = []
    total_latency_expansion = 0.0
    total_latency_retrieval = 0.0

    for r in per_query_results:
        per_query_summary.append({
            "query_id": r["query_id"],
            "origin": r.get("origin", "generated"),
            "status": r["status"],
            "result_count": r.get("result_count", 0),
            "latency_ms": r.get("latency_ms", 0.0),
            "error_msg": r.get("error_msg"),
        })
        if r.get("origin") == "original":
            total_latency_expansion += 0.0  # expansion đã đo riêng
        total_latency_retrieval += r.get("latency_ms", 0.0)

    trace: Dict[str, Any] = {
        "per_query_summary": per_query_summary,
        "total_retrieval_latency_ms": round(total_latency_retrieval, 2),
        "fusion_latency_ms": fusion_latency_ms,
        "config_snapshot": {
            "per_query_candidates": cfg.get("per_query_candidates", 12),
            "multi_query_rrf_k": cfg.get("multi_query_rrf_k", 60),
            "multi_query_original_weight": cfg.get("multi_query_original_weight", 1.5),
            "multi_query_variant_weight": cfg.get("multi_query_variant_weight", 1.0),
        }
    }

    if fusion_stats is not None:
        trace["union_child_count"] = fusion_stats.get("union_child_count", 0)
        trace["overlap_distribution"] = fusion_stats.get("overlap_distribution", {})

    return trace


# ==============================================================================
# 9. HIERARCHY STORE LOADER (BƯỚC 06)
# ==============================================================================

def load_hierarchy_store(
    storage_dir: Optional[Union[str, Path]] = None
) -> Dict[str, Any]:
    """
    Nạp children.json, parents.json, manifest.json từ store đã build.
    Trả {'children_by_id': {...}, 'parents_by_id': {...}, 'manifest': {...}}
    hoặc raise RuntimeError nếu store chưa sẵn sàng.
    """
    target = Path(storage_dir).resolve() if storage_dir else HIERARCHY_STORAGE_DIR

    status = get_hierarchy_status(storage_dir=target)
    if not status.get("is_built"):
        reason = status.get("reason", "Không rõ lý do.")
        raise RuntimeError(f"hierarchy_not_ready: {reason}")

    children_path = target / "children.json"
    parents_path = target / "parents.json"
    manifest_path = target / "manifest.json"

    with open(children_path, "r", encoding="utf-8") as f:
        children_list: List[Dict[str, Any]] = json.load(f)
    with open(parents_path, "r", encoding="utf-8") as f:
        parents_list: List[Dict[str, Any]] = json.load(f)
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest: Dict[str, Any] = json.load(f)

    children_by_id: Dict[str, Dict[str, Any]] = {c["child_id"]: c for c in children_list}
    parents_by_id: Dict[str, Dict[str, Any]] = {p["parent_id"]: p for p in parents_list}

    return {
        "children_by_id": children_by_id,
        "parents_by_id": parents_by_id,
        "manifest": manifest,
        "total_children": len(children_list),
        "total_parents": len(parents_list),
    }


# ==============================================================================
# 10. PARENT AGGREGATION + CONTEXT BUDGET (BƯỚC 06)
# ==============================================================================

def aggregate_parent_candidates(
    child_hits: List[Dict[str, Any]],
    registry: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Map fused child hits → parent documents, tính parent RRF score, áp context budget.

    Công thức Parent RRF score cho parent p:
      parent_rrf_score(p) = Σ_{c ∈ scoring_children(p)} [ 1 / (PARENT_RRF_K + mq_rank(c)) ]

    - Chỉ dùng tối đa PARENT_SCORE_CHILD_LIMIT child có multi_query_rank tốt nhất.
    - KHÔNG cộng raw MQ-RRF score, rerank score hay cosine distance.

    registry: output từ load_hierarchy_store(): {'children_by_id': {...}, 'parents_by_id': {...}}
    """
    cfg = config or {}
    parent_rrf_k = float(cfg.get("parent_rrf_k", 60))
    parent_score_child_limit = int(cfg.get("parent_score_child_limit", 3))
    parent_candidates_limit = int(cfg.get("parent_candidates", 10))
    total_context_max_chars = int(cfg.get("total_context_max_chars", 16000))
    parent_max_chars = int(cfg.get("parent_max_chars", 6000))

    children_by_id: Dict[str, Dict[str, Any]] = registry.get("children_by_id", {})
    parents_by_id: Dict[str, Dict[str, Any]] = registry.get("parents_by_id", {})

    t0 = time.perf_counter()

    # ------------------------------------------------------------------ #
    # 1. Map child_id → parent_id và lookup parent document              #
    # ------------------------------------------------------------------ #
    parent_groups: Dict[str, List[Dict[str, Any]]] = {}  # parent_id → [child_hits]
    mapping_table: List[Dict[str, Any]] = []
    missing_child_ids: List[str] = []
    missing_parent_ids: List[str] = []
    seen_parent_child_text: Dict[str, Set[str]] = {}  # phát hiện duplicate child text

    for hit in child_hits:
        cid = hit.get("child_id") or hit.get("chunk_id")
        if not cid:
            continue

        child_record = children_by_id.get(cid)
        if child_record is None:
            missing_child_ids.append(cid)
            continue

        parent_id = child_record.get("parent_id")
        if not parent_id:
            missing_child_ids.append(cid)
            continue

        parent_doc = parents_by_id.get(parent_id)
        if parent_doc is None:
            missing_parent_ids.append(parent_id)
            continue

        # Kiểm tra duplicate child text giữa các parent (hierarchy invariant)
        child_text = child_record.get("text", "")
        if parent_id not in seen_parent_child_text:
            seen_parent_child_text[parent_id] = set()
        # Duplicate child text trong cùng parent bình thường (thường không xảy ra)
        # Duplicate text trong parent KHÁC nhau là lỗi invariant
        for other_pid, other_texts in seen_parent_child_text.items():
            if other_pid != parent_id and child_text and child_text in other_texts:
                raise ValueError(
                    f"Hierarchy invariant violation: child text của '{cid}' xuất hiện "
                    f"trong cả parent '{parent_id}' và '{other_pid}'."
                )
        seen_parent_child_text[parent_id].add(child_text)

        if parent_id not in parent_groups:
            parent_groups[parent_id] = []
        parent_groups[parent_id].append(hit)

        mapping_table.append({
            "child_id": cid,
            "parent_id": parent_id,
            "multi_query_rank": hit.get("multi_query_rank"),
            "support_query_ids": hit.get("support_query_ids", []),
        })

    if missing_child_ids:
        raise KeyError(
            f"Child lookup thất bại cho {len(missing_child_ids)} ID: "
            f"{missing_child_ids[:5]}{'...' if len(missing_child_ids) > 5 else ''}"
        )
    if missing_parent_ids:
        raise KeyError(
            f"Parent lookup thất bại cho {len(missing_parent_ids)} ID: "
            f"{missing_parent_ids[:5]}{'...' if len(missing_parent_ids) > 5 else ''}"
        )

    mapping_latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    # ------------------------------------------------------------------ #
    # 2. Aggregation: tính parent_rrf_score                              #
    # ------------------------------------------------------------------ #
    t1 = time.perf_counter()
    parent_candidates: List[Dict[str, Any]] = []

    for parent_id, group_hits in parent_groups.items():
        parent_doc = parents_by_id[parent_id]

        # Sắp xếp child theo multi_query_rank ASC (rank 1 tốt nhất)
        sorted_hits = sorted(
            group_hits,
            key=lambda h: (h.get("multi_query_rank") or 99999, h.get("child_id", ""))
        )

        all_child_ids = [h.get("child_id") or h.get("chunk_id") for h in sorted_hits]
        scoring_hits = sorted_hits[:parent_score_child_limit]
        scoring_child_ids = [h.get("child_id") or h.get("chunk_id") for h in scoring_hits]
        anchor_hit = sorted_hits[0]
        anchor_child_id = anchor_hit.get("child_id") or anchor_hit.get("chunk_id")
        best_child_rank = anchor_hit.get("multi_query_rank") or 99999

        # Tính parent_rrf_score chỉ từ scoring children
        score = 0.0
        for h in scoring_hits:
            mq_rank = h.get("multi_query_rank")
            if mq_rank is not None:
                score += 1.0 / (parent_rrf_k + float(mq_rank))

        # Tổng hợp support_query_ids từ tất cả child hits
        all_support_qids: Set[str] = set()
        for h in sorted_hits:
            for qid in h.get("support_query_ids", []):
                all_support_qids.add(qid)

        def _qid_sort_key_local(qid: str) -> int:
            m = re.match(r"Q(\d+)$", qid)
            return int(m.group(1)) if m else 9999

        support_query_ids_sorted = sorted(all_support_qids, key=_qid_sort_key_local)

        # Lấy metadata từ parent_doc (store là source of truth)
        struct_path = {
            "chapter": None,
            "article": parent_doc.get("article_key"),
            "clause": None,
            "point": None,
        }
        # Nếu children_by_id có structural_path cho anchor child, ưu tiên lấy
        anchor_child_record = children_by_id.get(anchor_child_id, {})
        if anchor_child_record.get("structural_path"):
            struct_path = anchor_child_record["structural_path"]

        parent_candidates.append({
            "parent_id": parent_id,
            "source": parent_doc["source"],
            "page_start": parent_doc["page_start"],
            "page_end": parent_doc["page_end"],
            "structural_path": struct_path,
            "text": parent_doc["text"],
            "char_count": parent_doc.get("char_count", len(parent_doc["text"])),
            "parent_rrf_score": round(score, 8),
            "parent_rank": 0,  # gán sau khi sort
            "anchor_child_id": anchor_child_id,
            "scoring_child_ids": scoring_child_ids,
            "supporting_child_ids": all_child_ids,
            "support_query_ids": support_query_ids_sorted,
            "support_query_count": len(support_query_ids_sorted),
            "best_child_rank": best_child_rank,
            "ambiguous": bool(parent_doc.get("ambiguous_child_count", 0) > 0),
            "warnings": list(parent_doc.get("warnings", [])),
        })

    # Sort: parent_rrf_score DESC, support_query_count DESC, best_child_rank ASC, parent_id ASC
    parent_candidates.sort(key=lambda p: (
        -p["parent_rrf_score"],
        -p["support_query_count"],
        p["best_child_rank"],
        p["parent_id"]
    ))

    # Gán parent_rank trước khi cắt
    for rank, p in enumerate(parent_candidates, start=1):
        p["parent_rank"] = rank

    # Áp candidate limit (trước context budget)
    total_parent_count = len(parent_candidates)
    dropped_by_candidate_limit = max(0, total_parent_count - parent_candidates_limit)
    parent_candidates_trimmed = parent_candidates[:parent_candidates_limit]

    aggregation_latency_ms = round((time.perf_counter() - t1) * 1000, 2)

    # ------------------------------------------------------------------ #
    # 3. Context Budget                                                   #
    # ------------------------------------------------------------------ #
    t2 = time.perf_counter()
    selected_parents: List[Dict[str, Any]] = []
    dropped_by_budget: List[str] = []
    total_chars = 0
    seen_parent_ids: Set[str] = set()
    first_parent_oversized = False

    for p in parent_candidates_trimmed:
        pid = p["parent_id"]
        if pid in seen_parent_ids:
            continue  # duplicate parent
        p_chars = p.get("char_count", len(p["text"]))

        if not selected_parents:
            # Parent đầu tiên: luôn giữ, dù có vượt budget
            selected_parents.append(p)
            seen_parent_ids.add(pid)
            total_chars += p_chars
            if p_chars > total_context_max_chars:
                first_parent_oversized = True
                p["warnings"] = list(p.get("warnings", [])) + [
                    f"oversized_first_parent: {p_chars} chars > total_context_max_chars {total_context_max_chars}"
                ]
        elif total_chars + p_chars <= total_context_max_chars:
            selected_parents.append(p)
            seen_parent_ids.add(pid)
            total_chars += p_chars
        else:
            dropped_by_budget.append(pid)

    budget_latency_ms = round((time.perf_counter() - t2) * 1000, 2)
    total_latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    # ------------------------------------------------------------------ #
    # 4. Trace                                                            #
    # ------------------------------------------------------------------ #
    child_chars_total = sum(
        len(children_by_id.get(h.get("child_id") or h.get("chunk_id", ""), {}).get("text", ""))
        for h in child_hits
        if (h.get("child_id") or h.get("chunk_id"))
    )
    parent_chars_total = total_chars
    expansion_factor = round(parent_chars_total / child_chars_total, 3) if child_chars_total else 0.0

    # Ambiguous/warning counts
    ambiguous_count = sum(1 for p in selected_parents if p.get("ambiguous"))
    warn_count = sum(len(p.get("warnings", [])) for p in selected_parents)

    trace = {
        "input_child_hit_count": len(child_hits),
        "unique_parent_count_before_limit": total_parent_count,
        "unique_parent_count_selected": len(selected_parents),
        "dropped_by_candidate_limit": dropped_by_candidate_limit,
        "dropped_by_budget": dropped_by_budget,
        "first_parent_oversized": first_parent_oversized,
        "total_context_chars": parent_chars_total,
        "total_child_chars": child_chars_total,
        "context_expansion_factor": expansion_factor,
        "ambiguous_parent_count": ambiguous_count,
        "warning_count": warn_count,
        "children_per_parent": {
            p["parent_id"]: len(p["supporting_child_ids"]) for p in selected_parents
        },
        "parent_score_components": {
            p["parent_id"]: {
                "parent_rrf_score": p["parent_rrf_score"],
                "scoring_child_count": len(p["scoring_child_ids"]),
                "scoring_child_ids": p["scoring_child_ids"],
                "best_child_rank": p["best_child_rank"],
            }
            for p in selected_parents
        },
        "mapping_table": mapping_table,
        "latency_ms": {
            "mapping": mapping_latency_ms,
            "aggregation": aggregation_latency_ms,
            "budget": budget_latency_ms,
            "total": total_latency_ms,
        },
    }

    return {
        "status": "ok",
        "parents": selected_parents,
        "total_context_chars": parent_chars_total,
        "trace": trace,
    }


# ==============================================================================
# 11. PLACEHOLDERS BƯỚC 07+ (CHƯA TRIỂN KHAI)
# ==============================================================================

def rerank_parents_cross_encoder(
    query: str,
    parents: List[Dict[str, Any]],
    reranker_instance: Any = None,
    min_score: float = 0.50,
) -> List[Dict[str, Any]]:
    """
    Rerank các Parent Candidate bằng Cross-Encoder sử dụng câu hỏi gốc Q0 và text của Parent.
    Hỗ trợ Dependency Injection qua reranker_instance cho offline testing.
    """
    if not parents:
        return []

    parent_list = [copy.deepcopy(p) for p in parents]

    scores = None
    if reranker_instance is not None:
        try:
            pairs = [[query, p.get("text", "")] for p in parent_list]
            if hasattr(reranker_instance, "predict"):
                raw = reranker_instance.predict(pairs)
                scores = [float(s) for s in raw]
            elif hasattr(reranker_instance, "compute_score"):
                raw = reranker_instance.compute_score(pairs)
                scores = [float(s) for s in raw]
            elif callable(reranker_instance):
                scores = [float(s) for s in reranker_instance(query, [p.get("text", "") for p in parent_list])]
        except Exception as exc:
            for p in parent_list:
                p["rerank_score"] = None
                p["rerank_rank"] = None
                p["accepted"] = True
                p["warnings"] = list(p.get("warnings", [])) + [f"reranker_error: {exc}"]
            return parent_list
    else:
        try:
            from advanced_rag import load_reranker_model, compute_rerank_scores
            model = load_reranker_model()
            pairs = [[query, p.get("text", "")] for p in parent_list]
            scores = compute_rerank_scores(model, pairs)
        except Exception:
            scores = None

    if scores is None:
        for idx, p in enumerate(parent_list, 1):
            p["rerank_score"] = None
            p["rerank_rank"] = idx
            p["accepted"] = True
            p["warnings"] = list(p.get("warnings", [])) + ["reranker_unavailable"]
        return parent_list

    for p, sc in zip(parent_list, scores):
        p["rerank_score"] = round(float(sc), 4)
        p["accepted"] = float(sc) >= min_score

    # Sắp xếp giảm dần theo rerank_score
    parent_list.sort(key=lambda x: (x.get("rerank_score") is not None, x.get("rerank_score") or -999.0), reverse=True)
    for rank_idx, p in enumerate(parent_list, 1):
        p["rerank_rank"] = rank_idx

    return parent_list


def query_hierarchical_rag(
    question: str,
    mode: str = "multi_parent",
    strategy: str = "hierarchical",
    top_k: Optional[int] = None,
    config: Optional[Dict[str, Any]] = None,
    retrieval_only: bool = False,
    generator_fn: Optional[Callable] = None,
    per_query_retriever: Optional[Callable] = None,
    reranker_instance: Optional[Any] = None,
    store: Optional[Dict[str, Any]] = None,
    custom_generation_fn: Optional[Callable] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Toàn bộ pipeline truy vấn Buổi 09 hỗ trợ 4 chế độ:
    - single_flat: Q0 -> Hybrid child retrieval -> Child chunks (không mở rộng parent)
    - multi_flat: Q0..Qn -> Fan-out Hybrid -> Cross-Query RRF -> Child chunks (không mở rộng parent)
    - single_parent: Q0 -> Hybrid child retrieval -> Parent aggregation -> Rerank parents
    - multi_parent: Q0..Qn -> Fan-out Hybrid -> Cross-Query RRF -> Parent aggregation -> Rerank parents
    """
    if mode not in ALLOWED_MODES:
        raise ValueError(f"Chế độ mode '{mode}' không hợp lệ. Chỉ chấp nhận: {sorted(list(ALLOWED_MODES))}")

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Câu hỏi không được để rỗng.")

    q_clean = question.strip()
    cfg = config or load_buoi_09_config()
    final_k = top_k if top_k is not None else cfg.get("final_parent_top_k", 3)
    min_rerank_score = cfg.get("rerank_min_score", 0.50)

    t0 = time.perf_counter()
    warnings: List[str] = []
    gen_call_count = 0
    emb_call_count = 0

    # 1. Query Generation
    t_exp_start = time.perf_counter()
    queries = []
    expansion_trace = {}
    if mode in ("multi_flat", "multi_parent"):
        exp_res = generate_query_variants(q_clean, config=cfg, query_generator_fn=generator_fn)
        queries = exp_res.get("queries", [])
        expansion_trace = exp_res
        if not exp_res.get("cache_hit"):
            gen_call_count += 1
        if exp_res.get("error"):
            warnings.append(f"query_expansion_warning: {exp_res['error']}")
    else:
        queries = [{"query_id": "Q0", "text": q_clean, "origin": "original", "focus": "câu hỏi gốc"}]
    lat_expansion = round((time.perf_counter() - t_exp_start) * 1000, 2)

    # 2. Fan-out retrieval & Cross-query fusion
    q_set = {"status": "ok", "queries": queries, "original_question": q_clean}
    ret_res = fan_out_multi_query_retrieval(
        query_set=q_set,
        config=cfg,
        hybrid_retriever_fn=per_query_retriever,
    )
    if ret_res.get("status") == "q0_retrieval_failed":
        return {
            "status": "q0_retrieval_failed",
            "mode": mode,
            "question": q_clean,
            "answer": "",
            "citations": [],
            "evidence": [],
            "parents": [],
            "fused_children": [],
            "per_query_results": ret_res.get("per_query_results", []),
            "generation_call_count": gen_call_count,
            "embedding_call_count": emb_call_count,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            "trace": ret_res.get("trace", {}),
            "warnings": [ret_res.get("error", "Q0 retrieval failed")],
        }

    fused_children = ret_res.get("fused_children", [])
    per_query_results = ret_res.get("per_query_results", [])
    emb_call_count += len([r for r in per_query_results if r.get("status") == "ok"])

    # 3. Branching theo Mode: Flat vs Parent
    is_parent_mode = "parent" in mode
    selected_parents: List[Dict[str, Any]] = []
    agg_trace: Dict[str, Any] = {}

    if is_parent_mode:
        reg = store if store is not None else load_hierarchy_store()
        agg_res = aggregate_parent_candidates(
            child_hits=fused_children,
            registry=reg,
            config=cfg,
        )
        parent_candidates = agg_res.get("parents", [])
        agg_trace = agg_res.get("trace", {})

        reranked_parents = rerank_parents_cross_encoder(
            query=q_clean,
            parents=parent_candidates,
            reranker_instance=reranker_instance,
            min_score=min_rerank_score,
        )
        accepted_parents = [p for p in reranked_parents if p.get("accepted", True)]
        selected_parents = accepted_parents[:final_k] if accepted_parents else (reranked_parents[:1] if reranked_parents else [])
        evidence = selected_parents
    else:
        evidence = fused_children[:final_k]
        selected_parents = []

    # 4. Status và Insufficient Evidence Gate
    pipeline_status = "ok"
    if not evidence:
        pipeline_status = "insufficient_evidence"
    elif is_parent_mode and all(not p.get("accepted", True) for p in selected_parents):
        pipeline_status = "insufficient_evidence"

    # 5. Answer Generation (Grounded) nếu không phải retrieval_only
    raw_answer = ""
    citations: List[Dict[str, Any]] = []

    if retrieval_only:
        pipeline_status = "retrieval_only"
    elif pipeline_status == "insufficient_evidence":
        raw_answer = "Không tìm thấy đủ thông tin liên quan trong tài liệu đã cung cấp."
    else:
        context_items = []
        for idx, ev in enumerate(evidence, 1):
            lbl = f"[E{idx}]"
            ev["evidence_id"] = lbl
            if is_parent_mode:
                text_block = ev.get("text", "")
                src = ev.get("source", "")
                title = ev.get("title", "")
                context_items.append(f"{lbl} Nguồn: {src} - {title}\n{text_block}")
            else:
                text_block = ev.get("text", "")
                src = ev.get("source", "")
                cid = ev.get("child_id") or ev.get("chunk_id", "")
                context_items.append(f"{lbl} Nguồn: {src} (chunk: {cid})\n{text_block}")

        joined_context = "\n\n---\n\n".join(context_items)
        prompt = (
            "Bạn là trợ lý pháp lý chuyên nghiệp. Hãy trả lời câu hỏi dựa trên các tài liệu được cung cấp dưới đây.\n"
            "Quy tắc:\n"
            "1. Chỉ sử dụng thông tin trong ngữ cảnh được cung cấp.\n"
            "2. Gắn nhãn trích dẫn [E1], [E2] sau mỗi khẳng định lấy từ tài liệu.\n"
            "3. Nếu không đủ thông tin, nói rõ: 'Không tìm thấy đủ thông tin liên quan trong tài liệu đã cung cấp.'\n\n"
            f"<<< DỮ LIỆU NGỮ CẢNH >>>\n{joined_context}\n<<< HẾT NGỮ CẢNH >>>\n\n"
            f"CÂU HỎI: {q_clean}\n\nCÂU TRẢ LỜI:"
        )

        gen_text = ""
        if custom_generation_fn is not None:
            gen_text = custom_generation_fn(prompt)
            answer_gen_call_count += 1
            pipeline_status = "answered"
        else:
            api_key = cfg.get("api_key")
            if api_key:
                try:
                    from google import genai
                    client = genai.Client(api_key=api_key)
                    resp = client.models.generate_content(
                        model=cfg.get("generation_model", "gemini-3.5-flash-lite"),
                        contents=prompt,
                    )
                    gen_text = resp.text.strip()
                    answer_gen_call_count += 1
                    pipeline_status = "answered"
                except Exception as exc:
                    warnings.append(f"generation_error: {exc}")
                    pipeline_status = "generation_error"
            else:
                pipeline_status = "retrieval_only"
                warnings.append("generation_unavailable_no_api_key")

        raw_answer = gen_text

        if is_parent_mode:
            for idx, p in enumerate(selected_parents, 1):
                c_ids = p.get("supporting_child_ids", p.get("anchor_child_ids", []))
                c_str = ", ".join(c_ids[:4])
                if len(c_ids) > 4:
                    c_str += f", ... (+{len(c_ids)-4})"
                title = (
                    p.get("structural_path", {}).get("article")
                    or p.get("title")
                    or (p.get("parent_id", "").split("::")[-2] if "::" in p.get("parent_id", "") else p.get("parent_id", ""))
                )
                ps = p.get("page_start", "?")
                pe = p.get("page_end", "?")
                display = f"[Nguồn: {p.get('source','')}, {title}, tr. {ps}-{pe}, các chunks kích hoạt: {c_str}]"
                citations.append({
                    "label": f"[E{idx}]",
                    "source": p.get("source", ""),
                    "title": title,
                    "page_start": ps,
                    "page_end": pe,
                    "supporting_child_ids": c_ids,
                    "display": display,
                })
        else:
            for idx, c in enumerate(evidence, 1):
                cid = c.get("child_id") or c.get("chunk_id", "")
                src = c.get("source", "")
                ps = c.get("page_start", "?")
                pe = c.get("page_end", "?")
                display = f"[Nguồn: {src}, tr. {ps}-{pe}, chunk: {cid}]"
                citations.append({
                    "label": f"[E{idx}]",
                    "source": src,
                    "chunk_id": cid,
                    "page_start": ps,
                    "page_end": pe,
                    "display": display,
                })

    total_ctx_chars = (
        sum(len(p.get("text", "")) for p in selected_parents)
        if is_parent_mode
        else sum(len(c.get("text", "")) for c in evidence)
    )
    child_chars = sum(len(c.get("text", "")) for c in fused_children)
    expansion_factor = round(total_ctx_chars / child_chars, 2) if (child_chars and is_parent_mode) else 1.0

    trace = {
        "mode": mode,
        "query_expansion": expansion_trace,
        "retrieval_trace": ret_res.get("trace", {}),
        "parent_aggregation_trace": agg_trace,
        "total_context_chars": total_ctx_chars,
        "context_expansion_factor": expansion_factor,
        "input_child_hit_count": len(fused_children),
        "latency_ms": {
            "query_expansion": lat_expansion,
            "retrieval": ret_res.get("trace", {}).get("total_retrieval_latency_ms", 0.0),
            "parent_aggregation": agg_trace.get("latency_ms", {}).get("total", 0.0),
            "total": round((time.perf_counter() - t0) * 1000, 2),
        },
    }

    return {
        "status": pipeline_status,
        "mode": mode,
        "question": q_clean,
        "answer": raw_answer,
        "citations": citations,
        "evidence": evidence,
        "parents": selected_parents,
        "fused_children": fused_children,
        "per_query_results": per_query_results,
        "generation_call_count": answer_gen_call_count,
        "query_generation_call_count": query_gen_call_count,
        "answer_generation_call_count": answer_gen_call_count,
        "embedding_call_count": emb_call_count,
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        "trace": trace,
        "warnings": warnings + ret_res.get("trace", {}).get("warnings", []),
    }


# ==============================================================================
# 10. CLI COMMANDS
# ==============================================================================

def cli_hierarchy_audit(args: argparse.Namespace):
    """Thực hiện audit dữ liệu cấu trúc cấp bậc (Read-only, không ghi store)."""
    cfg = load_buoi_09_config()
    print("=== AUDIT HIERARCHY DỮ LIỆU (READ-ONLY) ===")
    chunks, load_stats = load_and_order_hierarchical_chunks(input_path=args.input_dir)
    print(f"- Số files đọc: {load_stats['files_read']}")
    print(f"- Tổng số records: {load_stats['total_records']}")
    print(f"- Số nguồn tài liệu: {load_stats['sources_count']}")

    children, res_stats = resolve_child_hierarchy(chunks)
    print("\n--- KẾT QUẢ PHÂN GIẢI PHÂN CẤP (RESOLUTION) ---")
    for method, count in res_stats["methods"].items():
        pct = (count / len(children)) * 100 if children else 0
        print(f"  - {method:<20}: {count:>4} ({pct:>5.1f}%)")
    print(f"  - Tổng chunk ambiguous : {res_stats['ambiguous_children_count']:>4}")
    print(f"  - Tổng số warnings     : {res_stats['total_warnings']:>4}")

    if res_stats["warning_breakdown"]:
        print("\n--- PHÂN LOẠI CẢNH BÁO ---")
        for w_type, w_cnt in res_stats["warning_breakdown"].items():
            print(f"  - {w_type:<30}: {w_cnt:>3}")

    _, parents, p_stats = build_parent_documents(children, parent_max_chars=cfg["parent_max_chars"])
    print("\n--- THỐNG KÊ PARENT DOCUMENTS ---")
    print(f"- Giới hạn PARENT_MAX_CHARS: {cfg['parent_max_chars']} ký tự")
    print(f"- Tổng số Parents tạo ra  : {p_stats['total_parents']}")
    print(f"- Số Article bị chia nhỏ  : {p_stats['split_articles_count']}")
    print(f"- Số chunk đơn vượt giới hạn: {p_stats['oversized_single_children_count']}")
    print(f"- Phân bố độ dài Parent: Min={p_stats['parent_size_min']} | Median={p_stats['parent_size_median']} | P95={p_stats['parent_size_p95']} | Max={p_stats['parent_size_max']}")


def cli_build_hierarchy(args: argparse.Namespace):
    """Thực hiện build toàn bộ cấu trúc Hierarchy và lưu Atomic vào store."""
    cfg = load_buoi_09_config()
    print("=== BẮT ĐẦU BUILD HIERARCHY REGISTRY & PARENT STORE ===")
    chunks, load_stats = load_and_order_hierarchical_chunks(input_path=args.input_dir)
    children, res_stats = resolve_child_hierarchy(chunks)
    children, parents, p_stats = build_parent_documents(children, parent_max_chars=cfg["parent_max_chars"])

    now_iso = datetime.now(timezone.utc).isoformat()
    manifest = {
        "schema_version": "1.0",
        "strategy": "hierarchical",
        "build_timestamp": now_iso,
        "input_file_fingerprints": load_stats["file_fingerprints"],
        "config_identity": {
            "parent_max_chars": cfg["parent_max_chars"],
            "parent_candidates": cfg["parent_candidates"],
            "final_parent_top_k": cfg["final_parent_top_k"]
        },
        "counts": {
            "total_sources": load_stats["sources_count"],
            "total_children": len(children),
            "total_parents": len(parents),
            "ambiguous_children": res_stats["ambiguous_children_count"],
            "oversized_single_children": p_stats["oversized_single_children_count"]
        },
        "warning_counts": {
            "ambiguous_children": res_stats["ambiguous_children_count"],
            "oversized_single_children": p_stats["oversized_single_children_count"],
            "article_split_windows": p_stats["split_articles_count"],
            "total_warnings": res_stats["total_warnings"]
        }
    }

    res = save_hierarchy_store(
        children=children,
        parents=parents,
        manifest=manifest,
        storage_dir=args.storage_dir
    )
    print(f"Build hoàn tất! Trạng thái: {res['status']}")
    print(f"- Storage: {res['storage_dir']}")
    print(f"- Tệp đã lưu: {res['files_saved']}")
    print(f"- Tổng children: {len(children)} | Tổng parents: {len(parents)} | Warnings: {manifest['warning_counts']['total_warnings']}")


def cli_hierarchy_status(args: argparse.Namespace):
    """Xem trạng thái Hierarchy Store (Read-only tuyệt đối)."""
    st = get_hierarchy_status(storage_dir=args.storage_dir)
    print("=== TRẠNG THÁI HIERARCHY STORE (READ-ONLY) ===")
    print(f"- Thư mục lưu trữ: {st['storage_dir']}")
    print(f"- Đã khởi tạo (is_built): {'Có' if st['is_built'] else 'Chưa'}")
    if st["is_built"]:
        print(f"- Build Timestamp: {st['build_timestamp']}")
        print(f"- Schema Version: {st['schema_version']}")
        print(f"- Strategy: {st['strategy']}")
        print(f"- Số Child Chunks: {st['total_children']}")
        print(f"- Số Parent Documents: {st['total_parents']}")
        print(f"- Số Child Ambiguous: {st['ambiguous_children']}")
        print(f"- Tổng Warnings: {st['total_warnings']}")
    else:
        print(f"- Lý do: {st.get('reason')}")


def cli_multi_child(args: argparse.Namespace):
    """CLI lệnh multi-child: fan-out retrieval + cross-query RRF, hiển thị bảng kết quả."""
    cfg = load_buoi_09_config()
    print("=== MULTI-CHILD FAN-OUT RETRIEVAL (BUỔI 09) ===")
    print(f"Câu hỏi: '{args.question}'")
    print()

    # Bước 1: Multi-Query Expansion
    expansion_result = generate_query_variants(question=args.question, config=cfg)
    queries = expansion_result.get("queries", [])

    print(f"--- Query Expansion (status: {expansion_result['status']}) ---")
    for q in queries:
        print(f"  [{q['query_id']}] ({q['origin']}) {q['text']}")
    print()

    # Bước 2: Fan-out retrieval (sẽ dùng real retriever nếu có storage)
    result = fan_out_multi_query_retrieval(
        query_set=expansion_result,
        config=cfg,
    )

    status = result.get("status", "unknown")
    print(f"--- Kết quả Fan-out (status: {status}) ---")
    if status in ("q0_retrieval_failed", "metadata_mismatch_error"):
        print(f"LỖI: {result.get('error')}")
        return

    if status == "multi_query_partial":
        print("WARNING: Một số generated query gặp lỗi retrieval. Kết quả có thể không đầy đủ.")

    # Bảng trace per-query
    trace = result.get("trace", {})
    per_q = trace.get("per_query_summary", [])
    if per_q:
        print("\n--- PER-QUERY RETRIEVAL TRACE ---")
        header = f"{'QID':<5} {'Origin':<12} {'Status':<8} {'Results':>8} {'Latency(ms)':>12}"
        print(header)
        print("-" * len(header))
        for pq in per_q:
            err = f" [{pq['error_msg'][:40]}]" if pq.get("error_msg") else ""
            print(f"{pq['query_id']:<5} {pq['origin']:<12} {pq['status']:<8} "
                  f"{pq['result_count']:>8} {pq['latency_ms']:>12.1f}{err}")

    # Bảng child results
    fused = result.get("fused_children", [])
    total = len(fused)
    overlap_dist = trace.get("overlap_distribution", {})
    print(f"\n--- CHILD HITS (union={total}) | Overlap: {dict(sorted(overlap_dist.items()))} ---")

    if fused:
        col_qids = sorted({qid for item in fused for qid in item.get("support_query_ids", [])})
        header2 = f"{'Rank':>4} {'child_id':<40} {'MQ-RRF':>10} {'Sup':>4}  " + \
                  "  ".join(f"{q:<5}" for q in col_qids)
        print(header2)
        print("-" * len(header2))
        for item in fused:
            ranks_str = "  ".join(
                f"{item['per_query_ranks'].get(q, '-')!s:<5}" for q in col_qids
            )
            print(
                f"{item['multi_query_rank']:>4} "
                f"{item['child_id']:<40} "
                f"{item['multi_query_rrf_score']:>10.6f} "
                f"{item['support_query_count']:>4}  "
                + ranks_str
            )
    else:
        print("(Không có kết quả child nào.)")

    fus_lat = trace.get("fusion_latency_ms")
    ret_lat = trace.get("total_retrieval_latency_ms", 0)
    print(f"\nRetrieval latency tổng: {ret_lat:.1f} ms | Fusion latency: {fus_lat} ms")


def cli_parent_retrieve(args: argparse.Namespace):
    """CLI lệnh parent-retrieve: fan-out retrieval + child→parent mapping + context budget."""
    cfg = load_buoi_09_config()
    mode = getattr(args, "mode", "multi_parent")
    print(f"=== PARENT RETRIEVE (mode={mode}) - BUỔI 09 ===")
    print(f"Câu hỏi: '{args.question}'")
    print()

    # --- Kiểm tra hierarchy store trước bất kỳ retrieval nào ---
    hs = get_hierarchy_status()
    if not hs.get("is_built"):
        print(f"LỖI: Hierarchy store chưa sẵn sàng. Lý do: {hs.get('reason')}")
        print("Điều kiện tiên quyết: chạy 'build-hierarchy' trước.")
        return

    try:
        registry = load_hierarchy_store()
    except RuntimeError as e:
        print(f"LỖI tải hierarchy store: {e}")
        return

    print(f"--- Registry đã nạp: {registry['total_children']} children, "
          f"{registry['total_parents']} parents ---")

    # --- Query expansion ---
    if mode == "single_parent":
        # single_parent: chỉ dùng Q0
        q0_clean = normalize_query_text(args.question)
        expansion_result = {
            "original_question": q0_clean,
            "status": "ready",
            "queries": [
                {"query_id": "Q0", "origin": "original", "text": q0_clean, "focus": "original_intent"}
            ]
        }
    else:
        expansion_result = generate_query_variants(question=args.question, config=cfg)

    queries = expansion_result.get("queries", [])
    print(f"--- Query Expansion (status: {expansion_result['status']}, {len(queries)} queries) ---")
    for q in queries:
        print(f"  [{q['query_id']}] ({q['origin']}) {q['text']}")
    print()

    # --- Fan-out retrieval ---
    fanout_result = fan_out_multi_query_retrieval(
        query_set=expansion_result,
        config=cfg,
    )
    fanout_status = fanout_result.get("status")
    print(f"--- Fan-out (status: {fanout_status}) ---")
    if fanout_status in ("q0_retrieval_failed", "metadata_mismatch_error"):
        print(f"LỖI: {fanout_result.get('error')}")
        return
    if fanout_status == "multi_query_partial":
        print("WARNING: Một số generated query lỗi retrieval.")

    child_hits = fanout_result.get("fused_children", [])
    print(f"Child hits fused: {len(child_hits)}")
    print()

    # --- Parent aggregation ---
    try:
        agg_result = aggregate_parent_candidates(
            child_hits=child_hits,
            registry=registry,
            config=cfg,
        )
    except (KeyError, ValueError) as e:
        print(f"LỖI aggregation: {e}")
        return

    parents = agg_result.get("parents", [])
    trace = agg_result.get("trace", {})

    print(f"--- Tổng hợp Parents ---")
    print(f"- Input child hits: {trace.get('input_child_hit_count')}")
    print(f"- Unique parents (trước limit): {trace.get('unique_parent_count_before_limit')}")
    print(f"- Parents được chọn (sau budget): {trace.get('unique_parent_count_selected')}")
    print(f"- Bị loại bởi candidate limit: {trace.get('dropped_by_candidate_limit')}")
    print(f"- Bị loại bởi context budget: {len(trace.get('dropped_by_budget', []))}")
    print(f"- Tổng context chars: {trace.get('total_context_chars')}")
    print(f"- Context expansion factor: {trace.get('context_expansion_factor'):.2f}x")
    if trace.get("first_parent_oversized"):
        print("  WARNING: Parent đầu tiên vượt TOTAL_CONTEXT_MAX_CHARS.")
    print()

    # --- In cây mapping ---
    print("--- MAPPING TREE (Parent → Supporting Children → Queries) ---")
    for p in parents:
        score_info = f"score={p['parent_rrf_score']:.6f} | rank={p['parent_rank']}"
        print(f"\n┌ Parent [{p['parent_rank']}] {p['parent_id']}")
        print(f"| {score_info}")
        print(f"| Source: {p['source']} | Pages: {p['page_start']}-{p['page_end']}")
        print(f"| Queries: {p['support_query_ids']} | Children: {len(p['supporting_child_ids'])}")
        print(f"| Scoring children (top {len(p['scoring_child_ids'])}): {p['scoring_child_ids']}")
        if p.get("warnings"):
            print(f"| Warnings: {p['warnings']}")

        # In danh sách supporting children và query rank
        for cid in p["supporting_child_ids"]:
            # Tìm hit tương ứng
            matching_hit = next(
                (h for h in child_hits
                 if (h.get("child_id") or h.get("chunk_id")) == cid),
                None
            )
            if matching_hit:
                q_ids = matching_hit.get("support_query_ids", [])
                mq_rank = matching_hit.get("multi_query_rank", "?")
                is_scoring = cid in p["scoring_child_ids"]
                marker = "[SCORING]" if is_scoring else "[support]"
                print(f"\u2514── {marker} {cid} | MQ-rank={mq_rank} | queries={q_ids}")

    print(f"\nLatency: mapping={trace['latency_ms']['mapping']}ms, "
          f"aggregation={trace['latency_ms']['aggregation']}ms, "
          f"budget={trace['latency_ms']['budget']}ms, "
          f"total={trace['latency_ms']['total']}ms")


def cli_expand_query(args: argparse.Namespace):
    """Thực hiện mở rộng câu hỏi (Multi-Query Expansion) từ CLI."""
    cfg = load_buoi_09_config()
    print("=== MULTI-QUERY EXPANSION (BUỔI 09) ===")
    res = generate_query_variants(question=args.question, config=cfg)
    print(f"- Câu hỏi gốc: '{res['original_question']}'")
    print(f"- Trạng thái: {res['status']}")
    print(f"- Mô hình: {res['model']}")
    print(f"- Latency: {res['generation_latency_ms']} ms")
    print(f"- Cache hit: {res['cache_hit']}")
    print(f"- Bỏ trùng/lỗi: {res['dropped_duplicate_count']}")
    if res.get("error"):
        print(f"- Lỗi: {res['error']}")

    print("\n--- DANH SÁCH BIẾN THỂ TRUY VẤN (QUERY SET) ---")
    for q in res["queries"]:
        print(f"[{q['query_id']}] ({q['origin']} | {q['focus']})")
        print(f"     Text: {q['text']}")


def main():
    parser = argparse.ArgumentParser(
        description="Hierarchical & Multi-Query Advanced RAG - Buổi 09",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Lệnh thực hiện")

    # Command: hierarchy-audit
    audit_parser = subparsers.add_parser("hierarchy-audit", help="Kiểm tra phân tích cấu trúc hierarchy (Read-only)")
    audit_parser.add_argument("--input-dir", type=str, default=None, help="Đường dẫn thư mục chunks")

    # Command: build-hierarchy
    build_parser = subparsers.add_parser("build-hierarchy", help="Xây dựng registry và parent store (Atomic write)")
    build_parser.add_argument("--input-dir", type=str, default=None, help="Đường dẫn thư mục chunks")
    build_parser.add_argument("--storage-dir", type=str, default=None, help="Đường dẫn thư mục lưu trữ storage")

    # Command: hierarchy-status
    status_parser = subparsers.add_parser("hierarchy-status", help="Xem trạng thái registry hiện tại (Read-only)")
    status_parser.add_argument("--storage-dir", type=str, default=None, help="Đường dẫn thư mục lưu trữ storage")

    # Command: expand-query
    expand_parser = subparsers.add_parser("expand-query", help="Mở rộng câu hỏi thành tập Query Variants đa chiều")
    expand_parser.add_argument("--question", type=str, required=True, help="Câu hỏi pháp lý cần mở rộng")

    # Command: multi-child (Bước 05)
    mc_parser = subparsers.add_parser(
        "multi-child",
        help="Fan-out multi-query retrieval + Cross-Query RRF, hiển thị bảng child hits"
    )
    mc_parser.add_argument("--question", type=str, required=True, help="Câu hỏi pháp lý cần truy vấn")

    # Command: parent-retrieve (Bước 06)
    pr_parser = subparsers.add_parser(
        "parent-retrieve",
        help="Fan-out retrieval + child→parent mapping + context budget"
    )
    pr_parser.add_argument("--question", type=str, required=True, help="Câu hỏi pháp lý")
    pr_parser.add_argument(
        "--mode", type=str, default="multi_parent",
        choices=["single_parent", "multi_parent"],
        help="single_parent (chỉ Q0) hoặc multi_parent (Q0+variants). Mặc định: multi_parent."
    )

    args = parser.parse_args()

    if args.command == "hierarchy-audit":
        cli_hierarchy_audit(args)
    elif args.command == "build-hierarchy":
        cli_build_hierarchy(args)
    elif args.command == "hierarchy-status":
        cli_hierarchy_status(args)
    elif args.command == "expand-query":
        cli_expand_query(args)
    elif args.command == "multi-child":
        cli_multi_child(args)
    elif args.command == "parent-retrieve":
        cli_parent_retrieve(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
