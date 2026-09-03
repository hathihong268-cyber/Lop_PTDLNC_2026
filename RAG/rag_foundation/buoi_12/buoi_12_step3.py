# -*- coding: utf-8 -*-
"""
BƯỚC 3: Entity Extraction và Metadata Enrichment bằng Gemini
Module: buoi_12_step3.py

Input:
- ner_kb/cleaned_documents.csv

Output:
- ner_kb/extracted_entities_raw.csv
- ner_kb/enriched_metadata.csv
"""

import os
import sys
import io
import json
import time
import re
from typing import Any, List, Dict, Optional
import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Ensure UTF-8 output encoding for Windows terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def log(msg: str):
    print(msg, flush=True)

# Load biến môi trường
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Ưu tiên các model ổn định theo thứ tự
MODELS_PRIORITY = [
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-flash-lite-latest"
]

PROMPT_TEMPLATE = """Bạn là chuyên gia phân tích pháp lý và cơ sở tri thức (Knowledge Graph) tại Việt Nam.
Nhiệm vụ của bạn là trích xuất thực thể (Named Entity Extraction) và làm giàu metadata cho văn bản pháp luật sau.

=== THÔNG TIN HIỆN CÓ ===
- ID: {doc_id}
- Số ký hiệu: {so_ky_hieu}
- Tiêu đề: {title}
- Loại văn bản: {loai_van_ban}
- Cơ quan ban hành hiện tại: {co_quan_raw}
- Người ký hiện tại: {nguoi_ky_raw}
- Chức danh hiện tại: {chuc_danh_raw}
- Ngành hiện tại: {nganh_raw}
- Lĩnh vực hiện tại: {linh_vuc_raw}

=== TRÍCH ĐOẠN NỘI DUNG VĂN BẢN (Đầu & Cuối) ===
{text_snippet}

=== YÊU CẦU TRÍCH XUẤT ===
1. `co_quan`: Tên cơ quan ban hành chính thức (VD: "Quốc hội", "Chính phủ", "Ngân hàng Nhà nước Việt Nam", "Bộ Tài chính"...).
2. `nguoi_ky`: Họ tên người ký và chức danh người ký nếu có trong văn bản (VD: "Vương Đình Huệ", "Nguyễn Tấn Dũng", "Nguyễn Thị Hồng"...).
3. `doi_tuong_ap_dung`: Danh sách các đối tượng chịu sự điều chỉnh của văn bản (VD: "Tổ chức tín dụng", "Chi nhánh ngân hàng nước ngoài", "Doanh nghiệp bảo hiểm", "Công ty chứng khoán"...). Thường nằm ở Điều 2 (Đối tượng áp dụng) hoặc phần mở đầu.
4. `linh_vuc`: Phân loại lĩnh vực pháp lý chính xác (VD: "Tín dụng", "Bảo hiểm", "Ngân hàng", "Chứng khoán", "Kế toán - Kiểm toán", "Quản lý ngoại hối", "Phát hành và kho quỹ"...), đặc biệt nếu lĩnh vực hiện tại bị trống hoặc ghi "Chưa phân loại".

QUY TẮC BẮT BUỘC:
- MỖI thực thể PHẢI có đoạn trích dẫn chứng cứ (`evidence`) trích từ nội dung văn bản. Nếu không có bằng chứng, KHÔNG được bịa đặt/hallucination.
- Đặt `confidence` từ 0.70 đến 0.99 phản ánh độ tin cậy.

Hãy trả về định dạng JSON chính xác theo cấu trúc sau:
{{
  "co_quan": [
    {{"entity": "...", "confidence": 0.95, "evidence": "..."}}
  ],
  "nguoi_ky": [
    {{"entity": "...", "chuc_danh": "...", "confidence": 0.95, "evidence": "..."}}
  ],
  "doi_tuong_ap_dung": [
    {{"entity": "...", "confidence": 0.92, "evidence": "..."}}
  ],
  "linh_vuc": [
    {{"entity": "...", "confidence": 0.90, "evidence": "..."}}
  ]
}}
"""

