"""
Ứng dụng Web Streamlit — Buổi 09:
RAG Foundation — Multi-query & Parent–Child Retrieval.

Pipeline: Query fan-out → Hybrid per query → Cross-query RRF → Parent expansion → Parent rerank

Năm tab chính:
1. Ask Advanced RAG       — Hỏi đáp multi-parent với citations
2. Query Fan-out          — Hiển thị Q0..Qn, ma trận query–child
3. Parent–Child Explorer  — Cây parent → anchor children, rank movement
4. Mode Comparison        — Đối chiếu 4 chế độ retrieval-only
5. Evaluation             — Đọc báo cáo đánh giá sẵn có

Thiết kế hoàn toàn khác Buổi 08:
- Multi-query fan-out visible ngay Tab 2
- Query–child matrix
- Parent–child tree với rank before/after rerank
- Context expansion factor hiển thị rõ
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

# ─── Path setup ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = (BASE_DIR / "reports").resolve()
EVAL_FILE = (BASE_DIR / "eval" / "questions.json").resolve()

# ─── Safe import of backend modules ──────────────────────────────────────────
import sys
sys.path.insert(0, str(BASE_DIR))

try:
    from hierarchical_rag import (
        load_buoi_09_config,
        get_hierarchy_status,
        generate_query_variants,
        fan_out_multi_query_retrieval,
        aggregate_parent_candidates,
        load_hierarchy_store,
        query_hierarchical_rag,
    )
    _HIER_AVAILABLE = True
    _HIER_ERR_MSG = ""
except Exception as _hier_err:
    _HIER_AVAILABLE = False
    _HIER_ERR_MSG = str(_hier_err)

try:
    from advanced_rag import (
        load_advanced_config,
        get_advanced_status,
        query_advanced_rag,
        ALLOWED_STRATEGIES,
        DEFAULT_INPUT_DIR,
    )
    _ADV_AVAILABLE = True
    _ADV_ERR_MSG = ""
except Exception as _adv_err:
    _ADV_AVAILABLE = False
    _ADV_ERR_MSG = str(_adv_err)

# Ưu tiên pipeline Buổi 09
if _HIER_AVAILABLE and "query_hierarchical_rag" in globals():
    query_advanced_rag = query_hierarchical_rag
    _ADV_AVAILABLE = True


# ─── Constants ────────────────────────────────────────────────────────────────
FOUR_MODES: List[str] = ["single_flat", "multi_flat", "single_parent", "multi_parent"]
STRATEGY_FIXED = "hierarchical"

MODE_LABELS: Dict[str, str] = {
    "single_flat":   "Single-Flat",
    "multi_flat":    "Multi-Flat",
    "single_parent": "Single-Parent",
    "multi_parent":  "Multi-Parent (Buoi09) \u2605",
}

QUERY_TYPE_COLORS: Dict[str, str] = {
    "original":          "#f59e0b",
    "paraphrase":        "#6366f1",
    "exact_legal_terms": "#10b981",
    "legal_focus":       "#10b981",
    "terminology":       "#0ea5e9",
    "missing_aspect":    "#ec4899",
}

ERROR_GUIDANCE: Dict[str, str] = {
    "hierarchy_not_ready":
        "\U0001f3d7\ufe0f **Hierarchy store chua san sang.** Chay lenh CLI: "
        "`python -m hierarchical_rag build` de build hierarchy store.",
    "collection_not_ready":
        "\U0001f5c4\ufe0f **ChromaDB collection chua duoc index.** Chay `python -m rag index`.",
    "query_generation_unavailable":
        "\U0001f511 **Khong the sinh query variants.** Kiem tra GEMINI_API_KEY trong `.env`.",
    "multi_query_partial":
        "\u26a0\ufe0f **Mot so query variant that bai** (Q0 van OK). Ket qua tu cac query thanh cong.",
    "reranker_unavailable":
        "\U0001f916 **Mo hinh Reranker khong kha dung.** Can Internet de tai `BAAI/bge-reranker-v2-m3`.",
    "insufficient_evidence":
        "\U0001f4ed **Khong tim thay bang chung du diem.** Thu ha `RERANK_MIN_SCORE` hoac tang `PARENT_CANDIDATES`.",
    "generation_error":
        "\U0001f4a5 **Loi khi goi LLM generation.** Kiem tra GEMINI_API_KEY va quota.",
}

SAMPLE_QUESTIONS = [
    "Kh\u00e1ch h\u00e0ng c\u1ea7n \u0111\u00e1p \u1ee9ng nh\u1eefng \u0111i\u1ec1u ki\u1ec7n g\u00ec \u0111\u1ec3 \u0111\u01b0\u1ee3c t\u1ed5 ch\u1ee9c t\u00edn d\u1ee5ng xem x\u00e9t cho vay v\u1ed1n?",
    "Cho vay theo quy \u0111\u1ecbnh c\u1ee7a Ng\u00e2n h\u00e0ng Nh\u00e0 n\u01b0\u1edbc \u0111\u01b0\u1ee3c \u0111\u1ecbnh ngh\u0129a nh\u01b0 th\u1ebf n\u00e0o?",
    "Th\u1eddi h\u1ea1n cho vay gi\u1eefa t\u1ed5 ch\u1ee9c t\u00edn d\u1ee5ng v\u00e0 kh\u00e1ch h\u00e0ng \u0111\u01b0\u1ee3c x\u00e1c \u0111\u1ecbnh d\u1ef1a tr\u00ean nh\u1eefng c\u0103n c\u1ee9 n\u00e0o?",
    "T\u1ed5 ch\u1ee9c t\u00edn d\u1ee5ng xem x\u00e9t c\u01a1 c\u1ea5u l\u1ea1i th\u1eddi h\u1ea1n tr\u1ea3 n\u1ee3 theo nh\u1eefng \u0111i\u1ec1u ki\u1ec7n n\u00e0o?",
    "Tr\u01b0\u1eddng h\u1ee3p n\u00e0o \u00e1p d\u1ee5ng m\u1ee9c tr\u1ea7n l\u00e3i su\u1ea5t cho vay ng\u1eafn h\u1ea1n do Th\u1ed1ng \u0111\u1ed1c NHNN quy \u0111\u1ecbnh?",
]


# ═════════════════════════════════════════════════════════════════════════════
# CSS
# ═════════════════════════════════════════════════════════════════════════════

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.b09-hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f3460 100%);
    border-radius: 14px; padding: 28px 32px 22px; margin-bottom: 24px;
}
.b09-hero h1 { color: #f8fafc; font-size: 1.85rem; font-weight: 800; margin: 0 0 6px; line-height: 1.2; }
.b09-pipeline {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(99,102,241,0.25); border: 1px solid rgba(99,102,241,0.5);
    border-radius: 20px; padding: 4px 14px; font-size: 0.78rem;
    color: #a5b4fc; font-weight: 500; flex-wrap: wrap;
}
.b09-step { color: #c7d2fe; }
.b09-arrow { color: #6366f1; font-weight: 700; }

.qcard { border-radius: 10px; padding: 14px 16px; margin-bottom: 10px; border: 1.5px solid transparent; }
.qcard-q0 { background: linear-gradient(135deg, #fef3c7, #fde68a); border-color: #f59e0b; }
.qcard-gen { background: linear-gradient(135deg, #ede9fe, #ddd6fe); border-color: #7c3aed; }
.qcard-label { font-weight: 700; font-size: 0.8rem; letter-spacing: 0.05em; text-transform: uppercase; }
.qcard-text { font-size: 0.95rem; margin-top: 4px; color: #1e293b; }
.qcard-meta { font-size: 0.75rem; color: #64748b; margin-top: 6px; }

.parent-card { border-radius: 10px; border: 2px solid #e2e8f0; margin-bottom: 16px; overflow: hidden; }
.parent-header {
    background: linear-gradient(90deg, #1e293b, #334155); color: #f1f5f9;
    padding: 12px 16px; font-weight: 700; font-size: 0.95rem;
    display: flex; justify-content: space-between; align-items: center;
}
.parent-body { padding: 14px 16px; background: #f8fafc; }
.child-pill {
    display: inline-block; background: #e0e7ff; color: #3730a3;
    border-radius: 6px; padding: 2px 8px; font-size: 0.75rem; font-weight: 600; margin: 2px 3px;
}
.ambiguous-badge {
    background: #fee2e2; color: #991b1b; border-radius: 6px;
    padding: 2px 8px; font-size: 0.75rem; font-weight: 700; margin-left: 6px;
}
.rank-up   { color: #10b981; font-weight: 700; }
.rank-same { color: #94a3b8; font-weight: 700; }
.rank-down { color: #ef4444; font-weight: 700; }

.ev-card { border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px; margin-bottom: 12px; background: #fff; }
.ev-card.accepted { border-left: 5px solid #10b981; }
.ev-card.rejected { border-left: 5px solid #ef4444; background: #fff5f5; }

.mode-badge { display: inline-block; border-radius: 6px; padding: 3px 10px; font-size: 0.78rem; font-weight: 700; color: #fff; }
.mode-sf { background: #6366f1; }
.mode-mf { background: #0ea5e9; }
.mode-sp { background: #10b981; }
.mode-mp { background: #f59e0b; }

.expansion-box {
    background: linear-gradient(135deg, #0f172a, #1e293b); color: #a5b4fc;
    border-radius: 12px; padding: 18px 22px; text-align: center;
    font-size: 2.4rem; font-weight: 800;
}
.expansion-label { font-size: 0.75rem; color: #64748b; margin-top: 4px; font-weight: 500; }
</style>
"""


