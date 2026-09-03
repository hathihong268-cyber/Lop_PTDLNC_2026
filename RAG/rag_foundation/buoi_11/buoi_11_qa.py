"""
Module Bước 3: Tích hợp Ngữ cảnh Đa bước và Gọi LLM (Gemini API)
Bài thực hành 2 - Buổi 11: Multi-hop Graph RAG và Ứng dụng Hỏi Đáp (QA)

Chức năng:
1. Kết nối Ngữ cảnh Graph RAG (Vector Matches + Đồ thị Đa bước Multi-hop) vào Gemini API.
2. Thiết kế và tinh chỉnh cấu trúc System Prompt & Grounding:
   - Cung cấp Schema Đồ thị (Document, Chunk, PART_OF, PARENT_OF, CAN_CU, THAY_THE, HOP_NHAT, SUA_DOI_BO_SUNG,...).
   - Cung cấp cấu trúc phân cấp văn bản pháp luật Việt Nam.
   - Ràng buộc Grounding nghiêm ngặt: Chỉ trả lời dựa trên ngữ cảnh, nêu rõ nếu thiếu thông tin, trích dẫn nguồn.
3. Hỗ trợ so sánh câu trả lời giữa các cấu hình số bước nhảy (0 hop, 1 hop, 2 hops) phục vụ Bước 4.
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv

from google import genai
from google.genai import types

# Cấu hình UTF-8 trên Windows console
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Load biến môi trường
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# Import module Bước 1 và Bước 2
from buoi_11_db import get_neo4j_driver, get_db_config
from buoi_11_retrieval import search_graph_rag_context, format_graph_context_for_prompt

# Cấu hình Gemini API
DEFAULT_GENERATION_MODEL = os.getenv("GEMINI_GENERATION_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()


# ==============================================================================
# 1. THIẾT KẾ SYSTEM PROMPT CHUYÊN SÂU CHO HỆ THỐNG GRAPH RAG PHÁP LUẬT
# ==============================================================================

SYSTEM_INSTRUCTION = """Bạn là một Chuyên gia Trợ lý Pháp lý AI cao cấp chuyên phân tích và tra cứu hệ thống Văn bản Quy phạm Pháp luật Việt Nam dựa trên Cơ sở Tri thức Đồ thị (Graph RAG).

=== 1. LƯỢC ĐỒ DỮ LIỆU ĐỒ THỊ (GRAPH SCHEMA) ===
Hệ thống đồ thị tri thức lưu trữ các thực thể và quan hệ pháp lý như sau:
1. Nút (:Document): Đại diện cho một văn bản quy phạm pháp luật hoàn chỉnh.
   - Các thuộc tính chính: `id`, `title` (Tên/Trích yếu), `so_ky_hieu` (Số hiệu văn bản), `loai_van_ban`, `co_quan_ban_hanh`, `ngay_ban_hanh`, `ngay_co_hieu_luc`, `tinh_trang_hieu_luc`.
2. Nút (:Chunk): Đại diện cho một phân đoạn nội dung theo cấu trúc pháp lý (Điều, Khoản, Điểm, Phần, Chương, Mục).
   - Các thuộc tính: `id`, `heading` (Tiêu đề mục), `level` (Cấp độ phân cấp), `seq_order` (Thứ tự tuần tự), `text` (Nội dung trích đoạn).
3. Mối quan hệ nội bộ cấu trúc văn bản:
   - `(:Chunk)-[:PART_OF]->(:Document)`: Phân đoạn thuộc về văn bản nào.
   - `(:Chunk)-[:PARENT_OF]->(:Chunk)`: Quan hệ phân cấp mục cha - mục con.
   - `(:Chunk)-[:NEXT]->(:Chunk)`: Thứ tự đọc tuần tự giữa các đoạn liền kề.
4. Mối quan hệ liên kết giữa các tài liệu pháp luật (Multi-hop Legal Relationships):
   - `(:Document)-[:CAN_CU]->(:Document)`: Văn bản ban hành dựa trên căn cứ thẩm quyền của luật/nghị định cấp trên.
   - `(:Document)-[:THAY_THE]->(:Document)`: Văn bản mới bãi bỏ và thay thế toàn bộ hiệu lực của văn bản cũ.
   - `(:Document)-[:HOP_NHAT]->(:Document)`: Văn bản hợp nhất kết hợp nội dung từ văn bản gốc và các văn bản sửa đổi.
   - `(:Document)-[:SUA_DOI_BO_SUNG]->(:Document)`: Văn bản sửa đổi, bổ sung một số điều khoản của văn bản trước.
   - `(:Document)-[:VAN_BAN_BO_SUNG]->(:Document)`: Văn bản quy định chi tiết hoặc hướng dẫn bổ sung.

