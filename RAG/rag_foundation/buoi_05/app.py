"""Giao dien Streamlit - Kham pha & so sanh chunks RAG (Buoi 5).

Chay:  streamlit run app.py
Du lieu: chi doc tu output/ -- khong goi API, khong tao embedding.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Hang so duong dan
# ---------------------------------------------------------------------------
ROOT    = Path(__file__).resolve().parent
OUTPUT  = ROOT / "output"
CHUNKS  = OUTPUT / "chunks"
REPORTS = OUTPUT / "reports"

STRATEGIES = ("fixed-size", "semantic", "hierarchical")

STRATEGY_LABELS = {
    "fixed-size":   "Fixed-size",
    "semantic":     "Semantic",
    "hierarchical": "Hierarchical",
}

STRATEGY_ICONS = {
    "fixed-size":   "📐",
    "semantic":     "🧠",
    "hierarchical": "🏛️",
}

# ---------------------------------------------------------------------------
# Tai du lieu (co cache)
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_reports() -> list[dict]:
    paths = sorted(REPORTS.glob("*__report.json"))
    return [json.loads(p.read_text(encoding="utf-8")) for p in paths]


@st.cache_data(show_spinner=False)
def load_chunks(stem: str, strategy: str) -> list[dict]:
    path = CHUNKS / f"{stem}__{strategy}.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    path_legacy = OUTPUT / f"{stem}_chunks.json"
    if path_legacy.is_file():
        raw = json.loads(path_legacy.read_text(encoding="utf-8"))
        return [c for c in raw if c.get("strategy") == strategy]
    return []


def get_stems(reports: list[dict]) -> list[str]:
    return [Path(r["source"]).stem for r in reports]


# ---------------------------------------------------------------------------
# Tien ich hien thi
# ---------------------------------------------------------------------------

def highlight_text(text: str, query: str) -> str:
    if not query.strip():
        return text
    escaped_q = re.escape(query.strip())
    return re.sub(
        f"({escaped_q})",
        r'<mark style="background:#facc15;color:#1e293b;border-radius:3px;padding:0 2px">\1</mark>',
        text,
        flags=re.IGNORECASE,
    )


def build_stats_df(reports: list[dict]) -> pd.DataFrame:
    rows = []
    for r in reports:
        stem = Path(r["source"]).stem
        for strategy, vals in r.get("statistics", {}).items():
            rows.append({
                "Tai lieu":            stem,
                "Chien luoc":          strategy,
                "So chunk":            vals["chunk_count"],
                "Do dai TB (ky tu)":   vals["length_avg"],
                "Nho nhat":            vals["length_min"],
                "Lon nhat":            vals["length_max"],
            })
    return pd.DataFrame(rows)


def chunk_table_df(chunks: list[dict]) -> pd.DataFrame:
    rows = []
    for c in chunks:
        structure_path = " > ".join(c.get("structure", {}).values()) or "—"
        rows.append({
            "chunk_id":  c["chunk_id"],
            "Trang":     f'{c["page_start"]}–{c["page_end"]}',
            "Ky tu":     len(c["text"]),
            "Cau truc":  structure_path,
            "Xem truoc": c["text"][:120].replace("\n", " ") + ("…" if len(c["text"]) > 120 else ""),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# CSS tuy chinh (dark glassmorphism)
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #0f172a 100%);
}

[data-testid="stSidebar"] {
    background: rgba(15,23,42,0.92) !important;
    border-right: 1px solid rgba(99,102,241,0.25);
}

h1 { color: #e2e8f0 !important; font-weight: 700 !important; }
h2 { color: #94a3b8 !important; font-weight: 600 !important; }
h3 { color: #7dd3fc !important; font-weight: 600 !important; }

[data-testid="stMetric"] {
    background: rgba(30,41,59,0.85);
    border: 1px solid rgba(99,102,241,0.3);
    border-radius: 12px;
    padding: 14px 18px !important;
}
[data-testid="stMetricValue"] { color: #7dd3fc !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { color: #94a3b8 !important; }

.stTabs [data-baseweb="tab-list"] {
    background: rgba(15,23,42,0.7);
    border-radius: 10px;
    gap: 4px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"]     { border-radius: 8px !important; color: #94a3b8 !important; }
.stTabs [aria-selected="true"]   { background: rgba(99,102,241,0.25) !important; color: #c7d2fe !important; }

.chunk-card {
    background: rgba(30,41,59,0.8);
    border: 1px solid rgba(99,102,241,0.2);
    border-left: 4px solid #6366f1;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 12px;
}
.chunk-text { font-size: 14px; color: #cbd5e1; line-height: 1.7; white-space: pre-wrap; }

.breadcrumb {
    font-size: 12px; color: #94a3b8;
    background: rgba(99,102,241,0.12);
    border-radius: 6px; padding: 3px 10px;
    display: inline-block; margin-bottom: 8px;
}

.stAlert { border-radius: 10px !important; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0f172a; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
</style>
"""

