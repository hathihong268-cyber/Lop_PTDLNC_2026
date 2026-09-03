"""Giao diện Streamlit để khám phá chunks đã tạo ở output/ của Buổi 5."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
REPORTS = OUTPUT / "reports"
CHUNKS = OUTPUT / "chunks"
STRATEGIES = ("fixed-size", "semantic", "hierarchical")


@st.cache_data(show_spinner=False)
def load_reports() -> list[dict]:
    reports = []
    for path in sorted(REPORTS.glob("*__report.json")):
        reports.append(json.loads(path.read_text(encoding="utf-8")))
    return reports


@st.cache_data(show_spinner=False)
def load_chunks(source: str, strategy: str) -> list[dict]:
    path = CHUNKS / f"{Path(source).stem}__{strategy}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []


def stats_frame(reports: list[dict]) -> pd.DataFrame:
    rows = []
    for report in reports:
        for strategy, values in report["statistics"].items():
            rows.append({"Tài liệu": report["source"], "Chiến lược": strategy,
                         "Số chunk": values["chunk_count"], "Độ dài TB": values["length_avg"],
                         "Nhỏ nhất": values["length_min"], "Lớn nhất": values["length_max"]})
    return pd.DataFrame(rows)


def main() -> None:
    st.set_page_config(page_title="Khám phá chunks RAG – Buổi 5", page_icon="📚", layout="wide")
    st.title("Khám phá chunks RAG – Buổi 5")
    st.caption("Dữ liệu chỉ đọc từ thư mục output; giao diện không gọi API, không tạo embedding.")

    reports = load_reports()
    if not reports:
        st.warning("Chưa có báo cáo trong output/. Hãy chạy rag_pipeline.py --write trước.")
        st.code(r".\RAG\rag_foundation\buoi_05\.venv\Scripts\python.exe .\RAG\rag_foundation\buoi_05\src\rag_pipeline.py --write", language="powershell")
        return

    sources = [report["source"] for report in reports]
    with st.sidebar:
        st.header("Bộ lọc")
        source = st.selectbox("Tài liệu", sources)
        strategy = st.selectbox("Chiến lược", STRATEGIES)
        query = st.text_input("Tìm trong nội dung", placeholder="Ví dụ: tổ chức tín dụng")

    selected_report = next(report for report in reports if report["source"] == source)
    st.subheader("So sánh chiến lược")
    frame = stats_frame(reports)
    selected_stats = frame[frame["Tài liệu"] == source].set_index("Chiến lược")
    st.bar_chart(selected_stats["Số chunk"])
    st.dataframe(selected_stats, use_container_width=True)

    if selected_report.get("ocr_used"):
        st.info("Tài liệu này dùng OCR fallback LlamaParse vì text layer PDF không đáng tin cậy.")
    for warning in selected_report.get("warnings", []):
        st.warning(warning)

    chunks = load_chunks(source, strategy)
    if query.strip():
        needle = query.casefold()
        chunks = [chunk for chunk in chunks if needle in chunk["text"].casefold()]
    if not chunks:
        st.warning("Không có chunk nào khớp bộ lọc hiện tại.")
        return

    lengths = [len(chunk["text"]) for chunk in chunks]
    col1, col2, col3 = st.columns(3)
    col1.metric("Chunk đang hiển thị", len(chunks))
    col2.metric("Độ dài trung bình", f"{sum(lengths) / len(lengths):.0f} ký tự")
    col3.metric("Khoảng độ dài", f"{min(lengths)}–{max(lengths)}")

    table = pd.DataFrame([
        {"chunk_id": chunk["chunk_id"], "trang": f'{chunk["page_start"]}–{chunk["page_end"]}',
         "ký tự": len(chunk["text"]), "cấu trúc": " › ".join(chunk.get("structure", {}).values()) or "—"}
        for chunk in chunks
    ])
    st.subheader(f"{strategy}: {source}")
    st.dataframe(table, use_container_width=True, hide_index=True)

    chunk_ids = [chunk["chunk_id"] for chunk in chunks]
    chosen_id = st.selectbox("Xem chi tiết chunk", chunk_ids)
    chosen = next(chunk for chunk in chunks if chunk["chunk_id"] == chosen_id)
    st.json({key: value for key, value in chosen.items() if key != "text"})
    st.text_area("Nội dung chunk", chosen["text"], height=320, disabled=True)


if __name__ == "__main__":
    main()
