"""
Ứng dụng Web Quản lý Danh mục Văn bản Nội bộ (agribank-vanban)
Dự án: agribank-rag
Buổi: 04 - Quản lý Văn bản Nội bộ & Vibe Coding với AntiGravity
"""

import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ===================================================
# 1. DỮ LIỆU LƯU TẠM TRONG BỘ NHỚ (IN-MEMORY)
# ===================================================
# Mỗi văn bản gồm: id, so_hieu, tieu_de, ngay_ban_hanh, con_hieu_luc (True/False)
danh_sach_van_ban = [
    {
        "id": 1,
        "so_hieu": "41/2016/TT-NHNN",
        "tieu_de": "Quy định tỷ lệ an toàn vốn đối với ngân hàng thương mại, chi nhánh ngân hàng nước ngoài",
        "ngay_ban_hanh": "2016-12-30",
        "con_hieu_luc": True
    },
    {
        "id": 2,
        "so_hieu": "15/2026/QĐ-KTNB",
        "tieu_de": "Quy chế kiểm toán nội bộ hệ thống Công nghệ Thông tin và Core Banking Agribank",
        "ngay_ban_hanh": "2026-02-15",
        "con_hieu_luc": True
    },
    {
        "id": 3,
        "so_hieu": "02/2023/TT-NHNN",
        "tieu_de": "Quy định về việc tổ chức tín dụng cơ cấu lại thời hạn trả nợ và giữ nguyên nhóm nợ",
        "ngay_ban_hanh": "2023-04-23",
        "con_hieu_luc": False
    },
    {
        "id": 4,
        "so_hieu": "11/2024/TT-NHNN",
        "tieu_de": "Quy định về bảo đảm an toàn, bảo mật cho việc cung cấp dịch vụ trực tuyến trong ngành Ngân hàng",
        "ngay_ban_hanh": "2024-06-28",
        "con_hieu_luc": True
    }
]

next_id = 5


# ===================================================
# 2. HÀM TIỆN ÍCH KIỂM TRA ĐỊNH DẠNG (VALIDATION)
# ===================================================

def validate_date(date_text):
    """Kiểm tra ngày ban hành có đúng định dạng YYYY-MM-DD không."""
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
        return True
    except ValueError:
        return False


# ===================================================
# 3. ROUTES & API ENDPOINTS
# ===================================================

@app.route("/")
def index():
    """Hiển thị giao diện chính ứng dụng quản lý văn bản."""
    return render_template("index.html")


@app.route("/api/vanban", methods=["GET"])
def get_van_ban():
    """
    Lấy danh sách văn bản với bộ lọc và tìm kiếm.
    Query params:
      - search: từ khóa tìm kiếm trong số hiệu hoặc tiêu đề
      - status: 'all' | 'con_hieu_luc' | 'het_hieu_luc'
    """
    search_term = request.args.get("search", "").strip().lower()
    status_filter = request.args.get("status", "all").strip().lower()

    ket_qua = danh_sach_van_ban

    # 1. Lọc theo trạng thái hiệu lực
    if status_filter == "con_hieu_luc":
        ket_qua = [vb for vb in ket_qua if vb["con_hieu_luc"] is True]
    elif status_filter == "het_hieu_luc":
        ket_qua = [vb for vb in ket_qua if vb["con_hieu_luc"] is False]

    # 2. Lọc theo từ khóa tìm kiếm (số hiệu hoặc tiêu đề)
    if search_term:
        ket_qua = [
            vb for vb in ket_qua
            if search_term in vb["so_hieu"].lower() or search_term in vb["tieu_de"].lower()
        ]

    # Tính toán các chỉ số thống kê
    count_con_hieu_luc = sum(1 for vb in danh_sach_van_ban if vb["con_hieu_luc"])
    count_het_hieu_luc = sum(1 for vb in danh_sach_van_ban if not vb["con_hieu_luc"])

    return jsonify({
        "success": True,
        "data": ket_qua,
        "total": len(danh_sach_van_ban),
        "count_con_hieu_luc": count_con_hieu_luc,
        "count_het_hieu_luc": count_het_hieu_luc
    })