# ═════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ═════════════════════════════════════════════════════════════════════════════

def _ss(key: str, default=None):
    return st.session_state.get(key, default)


def _set(key: str, value):
    st.session_state[key] = value


# ═════════════════════════════════════════════════════════════════════════════
# CACHED LOADERS
# ═════════════════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner=False)
def _cfg() -> Dict[str, Any]:
    """Config sans API key."""
    if not _HIER_AVAILABLE:
        return {}
    try:
        c = load_buoi_09_config()
        return {k: v for k, v in c.items() if k != "api_key"}
    except Exception:
        return {}


@st.cache_data(show_spinner=False, ttl=30)
def _h_status() -> Dict[str, Any]:
    if not _HIER_AVAILABLE:
        return {"is_built": False, "reason": "hierarchical_rag unavailable"}
    return get_hierarchy_status()


@st.cache_data(show_spinner=False, ttl=30)
def _adv_status(strategy: str) -> Dict[str, Any]:
    if not _ADV_AVAILABLE:
        return {}
    try:
        return get_advanced_status(strategy=strategy)
    except Exception as e:
        return {"error": str(e)}


# ═════════════════════════════════════════════════════════════════════════════
# PURE HELPER FUNCTIONS  (unit-testable, no Streamlit)
# ═════════════════════════════════════════════════════════════════════════════