=== 2. NGUYÊN TẮC TRẢ LỜI NGHIÊM NGẶT (STRICT GROUNDING) ===
1. CHỈ SỬ DỤNG THÔNG TIN TRONG NGỮ CẢNH: Mọi thông tin, kết luận, điều khoản bạn đưa ra BẮT BUỘC phải dựa hoàn toàn vào các đoạn văn bản (Direct Matches), đường dẫn liên kết đồ thị (Graph Traversal), và các phân đoạn mở rộng (Multi-hop Context) được cung cấp bên dưới.
2. TUYỆT ĐỐI KHÔNG SUY ĐOÁN NGOÀI DỮ LIỆU: Nếu ngữ cảnh được cung cấp KHÔNG chứa đủ thông tin để trả lời toàn bộ hoặc một phần câu hỏi, bạn PHẢI nêu rõ: "Dựa trên ngữ cảnh và đồ thị tri thức hiện có, không có đủ thông tin về [nội dung thiếu]" thay vì tự suy đoán hoặc sử dụng kiến thức ngoài.
3. GIẢI THÍCH ĐƯỜNG DẪN QUAN HỆ ĐA BƯỚC: Khi câu hỏi yêu cầu xác định mối quan hệ giữa các tài liệu (như văn bản bị thay thế, văn bản căn cứ, văn bản hợp nhất), hãy chỉ rõ chuỗi liên kết đồ thị (Ví dụ: `Nghị định 46/2023/NĐ-CP -[:THAY_THE]-> Nghị định 73/2016/NĐ-CP`) và giải thích chi tiết nội dung liên quan dựa trên các đoạn trích dẫn thu thập được từ bước nhảy đó.
4. TRÍCH DẪN NGUỒN CHÍNH XÁC: Luôn ghi rõ Số ký hiệu văn bản, Tên văn bản, Tiêu đề điều/khoản tương ứng cho từng luận điểm.

=== 3. ĐỊNH DẠNG CÂU TRẢ LỜI ===
Trình bày câu trả lời theo cấu trúc rõ ràng, chuyên nghiệp bằng Tiếng Việt Markdown:
- **1. Tóm tắt câu trả lời (Direct Answer)**: Trả lời trực diện, súc tích trọng tâm câu hỏi.
- **2. Phân tích chi tiết & Căn cứ pháp lý**: Trình bày từng nội dung cụ thể với trích dẫn điều khoản.
- **3. Mối quan hệ liên kết đồ thị (nếu có đa bước)**: Nêu rõ văn bản liên quan và đường dẫn quan hệ được phát hiện.
- **4. Nguồn trích dẫn (Citations)**: Liệt kê danh sách các văn bản và điều khoản đã sử dụng.
"""


# ==============================================================================
# 2. KHỞI TẠO CLIENT GEMINI VÀ XÂY DỰNG PROMPT
# ==============================================================================

def get_gemini_client(api_key: Optional[str] = None) -> genai.Client:
    """Khởi tạo Google GenAI Client."""
    key = (api_key or GEMINI_API_KEY).strip()
    if not key:
        raise ValueError(
            "GEMINI_API_KEY chưa được cấu hình. Vui lòng kiểm tra file .env hoặc biến môi trường!"
        )
    return genai.Client(api_key=key)


def build_qa_prompt(query: str, retrieval_data: Dict[str, Any]) -> str:
    """
    Xây dựng User Prompt kết hợp câu hỏi của người dùng và toàn bộ ngữ cảnh Graph RAG.
    """
    formatted_context = retrieval_data.get("formatted_context", "")
    if not formatted_context:
        formatted_context = format_graph_context_for_prompt(retrieval_data)

    user_prompt = f"""Dưới đây là Ngữ cảnh dữ liệu được truy xuất từ Hệ thống Graph RAG (bao gồm các phân đoạn văn bản khớp trực tiếp bằng Vector và các mối quan hệ mở rộng Đa bước):

{formatted_context}

--------------------------------------------------------------------------------
CÂU HỎI CẦN GIẢI ĐÁP:
{query.strip()}
--------------------------------------------------------------------------------