# ---------------------------------------------------------------------------
# Tab: Tong quan
# ---------------------------------------------------------------------------

def tab_tong_quan(reports: list[dict], stats_df: pd.DataFrame) -> None:
    st.markdown("### Thong ke tong quan — tat ca tai lieu")

    pivot = stats_df.pivot_table(
        index="Tai lieu", columns="Chien luoc", values="So chunk", aggfunc="sum"
    ).reset_index()

    col_chart, col_table = st.columns([3, 2], gap="large")
    with col_chart:
        st.markdown("**So chunk theo tai lieu va chien luoc**")
        chart_data = pivot.set_index("Tai lieu")
        st.bar_chart(chart_data)

    with col_table:
        st.markdown("**Bang chi tiet**")
        st.dataframe(
            stats_df.style.format({"Do dai TB (ky tu)": "{:.0f}"}),
            hide_index=True, use_container_width=True,
        )

    st.divider()
    st.markdown("### Tong quan tung tai lieu")
    for report in reports:
        stem   = Path(report["source"]).stem
        cols   = st.columns(4, gap="small")
        cols[0].markdown(f"**{stem}**")
        for i, strat in enumerate(STRATEGIES):
            vals = report.get("statistics", {}).get(strat, {})
            icon = STRATEGY_ICONS[strat]
            cols[i + 1].metric(
                f"{icon} {STRATEGY_LABELS[strat]}",
                f"{vals.get('chunk_count', 0)} chunks",
                f"TB {vals.get('length_avg', 0):.0f} ky tu",
            )
        if report.get("warnings"):
            with st.expander(f"Canh bao — {stem}"):
                for w in report["warnings"]:
                    st.warning(w)


# ---------------------------------------------------------------------------
# Tab: Kham pha chunk
# ---------------------------------------------------------------------------

