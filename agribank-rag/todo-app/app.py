"""
Ứng dụng Web Quản lý Công việc Nội bộ KTNB (agribank-todo)
Dự án: agribank-rag
Buổi: 03 - Vibe Coding với AntiGravity
"""

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ==========================================
# 1. DỮ LIỆU LƯU TẠM TRONG BỘ NHỚ (IN-MEMORY)
# ==========================================
# Mỗi công việc gồm: id, ten, nguoi_phu_trach, trang_thai
# Trang thai hop le: 'dang_lam', 'xong'
danh_sach_cong_viec = [
    {
        "id": 1,
        "ten": "Rà soát Thông tư 41/2016/TT-NHNN về an toàn vốn",
        "nguoi_phu_trach": "Nguyễn Văn A",
        "trang_thai": "dang_lam"
    },
    {
        "id": 2,
        "ten": "Lập checklist kiểm toán hệ thống Core Banking quý 3",
        "nguoi_phu_trach": "Trần Thị B",
        "trang_thai": "dang_lam"
    },
    {
        "id": 3,
        "ten": "Đối chiếu quy trình cấp tín dụng nông nghiệp công nghệ cao",
        "nguoi_phu_trach": "Lê Văn C",
        "trang_thai": "xong"
    }
]

# Tự động tăng ID cho công việc mới
next_id = 4


# ==========================================
# 2. ROUTES PHỤC VỤ GIAO DIỆN & API
# ==========================================

@app.route("/")
def index():
    """Hiển thị giao diện chính của ứng dụng."""
    return render_template("index.html")


@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    """
    Lấy danh sách công việc.
    Hỗ trợ query parameter: ?status=all|dang_lam|xong
    """
    status_filter = request.args.get("status", "all").strip().lower()
    
    if status_filter in ["dang_lam", "xong"]:
        ket_qua = [cv for cv in danh_sach_cong_viec if cv["trang_thai"] == status_filter]
    else:
        ket_qua = danh_sach_cong_viec

    return jsonify({
        "success": True,
        "data": ket_qua,
        "total": len(danh_sach_cong_viec),
        "count_dang_lam": sum(1 for cv in danh_sach_cong_viec if cv["trang_thai"] == "dang_lam"),
        "count_xong": sum(1 for cv in danh_sach_cong_viec if cv["trang_thai"] == "xong")
    })


@app.route("/api/tasks", methods=["POST"])
def add_task():
    """
    Thêm một công việc mới.
    Yêu cầu JSON body: { "ten": "...", "nguoi_phu_trach": "..." }
    """
    global next_id
    data = request.get_json(silent=True) or {}
    
    # Xử lý trường hợp kiểu dữ liệu không phải chuỗi hoặc chứa toàn khoảng trắng
    ten = str(data.get("ten", "")).strip() if data.get("ten") is not None else ""
    nguoi_phu_trach = str(data.get("nguoi_phu_trach", "")).strip() if data.get("nguoi_phu_trach") is not None else ""
    
    # Kiểm tra trường hợp rỗng / khoảng trắng
    if not ten:
        return jsonify({"success": False, "message": "Tên công việc không được để trống hoặc chỉ chứa khoảng trắng!"}), 400
    if not nguoi_phu_trach:
        return jsonify({"success": False, "message": "Người phụ trách không được để trống hoặc chỉ chứa khoảng trắng!"}), 400

    cong_viec_moi = {
        "id": next_id,
        "ten": ten,
        "nguoi_phu_trach": nguoi_phu_trach,
        "trang_thai": "dang_lam"  # Mặc định công việc mới là 'dang_lam'
    }
    
    danh_sach_cong_viec.append(cong_viec_moi)
    next_id += 1
    
    return jsonify({
        "success": True,
        "message": "Thêm công việc thành công!",
        "data": cong_viec_moi
    }), 201


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    """
    Sửa thông tin công việc theo ID.
    Yêu cầu JSON body: { "ten": "...", "nguoi_phu_trach": "...", "trang_thai": "dang_lam"|"xong" }
    """
    data = request.get_json(silent=True) or {}
    
    # Tìm công việc theo ID (xử lý trường hợp sửa công việc không tồn tại)
    task = next((cv for cv in danh_sach_cong_viec if cv["id"] == task_id), None)
    if not task:
        return jsonify({"success": False, "message": f"Không tìm thấy công việc với mã #{task_id}"}), 404
        
    ten = str(data.get("ten", "")).strip() if data.get("ten") is not None else ""
    nguoi_phu_trach = str(data.get("nguoi_phu_trach", "")).strip() if data.get("nguoi_phu_trach") is not None else ""
    trang_thai = str(data.get("trang_thai", "")).strip().lower()
    
    if not ten:
        return jsonify({"success": False, "message": "Tên công việc không được để trống hoặc chỉ chứa khoảng trắng!"}), 400
    if not nguoi_phu_trach:
        return jsonify({"success": False, "message": "Người phụ trách không được để trống hoặc chỉ chứa khoảng trắng!"}), 400
    if trang_thai and trang_thai not in ["dang_lam", "xong"]:
        return jsonify({"success": False, "message": "Trạng thái chỉ có thể là 'dang_lam' hoặc 'xong'!"}), 400

    task["ten"] = ten
    task["nguoi_phu_trach"] = nguoi_phu_trach
    if trang_thai:
        task["trang_thai"] = trang_thai

    return jsonify({
        "success": True,
        "message": "Cập nhật công việc thành công!",
        "data": task
    })


@app.route("/api/tasks/<int:task_id>/toggle", methods=["PATCH"])
def toggle_task_status(task_id):
    """
    Đảo trạng thái hoàn thành: 'dang_lam' <-> 'xong'.
    """
    task = next((cv for cv in danh_sach_cong_viec if cv["id"] == task_id), None)
    if not task:
        return jsonify({"success": False, "message": f"Không tìm thấy công việc #{task_id}"}), 404

    task["trang_thai"] = "xong" if task["trang_thai"] == "dang_lam" else "dang_lam"
    
    return jsonify({
        "success": True,
        "message": f"Đã chuyển trạng thái sang {'Xong' if task['trang_thai'] == 'xong' else 'Đang làm'}",
        "data": task
    })


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    """
    Xóa công việc theo ID.
    """
    global danh_sach_cong_viec
    task = next((cv for cv in danh_sach_cong_viec if cv["id"] == task_id), None)
    
    if not task:
        return jsonify({"success": False, "message": f"Không tìm thấy công việc #{task_id}"}), 404

    danh_sach_cong_viec = [cv for cv in danh_sach_cong_viec if cv["id"] != task_id]
    
    return jsonify({
        "success": True,
        "message": f"Đã xóa thành công công việc #{task_id}"
    })


if __name__ == "__main__":
    print("=" * 60)
    print("  Ứng dụng Quản lý công việc KTNB (Agribank To-Do)")
    print("  Đang chạy tại: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=True)