@app.route("/api/vanban", methods=["POST"])
def add_van_ban():
    """
    Thêm một văn bản mới vào danh mục.
    JSON body: { "so_hieu": "...", "tieu_de": "...", "ngay_ban_hanh": "YYYY-MM-DD", "con_hieu_luc": true/false }
    """
    global next_id
    data = request.get_json(silent=True) or {}

    so_hieu = str(data.get("so_hieu", "")).strip()
    tieu_de = str(data.get("tieu_de", "")).strip()
    ngay_ban_hanh = str(data.get("ngay_ban_hanh", "")).strip()
    con_hieu_luc = bool(data.get("con_hieu_luc", True))

    # Kiểm tra dữ liệu đầu vào (Validation)
    if not so_hieu:
        return jsonify({"success": False, "message": "Số hiệu văn bản không được để trống!"}), 400
    if not tieu_de:
        return jsonify({"success": False, "message": "Tiêu đề văn bản không được để trống!"}), 400
    if not ngay_ban_hanh or not validate_date(ngay_ban_hanh):
        return jsonify({"success": False, "message": "Ngày ban hành không hợp lệ! (Định dạng yêu cầu: YYYY-MM-DD)"}), 400

    # Kiểm tra trùng số hiệu (cảnh báo hoặc ngăn chặn)
    da_ton_tai = any(vb["so_hieu"].lower() == so_hieu.lower() for vb in danh_sach_van_ban)
    if da_ton_tai:
        return jsonify({"success": False, "message": f"Số hiệu văn bản '{so_hieu}' đã tồn tại trong hệ thống!"}), 400

    van_ban_moi = {
        "id": next_id,
        "so_hieu": so_hieu,
        "tieu_de": tieu_de,
        "ngay_ban_hanh": ngay_ban_hanh,
        "con_hieu_luc": con_hieu_luc
    }

    danh_sach_van_ban.append(van_ban_moi)
    next_id += 1

    return jsonify({
        "success": True,
        "message": f"Đã thêm thành công văn bản số '{so_hieu}'!",
        "data": van_ban_moi
    }), 201


@app.route("/api/vanban/<int:vb_id>", methods=["PUT"])
def update_van_ban(vb_id):
    """
    Cập nhật thông tin văn bản theo ID.
    JSON body: { "so_hieu": "...", "tieu_de": "...", "ngay_ban_hanh": "...", "con_hieu_luc": true/false }
    """
    data = request.get_json(silent=True) or {}
    
    van_ban = next((vb for vb in danh_sach_van_ban if vb["id"] == vb_id), None)
    if not van_ban:
        return jsonify({"success": False, "message": f"Không tìm thấy văn bản có mã #{vb_id}!"}), 404

    so_hieu = str(data.get("so_hieu", "")).strip()
    tieu_de = str(data.get("tieu_de", "")).strip()
    ngay_ban_hanh = str(data.get("ngay_ban_hanh", "")).strip()
    con_hieu_luc = data.get("con_hieu_luc")

    if not so_hieu:
        return jsonify({"success": False, "message": "Số hiệu văn bản không được để trống!"}), 400
    if not tieu_de:
        return jsonify({"success": False, "message": "Tiêu đề văn bản không được để trống!"}), 400
    if not ngay_ban_hanh or not validate_date(ngay_ban_hanh):
        return jsonify({"success": False, "message": "Ngày ban hành không đúng định dạng YYYY-MM-DD!"}), 400

    # Kiểm tra trùng số hiệu với văn bản khác
    da_ton_tai = any(vb["id"] != vb_id and vb["so_hieu"].lower() == so_hieu.lower() for vb in danh_sach_van_ban)
    if da_ton_tai:
        return jsonify({"success": False, "message": f"Số hiệu văn bản '{so_hieu}' bị trùng với văn bản khác!"}), 400

    van_ban["so_hieu"] = so_hieu
    van_ban["tieu_de"] = tieu_de
    van_ban["ngay_ban_hanh"] = ngay_ban_hanh
    if con_hieu_luc is not None:
        van_ban["con_hieu_luc"] = bool(con_hieu_luc)

    return jsonify({
        "success": True,
        "message": "Cập nhật thông tin văn bản thành công!",
        "data": van_ban
    })


@app.route("/api/vanban/<int:vb_id>/toggle-status", methods=["PATCH"])
def toggle_status(vb_id):
    """Đổi nhanh trạng thái hiệu lực: Còn hiệu lực <-> Hết hiệu lực."""
    van_ban = next((vb for vb in danh_sach_van_ban if vb["id"] == vb_id), None)
    if not van_ban:
        return jsonify({"success": False, "message": f"Không tìm thấy văn bản #{vb_id}!"}), 404

    van_ban["con_hieu_luc"] = not van_ban["con_hieu_luc"]
    trang_thai_str = "Còn hiệu lực" if van_ban["con_hieu_luc"] else "Hết hiệu lực"

    return jsonify({
        "success": True,
        "message": f"Đã đổi trạng thái sang '{trang_thai_str}'",
        "data": van_ban
    })


@app.route("/api/vanban/<int:vb_id>", methods=["DELETE"])
def delete_van_ban(vb_id):
    """Xóa văn bản theo ID."""
    global danh_sach_van_ban
    van_ban = next((vb for vb in danh_sach_van_ban if vb["id"] == vb_id), None)
    if not van_ban:
        return jsonify({"success": False, "message": f"Không tìm thấy văn bản #{vb_id}!"}), 404

    danh_sach_van_ban = [vb for vb in danh_sach_van_ban if vb["id"] != vb_id]

    return jsonify({
        "success": True,
        "message": f"Đã xóa văn bản '{van_ban['so_hieu']}' khỏi danh mục!"
    })


if __name__ == "__main__":
    print("=" * 65)
    print("  Ứng dụng Quản lý Văn bản Nội bộ KTNB (Agribank VanBan)")
    print("  Đang chạy tại: http://127.0.0.1:5001")
    print("=" * 65)
    app.run(host="127.0.0.1", port=5001, debug=True)