def tab_kham_pha(reports: list[dict]) -> None:
    stems = get_stems(reports)

    with st.sidebar:
        st.markdown("### Bo loc")
        selected_stem     = st.selectbox("Tai lieu", stems, key="kp_stem")
        selected_strategy = st.selectbox(
            "Chien luoc chunking", STRATEGIES,
            format_func=lambda s: f"{STRATEGY_ICONS[s]} {STRATEGY_LABELS[s]}",
            key="kp_strategy",
        )
        query = st.text_input("Tim trong noi dung", placeholder="Vi du: to chuc tin dung", key="kp_query")
        st.divider()
        descs = {
            "fixed-size":   "Cat van ban thanh cac doan co **kich thuoc co dinh** (tinh bang ky tu), voi phan **goi dau (overlap)** de khong mat ngu canh.",
            "semantic":     "Ngat theo **ranh gioi doan van / cau**. Chunk giu nguyen y nghia hoan chinh.",
            "hierarchical": "Theo doi **cau truc phan cap** Chuong > Dieu > Khoan > Diem. Moi chunk mang metadata `structure`.",
        }
        st.info(descs[selected_strategy])

    chunks: list[dict[str, Any]] = load_chunks(selected_stem, selected_strategy)

    if not chunks:
        st.warning("Chua co du lieu chunk. Hay chay rag_pipeline.py --write truoc.")
        st.code("python RAG\\rag_foundation\\buoi_05\\src\\rag_pipeline.py --write", language="powershell")
        return

    if query.strip():
        needle = query.casefold()
        chunks = [c for c in chunks if needle in c["text"].casefold()]

    icon = STRATEGY_ICONS[selected_strategy]
    st.markdown(f"#### {icon} {STRATEGY_LABELS[selected_strategy]} — `{selected_stem}`")

    if not chunks:
        st.warning("Khong co chunk nao khop voi tu khoa tim kiem.")
        return

    lengths = [len(c["text"]) for c in chunks]
    m1, m2, m3, m4 = st.columns(4, gap="small")
    m1.metric("Tong chunk",       len(chunks))
    m2.metric("Do dai TB",        f"{sum(lengths)/len(lengths):.0f} ky tu")
    m3.metric("Nho nhat",         f"{min(lengths)} ky tu")
    m4.metric("Lon nhat",         f"{max(lengths)} ky tu")

    # Histogram
    with st.expander("Phan phoi do dai chunk", expanded=False):
        n_bins = min(20, max(5, int(math.sqrt(len(lengths)))))
        min_l, max_l = min(lengths), max(lengths)
        step = (max_l - min_l) / n_bins if max_l != min_l else 1
        hist_counts = [0] * n_bins
        for ll in lengths:
            idx = min(int((ll - min_l) / (max_l - min_l + 1) * n_bins), n_bins - 1)
            hist_counts[idx] += 1
        hist_df = pd.DataFrame({
            "Khoang ky tu": [f"{int(min_l + i*step)}-{int(min_l + (i+1)*step)}" for i in range(n_bins)],
            "So chunk":     hist_counts,
        }).set_index("Khoang ky tu")
        st.bar_chart(hist_df)

    st.divider()
    st.markdown("**Danh sach chunks**")
    st.dataframe(chunk_table_df(chunks), hide_index=True, use_container_width=True)

    st.divider()
    st.markdown("**Xem chi tiet chunk**")
    chunk_ids = [c["chunk_id"] for c in chunks]
    chosen_id = st.selectbox("Chon chunk", chunk_ids, key="kp_chosen")
    chosen    = next(c for c in chunks if c["chunk_id"] == chosen_id)

    structure = chosen.get("structure", {})
    if structure:
        breadcrumb = " > ".join(structure.values())
        st.markdown(f"<div class='breadcrumb'>📍 {breadcrumb}</div>", unsafe_allow_html=True)

    with st.expander("Metadata", expanded=True):
        st.json({k: v for k, v in chosen.items() if k != "text"})

    st.markdown("**Noi dung chunk:**")
    display_text = highlight_text(chosen["text"], query)
    st.markdown(
        f'<div class="chunk-card"><div class="chunk-text">{display_text}</div></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Tab: So sanh
# ---------------------------------------------------------------------------

def tab_so_sanh(reports: list[dict]) -> None:
    stems = get_stems(reports)
    st.markdown("### So sanh song song hai chien luoc")

    col_l, col_r, col_idx = st.columns([2, 2, 1], gap="medium")
    with col_l:
        stem_l  = st.selectbox("Tai lieu (Trai)",      stems,      key="cmp_stem_l")
        strat_l = st.selectbox("Chien luoc (Trai)", STRATEGIES,
                               format_func=lambda s: f"{STRATEGY_ICONS[s]} {STRATEGY_LABELS[s]}",
                               key="cmp_strat_l")
    with col_r:
        strat_r = st.selectbox("Chien luoc (Phai)", STRATEGIES,
                               format_func=lambda s: f"{STRATEGY_ICONS[s]} {STRATEGY_LABELS[s]}",
                               key="cmp_strat_r", index=1)
        stem_r  = st.selectbox("Tai lieu (Phai)",      stems,      key="cmp_stem_r")
    with col_idx:
        idx = st.number_input("Thu tu chunk (0-based)", min_value=0, value=0, key="cmp_idx")

    chunks_l = load_chunks(stem_l, strat_l)
    chunks_r = load_chunks(stem_r, strat_r)

    if not chunks_l or not chunks_r:
        st.warning("Chua co chunk cho it nhat mot trong hai lua chon.")
        return

    st.divider()
    s_col_l, s_col_r = st.columns(2, gap="large")
    for col, cks, strat, stem in ((s_col_l, chunks_l, strat_l, stem_l),
                                   (s_col_r, chunks_r, strat_r, stem_r)):
        lens = [len(c["text"]) for c in cks]
        with col:
            st.markdown(f"**{STRATEGY_ICONS[strat]} {STRATEGY_LABELS[strat]}** — `{stem}`")
            c1, c2 = st.columns(2)
            c1.metric("So chunk",  len(cks))
            c2.metric("Do dai TB", f"{sum(lens)/len(lens):.0f}")

    st.divider()
    st.markdown(f"**Chunk thu tu #{idx}**")
    left_col, right_col = st.columns(2, gap="large")

    def _show(col: Any, cks: list[dict], label: str) -> None:
        with col:
            st.markdown(f"**{label}**")
            if idx < len(cks):
                c = cks[idx]
                st.caption(c["chunk_id"])
                st.markdown(f"Trang `{c['page_start']}–{c['page_end']}` | {len(c['text'])} ky tu")
                if c.get("structure"):
                    bc = " > ".join(c["structure"].values())
                    st.markdown(f"<div class='breadcrumb'>📍 {bc}</div>", unsafe_allow_html=True)
                st.markdown(
                    f'<div class="chunk-card"><div class="chunk-text">{c["text"]}</div></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.info(f"Khong co chunk thu {idx} (tong: {len(cks)}).")

    _show(left_col,  chunks_l, f"{STRATEGY_ICONS[strat_l]} {STRATEGY_LABELS[strat_l]}")
    _show(right_col, chunks_r, f"{STRATEGY_ICONS[strat_r]} {STRATEGY_LABELS[strat_r]}")


# ---------------------------------------------------------------------------
# Tab: Giai thich
# ---------------------------------------------------------------------------

def tab_giai_thich() -> None:
    st.markdown("### Giai thich chien luoc chunking")

    info = {
        "fixed-size": (
            "Cat van ban thanh cac doan co **kich thuoc co dinh** (tinh bang ky tu), "
            "voi phan **goi dau (overlap)** de khong mat ngu canh o ranh gioi chunk."
        ),
        "semantic": (
            "Ngat theo **ranh gioi doan van / cau** (dau xuong dong doi hoac chu hoa dau dong). "
            "Chunk giu nguyen y nghia hoan chinh cua moi doan."
        ),
        "hierarchical": (
            "Theo doi **cau truc phan cap** Chuong → Dieu → Khoan → Diem. "
            "Moi chunk mang metadata `structure` cho biet vi tri trong van ban phap luat."
        ),
    }
    for strat, desc in info.items():
        with st.expander(f"{STRATEGY_ICONS[strat]} {STRATEGY_LABELS[strat]}", expanded=True):
            st.markdown(desc)

    st.divider()
    st.markdown("### 3 tinh huong loi da xu ly trong pipeline")

    scenarios = [
        (
            "1. Loi font / encoding / ky tu la trong text layer PDF",
            "Ky tu \\ufffd, dau encoding sai, so lan trong tu (th6ng), hoac trang rong.",
            "Danh dau trang bad → render thanh anh (khong sua PDF goc) → goi LlamaParse OCR → chuan hoa NFC.",
        ),
        (
            "2. Van ban khong co cau truc phan cap Chuong / Dieu",
            "Hierarchical chunker khong khop bat ky pattern CHUONG/DIEU/MUC nao.",
            "KHONG bia heading. Ghi canh bao vao warnings cua report. Van sinh chunk thuan noi dung.",
        ),
        (
            "3. API Key Llama Cloud khong hop le / chua cau hinh",
            "RuntimeError khi goi ocr_entire_file() vi LLAMA_CLOUD_API_KEY trong.",
            "Bat loi tai process_pdf() → in thong bao LOI → exit code 1; cac PDF khac van tiep tuc.",
        ),
    ]

    for title, symptom, solution in scenarios:
        st.markdown(f"**{title}**")
        col_s, col_x = st.columns(2)
        col_s.error(f"**Dau hieu:** {symptom}")
        col_x.success(f"**Xu ly:** {solution}")
        st.divider()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="RAG Chunk Explorer – Buoi 5",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    st.markdown(
        "<h1>📚 RAG Chunk Explorer "
        "<span style='font-size:16px;color:#64748b'>Buoi 5</span></h1>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Visualize & so sanh ba chien luoc chunking: Fixed-size · Semantic · Hierarchical | "
        "Chi doc tu output/ — khong goi API, khong tao embedding."
    )

    reports = load_reports()
    if not reports:
        st.error(
            "**Chua co du lieu trong output/.** "
            "Hay chay pipeline voi co --write de tao chunks truoc:"
        )
        st.code(
            "cd /d \"d:\\Lop PTDLNC 2026\"\n"
            "python RAG\\rag_foundation\\buoi_05\\src\\rag_pipeline.py --write",
            language="powershell",
        )
        return

    stats_df = build_stats_df(reports)

    tab_ov, tab_kp, tab_cmp, tab_ex = st.tabs([
        "🏠 Tong quan",
        "🔬 Kham pha chunk",
        "⚖️ So sanh",
        "📖 Giai thich",
    ])

    with tab_ov:
        tab_tong_quan(reports, stats_df)
    with tab_kp:
        tab_kham_pha(reports)
    with tab_cmp:
        tab_so_sanh(reports)
    with tab_ex:
        tab_giai_thich()


if __name__ == "__main__":
    main()
