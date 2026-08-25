# ============================================
# BÀI 11 - GAME TRẮC NGHIỆM
# Yêu cầu AI: "Tạo game trắc nghiệm 5 câu hỏi
# về kiến thức tổng hợp, có chấm điểm và xếp loại"
# ============================================

import random

cau_hoi = [
    {
        "cau": "Thủ đô của Việt Nam là gì?",
        "dap_an": ["A. TP. Hồ Chí Minh", "B. Hà Nội", "C. Đà Nẵng", "D. Huế"],
        "dung": "B"
    },
    {
        "cau": "1 + 1 = ?",
        "dap_an": ["A. 1", "B. 3", "C. 2", "D. 11"],
        "dung": "C"
    },
    {
        "cau": "Python là gì?",
        "dap_an": ["A. Một loài rắn", "B. Ngôn ngữ lập trình", "C. Phần mềm đồ họa", "D. Hệ điều hành"],
        "dung": "B"
    },
    {
        "cau": "Việt Nam có bao nhiêu tỉnh thành?",
        "dap_an": ["A. 58", "B. 60", "C. 63", "D. 65"],
        "dung": "C"
    },
    {
        "cau": "AI viết tắt của từ gì?",
        "dap_an": ["A. Auto Intelligence", "B. Artificial Intelligence", "C. Advanced Internet", "D. Android Interface"],
        "dung": "B"
    },
    {
        "cau": "Năm 2025 có bao nhiêu ngày?",
        "dap_an": ["A. 364", "B. 366", "C. 365", "D. 360"],
        "dung": "C"
    },
    {
        "cau": "Ngôn ngữ nào được dùng nhiều nhất trong AI/ML?",
        "dap_an": ["A. Java", "B. C++", "C. Python", "D. JavaScript"],
        "dung": "C"
    },
]

print("=" * 40)
print("       🎮 GAME TRẮC NGHIỆM")
print("=" * 40)

ten = input("Nhập tên của bạn: ").strip()
if not ten:
    ten = "Bạn"

print(f"\nChào {ten}! Game bắt đầu! 🚀")
print("Trả lời bằng cách nhập A, B, C hoặc D\n")

# Chọn ngẫu nhiên 5 câu từ ngân hàng câu hỏi
bo_cau_hoi = random.sample(cau_hoi, 5)
diem = 0

for i, cau in enumerate(bo_cau_hoi, 1):
    print(f"Câu {i}/5: {cau['cau']}")
    for dap_an in cau["dap_an"]:
        print(f"  {dap_an}")

    # Yêu cầu nhập lại cho đến khi đúng định dạng A/B/C/D
    while True:
        tra_loi = input("Đáp án của bạn (A/B/C/D): ").upper().strip()
        if tra_loi in ["A", "B", "C", "D"]:
            break
        print("❌ Vui lòng chỉ nhập A, B, C hoặc D!")

    if tra_loi == cau["dung"]:
        print("🎉 Đúng rồi!\n")
        diem += 1
    else:
        print(f"❌ Sai! Đáp án đúng là: {cau['dung']}\n")

# Tổng kết
print("=" * 40)
print(f"  KẾT QUẢ CỦA {ten.upper()}")
print("=" * 40)
print(f"  Điểm số: {diem}/5")
print(f"  Tỷ lệ:   {diem * 20}%")

if diem == 5:
    xep_loai = "🏆 XUẤT SẮC!"
elif diem >= 4:
    xep_loai = "🥇 Giỏi!"
elif diem >= 3:
    xep_loai = "🥈 Khá!"
elif diem >= 2:
    xep_loai = "🥉 Trung bình"
else:
    xep_loai = "😅 Cần cố gắng thêm!"

print(f"  Xếp loại: {xep_loai}")
print("=" * 40)
