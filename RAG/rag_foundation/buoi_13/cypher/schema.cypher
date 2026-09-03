// ==============================================================================
// SCHEMA CYPHER - WIKI RISK GRAPH MVP
// Khởi tạo Ràng buộc duy nhất (Unique Constraints) và Chỉ mục (Indexes)
// ==============================================================================

// 1. RÀNG BUỘC DUY NHẤT (UNIQUE CONSTRAINTS THEO ID)
// Đảm bảo mỗi Node có id là duy nhất và tự động tạo Index trên id

CREATE CONSTRAINT rui_ro_id_unique IF NOT EXISTS
FOR (r:RuiRo)
REQUIRE r.id IS UNIQUE;

CREATE CONSTRAINT kiem_soat_id_unique IF NOT EXISTS
FOR (k:KiemSoat)
REQUIRE k.id IS UNIQUE;

CREATE CONSTRAINT su_kien_rui_ro_id_unique IF NOT EXISTS
FOR (s:SuKienRuiRo)
REQUIRE s.id IS UNIQUE;

// 2. CHỈ MỤC BỔ TRỢ ĐỂ TĂNG TỐC TRUY VẤN (INDEXES)

CREATE INDEX rui_ro_category_idx IF NOT EXISTS
FOR (r:RuiRo)
ON (r.category);

CREATE INDEX rui_ro_inherent_level_idx IF NOT EXISTS
FOR (r:RuiRo)
ON (r.inherent_level);

CREATE INDEX kiem_soat_type_idx IF NOT EXISTS
FOR (k:KiemSoat)
ON (k.control_type);

CREATE INDEX su_kien_severity_idx IF NOT EXISTS
FOR (s:SuKienRuiRo)
ON (s.severity);

CREATE INDEX relation_status_idx IF NOT EXISTS
FOR ()-[r:MITIGATES]-()
ON (r.verification_status);
