// ==============================================================================
// DEMO QUERIES CYPHER - WIKI RISK GRAPH MVP
// Bộ truy vấn mẫu khai thác đồ thị tri thức rủi ro
// ==============================================================================

// ------------------------------------------------------------------------------
// QUERY A: XEM TOÀN BỘ GRAPH (TẤT CẢ NODE & EDGE ĐÃ NẠP)
// ------------------------------------------------------------------------------
MATCH (n)
OPTIONAL MATCH (n)-[r]->(m)
RETURN n, r, m;


// ------------------------------------------------------------------------------
// QUERY B: TÌM KIỂM SOÁT GIẢM THIỂU MỘT RỦI RO CỤ THỂ (VD: RR-001)
// ------------------------------------------------------------------------------
// :params { risk_id: 'RR-001' }
MATCH (k:KiemSoat)-[r:MITIGATES]->(rr:RuiRo {id: $risk_id})
RETURN rr.id AS risk_id,
       rr.name AS risk_name,
       k.id AS control_id,
       k.name AS control_name,
       k.control_type AS control_type,
       k.frequency AS frequency,
       k.effectiveness AS effectiveness,
       r.evidence_quote AS evidence,
       r.confidence AS confidence,
       r.verification_status AS status;


// ------------------------------------------------------------------------------
// QUERY C: TÌM CÁC SỰ KIỆN ĐÃ GHI NHẬN CỦA MỘT RỦI RO (VD: RR-001)
// ------------------------------------------------------------------------------
// :params { risk_id: 'RR-001' }
MATCH (rr:RuiRo {id: $risk_id})-[r:OBSERVED_AS]->(sk:SuKienRuiRo)
RETURN rr.id AS risk_id,
       rr.name AS risk_name,
       sk.id AS event_id,
       sk.description AS event_description,
       sk.occurred_at AS occurred_at,
       sk.discovered_at AS discovered_at,
       sk.severity AS severity,
       sk.loss_amount_vnd AS loss_vnd,
       r.evidence_quote AS evidence,
       r.verification_status AS status;


// ------------------------------------------------------------------------------
// QUERY D: TÌM ĐƯỜNG ĐI ĐẦY ĐỦ: KiemSoat -> RuiRo -> SuKienRuiRo
// ------------------------------------------------------------------------------
MATCH path = (k:KiemSoat)-[m:MITIGATES]->(rr:RuiRo)-[o:OBSERVED_AS]->(sk:SuKienRuiRo)
RETURN k.id AS control_id,
       k.name AS control_name,
       rr.id AS risk_id,
       rr.name AS risk_name,
       rr.category AS risk_category,
       sk.id AS event_id,
       sk.description AS event_description,
       sk.loss_amount_vnd AS loss_vnd
ORDER BY rr.id;


// ------------------------------------------------------------------------------
// QUERY E: TÌM RỦI RO CHƯA CÓ KIỂM SOÁT GIẢM THIỂU (UNMITIGATED RISKS)
// ------------------------------------------------------------------------------
MATCH (rr:RuiRo)
WHERE NOT ( (:KiemSoat)-[:MITIGATES]->(rr) )
RETURN rr.id AS unmitigated_risk_id,
       rr.name AS risk_name,
       rr.category AS category,
       rr.inherent_level AS inherent_level,
       rr.residual_level AS residual_level,
       rr.owner_unit_id AS owner_unit_id;


// ------------------------------------------------------------------------------
// QUERY F: TÌM CÁC LIÊN KẾT CHƯA ĐƯỢC XÁC MINH (CHƯA VERIFIED / PROPOSED)
// ------------------------------------------------------------------------------
MATCH (source)-[r]->(target)
WHERE coalesce(r.verification_status, 'PROPOSED') <> 'VERIFIED'
RETURN labels(source)[0] AS source_type,
       source.id AS source_id,
       type(r) AS relation_type,
       labels(target)[0] AS target_type,
       target.id AS target_id,
       r.confidence AS confidence,
       r.verification_status AS verification_status,
       r.evidence_quote AS evidence;
