---
id: HOME
type: Dashboard
title: Trang Chủ Wiki Tri Thức Rủi Ro
---

# 🛡️ Wiki Tri Thức Rủi Ro (Wiki Risk Graph)

Hệ thống cơ sở tri thức đồ thị rủi ro phục vụ đào tạo và tra cứu.

---

## 📊 1. Thống kê Đồ thị Tri thức
- **Tổng số thực thể (Nodes):** **34**
  - 🔴 Hồ sơ Rủi ro (`:RuiRo`): **12**
  - 🟢 Chốt Kiểm soát (`:KiemSoat`): **10**
  - 🟡 Sự kiện Rủi ro (`:SuKienRuiRo`): **12**
- **Tổng số liên kết (Edges):** **22**
  - 🛡️ Giảm thiểu rủi ro (`MITIGATES`): **10**
  - ⚠️ Biểu hiện thành sự kiện (`OBSERVED_AS`): **12**

---

## 🎯 2. Mô hình Luồng Quan hệ MVP
```
[KiemSoat] ──(MITIGATES)──► [RuiRo] ──(OBSERVED_AS)──► [SuKienRuiRo]
```

---

## 🔴 3. Danh mục Hồ sơ Rủi ro (RuiRo)
1. [[RR-001 - Giao dịch chuyển tiền bị hạch toán sai]]
2. [[RR-002 - Phê duyệt tín dụng vượt thẩm quyền]]
3. [[RR-003 - Giải ngân thiếu hồ sơ bảo đảm]]
4. [[RR-004 - Lộ thông tin khách hàng]]
5. [[RR-005 - Gián đoạn dịch vụ ngân hàng số]]
6. [[RR-006 - Gian lận giả mạo yêu cầu chuyển tiền]]
7. [[RR-007 - Chậm báo cáo giao dịch đáng ngờ]]
8. [[RR-008 - Định giá tài sản bảo đảm không chính xác]]
9. [[RR-009 - Không phát hiện giao dịch bất thường]]
10. [[RR-010 - Sai lệch số liệu báo cáo quản trị]]
11. [[RR-011 - Nhà cung cấp công nghệ không đáp ứng cam kết]]
12. [[RR-012 - Xung đột lợi ích trong mua sắm]]

---

## 🟢 4. Danh mục Chốt Kiểm soát (KiemSoat)
1. [[KS-001 - Đối soát tự động giao dịch và sổ cái]]
2. [[KS-002 - Kiểm tra hạn mức phê duyệt trên hệ thống]]
3. [[KS-003 - Checklist điều kiện giải ngân bắt buộc]]
4. [[KS-004 - Rà soát quyền truy cập định kỳ]]
5. [[KS-005 - Kiểm thử khả năng chịu tải và chuyển đổi dự phòng]]
6. [[KS-006 - Xác thực hai kênh với lệnh chuyển tiền ngoại lệ]]
7. [[KS-007 - Theo dõi SLA xử lý cảnh báo AML]]
8. [[KS-008 - Rà soát độc lập định giá tài sản bảo đảm]]
9. [[KS-009 - Hiệu chỉnh luật phát hiện giao dịch gian lận]]
10. [[KS-010 - Đối chiếu dữ liệu nguồn trước khi phát hành báo cáo]]

---

## 🟡 5. Danh mục Sự kiện Rủi ro (SuKienRuiRo)
1. [[SK-001 - Sai lệch trạng thái giao dịch được phát hiện khi đối soát cuối ngày]]
2. [[SK-002 - Hồ sơ tín dụng được phê duyệt vượt hạn mức của người phê duyệt]]
3. [[SK-003 - Giải ngân trước khi hoàn thiện chứng từ bảo đảm]]
4. [[SK-004 - Tài khoản có quyền truy cập dữ liệu vượt phạm vi công việc]]
5. [[SK-005 - Dịch vụ ngân hàng số gián đoạn trong giờ cao điểm]]
6. [[SK-006 - Yêu cầu chuyển tiền giả mạo được xử lý trước khi bị thu hồi]]
7. [[SK-007 - Báo cáo giao dịch đáng ngờ nộp quá hạn nội bộ]]
8. [[SK-008 - Rà soát phát hiện giá trị tài sản bảo đảm đã hết hiệu lực]]
9. [[SK-009 - Giao dịch bất thường chỉ bị phát hiện sau khi khách hàng khiếu nại]]
10. [[SK-010 - Báo cáo quản trị sử dụng dữ liệu nguồn chưa đối chiếu]]
11. [[SK-011 - Nhà cung cấp chậm khôi phục dịch vụ so với SLA]]
12. [[SK-012 - Kiểm tra sau mua sắm phát hiện thiếu kê khai xung đột lợi ích]]
