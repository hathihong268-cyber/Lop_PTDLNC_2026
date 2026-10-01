# BÁO CÁO PHÂN TÍCH VÀ KIỂM THỬ TÁI SỬ DỤNG DỮ LIỆU & RETRIEVER RBAC (BUỔI 17)

Báo cáo này liên kết trực tiếp với báo cáo phân tích RBAC tại [`buoi_17/outputs/rbac_reuse_report.md`](file:///c:/Users/admins/Desktop/05_m%E1%BA%ABu/Rag_thuchanh/RAG/rag_foundation/buoi_17/outputs/rbac_reuse_report.md) và kết quả kiểm thử truy xuất an toàn tại [`buoi_17/outputs/secure_retrieval_test.md`](file:///c:/Users/admins/Desktop/05_m%E1%BA%ABu/Rag_thuchanh/RAG/rag_foundation/buoi_17/outputs/secure_retrieval_test.md).

## 1. Phân bố Quyền Hạn RBAC trên Tập Dữ liệu (720 Chunks)

* **Admin:** 720/720 chunks (100.0%)
* **Risk_Officer:** 563/720 chunks (78.2%)
* **Employee:** 563/720 chunks (78.2%)
* **HR_Manager:** 418/720 chunks (58.1%)
* **Guest:** 261/720 chunks (36.25%)

## 2. Kiểm thử Phân quyền Across 5 Roles + Unknown Role

* **HR_Manager:** Truy cập thành công chunk quy định nhân sự nhạy cảm `doc_44209_dieu_24`.
* **Risk_Officer / Employee / Guest:** Bị chặn 100% đối với `doc_44209_dieu_24` (Lọc trước retrieval/context).
* **Unknown Role (`Unknown_Hacker_Role`):** Kích hoạt Default Deny, chuyển hướng về quyền `Guest` và ghi nhận cảnh báo an toàn.

## 3. Kết luận Trạng thái (Final Status)

```text
RBAC REUSED: YES
FILTER BEFORE RETRIEVAL: PASS
UNKNOWN ROLE DEFAULT DENY: PASS
```