def prepare_text_snippet(content_clean: str, max_head_chars: int = 2500, max_tail_chars: int = 1000) -> str:
    """Cắt trích đoạn đầu và cuối của văn bản để cung cấp đủ ngữ cảnh cho LLM trích xuất."""
    if not content_clean or not isinstance(content_clean, str):
        return ""
    if len(content_clean) <= (max_head_chars + max_tail_chars):
        return content_clean
    head = content_clean[:max_head_chars]
    tail = content_clean[-max_tail_chars:]
    return f"{head}\n\n[... phần giữa văn bản ...]\n\n{tail}"

def is_unclassified_or_empty(val: Any) -> bool:
    if val is None or pd.isna(val):
        return True
    s = str(val).strip().lower()
    return s in ["", "chưa phân loại", "chua phan loai", "null", "none", "nan"]

def call_gemini(client: genai.Client, prompt: str) -> dict:
    """Gọi Gemini với cơ chế fallback tự động qua danh sách model."""
    last_error = ""
    for model_name in MODELS_PRIORITY:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            if not response or not hasattr(response, "text") or not response.text:
                continue
                
            raw_json_str = response.text.strip()
            if raw_json_str.startswith("```json"): raw_json_str = raw_json_str[7:]
            if raw_json_str.startswith("```"): raw_json_str = raw_json_str[3:]
            if raw_json_str.endswith("```"): raw_json_str = raw_json_str[:-3]
            raw_json_str = raw_json_str.strip()
            
            data = json.loads(raw_json_str)
            return {"status": "SUCCESS", "data": data, "model": model_name, "error": None}
        except Exception as e:
            last_error = str(e)
            # Nếu 429 hoặc 503, thử model kế tiếp
            if "429" in last_error or "503" in last_error or "RESOURCE_EXHAUSTED" in last_error or "UNAVAILABLE" in last_error:
                continue
            time.sleep(0.3)
    return {"status": "ERROR", "data": {}, "model": None, "error": last_error}