Hãy dựa vào các nguyên tắc trong System Instruction để trả lời câu hỏi trên một cách chính xác, trung thực với ngữ cảnh và đầy đủ căn cứ pháp lý."""

    return user_prompt


# ==============================================================================
# 3. HÀM TẠO CÂU TRẢ LỜI ĐA BƯỚC BẰNG GEMINI API (GENERATION PIPELINE)
# ==============================================================================

def generate_graph_rag_answer(
    query: str,
    top_k: int = 3,
    num_hops: int = 1,
    rel_types: Optional[List[str]] = None,
    chunks_per_hop_doc: int = 2,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: float = 0.1,
    driver: Optional[Any] = None,
    database: Optional[str] = None
) -> Dict[str, Any]:
    """
    Quy trình tích hợp hoàn chỉnh từ Truy vấn Ngữ cảnh Đa bước (Bước 2) tới Sinh Câu trả lời LLM (Bước 3):

    1. Thực hiện tìm kiếm Vector + Graph Multi-hop bằng `search_graph_rag_context`.
    2. Đóng gói Prompt hệ thống chuyên sâu và User Prompt chứa Ngữ cảnh.
    3. Gửi yêu cầu tới Gemini API để tạo câu trả lời với kiểm soát chặt chẽ.
    4. Trả về kết quả hoàn chỉnh bao gồm câu trả lời, bằng chứng pháp lý và thời gian xử lý.

    Args:
        query: Câu hỏi người dùng.
        top_k: Số chunk tìm kiếm trực tiếp (mặc định: 3).
        num_hops: Số bước nhảy đa bước (0 = chỉ vector; 1 = 1 hop; 2 = 2 hops...).
        rel_types: Danh sách quan hệ pháp luật cho phép duyệt.
        chunks_per_hop_doc: Số chunk lấy từ mỗi văn bản liên quan.
        model_name: Tên mô hình Gemini (mặc định: gemini-2.5-flash).
        api_key: Khóa API Gemini (tự động lấy từ .env nếu bỏ trống).
        temperature: Độ sáng tạo của LLM (khuyến nghị 0.0 - 0.2 cho hỏi đáp luật).
        driver: Neo4j Driver (tùy chọn).
        database: Tên Neo4j database (tùy chọn).

    Returns:
        Dict chứa câu trả lời đầy đủ, metadata ngữ cảnh, đường dẫn liên kết, và metrics.
    """
    model_id = model_name or DEFAULT_GENERATION_MODEL
    key = api_key or GEMINI_API_KEY

    # Bước 3.1: Truy vấn ngữ cảnh Đồ thị Đa bước (Gọi module Bước 2)
    t_start = time.time()
    retrieval_res = search_graph_rag_context(
        query=query,
        top_k=top_k,
        num_hops=num_hops,
        rel_types=rel_types,
        chunks_per_hop_doc=chunks_per_hop_doc,
        driver=driver,
        database=database
    )
    retrieval_time = time.time() - t_start

    # Bước 3.2: Xây dựng Prompt
    user_prompt = build_qa_prompt(query, retrieval_res)

    # Bước 3.3: Gọi Gemini Generation API
    llm_error = None
    generated_text = ""
    llm_time = 0.0

    try:
        client = get_gemini_client(key)
        t_llm_start = time.time()

        # Cấu hình sinh nội dung với System Instruction
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=temperature,
            max_output_tokens=2048,
        )

        response = client.models.generate_content(
            model=model_id,
            contents=user_prompt,
            config=config
        )

        llm_time = time.time() - t_llm_start
        if hasattr(response, "text") and response.text:
            generated_text = response.text.strip()
        else:
            generated_text = "[!] LLM không trả về văn bản phản hồi."

    except Exception as e:
        llm_error = str(e)
        generated_text = f"[!] Lỗi khi gọi Gemini API ({model_id}): {llm_error}"

    total_time = time.time() - t_start

    # Trích xuất danh sách nguồn văn bản đã sử dụng
    sources = []
    seen_so = set()
    for c in retrieval_res.get("all_chunks", []):
        so = c.get("doc_so_ky_hieu")
        if so and so not in seen_so:
            seen_so.add(so)
            sources.append({
                "so_ky_hieu": so,
                "title": c.get("doc_title"),
                "co_quan": c.get("doc_co_quan_ban_hanh"),
                "hop_level": c.get("hop_level", 0),
                "type": c.get("retrieval_type", "DIRECT")
            })

    return {
        "query": query,
        "answer": generated_text,
        "num_hops": num_hops,
        "top_k": top_k,
        "model_name": model_id,
        "temperature": temperature,
        "retrieval_data": retrieval_res,
        "traversal_paths": retrieval_res.get("traversal_paths", []),
        "sources": sources,
        "error": llm_error,
        "metrics": {
            "retrieval_time_s": retrieval_time,
            "llm_generation_time_s": llm_time,
            "total_pipeline_time_s": total_time,
            "num_direct_chunks": len(retrieval_res.get("initial_chunks", [])),
            "num_traversal_paths": len(retrieval_res.get("traversal_paths", [])),
            "num_hop_chunks": len(retrieval_res.get("hop_chunks", [])),
            "num_total_chunks": len(retrieval_res.get("all_chunks", []))
        }
    }


# ==============================================================================
# 4. HÀM SO SÁNH CÂU TRẢ LỜI THEO SỐ BƯỚC NHẢY (0-HOP VS 1-HOP VS 2-HOPS)
# ==============================================================================

def compare_hops_answers(
    query: str,
    hops_list: List[int] = [0, 1],
    top_k: int = 3,
    model_name: Optional[str] = None
) -> Dict[int, Dict[str, Any]]:
    """
    Thực hiện chạy cùng 1 câu hỏi với các cấu hình số bước nhảy khác nhau (0 hop, 1 hop,...)
    để so sánh sự khác biệt và chứng minh hiệu quả của cơ chế Graph Multi-hop.
    """
    results = {}
    driver = get_neo4j_driver()
    try:
        for hops in hops_list:
            print(f"\n[*] Đang xử lý câu hỏi với cấu hình {hops} HOP(S)...")
            res = generate_graph_rag_answer(
                query=query,
                top_k=top_k,
                num_hops=hops,
                model_name=model_name,
                driver=driver
            )
            results[hops] = res
    finally:
        driver.close()

    return results


def print_qa_result(res: Dict[str, Any]):
    """Hiển thị kết quả Hỏi Đáp chi tiết trên Terminal."""
    print("\n" + "=" * 90)
    print(f"🏛️ KẾT QUẢ HỎI ĐÁP PHÁP LUẬT (GRAPH RAG - BƯỚC 3)")
    print(f"❓ Câu hỏi: {res['query']}")
    print(f"⚙️ Cấu hình: Mô hình: {res['model_name']} | Số bước nhảy (Hops): {res['num_hops']} | Top-k: {res['top_k']}")
    print("=" * 90)

    m = res["metrics"]
    print(f"⏱️ THỜI GIAN:")
    print(f"  • Truy xuất Ngữ cảnh : {m['retrieval_time_s']:.3f}s ({m['num_direct_chunks']} chunk trực tiếp + {m['num_hop_chunks']} chunk đa bước)")
    print(f"  • Gemini Sinh câu trả lời: {m['llm_generation_time_s']:.3f}s")
    print(f"  • Tổng thời gian      : {m['total_pipeline_time_s']:.3f}s")

    if res["traversal_paths"]:
        print(f"\n🔗 ĐƯỜNG DẪN QUAN HỆ ĐỒ THỊ KHÁM PHÁ ĐƯỢC ({len(res['traversal_paths'])} liên kết):")
        for idx, p in enumerate(res["traversal_paths"], 1):
            rels_str = " -> ".join([f"[:{r['type']} ({r.get('relationship','')})]" for r in p["relationships"]])
            print(f"  {idx}. [{p['seed_so_ky_hieu']}] --{rels_str}--> [{p['target_so_ky_hieu']}]")

    print("\n" + "-" * 90)
    print("💡 CÂU TRẢ LỜI TỪ GEMINI LLM:")
    print("-" * 90)
    print(res["answer"])

    print("\n" + "-" * 90)
    print("📚 DANH SÁCH VĂN BẢN NGUỒN SỬ DỤNG:")
    print("-" * 90)
    for s in res.get("sources", []):
        print(f"  • {s['so_ky_hieu']}: {s['title'][:70]}... (Hop: {s['hop_level']}, Cơ quan: {s['co_quan']})")
    print("=" * 90)


# ==============================================================================
# 5. CLI CHẠY TRỰC TIẾP
# ==============================================================================

if __name__ == "__main__":
    print("=" * 90)
    print(" BƯỚC 3: TÍCH HỢP NGỮ CẢNH ĐA BƯỚC VÀO GEMINI LLM API (GRAPH RAG QA)")
    print("=" * 90)

    sample_query = "Nghị định 46/2023/NĐ-CP thay thế cho nghị định nào, và nghị định bị thay thế đó có nội dung gì nổi bật về kinh doanh bảo hiểm?"
    
    print(f"\n[*] Đang chạy thử nghiệm câu hỏi mẫu:")
    print(f"    \"{sample_query}\"\n")

    try:
        qa_result = generate_graph_rag_answer(
            query=sample_query,
            top_k=3,
            num_hops=1,
            model_name=DEFAULT_GENERATION_MODEL
        )
        print_qa_result(qa_result)
    except Exception as e:
        print(f"\n[!] Lỗi khi thực hiện: {e}")
        print("    Vui lòng kiểm tra Neo4j (kb-hops) và API Key trong .env.")