def build_query_child_matrix(
    per_query_results: List[Dict[str, Any]],
    fused_children: List[Dict[str, Any]],
) -> pd.DataFrame:
    """
    Ma tran hang = child chunk, cot = Q0..Qn.
    O = rank cua chunk trong query do, hoac None.
    """
    query_ids = [r["query_id"] for r in per_query_results]
    qid_to_ranks: Dict[str, Dict[str, int]] = {qid: {} for qid in query_ids}
    for qr in per_query_results:
        qid = qr["query_id"]
        for rank_idx, c in enumerate(qr.get("candidates", []), start=1):
            cid = c.get("child_id") or c.get("chunk_id", "")
            if cid:
                qid_to_ranks[qid][cid] = rank_idx

    seen: set = set()
    ordered_ids: List[str] = []
    for c in fused_children:
        cid = c.get("child_id") or c.get("chunk_id", "")
        if cid and cid not in seen:
            ordered_ids.append(cid)
            seen.add(cid)

    rows = []
    fused_by_id = {
        (c.get("child_id") or c.get("chunk_id", "")): c
        for c in fused_children
    }
    for mq_rank, cid in enumerate(ordered_ids, start=1):
        child = fused_by_id.get(cid, {})
        row: Dict[str, Any] = {
            "Child ID": cid,
            "MQ Rank": mq_rank,
            "Support Q#": len(child.get("support_query_ids", [])),
            "MQ-RRF Score": round(child.get("cross_query_rrf_score", 0.0), 6),
        }
        for qid in query_ids:
            rank = qid_to_ranks[qid].get(cid)
            row[qid] = rank  # None means absent
        rows.append(row)

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def build_mode_comparison_row(mode: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tao mot hang cho bang Mode Comparison.
    Unit-testable — no side effects.
    """
    parents = result.get("parents", [])
    children = result.get("fused_children", [])
    trace = result.get("trace", {})
    is_parent_mode = "parent" in mode

    if is_parent_mode:
        evidence_ids = [p.get("parent_id", "") for p in parents]
        sources = list({p.get("source", "") for p in parents})
        ctx_chars = trace.get("total_context_chars",
                               sum(len(p.get("text", "")) for p in parents))
        child_count = trace.get("input_child_hit_count", len(children))
        parent_count = len(parents)
        expansion_factor = trace.get("context_expansion_factor", 0.0)
        unit_type = "parent"
    else:
        evidence_ids = [c.get("child_id") or c.get("chunk_id", "") for c in children]
        sources = list({c.get("source", "") for c in children})
        ctx_chars = sum(len(c.get("text", "")) for c in children)
        child_count = len(children)
        parent_count = 0
        expansion_factor = 1.0
        unit_type = "child"

    articles = list({s.replace(".pdf", "").replace("_", " ") for s in sources if s})

    return {
        "Mode": mode,
        "Status": result.get("status", "error"),
        "Unit Type": unit_type,
        "Evidence IDs": evidence_ids,
        "Evidence Count": len(evidence_ids),
        "Sources": sources,
        "Articles": articles,
        "Unique Sources": len(sources),
        "Unique Articles": len(articles),
        "Child Count": child_count,
        "Parent Count": parent_count,
        "Context Chars": ctx_chars,
        "Expansion Factor": round(expansion_factor, 2),
        "Latency (ms)": result.get("latency_ms", 0.0),
        "Generation Calls": result.get("generation_call_count", 0),
        "Embedding Calls": result.get("embedding_call_count", 0),
        "Warnings": result.get("warnings", []),
    }


def build_parent_tree_data(
    parents: List[Dict[str, Any]],
    children_by_id: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Xay dung du lieu cay parent-child.
    Unit-testable — no side effects.
    """
    children_by_id = children_by_id or {}
    tree: List[Dict[str, Any]] = []
    for p in parents:
        parent_rank = p.get("parent_rank", "?")
        rerank_rank = p.get("rerank_rank")
        rank_change = None
        if rerank_rank is not None and isinstance(parent_rank, int):
            rank_change = parent_rank - rerank_rank

        struct = p.get("structural_path", {})
        supporting_ids = p.get("supporting_child_ids",
                                p.get("anchor_child_ids", []))
        supporting_children = []
        for cid in supporting_ids:
            crec = children_by_id.get(cid, {})
            supporting_children.append({
                "child_id": cid,
                "anchor_snippet": crec.get("text", "")[:150],
                "support_queries": [],
            })

        tree.append({
            "parent_id": p.get("parent_id", ""),
            "source": p.get("source", ""),
            "title": (struct.get("article")
                      or p.get("parent_id", "").split("::")[-1]),
            "chapter": struct.get("chapter"),
            "article": struct.get("article"),
            "page_start": p.get("page_start"),
            "page_end": p.get("page_end"),
            "parent_rank": parent_rank,
            "rerank_rank": rerank_rank,
            "rank_change": rank_change,
            "parent_rrf_score": p.get("parent_rrf_score",
                                       p.get("aggregated_score", 0.0)),
            "rerank_score": p.get("rerank_score"),
            "accepted": p.get("accepted", True),
            "ambiguous": p.get("ambiguous", False),
            "warnings": p.get("warnings", []),
            "support_query_ids": p.get("support_query_ids", []),
            "support_query_count": p.get("support_query_count", 0),
            "supporting_children": supporting_children,
            "char_count": p.get("char_count", len(p.get("text", ""))),
            "text": p.get("text", ""),
        })
    return tree


def format_citation(parent: Dict[str, Any], evidence_index: int) -> Dict[str, str]:
    """
    Format citation theo contract Buoi 09.
    [Nguon: <source>, <title>, tr. <page_start>-<page_end>, cac chunks kich hoat: <ids>]
    """
    label = f"[E{evidence_index}]"
    source = parent.get("source", "")
    title = (parent.get("title")
             or parent.get("parent_id", "").split("::")[-1])
    p_start = parent.get("page_start", "?")
    p_end = parent.get("page_end", "?")
    child_ids: List[str] = parent.get("supporting_child_ids",
                                       parent.get("anchor_child_ids", []))
    chunks_str = ", ".join(str(c) for c in child_ids[:4])
    if len(child_ids) > 4:
        chunks_str += f", ... (+{len(child_ids)-4})"
    citation_text = (
        f"[Nguon: {source}, {title}, "
        f"tr. {p_start}-{p_end}, cac chunks kich hoat: {chunks_str}]"
    )
    return {"label": label, "citation": citation_text,
            "source": source, "title": title,
            "page_start": p_start, "page_end": p_end}


def map_error_status(status: str) -> Dict[str, str]:
    """
    Map trang thai -> {icon, title, guidance, severity}.
    Khong dump stack trace.
    """
    _map: Dict[str, tuple] = {
        "answered":                    ("\u2705", "Tra loi thanh cong (Grounded Answer)", "", "success"),
        "insufficient_evidence":       ("\U0001f4ed", "Khong du bang chung",
                                        ERROR_GUIDANCE["insufficient_evidence"], "warning"),
        "retrieval_only":              ("\U0001f50d", "Chi truy xuat, chua sinh cau tra loi", "", "info"),
        "reranker_unavailable":        ("\U0001f916", "Reranker khong kha dung",
                                        ERROR_GUIDANCE["reranker_unavailable"], "error"),
        "generation_error":            ("\U0001f4a5", "Loi sinh cau tra loi",
                                        ERROR_GUIDANCE["generation_error"], "error"),
        "hierarchy_not_ready":         ("\U0001f3d7\ufe0f", "Hierarchy store chua san sang",
                                        ERROR_GUIDANCE["hierarchy_not_ready"], "error"),
        "collection_not_ready":        ("\U0001f5c4\ufe0f", "Collection chua index",
                                        ERROR_GUIDANCE["collection_not_ready"], "error"),
        "query_generation_unavailable": ("\U0001f511", "Khong the sinh query variants",
                                         ERROR_GUIDANCE["query_generation_unavailable"], "warning"),
        "multi_query_partial":         ("\u26a0\ufe0f", "Multi-query mot phan thanh cong",
                                        ERROR_GUIDANCE["multi_query_partial"], "warning"),
        "q0_retrieval_failed":         ("\u274c", "Truy xuat Q0 that bai",
                                        ERROR_GUIDANCE["collection_not_ready"], "error"),
    }
    icon, title, guidance, severity = _map.get(status, ("\u2139\ufe0f", status, "", "info"))
    return {"icon": icon, "title": title, "guidance": guidance, "severity": severity}


def _rank_badge_html(parent_rank, rerank_rank, rank_change) -> str:
    if rerank_rank is None:
        return f"Parent rank: <b>#{parent_rank}</b> (chua rerank)"
    if rank_change is None:
        chg = ""
        cls = "rank-same"
    elif rank_change > 0:
        chg = f"\u25b2 +{rank_change}"
        cls = "rank-up"
    elif rank_change < 0:
        chg = f"\u25bc {rank_change}"
        cls = "rank-down"
    else:
        chg = "\u2192 ="
        cls = "rank-same"
    return (
        f"Parent rank: <b>#{parent_rank}</b> \u2192 Rerank rank: <b>#{rerank_rank}</b> "
        f'<span class="{cls}">{chg}</span>'
    )


# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═════════════════════════════════════════════════════════════════════════════

def render_sidebar() -> Dict[str, Any]:
    """Render sidebar. Khong build/index/download."""
    with st.sidebar:
        st.markdown("## \u2699\ufe0f C\u1ea5u H\u00ecnh Bu\u1ed5i 09")

        selected_mode = st.selectbox(
            "\U0001f500 Ch\u1ebf \u0111\u1ed9 m\u1eb7c \u0111\u1ecbnh (Mode):",
            options=FOUR_MODES,
            index=FOUR_MODES.index("multi_parent"),
            format_func=lambda m: MODE_LABELS[m],
            help="Ch\u1ebf \u0111\u1ed9 d\u00f9ng \u1edf Tab 1. Tab 4 lu\u00f4n ch\u1ea1y c\u1ea3 4 ch\u1ebf \u0111\u1ed9.",
        )

        st.divider()
        st.markdown("### \U0001f4d0 Tham S\u1ed1 Multi-Query")
        mq_count = st.slider("MULTI_QUERY_COUNT:", 1, 5, 3,
                              help="S\u1ed1 query variant sinh th\u00eam (kh\u00f4ng k\u1ec3 Q0).")
        per_query_cands = st.slider("PER_QUERY_CANDIDATES:", 5, 50, 12,
                                    help="S\u1ed1 child candidates m\u1ed7i query.")

        st.divider()
        st.markdown("### \U0001f33f Tham S\u1ed1 Parent\u2013Child")
        parent_cands = st.slider("PARENT_CANDIDATES:", 3, 30, 10)
        final_parent_top_k = st.slider("FINAL_PARENT_TOP_K:", 1, 10, 3)
        rerank_min_score = st.slider("RERANK_MIN_SCORE:", 0.0, 1.0, 0.50, 0.05)

        st.divider()
        st.caption(f"\U0001f512 **Strategy:** `{STRATEGY_FIXED}` *(c\u1ed1 \u0111\u1ecbnh)*")

        # API key
        cfg_safe = _cfg()
        has_key = cfg_safe.get("has_api_key", False)
        if has_key:
            st.success("\U0001f511 Gemini API Key: **\u0110\u00e3 c\u1ea5u h\u00ecnh**")
        else:
            st.error("\U0001f511 Gemini API Key: **Ch\u01b0a c\u00f3 (.env)**")

        if cfg_safe:
            with st.expander("\U0001f916 Models"):
                st.caption(f"**Embedding:** `{cfg_safe.get('embedding_model','—')}`")
                st.caption(f"**Generation:** `{cfg_safe.get('generation_model','—')}`")
                st.caption(f"**Reranker:** `{cfg_safe.get('reranker_model','—')}`")

        st.divider()
        st.markdown("### \U0001f4e6 Hierarchy Store")
        hs = _h_status()
        if hs.get("is_built"):
            nc = hs.get("total_children", "?")
            np_ = hs.get("total_parents", "?")
            na = hs.get("ambiguous_children", 0) or 0
            st.success(f"\u2705 **Ready** \u2014 {nc} children / {np_} parents")
            if na:
                st.warning(f"\u26a0\ufe0f Ambiguous: **{na}**")
            st.caption(f"Strategy: `{hs.get('strategy','?')}`")
            ts = str(hs.get("build_timestamp",""))[:16]
            if ts:
                st.caption(f"Built: `{ts}`")
        else:
            st.error("\u274c **Missing / Stale**")
            if hs.get("reason"):
                st.caption(hs["reason"])
            st.info("\U0001f4a1 Ch\u1ea1y: `python -m hierarchical_rag build`", icon="\U0001f528")

        st.markdown("### \U0001f5c4\ufe0f ChromaDB Collection")
        adv = _adv_status(STRATEGY_FIXED)
        if adv.get("collection_exists"):
            st.success(f"\u2705 **Indexed** \u2014 {adv.get('record_count','?')} records")
        elif "error" in adv:
            st.error(f"\u274c {adv['error'][:60]}")
        else:
            st.warning("\u26a0\ufe0f **Ch\u01b0a index**")
        if adv.get("reranker_cached"):
            st.caption("\U0001f4be Reranker: `Cache s\u1eb5n c\u00f3`")
        else:
            st.caption("\u23f3 Reranker: `Ch\u01b0a cache`")

    return {
        "mode": selected_mode,
        "multi_query_count": mq_count,
        "per_query_candidates": per_query_cands,
        "parent_candidates": parent_cands,
        "final_parent_top_k": final_parent_top_k,
        "rerank_min_score": rerank_min_score,
        "strategy": STRATEGY_FIXED,
        "has_api_key": has_key,
    }


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — Ask Advanced RAG
# ═════════════════════════════════════════════════════════════════════════════

def render_tab_ask(ui_cfg: Dict[str, Any]):
    st.markdown(
        "H\u1ecfi \u0111\u00e1p v\u1edbi **Grounded Generation** + Parent\u2013Child Citations. "
        "Ch\u1ec9 ch\u1ea1y khi b\u1ea5m n\u00fat \u2014 kh\u00f4ng t\u1ef1 query khi rerun widget."
    )
    preset = st.selectbox(
        "\U0001f4a1 Ch\u1ecdn c\u00e2u h\u1ecfi m\u1eabu:",
        options=["<T\u1ef1 nh\u1eadp>"] + SAMPLE_QUESTIONS,
        key="tab1_preset",
    )
    default_q = "" if preset == "<T\u1ef1 nh\u1eadp>" else preset
    user_query = st.text_area(
        "C\u00e2u h\u1ecfi:", value=default_q, height=90,
        placeholder="Nh\u1eadp c\u00e2u h\u1ecfi v\u1ec1 quy \u0111\u1ecbnh t\u00e0i ch\u00ednh \u2013 ng\u00e2n h\u00e0ng...",
        key="tab1_query",
    )
    mode_for_q = st.selectbox(
        "Ch\u1ebf \u0111\u1ed9:", options=FOUR_MODES,
        index=FOUR_MODES.index(ui_cfg["mode"]),
        format_func=lambda m: MODE_LABELS[m], key="tab1_mode",
    )
    col_btn, _ = st.columns([1, 5])
    with col_btn:
        run_btn = st.button("\U0001f680 H\u1ecfi", type="primary", use_container_width=True)

    if run_btn and user_query.strip():
        if not _ADV_AVAILABLE:
            st.error("\u274c Module `advanced_rag` kh\u00f4ng kh\u1ea3 d\u1ee5ng.")
            return
        dyn = dict(_cfg())
        dyn.update({
            "multi_query_count": ui_cfg["multi_query_count"],
            "per_query_candidates": ui_cfg["per_query_candidates"],
            "parent_candidates": ui_cfg["parent_candidates"],
            "final_parent_top_k": ui_cfg["final_parent_top_k"],
            "rerank_min_score": ui_cfg["rerank_min_score"],
        })
        with st.spinner("Dang thuc hien pipeline Multi-query & Parent-Child RAG..."):
            t0 = time.perf_counter()
            try:
                res = query_advanced_rag(
                    question=user_query.strip(), mode=mode_for_q,
                    strategy=STRATEGY_FIXED,
                    top_k=ui_cfg["final_parent_top_k"], config=dyn,
                )
                res["_wall_ms"] = round((time.perf_counter() - t0) * 1000, 1)
                _set("tab1_result", res)
            except Exception as exc:
                err = str(exc)
                code = next((k for k in ERROR_GUIDANCE if k in err.lower()), "generation_error")
                _set("tab1_result", {
                    "status": code, "answer": "", "citations": [],
                    "evidence": [], "warnings": [err[:300]],
                    "_wall_ms": round((time.perf_counter() - t0) * 1000, 1),
                })

    res = _ss("tab1_result")
    if res is None:
        st.info("\U0001f4a1 Nh\u1eadp c\u00e2u h\u1ecfi v\u00e0 b\u1ea5m **H\u1ecfi**.")
        return

    si = map_error_status(res.get("status", ""))
    msg = f"{si['icon']} **{si['title']}** | Mode: `{res.get('mode', mode_for_q)}`"
    if si["severity"] == "success":
        st.success(msg)
    elif si["severity"] == "warning":
        st.warning(msg)
    elif si["severity"] == "error":
        st.error(msg)
        if si["guidance"]:
            st.info(si["guidance"])
        return
    else:
        st.info(msg)
    if si["guidance"] and si["severity"] != "error":
        st.info(si["guidance"])

    # Latency
    trace = res.get("trace", {})
    lat = trace.get("latency_ms", {})
    wall_ms = res.get("_wall_ms", 0)
    gen_calls = res.get("generation_call_count", 1 if res.get("answer") else 0)
    emb_calls = res.get("embedding_call_count", 0)
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("\u23f1\ufe0f Total Latency", f"{wall_ms:.0f} ms")
    m2.metric("\U0001f500 Expansion ms",
              f"{lat.get('query_expansion', lat.get('expansion', 0)):.0f}")
    m3.metric("\U0001f916 Generation Calls", gen_calls)
    m4.metric("\U0001f522 Embedding Calls", emb_calls)

    # Answer
    if res.get("answer"):
        st.markdown("### \U0001f4dd C\u00e2u tr\u1ea3 l\u1eddi t\u1ed5ng h\u1ee3p")
        st.markdown(res["answer"])

    # Citations from parents
    parents = res.get("parents", [])
    if parents:
        st.markdown("#### \U0001f4da Ngu\u1ed3n tr\u00edch d\u1eabn (Parent Documents)")
        for idx, p in enumerate(parents, 1):
            cit = format_citation(p, idx)
            st.markdown(f"- **{cit['label']}** `{cit['citation']}`")
    elif res.get("citations"):
        st.markdown("#### \U0001f4da Ngu\u1ed3n tr\u00edch d\u1eabn")
        for cit in res["citations"]:
            st.markdown(
                f"- **{cit.get('label','')}**: `{cit.get('source','')}` "
                f"(tr. {cit.get('page_start','?')}-{cit.get('page_end','?')}) "
                f"— *`{cit.get('chunk_id','')}`*"
            )

    # Warnings
    if res.get("warnings"):
        with st.expander("\u26a0\ufe0f C\u1ea3nh b\u00e1o"):
            for w in res["warnings"]:
                st.warning(w)

    # Evidence cards
    if res.get("evidence"):
        st.markdown("### \U0001f4c4 Evidence Cards")
        for ev in res["evidence"]:
            accepted = ev.get("accepted", True)
            cls = "accepted" if accepted else "rejected"
            badge = "\u2705 CH\u1ea4P THU\u1eacN" if accepted else "\u274c B\u1eca LO\u1ea0I"
            parts = []
            if ev.get("rerank_score") is not None:
                parts.append(f"Rerank: **{ev['rerank_score']:.4f}** (#{ev.get('rerank_rank','?')})")
            if ev.get("parent_rrf_score") is not None:
                parts.append(f"Parent RRF: **{ev['parent_rrf_score']:.6f}**")
            if ev.get("rrf_score") is not None:
                parts.append(f"RRF: **{ev['rrf_score']:.6f}**")
            scores = " | ".join(parts)
            st.markdown(
                f'<div class="ev-card {cls}">'
                f'<div style="display:flex;justify-content:space-between;">'
                f'<strong>{ev.get("evidence_id","")}: {ev.get("source","")} '
                f'tr.{ev.get("page_start","?")}-{ev.get("page_end","?")}</strong>'
                f'<span>{badge}</span></div>'
                f'<div style="font-size:0.8rem;color:#64748b;margin:4px 0;">{scores}</div>'
                f'<div style="font-size:0.9rem;">{ev.get("text","")[:280]}...</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — Query Fan-out
# ═════════════════════════════════════════════════════════════════════════════

def _query_card_html(q: Dict[str, Any], result: Optional[Dict[str, Any]]) -> str:
    is_q0 = q.get("origin") == "original"
    cls = "qcard qcard-q0" if is_q0 else "qcard qcard-gen"
    qid = q.get("query_id", "?")
    focus = q.get("focus", "")
    color = QUERY_TYPE_COLORS.get(focus, "#6366f1")
    label = f"\u2605 {qid} \u2014 C\u00c2U H\u1ecei G\u1ed0C" if is_q0 else f"\u25ce {qid} \u2014 SINH B\u1edcI LLM"
    status = result.get("status", "ok") if result else "—"
    rc = result.get("result_count", 0) if result else "—"
    lat = f"{result.get('latency_ms', 0):.1f} ms" if result else "—"
    valid = "\u2705" if status == "ok" else "\u274c"
    return (
        f'<div class="{cls}">'
        f'<div class="qcard-label" style="color:{color};">{label}</div>'
        f'<div class="qcard-text">{q.get("text","")}</div>'
        f'<div class="qcard-meta">Focus: <b>{focus}</b> | '
        f'Origin: <b>{q.get("origin","")}</b> | Valid: {valid} | '
        f'Results: <b>{rc}</b> | Latency: <b>{lat}</b></div>'
        f'</div>'
    )


def render_tab_fanout(ui_cfg: Dict[str, Any]):
    st.markdown(
        "Hi\u1ec3n th\u1ecb **Query Fan-out**: m\u1ed7i c\u00e2u h\u1ecfi variant, "
        "k\u1ebft qu\u1ea3 ri\u00eang v\u00e0 **ma tr\u1eadn query\u2013child**."
    )
    preset2 = st.selectbox(
        "\U0001f4a1 C\u00e2u h\u1ecfi m\u1eabu:",
        options=["<T\u1ef1 nh\u1eadp>"] + SAMPLE_QUESTIONS, key="tab2_preset",
    )
    default_q2 = "" if preset2 == "<T\u1ef1 nh\u1eadp>" else preset2
    fanout_q = st.text_area("C\u00e2u h\u1ecfi cho Fan-out:", value=default_q2,
                             height=80, key="tab2_query")
    run2 = st.button("\U0001f500 Ch\u1ea1y Query Fan-out", type="primary", key="tab2_run")

    if run2 and fanout_q.strip():
        if not _HIER_AVAILABLE:
            st.error("\u274c hierarchical_rag kh\u00f4ng kh\u1ea3 d\u1ee5ng.")
            return
        dyn = dict(_cfg())
        dyn.update({"multi_query_count": ui_cfg["multi_query_count"],
                    "per_query_candidates": ui_cfg["per_query_candidates"]})
        with st.spinner("Dang sinh query variants va fan-out retrieval..."):
            t0 = time.perf_counter()
            try:
                qs = generate_query_variants(fanout_q.strip(), config=dyn)
                fr = fan_out_multi_query_retrieval(query_set=qs, config=dyn)
                fr["_qs"] = qs
                fr["_wall_ms"] = round((time.perf_counter() - t0) * 1000, 1)
                _set("tab2_result", fr)
            except Exception as exc:
                _set("tab2_result", {"status": "error", "error": str(exc)})

    fr = _ss("tab2_result")
    if fr is None:
        st.info("\U0001f4a1 Nh\u1eadp c\u00e2u h\u1ecfi v\u00e0 b\u1ea5m **Ch\u1ea1y Query Fan-out**.")
        return
    if fr.get("status") == "error":
        st.error(f"\u274c {fr.get('error','')[:400]}")
        return

    qs_data = fr.get("_qs", {})
    queries = qs_data.get("queries", [])
    pqr = fr.get("per_query_results", [])
    fused = fr.get("fused_children", [])
    wall_ms = fr.get("_wall_ms", 0)
    qid_map = {r["query_id"]: r for r in pqr}

    st.divider()
    ok_n = sum(1 for r in pqr if r.get("status") == "ok")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("\U0001f500 Query Variants", len(queries))
    c2.metric("\u2705 Queries OK", ok_n)
    c3.metric("\U0001f9e9 Fused Children", len(fused))
    c4.metric("\u23f1\ufe0f Total ms", f"{wall_ms:.0f}")
    c5.metric("\U0001f916 Expansion ms", f"{qs_data.get('generation_latency_ms', 0):.0f}")

    if fr.get("status") == "multi_query_partial":
        st.warning("\u26a0\ufe0f " + ERROR_GUIDANCE["multi_query_partial"])

    st.markdown("### \U0001f4cb Queries (Q0..Qn)")
    for q in queries:
        st.markdown(
            _query_card_html(q, result=qid_map.get(q.get("query_id","Q0"))),
            unsafe_allow_html=True,
        )

    if fused and pqr:
        st.markdown("### \U0001f522 Ma Tr\u1eadn Query\u2013Child")
        st.caption(
            "H\u00e0ng = child chunk (theo MQ-RRF rank). "
            "C\u1ed9t = Q0..Qn. \u00d4 = rank trong query \u0111\u00f3 (xanh) ho\u1eb7c \u2014."
        )
        df_mat = build_query_child_matrix(pqr, fused)
        if not df_mat.empty:
            q_cols = [c for c in df_mat.columns if c.startswith("Q") and c != "Child ID"]

            def _style(val):
                if val is None or (isinstance(val, float) and pd.isna(val)):
                    return "color:#cbd5e1;"
                return "background:#d1fae5;color:#065f46;font-weight:700;border-radius:4px;"

            styled = df_mat.style.applymap(_style, subset=q_cols)
            fmt = {q: (lambda v: f"#{int(v)}" if v is not None and not (
                isinstance(v, float) and pd.isna(v)) else "\u2014") for q in q_cols}
            styled = styled.format(fmt)
            st.dataframe(styled, use_container_width=True, hide_index=True)
        else:
            st.info("fused_children rong.")


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — Parent-Child Explorer
# ═════════════════════════════════════════════════════════════════════════════

def render_tab_parent_child(ui_cfg: Dict[str, Any]):
    st.markdown(
        "Hi\u1ec3n th\u1ecb **c\u00e2y Parent\u2013Child**: parent document, "
        "anchor children v\u00e0 rank movement (tr\u01b0\u1edbc/sau rerank)."
    )
    preset3 = st.selectbox(
        "\U0001f4a1 C\u00e2u h\u1ecfi:",
        options=["<T\u1ef1 nh\u1eadp>"] + SAMPLE_QUESTIONS, key="tab3_preset",
    )
    default_q3 = "" if preset3 == "<T\u1ef1 nh\u1eadp>" else preset3
    pc_q = st.text_area("C\u00e2u h\u1ecfi:", value=default_q3, height=80, key="tab3_query")
    col_m, col_b = st.columns([2, 1])
    with col_m:
        mode3 = st.selectbox(
            "Mode:", options=["multi_parent", "single_parent"],
            format_func=lambda m: MODE_LABELS[m], key="tab3_mode",
        )
    with col_b:
        run3 = st.button("\U0001f33f Kh\u00e1m ph\u00e1 Parent\u2013Child",
                          type="primary", key="tab3_run")

    if run3 and pc_q.strip():
        if not _ADV_AVAILABLE:
            st.error("\u274c Module kh\u00f4ng kh\u1ea3 d\u1ee5ng.")
            return
        dyn = dict(_cfg())
        dyn.update({
            "multi_query_count": ui_cfg["multi_query_count"],
            "per_query_candidates": ui_cfg["per_query_candidates"],
            "parent_candidates": ui_cfg["parent_candidates"],
            "final_parent_top_k": ui_cfg["final_parent_top_k"],
            "rerank_min_score": ui_cfg["rerank_min_score"],
        })
        with st.spinner("Dang truy xuat va xay dung cay parent-child..."):
            t0 = time.perf_counter()
            try:
                r3 = query_advanced_rag(
                    question=pc_q.strip(), mode=mode3,
                    strategy=STRATEGY_FIXED,
                    top_k=ui_cfg["final_parent_top_k"], config=dyn,
                )
                r3["_wall_ms"] = round((time.perf_counter() - t0) * 1000, 1)
                _set("tab3_result", r3)
            except Exception as exc:
                _set("tab3_result", {"status": "error", "error": str(exc)})

    r3 = _ss("tab3_result")
    if r3 is None:
        st.info("\U0001f4a1 Nh\u1eadp c\u00e2u h\u1ecfi v\u00e0 b\u1ea5m **Kh\u00e1m ph\u00e1**.")
        return
    if r3.get("status") == "error":
        st.error(f"\u274c {r3.get('error','')[:400]}")
        return

    parents = r3.get("parents", r3.get("evidence", []))
    if not parents:
        si = map_error_status(r3.get("status", ""))
        st.warning(f"{si['icon']} {si['title']}")
        if si["guidance"]:
            st.info(si["guidance"])
        return

    # Load registry
    cbi: Dict[str, Any] = {}
    try:
        h_store = load_hierarchy_store()
        cbi = h_store.get("children_by_id", {})
    except Exception:
        pass

    tree = build_parent_tree_data(parents, cbi)
    trace3 = r3.get("trace", {})
    exp_f = trace3.get("context_expansion_factor", trace3.get("expansion_factor", 0.0))
    ctx_chars = trace3.get("total_context_chars", 0)

    # Expansion highlight
    ec1, ec2, ec3 = st.columns([1, 1, 2])
    ec1.markdown(
        f'<div class="expansion-box">{exp_f:.1f}\u00d7'
        f'<div class="expansion-label">Context Expansion</div></div>',
        unsafe_allow_html=True,
    )
    ec2.metric("\U0001f4c4 Context Chars", f"{ctx_chars:,}")
    ec3.metric("\U0001f33f Parents ch\u1ecdn", len(tree))

    st.divider()
    st.markdown(f"### \U0001f333 C\u00e2y Parent\u2013Child ({len(tree)} parent)")

    for p in tree:
        title = p.get("title") or p["parent_id"].split("::")[-1]
        ambig = p.get("ambiguous", False)
        ambig_html = '<span class="ambiguous-badge">\u26a0\ufe0f AMBIGUOUS</span>' if ambig else ""
        acc_icon = "\u2705" if p.get("accepted", True) else "\u274c"

        st.markdown(
            f'<div class="parent-card">'
            f'<div class="parent-header">'
            f'<span>{acc_icon} {title} {ambig_html}</span>'
            f'<span style="font-size:0.8rem;color:#94a3b8;">{p.get("source","")}</span>'
            f'</div><div class="parent-body">',
            unsafe_allow_html=True,
        )

        ic, sc = st.columns([3, 2])
        with ic:
            if p.get("chapter"):
                st.caption(f"\U0001f4d6 Ch.: {p['chapter']}")
            if p.get("article"):
                st.caption(f"\U0001f4c4 Art.: {p['article']}")
            ps, pe = p.get("page_start"), p.get("page_end")
            if ps:
                st.caption(f"\U0001f4c3 Pages: {ps}\u2013{pe}")
            st.markdown(
                _rank_badge_html(p["parent_rank"], p.get("rerank_rank"), p.get("rank_change")),
                unsafe_allow_html=True,
            )
            if p.get("support_query_ids"):
                sq = " ".join([f"`{q}`" for q in p["support_query_ids"]])
                st.caption(f"Support queries: {sq}")
        with sc:
            st.markdown(f"Parent RRF: **{p.get('parent_rrf_score', 0):.6f}**")
            if p.get("rerank_score") is not None:
                st.markdown(f"Rerank: **{p['rerank_score']:.4f}**")
            st.caption(f"\U0001f4cf {p.get('char_count', 0):,} chars")

        # Children sub-tree
        children_sub = p.get("supporting_children", [])
        if children_sub:
            with st.expander(f"\U0001f517 Children ({len(children_sub)} anchor chunks)"):
                for ch in children_sub:
                    cid = ch.get("child_id", "")
                    crec = cbi.get(cid, {})
                    snip = crec.get("text", ch.get("anchor_snippet", ""))[:150]
                    st.markdown(
                        f'<span class="child-pill">{cid}</span>',
                        unsafe_allow_html=True,
                    )
                    if snip:
                        st.caption(f"> {snip}...")

        # Full text
        if p.get("text"):
            with st.expander("\U0001f4dc Xem to\u00e0n v\u0103n Parent Document"):
                st.text(p["text"])

        # Warnings
        if p.get("warnings"):
            with st.expander("\u26a0\ufe0f Warnings"):
                for w in p["warnings"]:
                    st.warning(w)

        st.markdown("</div></div>", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — Mode Comparison
# ═════════════════════════════════════════════════════════════════════════════

def render_tab_mode_comparison(ui_cfg: Dict[str, Any]):
    st.markdown(
        "So s\u00e1nh **4 ch\u1ebf \u0111\u1ed9** tr\u00ean c\u00f9ng m\u1ed9t c\u00e2u h\u1ecfi \u2014 "
        "**ch\u1ec9 retrieval**, kh\u00f4ng g\u1ecdi LLM. "
        "Kh\u00f4ng tuy\u00ean b\u1ed1 mode th\u1eafng khi kh\u00f4ng c\u00f3 gold labels."
    )
    preset4 = st.selectbox(
        "\U0001f4a1 C\u00e2u h\u1ecfi:",
        options=["<T\u1ef1 nh\u1eadp>"] + SAMPLE_QUESTIONS, key="tab4_preset",
    )
    default_q4 = "" if preset4 == "<T\u1ef1 nh\u1eadp>" else preset4
    cmp_q = st.text_input("C\u00e2u h\u1ecfi so s\u00e1nh:", value=default_q4, key="tab4_query")
    run4 = st.button("\u26a1 Ch\u1ea1y So S\u00e1nh 4 Mode", type="primary", key="tab4_run")

    if run4 and cmp_q.strip():
        if not _ADV_AVAILABLE:
            st.error("\u274c Module kh\u00f4ng kh\u1ea3 d\u1ee5ng.")
            return
        dyn = dict(_cfg())
        dyn.update({
            "multi_query_count": ui_cfg["multi_query_count"],
            "per_query_candidates": ui_cfg["per_query_candidates"],
            "parent_candidates": ui_cfg["parent_candidates"],
            "final_parent_top_k": ui_cfg["final_parent_top_k"],
            "rerank_min_score": ui_cfg["rerank_min_score"],
        })
        results: Dict[str, Dict[str, Any]] = {}
        prog = st.progress(0, text="Kh\u1edfi ch\u1ea1y...")
        for i, m in enumerate(FOUR_MODES):
            prog.progress(i / len(FOUR_MODES), text=f"Mode `{m}`...")
            t_m = time.perf_counter()
            try:
                r_m = query_advanced_rag(
                    question=cmp_q.strip(), mode=m,
                    strategy=STRATEGY_FIXED,
                    top_k=ui_cfg["final_parent_top_k"], config=dyn,
                )
                r_m["latency_ms"] = round((time.perf_counter() - t_m) * 1000, 1)
                results[m] = r_m
            except Exception as exc:
                results[m] = {
                    "status": "error", "error": str(exc)[:300],
                    "latency_ms": round((time.perf_counter() - t_m) * 1000, 1),
                }
        prog.progress(1.0, text="Xong!")
        _set("tab4_results", results)
        _set("tab4_q", cmp_q.strip())

    results = _ss("tab4_results")
    if results is None:
        st.info("\U0001f4a1 Nh\u1eadp c\u00e2u h\u1ecfi v\u00e0 b\u1ea5m **Ch\u1ea1y So S\u00e1nh**.")
        return

    cq = _ss("tab4_q", "")
    st.divider()
    st.markdown(f'### \U0001f4ca B\u1ea3ng So S\u00e1nh \u2014 *"{cq[:60]}"*')
    st.caption("\u2139\ufe0f Kh\u00f4ng tuy\u00ean b\u1ed1 mode 'th\u1eafng' khi ch\u01b0a c\u00f3 gold labels \u0111\u00e3 x\u00e9t duy\u1ec7t.")

    rows_cmp = []
    for m in FOUR_MODES:
        r = results.get(m, {})
        if r.get("status") == "error":
            rows_cmp.append({
                "Mode": MODE_LABELS[m], "Status": "\u274c error",
                "Unit Type": "\u2014", "Evidence Count": 0,
                "Unique Sources": 0, "Child Count": 0, "Parent Count": 0,
                "Context Chars": 0, "Expansion Factor": "\u2014",
                "Latency (ms)": r.get("latency_ms", 0),
                "Gen Calls": 0, "Emb Calls": 0,
                "Warnings": str(r.get("error", ""))[:80],
            })
        else:
            cr = build_mode_comparison_row(m, r)
            ok = r.get("status", "") in ("answered", "retrieval_only", "ok")
            rows_cmp.append({
                "Mode": MODE_LABELS[m],
                "Status": f"{'✅' if ok else '⚠️'} {r.get('status','')}",
                "Unit Type": cr["Unit Type"],
                "Evidence Count": cr["Evidence Count"],
                "Unique Sources": cr["Unique Sources"],
                "Child Count": cr["Child Count"],
                "Parent Count": cr["Parent Count"],
                "Context Chars": cr["Context Chars"],
                "Expansion Factor": cr["Expansion Factor"],
                "Latency (ms)": cr["Latency (ms)"],
                "Gen Calls": cr["Generation Calls"],
                "Emb Calls": cr["Embedding Calls"],
                "Warnings": "; ".join(cr["Warnings"])[:80] if cr["Warnings"] else "",
            })

    st.dataframe(pd.DataFrame(rows_cmp), use_container_width=True, hide_index=True)

    # Per-mode columns
    st.markdown("### \U0001f50d Chi Ti\u1ebft T\u1eebng Mode")
    badge_map = {"single_flat": "mode-sf", "multi_flat": "mode-mf",
                 "single_parent": "mode-sp", "multi_parent": "mode-mp"}
    cols_m = st.columns(4)
    for i, m in enumerate(FOUR_MODES):
        r = results.get(m, {})
        with cols_m[i]:
            st.markdown(
                f'<span class="mode-badge {badge_map[m]}">{MODE_LABELS[m]}</span>',
                unsafe_allow_html=True,
            )
            if r.get("status") == "error":
                st.error(r.get("error", "")[:120])
                continue
            cr = build_mode_comparison_row(m, r)
            st.metric("Evidence", cr["Evidence Count"])
            st.metric("Expansion", f"{cr['Expansion Factor']:.1f}\u00d7")
            st.metric("Latency ms", cr["Latency (ms)"])
            for src in cr["Sources"][:3]:
                st.caption(f"\u2022 `{src[:35]}`")
            if cr["Evidence IDs"]:
                with st.expander("IDs"):
                    for eid in cr["Evidence IDs"][:5]:
                        st.caption(f"`{str(eid)[:60]}`")
            if cr["Warnings"]:
                with st.expander("\u26a0\ufe0f Warnings"):
                    for w in cr["Warnings"][:3]:
                        st.warning(w)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 5 — Evaluation
# ═════════════════════════════════════════════════════════════════════════════

def render_tab_evaluation():
    st.markdown("Doc bao cao \u0111anh gia da co. **Khong tu chay evaluator khi render.**")

    reports = sorted(REPORTS_DIR.glob("*.json"), reverse=True) if REPORTS_DIR.exists() else []
    if not reports:
        st.info(
            "\u2139\ufe0f Chua co bao cao trong `reports/`. "
            "Chay `python evaluate.py` de sinh bao cao."
        )
    else:
        sel = st.selectbox("\U0001f4ca Chon bao cao:", reports,
                           format_func=lambda p: p.name, key="tab5_report")
        try:
            with open(sel, "r", encoding="utf-8") as f:
                rd = json.load(f)
            metrics = rd.get("metrics", rd.get("results", {}))
            if isinstance(metrics, dict):
                st.markdown("#### \U0001f4c8 Chi So Danh Gia")
                mc1, mc2, mc3, mc4 = st.columns(4)
                if metrics.get("child_recall_at_k") is not None:
                    mc1.metric("Child Recall@K", f"{metrics['child_recall_at_k']:.3f}")
                if metrics.get("parent_recall_at_k") is not None:
                    mc2.metric("Parent Recall@K", f"{metrics['parent_recall_at_k']:.3f}")
                if metrics.get("mrr_at_k") is not None:
                    mc3.metric("MRR@K", f"{metrics['mrr_at_k']:.3f}")
                if metrics.get("ndcg_at_k") is not None:
                    mc4.metric("nDCG@K", f"{metrics['ndcg_at_k']:.3f}")
                mc5, mc6 = st.columns(2)
                if metrics.get("avg_latency_ms"):
                    mc5.metric("Avg Latency ms", f"{metrics['avg_latency_ms']:.1f}")
                if metrics.get("avg_context_chars"):
                    mc6.metric("Avg Context Chars", f"{metrics['avg_context_chars']:,.0f}")
            if rd.get("needs_human_review"):
                st.warning(
                    "\u26a0\ufe0f **Gold labels `needs_human_review: true`** \u2014 "
                    "Ket qua mang tinh chat tham khao. "
                    "Can chuyen gia phap ly tham dinh."
                )
            st.divider()
            with st.expander("\U0001f4c4 Toan bo JSON"):
                st.json(rd)
        except Exception as e:
            st.error(f"Loi doc bao cao: {e}")

    st.divider()
    st.markdown("### \U0001f3af Tap Cau Hoi Benchmark (`eval/questions.json`)")
    qs_data: List[Dict[str, Any]] = []
    if EVAL_FILE.exists():
        try:
            with open(EVAL_FILE, "r", encoding="utf-8") as f:
                qs_data = json.load(f)
        except Exception:
            pass

    if not qs_data:
        st.info("Khong tim thay `eval/questions.json`.")
    else:
        if any(q.get("needs_human_review") for q in qs_data):
            st.warning(
                "\u26a0\ufe0f Mot so cau hoi co `needs_human_review: true`. "
                "Can tham dinh truoc khi dung lam gold labels."
            )
        rows_q = []
        for q in qs_data:
            rel = q.get("relevant_chunk_ids") or q.get("relevant_parent_ids") or []
            rows_q.append({
                "ID": q.get("query_id", ""),
                "Cau hoi": q.get("question", q.get("query", ""))[:80],
                "Scope": q.get("scope", "in_scope"),
                "Relevant IDs": ", ".join(str(r) for r in rel[:3]) + (
                    "..." if len(rel) > 3 else ""),
                "Review": "\u26a0\ufe0f" if q.get("needs_human_review") else "\u2705",
            })
        st.dataframe(pd.DataFrame(rows_q), use_container_width=True, hide_index=True)


# ═════════════════════════════════════════════════════════════════════════════
# HEADER
# ═════════════════════════════════════════════════════════════════════════════

def render_header():
    steps = [
        "Query fan-out", "Hybrid per query",
        "Cross-query RRF", "Parent expansion", "Parent rerank",
    ]
    steps_html = ' <span class="b09-arrow">\u2192</span> '.join(
        f'<span class="b09-step">{s}</span>' for s in steps
    )
    st.markdown(
        f'<div class="b09-hero">'
        f'<h1>\u2696\ufe0f RAG Foundation \u2014 Bu\u1ed5i 09<br>'
        f'<span style="font-size:1.0rem;font-weight:500;color:#94a3b8;">'
        f'Multi-query &amp; Parent\u2013Child Retrieval</span></h1>'
        f'<div class="b09-pipeline">{steps_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

def main():
    st.set_page_config(
        page_title="RAG Buoi 09 - Multi-query & Parent-Child",
        page_icon="\U0001f33f",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    ui_cfg = render_sidebar()
    render_header()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "\U0001f4ac 1. Ask Advanced RAG",
        "\U0001f500 2. Query Fan-out",
        "\U0001f33f 3. Parent\u2013Child Explorer",
        "\u26a1 4. Mode Comparison",
        "\U0001f4c8 5. Evaluation",
    ])
    with tab1:
        render_tab_ask(ui_cfg)
    with tab2:
        render_tab_fanout(ui_cfg)
    with tab3:
        render_tab_parent_child(ui_cfg)
    with tab4:
        render_tab_mode_comparison(ui_cfg)
    with tab5:
        render_tab_evaluation()


if __name__ == "__main__":
    main()
