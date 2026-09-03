// ==============================================================================
// DEMO CYPHER QUERIES: CÁC TRUY VẤN MẪU KHÁM PHÁ KNOWLEDGE GRAPH MINI — BUỔI 14
// ==============================================================================

// ------------------------------------------------------------------------------
// 1. Thống kê tổng số Nodes theo Label thuộc Buổi 14
// ------------------------------------------------------------------------------
MATCH (n {lab_session: "buoi_14"})
RETURN labels(n)[0] AS node_label, count(n) AS total_nodes
ORDER BY total_nodes DESC;

// ------------------------------------------------------------------------------
// 2. Thống kê tổng số Relationships theo Type thuộc Buổi 14
// ------------------------------------------------------------------------------
MATCH ()-[r {lab_session: "buoi_14"}]->()
RETURN type(r) AS relationship_type, count(r) AS total_relations
ORDER BY total_relations DESC;

// ------------------------------------------------------------------------------
// 3. Tra cứu cấu trúc phân cấp: 1 Văn bản và tất cả Điều khoản trực thuộc
// ------------------------------------------------------------------------------
MATCH (v:VanBan {so_ky_hieu: "01/2014/TT-NHNN", lab_session: "buoi_14"})-[:CONTAINS]->(d:DieuKhoan)
RETURN v.so_ky_hieu AS van_ban, v.title AS tieu_de, count(d) AS so_luong_dieu_khoan;

// ------------------------------------------------------------------------------
// 4. Duyệt tuần tự chuỗi điều khoản NEXT liên tiếp trong cùng văn bản
// ------------------------------------------------------------------------------
MATCH (d1:DieuKhoan {lab_session: "buoi_14"})-[:NEXT]->(d2:DieuKhoan {lab_session: "buoi_14"})
WHERE d1.document_id = "44209" AND d1.article CONTAINS "Điều 50"
RETURN d1.id AS dieu_hien_tai, d1.article AS ten_dieu_1,
       d2.id AS dieu_tiep_theo, d2.article AS ten_dieu_2;

// ------------------------------------------------------------------------------
// 5. Khám phá các mối quan hệ liên văn bản thực tế trong CSDL
// (SUA_DOI_BO_SUNG, CAN_CU, VAN_BAN_BO_SUNG, THAY_THE, HOP_NHAT)
// ------------------------------------------------------------------------------
MATCH (v1:VanBan {lab_session: "buoi_14"})-[r]->(v2:VanBan {lab_session: "buoi_14"})
WHERE type(r) IN ["SUA_DOI_BO_SUNG", "CAN_CU", "VAN_BAN_BO_SUNG", "THAY_THE", "HOP_NHAT"]
RETURN v1.so_ky_hieu AS van_ban_nguon,
       type(r) AS loai_quan_he,
       r.relationship_label AS nhan_quan_he,
       v2.so_ky_hieu AS van_ban_dich;

// ------------------------------------------------------------------------------
// 6. Truy vấn 2-Hops: Từ Điều khoản -> Văn bản gốc -> Văn bản căn cứ pháp lý
// ------------------------------------------------------------------------------
MATCH (d:DieuKhoan {lab_session: "buoi_14"})<-[:CONTAINS]-(v1:VanBan)-[:CAN_CU]->(v2:VanBan)
WHERE d.article CONTAINS "Điều 11"
RETURN d.id AS chunk_id,
       d.article AS dieu_khoan,
       v1.so_ky_hieu AS van_ban_ban_hanh,
       v2.so_ky_hieu AS van_ban_can_cu,
       v2.title AS tieu_de_can_cu
LIMIT 10;

// ------------------------------------------------------------------------------
// 7. Kiểm tra các Node mồ côi (Orphan Nodes: Không có bất kỳ cạnh kết nối nào)
// ------------------------------------------------------------------------------
MATCH (n {lab_session: "buoi_14"})
WHERE NOT (n)--()
RETURN labels(n)[0] AS orphan_label, n.id AS orphan_id, n.title AS orphan_title;
