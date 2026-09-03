// ==============================================================================
// SCHEMA CYPHER: RÀNG BUỘC (CONSTRAINTS) VÀ CHỈ MỤC (INDEXES) — BUỔI 14
// ==============================================================================

// 1. Ràng buộc Khóa chính duy nhất (Uniqueness Constraints)
CREATE CONSTRAINT c_vanban_id IF NOT EXISTS
FOR (v:VanBan) REQUIRE v.id IS UNIQUE;

CREATE CONSTRAINT c_dieukhoan_id IF NOT EXISTS
FOR (d:DieuKhoan) REQUIRE d.id IS UNIQUE;

// 2. Chỉ mục hỗ trợ tìm kiếm và truy vấn đa chiều (Indexes)
CREATE INDEX idx_vanban_so_ky_hieu IF NOT EXISTS
FOR (v:VanBan) ON (v.so_ky_hieu);

CREATE INDEX idx_vanban_document_type IF NOT EXISTS
FOR (v:VanBan) ON (v.document_type);

CREATE INDEX idx_vanban_status IF NOT EXISTS
FOR (v:VanBan) ON (v.status);

CREATE INDEX idx_vanban_session IF NOT EXISTS
FOR (v:VanBan) ON (v.lab_session);

CREATE INDEX idx_dieukhoan_doc_id IF NOT EXISTS
FOR (d:DieuKhoan) ON (d.document_id);

CREATE INDEX idx_dieukhoan_session IF NOT EXISTS
FOR (d:DieuKhoan) ON (d.lab_session);