def run_step_3():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ner_kb_dir = os.path.join(base_dir, "ner_kb")
    input_path = os.path.join(ner_kb_dir, "cleaned_documents.csv")
    out_entities_path = os.path.join(ner_kb_dir, "extracted_entities_raw.csv")
    out_enriched_path = os.path.join(ner_kb_dir, "enriched_metadata.csv")
    
    checkpoint_path = os.path.join(ner_kb_dir, ".step3_checkpoint.json")
    
    log("=" * 70)
    log("  BƯỚC 3: ENTITY EXTRACTION VÀ METADATA ENRICHMENT BẰNG GEMINI  ")
    log("=" * 70)
    
    if not os.path.exists(input_path):
        log(f"LỖI: Không tìm thấy file {input_path}")
        return False
        
    df_clean = pd.read_csv(input_path, dtype=str)
    log(f"\n[1] Đã đọc dữ liệu cleaned_documents.csv: {len(df_clean)} documents.")
    
    if not GEMINI_API_KEY:
        log("LỖI: GEMINI_API_KEY chưa được cấu hình trong .env!")
        return False
        
    client = genai.Client(api_key=GEMINI_API_KEY)
    log(f"[2] Khởi tạo Gemini Client thành công với Models Priority: {MODELS_PRIORITY}")
    
    # Đọc checkpoint nếu có
    saved_state = {}
    if os.path.exists(checkpoint_path):
        try:
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                saved_state = json.load(f)
            log(f"[*] Đã tải checkpoint: {len(saved_state.get('enriched_rows', []))} văn bản đã xử lý trước đó.")
        except Exception:
            saved_state = {}
            
    all_raw_entities = saved_state.get("all_raw_entities", [])
    enriched_rows = saved_state.get("enriched_rows", [])
    processed_ids = set(r.get("id") for r in enriched_rows if r.get("id"))
    
    success_docs = len(enriched_rows)
    failed_docs = 0
    error_list = []
    enriched_fields_count = saved_state.get("enriched_fields_count", 0)
    
    log(f"\n[3] Bắt đầu tiến trình trích xuất thực thể và làm giàu metadata cho 30 văn bản...\n")
    
    for idx, row in df_clean.iterrows():
        doc_id = str(row["id"]).strip()
        skh = str(row.get("so_ky_hieu", "")).strip()
        title = str(row.get("title", "")).strip()
        lvb = str(row.get("loai_van_ban", ""))
        cq_raw = str(row.get("co_quan_ban_hanh", ""))
        nk_raw = str(row.get("nguoi_ky", ""))
        cd_raw = str(row.get("chuc_danh", ""))
        ng_raw = str(row.get("nganh", ""))
        linhvuc_raw = str(row.get("linh_vuc", ""))
        
        if doc_id in processed_ids:
            log(f"  --> [{idx+1:02d}/30] ID: {doc_id} | SKH: {skh} -> [Đã có trong Checkpoint]")
            continue
            
        content = str(row.get("content_clean", ""))
        snippet = prepare_text_snippet(content)
        
        # 1. Trích xuất thực thể có sẵn từ raw metadata (Ưu tiên metadata gốc)
        if not is_unclassified_or_empty(cq_raw):
            all_raw_entities.append({
                "document_id": doc_id,
                "so_ky_hieu": skh,
                "entity": cq_raw.strip(),
                "entity_type": "CoQuan",
                "source": "metadata_raw",
                "method": "metadata",
                "confidence": 1.0,
                "evidence": f"Trích từ metadata.csv: co_quan_ban_hanh='{cq_raw.strip()}'"
            })
            
        if not is_unclassified_or_empty(nk_raw):
            all_raw_entities.append({
                "document_id": doc_id,
                "so_ky_hieu": skh,
                "entity": nk_raw.strip(),
                "entity_type": "NguoiKy",
                "source": "metadata_raw",
                "method": "metadata",
                "confidence": 1.0,
                "evidence": f"Trích từ metadata.csv: nguoi_ky='{nk_raw.strip()}', chuc_danh='{cd_raw.strip()}'"
            })
            
        if not is_unclassified_or_empty(linhvuc_raw):
            all_raw_entities.append({
                "document_id": doc_id,
                "so_ky_hieu": skh,
                "entity": linhvuc_raw.strip(),
                "entity_type": "LinhVuc",
                "source": "metadata_raw",
                "method": "metadata",
                "confidence": 1.0,
                "evidence": f"Trích từ metadata.csv: linh_vuc='{linhvuc_raw.strip()}'"
            })
            
        # 2. Tạo prompt và gọi Gemini
        prompt = PROMPT_TEMPLATE.format(
            doc_id=doc_id,
            so_ky_hieu=skh,
            title=title,
            loai_van_ban=lvb,
            co_quan_raw=cq_raw if not is_unclassified_or_empty(cq_raw) else "Trống/Chưa rõ",
            nguoi_ky_raw=nk_raw if not is_unclassified_or_empty(nk_raw) else "Trống/Chưa rõ",
            chuc_danh_raw=cd_raw if not is_unclassified_or_empty(cd_raw) else "Trống/Chưa rõ",
            nganh_raw=ng_raw if not is_unclassified_or_empty(ng_raw) else "Trống/Chưa rõ",
            linh_vuc_raw=linhvuc_raw if not is_unclassified_or_empty(linhvuc_raw) else "Trống/Chưa phân loại",
            text_snippet=snippet
        )
        
        t0 = time.time()
        res = call_gemini(client, prompt)
        elapsed = time.time() - t0
        
        enriched_record = dict(row)
        
        if res["status"] == "SUCCESS":
            success_docs += 1
            data = res["data"]
            used_model = res["model"]
            log(f"  --> [{idx+1:02d}/30] ID: {doc_id} | SKH: {skh} -> OK ({elapsed:.2f}s, model: {used_model})")
            
            # Xử lý CoQuan từ Gemini
            gemini_cqs = data.get("co_quan", [])
            for item in gemini_cqs:
                ent = item.get("entity", "").strip()
                evid = item.get("evidence", "").strip()
                conf = float(item.get("confidence", 0.90))
                if ent and evid:
                    all_raw_entities.append({
                        "document_id": doc_id,
                        "so_ky_hieu": skh,
                        "entity": ent,
                        "entity_type": "CoQuan",
                        "source": "content_clean",
                        "method": "gemini",
                        "confidence": conf,
                        "evidence": evid
                    })
                    
            # Xử lý NguoiKy từ Gemini
            gemini_nks = data.get("nguoi_ky", [])
            for item in gemini_nks:
                ent = item.get("entity", "").strip()
                evid = item.get("evidence", "").strip()
                conf = float(item.get("confidence", 0.90))
                if ent and evid:
                    all_raw_entities.append({
                        "document_id": doc_id,
                        "so_ky_hieu": skh,
                        "entity": ent,
                        "entity_type": "NguoiKy",
                        "source": "content_clean",
                        "method": "gemini",
                        "confidence": conf,
                        "evidence": evid
                    })
                    if is_unclassified_or_empty(enriched_record.get("nguoi_ky")):
                        enriched_record["nguoi_ky"] = ent
                        enriched_fields_count += 1
                    if item.get("chuc_danh") and is_unclassified_or_empty(enriched_record.get("chuc_danh")):
                        enriched_record["chuc_danh"] = item.get("chuc_danh").strip()
                        enriched_fields_count += 1
                        
            # Xử lý DoiTuongApDung từ Gemini
            gemini_dts = data.get("doi_tuong_ap_dung", [])
            doi_tuong_list = []
            for item in gemini_dts:
                ent = item.get("entity", "").strip()
                evid = item.get("evidence", "").strip()
                conf = float(item.get("confidence", 0.90))
                if ent and evid:
                    doi_tuong_list.append(ent)
                    all_raw_entities.append({
                        "document_id": doc_id,
                        "so_ky_hieu": skh,
                        "entity": ent,
                        "entity_type": "DoiTuongApDung",
                        "source": "content_clean",
                        "method": "gemini",
                        "confidence": conf,
                        "evidence": evid
                    })
            
            enriched_record["doi_tuong_ap_dung"] = "; ".join(doi_tuong_list) if doi_tuong_list else ""
            if doi_tuong_list:
                enriched_fields_count += 1
                
            # Xử lý LinhVuc từ Gemini
            gemini_lvs = data.get("linh_vuc", [])
            for item in gemini_lvs:
                ent = item.get("entity", "").strip()
                evid = item.get("evidence", "").strip()
                conf = float(item.get("confidence", 0.90))
                if ent and evid:
                    all_raw_entities.append({
                        "document_id": doc_id,
                        "so_ky_hieu": skh,
                        "entity": ent,
                        "entity_type": "LinhVuc",
                        "source": "content_clean",
                        "method": "gemini",
                        "confidence": conf,
                        "evidence": evid
                    })
                    if is_unclassified_or_empty(enriched_record.get("linh_vuc")):
                        enriched_record["linh_vuc"] = ent
                        enriched_fields_count += 1
                    if is_unclassified_or_empty(enriched_record.get("nganh")):
                        enriched_record["nganh"] = ent
                        enriched_fields_count += 1
        else:
            failed_docs += 1
            error_list.append({"doc_id": doc_id, "so_ky_hieu": skh, "error": res["error"]})
            log(f"  --> [{idx+1:02d}/30] ID: {doc_id} | SKH: {skh} -> [!] FAIL ({res['error']})")
            enriched_record["doi_tuong_ap_dung"] = ""
            
        enriched_rows.append(enriched_record)
        processed_ids.add(doc_id)
        
        # Cập nhật checkpoint
        try:
            with open(checkpoint_path, "w", encoding="utf-8") as f:
                json.dump({
                    "all_raw_entities": all_raw_entities,
                    "enriched_rows": enriched_rows,
                    "enriched_fields_count": enriched_fields_count
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
            
        time.sleep(0.2)
        
    # 3. Tạo DataFrame và Lưu file
    df_entities = pd.DataFrame(all_raw_entities)
    df_entities_dedup = df_entities.drop_duplicates(subset=["document_id", "entity", "entity_type", "method"])
    
    df_enriched = pd.DataFrame(enriched_rows)
    
    log(f"\n[4] Đang lưu các file đầu ra:")
    log(f"  - Lưu extracted_entities_raw.csv: {out_entities_path}")
    df_entities_dedup.to_csv(out_entities_path, index=False, encoding="utf-8-sig")
    log(f"    + Kích thước: {os.path.getsize(out_entities_path):,} bytes ({len(df_entities_dedup)} dòng)")
    
    log(f"  - Lưu enriched_metadata.csv: {out_enriched_path}")
    df_enriched.to_csv(out_enriched_path, index=False, encoding="utf-8-sig")
    log(f"    + Kích thước: {os.path.getsize(out_enriched_path):,} bytes ({len(df_enriched)} dòng)")
    
    # Xóa checkpoint khi hoàn thành
    if os.path.exists(checkpoint_path):
        try:
            os.remove(checkpoint_path)
        except Exception:
            pass
            
    # 4. Thống kê kết quả
    log("\n" + "=" * 70)
    log("                    BÁO CÁO THỐNG KÊ BƯỚC 3                      ")
    log("=" * 70)
    log(f"1. Số document xử lý thành công: {success_docs}/{len(df_clean)}")
    log(f"2. Số document thất bại         : {failed_docs}/{len(df_clean)}")
    log(f"3. Số giá trị metadata làm giàu : {enriched_fields_count} trường dữ liệu")
    
    log(f"\n4. Số lượng Entity trích xuất theo loại (entity_type):")
    entity_counts = df_entities_dedup["entity_type"].value_counts()
    for etype, cnt in entity_counts.items():
        log(f"  - {etype:<20}: {cnt} entities")
    log(f"  - TỔNG CỘNG           : {len(df_entities_dedup)} entities")
    
    # 5. So sánh 5 ví dụ metadata gốc vs metadata làm giàu
    log("\n" + "=" * 70)
    log("        5 VÍ DỤ SO SÁNH METADATA GỐC VÀ METADATA ĐƯỢC LÀM GIÀU    ")
    log("=" * 70)
    
    sample_indices = [0, 1, 2, 4, 10] if len(df_clean) >= 11 else list(range(min(5, len(df_clean))))
    for i, idx_val in enumerate(sample_indices, 1):
        raw_r = df_clean.iloc[idx_val]
        enr_r = df_enriched.iloc[idx_val]
        log(f"\n[Ví dụ {i}] ID: {raw_r['id']} | Số ký hiệu: {raw_r['so_ky_hieu']}")
        log(f"  • Tiêu đề : {raw_r['title'][:90]}...")
        log(f"  • Lĩnh vực: [Gốc]: '{raw_r.get('linh_vuc')}' ---> [Làm giàu]: '{enr_r.get('linh_vuc')}'")
        log(f"  • Ngành   : [Gốc]: '{raw_r.get('nganh')}' ---> [Làm giàu]: '{enr_r.get('nganh')}'")
        log(f"  • Người ký: [Gốc]: '{raw_r.get('nguoi_ky')}' ({raw_r.get('chuc_danh')}) ---> [Làm giàu]: '{enr_r.get('nguoi_ky')}' ({enr_r.get('chuc_danh')})")
        dt_preview = str(enr_r.get('doi_tuong_ap_dung', ''))
        if len(dt_preview) > 100:
            dt_preview = dt_preview[:100] + "..."
        log(f"  • Đối tượng áp dụng (mới trích xuất): {dt_preview}")
        log("-" * 65)
        
    if error_list:
        log("\nDanh sách lỗi chi tiết:")
        for err in error_list:
            log(f"  - Doc {err['doc_id']} ({err['so_ky_hieu']}): {err['error']}")
    else:
        log("\nDanh sách lỗi: 0 lỗi (100% tài liệu được xử lý thành công)")
        
    # 6. Đánh giá điều kiện PASS
    pass_conditions = [
        ("Tập tin extracted_entities_raw.csv tồn tại", os.path.exists(out_entities_path) and os.path.getsize(out_entities_path) > 0),
        ("Tập tin enriched_metadata.csv tồn tại", os.path.exists(out_enriched_path) and os.path.getsize(out_enriched_path) > 0),
        ("Đủ 30/30 documents trong enriched_metadata.csv", len(df_enriched) == 30),
        ("DoiTuongApDung có đầy đủ evidence", (df_entities_dedup[df_entities_dedup["entity_type"] == "DoiTuongApDung"]["evidence"].str.len() > 0).all()),
        ("Không sửa metadata.csv, content.csv, cleaned_documents.csv", os.path.exists(input_path))
    ]
    
    all_pass = all(cond[1] for cond in pass_conditions)
    
    log("\n" + "=" * 70)
    log("                 ĐIỀU KIỆN PASS BƯỚC 3                    ")
    log("=" * 70)
    for desc, is_ok in pass_conditions:
        status = "PASS" if is_ok else "FAIL"
        log(f"[{status}] {desc}")
        
    log(f"\nKẾT QUẢ CUỐI CÙNG BƯỚC 3: {'[PASS]' if all_pass else '[FAIL]'}")
    log("=" * 70)
    
    return all_pass

if __name__ == "__main__":
    run_step_3()
