# BÁO CÁO ĐÁNH GIÁ DỮ LIỆU VÀ KẾT QUẢ AI COMPLIANCE GAP CHECKER (BUỔI 17)

## 1. Thông báo Khoảng trống Dữ liệu (Data Gap Notice)

> ⚠️ **BÁO CÁO THIẾU DỮ LIỆU ĐỐI CHIẾU (DATA GAP):**
> * Kết quả kiểm tra từ [`buoi_17/outputs/gap_input_catalog.md`](file:///c:/Users/admins/Desktop/05_m%E1%BA%ABu/Rag_thuchanh/RAG/rag_foundation/buoi_17/outputs/gap_input_catalog.md) xác nhận tập dữ liệu hiện tại chứa 15/15 văn bản đều là **EXTERNAL_REQUIREMENT** (Thông tư NHNN, Nghị định Chính phủ, Luật).
> * Trong corpus **KHÔNG CÓ VĂN BẢN QUY ĐỊNH NỘI BỘ (INTERNAL_POLICY)**.
> * Tuân thủ nguyên tắc thực tế: **Không tự ý sáng tạo văn bản nội bộ giả và không đưa ra kết luận tuân thủ (ĐÁP ỨNG / THIẾU / CHÊNH LỆCH) khi chưa có dữ liệu đối chiếu**.

---

## 2. Thiết kế Kiến trúc AI Compliance Gap Checker (8 Bước)

Dù dữ liệu chưa đủ đối chiếu 2 phía, module [`buoi_17/scripts/compliance_gap.py`](file:///c:/Users/admins/Desktop/05_m%E1%BA%ABu/Rag_thuchanh/RAG/rag_foundation/buoi_17/scripts/compliance_gap.py) đã được thiết lập hoàn chỉnh theo đúng luồng chuẩn 8 bước:

```text
1. Nhận Yêu cầu / Điều khoản bên ngoài (External Requirement)
2. Hybrid + Rerank tìm Điều khoản Nội bộ liên quan trong phạm vi RBAC cho phép
3. Trích xuất gợi ý từ Neo4j Knowledge Graph (nếu có quan hệ hữu ích, không bịa edge)
4. Đóng gói Evidence Package 2 phía:
   - External requirement & External citation
   - Internal evidence & Internal citation
5. Phân loại trạng thái Tuân thủ:
   - DAP_UNG (Đã có quy định nội bộ đáp ứng đủ)
   - THIEU (Chưa có quy định nội bộ tương ứng)
   - CHENH_LECH (Có quy định nhưng lệch nội dung/điều kiện)
   - CHUA_DU_BANG_CHUNG (Không đủ dữ liệu đối chiếu)
6. Giải thích lý do ngắn gọn (reason)
7. Tính toán điểm tin cậy (confidence)
8. Đánh dấu mặc định review_status = NEEDS_HUMAN_REVIEW (Không coi AI là kết luận kiểm toán cuối cùng)
```

---

## 3. Bảng Kết quả Ghi nhận tại File CSV [`compliance_gap_results.csv`](file:///c:/Users/admins/Desktop/05_m%E1%BA%ABu/Rag_thuchanh/RAG/rag_foundation/buoi_17/outputs/compliance_gap_results.csv)

| Yêu cầu Bên ngoài (External Req) | Trích dẫn Bên ngoài | Bằng chứng Nội bộ (Internal Evidence) | Trạng thái (Classification) | Lý do (Reason) | Human Review |
| :--- | :--- | :--- | :---: | :--- | :---: |
| Vận chuyển tiền mặt phải có xe chuyên dùng... | `[01/2014/TT-NHNN \| Điều 50]` | Không có dữ liệu `INTERNAL_POLICY` | **`CHUA_DU_BANG_CHUNG`** | DATA GAP: Missing Internal Policy Corpus | `NEEDS_HUMAN_REVIEW` |
| Tiêu chuẩn thủ kho tiền, thủ quỹ... | `[01/2014/TT-NHNN \| Điều 24]` | Không có dữ liệu `INTERNAL_POLICY` | **`CHUA_DU_BANG_CHUNG`** | DATA GAP: Missing Internal Policy Corpus | `NEEDS_HUMAN_REVIEW` |
| Tỷ lệ an toàn vốn tối thiểu (CAR) >= 8% | `[41/2016/TT-NHNN \| Điều 3]` | Không có dữ liệu `INTERNAL_POLICY` | **`CHUA_DU_BANG_CHUNG`** | DATA GAP: Missing Internal Policy Corpus | `NEEDS_HUMAN_REVIEW` |

---

## 4. Kết luận Trạng thái (Final Status)

```text
GAP CHECKER: PASS
HUMAN REVIEW REQUIRED: YES
```
