# BÁO CÁO KẾT QUẢ AI AUDIT CHECKLIST GENERATOR ENGINE (UC4)
**Hệ thống Sinh Danh mục Kiểm toán Tự động theo Domain & Đơn vị Agribank**

---

## 1. Tổng quan Đợt Sinh Checklist (Summary)
- **Ngày thực hiện**: 2026-08-24 21:36:47
- **Tổng số mục Checklist đã sinh**: 4 mục
- **Các Domain được kiểm tra**: An toàn kho quỹ & Vận chuyển tiền
- **Ràng buộc Trích dẫn (Citation Guardrail)**: Gắn kèm 100% Citation thật
- **Trạng thái Duyệt**: Mặc định `NEEDS_HUMAN_REVIEW` cho 100% mục checklist.

---

## 2. Bảng Tổng hợp Danh mục Kiểm toán (Audit Checklist Summary)

| Mã mục (Item ID) | Domain | Phạm vi (Unit) | Câu hỏi Kiểm toán chính | Mức độ Rủi ro | Citation văn bản gốc | Guardrail Status |
|---|---|---|---|---|---|---|
| `CHK_KHO_01` | An toàn kho quỹ & Vận chuyển tiền | `Chi nhánh loại 1` | Chi nhánh có tuân thủ đúng quy cách đóng gói tiền mặt (bó, b... | 🟡 MEDIUM | `01/2014/TT-NHNN - Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Điều 4. Đóng gói tiền mặt | doc_44209_điều_4__đóng_gói_tiền_mặt_4` | `NEEDS_HUMAN_REVIEW` |
| `CHK_KHO_02` | An toàn kho quỹ & Vận chuyển tiền | `Chi nhánh loại 1` | Việc niêm phong tiền mặt đã qua lưu thông, ngoại tệ và giấy ... | 🔴 HIGH | `01/2014/TT-NHNN - Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Điều 5. Niêm phong tiền mặt | doc_44209_điều_5__niêm_phong_tiền_mặt_5` | `NEEDS_HUMAN_REVIEW` |
| `CHK_KHO_03` | An toàn kho quỹ & Vận chuyển tiền | `Chi nhánh loại 1` | Mọi khoản thu, chi tiền mặt, ngoại tệ, giấy tờ có giá tại Ch... | 🔴 HIGH | `01/2014/TT-NHNN - Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Điều 7. Nguyên tắc thu, chi tiền mặt, ngoại tệ, giấy tờ có giá | doc_44209_điều_7__nguyên_tắc_thu__chi_tiền_mặt__ngoại_tệ__giấy_tờ_có_giá_7` | `NEEDS_HUMAN_REVIEW` |
| `CHK_KHO_04` | An toàn kho quỹ & Vận chuyển tiền | `Chi nhánh loại 1` | Chi nhánh có đảm bảo mỗi chứng từ thu/chi tiền mặt, ngoại tệ... | 🟡 MEDIUM | `01/2014/TT-NHNN - Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Điều 8. Bảng kê các loại tiền thu (hoặc chi) | doc_44209_điều_8__bảng_kê_các_loại_tiền_thu__hoặc_chi_8` | `NEEDS_HUMAN_REVIEW` |

---

## 3. Chi tiết Nội dung Checklist Kiểm toán (Detailed Checklist Items)

### Domain: **An toàn kho quỹ & Vận chuyển tiền** (4 mục kiểm tra)

#### Mã mục: `CHK_KHO_01` - Phạm vi: `Chi nhánh loại 1`
- **Câu hỏi Kiểm toán**: **Chi nhánh có tuân thủ đúng quy cách đóng gói tiền mặt (bó, bao, túi, hộp, thùng) theo quy định tại Điều 4 của Thông tư 01/2014/TT-NHNN không?**
- **Rủi ro Tiềm ẩn**: Việc đóng gói không đúng quy cách có thể dẫn đến sai lệch số lượng, khó khăn trong công tác kiểm đếm, tiềm ẩn rủi ro thất thoát tiền mặt và ảnh hưởng đến quy trình nghiệp vụ, uy tín của ngân hàng.
- **Mức độ Rủi ro**: 🟡 MEDIUM
- **Trích dẫn Văn bản gốc (Citation)**: `01/2014/TT-NHNN - Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Điều 4. Đóng gói tiền mặt | doc_44209_điều_4__đóng_gói_tiền_mặt_4`
- **Gợi ý Hành động Kiểm toán**: Kiểm tra thực địa tại kho quỹ, đối chiếu ngẫu nhiên các bó, bao, túi, hộp, thùng tiền mặt với quy định về số lượng tờ/miếng trong từng đơn vị đóng gói.
- **Trạng thái Duyệt (Guardrail)**: `NEEDS_HUMAN_REVIEW`

---
#### Mã mục: `CHK_KHO_02` - Phạm vi: `Chi nhánh loại 1`
- **Câu hỏi Kiểm toán**: **Việc niêm phong tiền mặt đã qua lưu thông, ngoại tệ và giấy tờ có giá tại Chi nhánh có đảm bảo đầy đủ nội dung trên giấy niêm phong và phương pháp niêm phong (kẹp chì kèm giấy niêm phong) theo quy định tại Điều 5 và Điều 6 của Thông tư 01/2014/TT-NHNN không?**
- **Rủi ro Tiềm ẩn**: Niêm phong không đúng quy định hoặc thiếu thông tin có thể gây khó khăn trong việc truy vết trách nhiệm, tiềm ẩn rủi ro giả mạo, thất thoát tài sản và vi phạm nghiêm trọng quy định về an toàn kho quỹ.
- **Mức độ Rủi ro**: 🔴 HIGH
- **Trích dẫn Văn bản gốc (Citation)**: `01/2014/TT-NHNN - Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Điều 5. Niêm phong tiền mặt | doc_44209_điều_5__niêm_phong_tiền_mặt_5`
- **Gợi ý Hành động Kiểm toán**: Kiểm tra ngẫu nhiên các bó, bao, túi tiền mặt, ngoại tệ, giấy tờ có giá đã niêm phong trong kho quỹ; đối chiếu nội dung trên giấy niêm phong và phương pháp niêm phong với quy định. Phỏng vấn cán bộ kho quỹ về quy trình niêm phong.
- **Trạng thái Duyệt (Guardrail)**: `NEEDS_HUMAN_REVIEW`

---
#### Mã mục: `CHK_KHO_03` - Phạm vi: `Chi nhánh loại 1`
- **Câu hỏi Kiểm toán**: **Mọi khoản thu, chi tiền mặt, ngoại tệ, giấy tờ có giá tại Chi nhánh có được thực hiện thông qua quỹ của đơn vị, căn cứ vào chứng từ kế toán hợp lệ, hợp pháp, và có đầy đủ chữ ký của các bên liên quan (người nộp/lĩnh, thủ quỹ/thủ kho/nhân viên thu chi) theo quy định tại Điều 7 của Thông tư 01/2014/TT-NHNN không?**
- **Rủi ro Tiềm ẩn**: Vi phạm nguyên tắc thu, chi hoặc thiếu sót trong chứng từ kế toán có thể dẫn đến rủi ro gian lận, thất thoát tài sản, sai sót nghiệp vụ, vi phạm quy định kế toán, thiếu trách nhiệm giải trình và ảnh hưởng đến tính minh bạch của hoạt động.
- **Mức độ Rủi ro**: 🔴 HIGH
- **Trích dẫn Văn bản gốc (Citation)**: `01/2014/TT-NHNN - Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Điều 7. Nguyên tắc thu, chi tiền mặt, ngoại tệ, giấy tờ có giá | doc_44209_điều_7__nguyên_tắc_thu__chi_tiền_mặt__ngoại_tệ__giấy_tờ_có_giá_7`
- **Gợi ý Hành động Kiểm toán**: Đối chiếu ngẫu nhiên các chứng từ thu, chi tiền mặt, ngoại tệ, giấy tờ có giá với sổ quỹ và kiểm tra tính hợp lệ, hợp pháp, đầy đủ chữ ký của chứng từ. Phỏng vấn cán bộ kế toán và thủ quỹ về quy trình kiểm soát chứng từ.
- **Trạng thái Duyệt (Guardrail)**: `NEEDS_HUMAN_REVIEW`

---
#### Mã mục: `CHK_KHO_04` - Phạm vi: `Chi nhánh loại 1`
- **Câu hỏi Kiểm toán**: **Chi nhánh có đảm bảo mỗi chứng từ thu/chi tiền mặt, ngoại tệ, giấy tờ có giá đều kèm theo Bảng kê các loại tiền thu/chi hoặc biên bản giao nhận, và việc kiểm đếm được thực hiện chính xác với sự chứng kiến của khách hàng theo quy định tại Điều 8 và Điều 9 của Thông tư 01/2014/TT-NHNN không?**
- **Rủi ro Tiềm ẩn**: Thiếu bảng kê chi tiết hoặc kiểm đếm không chính xác/không có sự chứng kiến của khách hàng có thể gây khó khăn trong kiểm soát, đối chiếu, tiềm ẩn rủi ro sai sót, gian lận trong giao dịch, dẫn đến tranh chấp với khách hàng và ảnh hưởng đến uy tín, chất lượng dịch vụ của ngân hàng.
- **Mức độ Rủi ro**: 🟡 MEDIUM
- **Trích dẫn Văn bản gốc (Citation)**: `01/2014/TT-NHNN - Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Điều 8. Bảng kê các loại tiền thu (hoặc chi) | doc_44209_điều_8__bảng_kê_các_loại_tiền_thu__hoặc_chi_8`
- **Gợi ý Hành động Kiểm toán**: Kiểm tra ngẫu nhiên các bộ chứng từ thu/chi để xác minh sự tồn tại của bảng kê/biên bản giao nhận. Quan sát trực tiếp quy trình kiểm đếm tại quầy giao dịch và phỏng vấn cán bộ giao dịch về việc tuân thủ quy định kiểm đếm có sự chứng kiến của khách hàng.
- **Trạng thái Duyệt (Guardrail)**: `NEEDS_HUMAN_REVIEW`

---


## 4. Kết luận & Hướng dẫn Sử dụng cho Đoàn Kiểm toán
1. Toàn bộ câu hỏi kiểm toán và rủi ro được tổng hợp từ dữ liệu quy định nội bộ Agribank và Thông tư NHNN.
2. Kiểm toán viên sử dụng danh mục này làm căn cứ lập kế hoạch kiểm toán thực địa tại Chi nhánh loại 1 và Khối CNTT.
3. Mọi điều chỉnh danh mục cần sự phê duyệt của Trưởng đoàn Kiểm toán (`NEEDS_HUMAN_REVIEW`).

---

CHECKLIST GENERATOR ENGINE: PASS
CHECKLIST ITEMS GENERATED: 4
CITATIONS ATTACHED: YES