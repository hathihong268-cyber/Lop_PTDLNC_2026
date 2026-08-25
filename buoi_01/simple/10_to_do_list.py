# ============================================
# BÀI 10 - ỨNG DỤNG TO-DO LIST
# Yêu cầu AI: "Tạo ứng dụng to-do list có thể
# thêm việc cần làm, đánh dấu hoàn thành và xóa"
# ============================================

cong_viec = []  # Mỗi phần tử là [tên công việc, trạng thái hoàn thành]

def hien_thi_danh_sach():
    if len(cong_viec) == 0:
        print("  📭 Danh sách đang trống! Hãy thêm việc cần làm.")
        return

    print(f"\n  {'STT':<5} {'TRẠNG THÁI':<12} {'CÔNG VIỆC'}")
    print("  " + "-" * 40)
    for i, (ten, hoan_thanh) in enumerate(cong_viec, 1):
        trang_thai = "✅ Xong" if hoan_thanh else "⏳ Chưa"
        print(f"  {i:<5} {trang_thai:<12} {ten}")

print("=" * 40)
print("       ✅ ỨNG DỤNG TO-DO LIST")
print("=" * 40)

while True:
    print("\nChức năng:")
    print("  1. Thêm công việc")
    print("  2. Đánh dấu hoàn thành")
    print("  3. Xóa công việc")
    print("  4. Xem danh sách")
    print("  0. Thoát")

    lua_chon = input("\nChọn (0-4): ")

    if lua_chon == "0":
        so_hoan_thanh = sum(1 for _, done in cong_viec if done)
        print(f"\n📊 Tổng kết: {so_hoan_thanh}/{len(cong_viec)} việc đã hoàn thành!")
        print("Tạm biệt! 👋")
        break

    elif lua_chon == "1":
        ten = input("Nhập tên công việc: ").strip()
        if not ten:
            print("❌ Tên công việc không được để trống!")
        else:
            cong_viec.append([ten, False])
            print(f"✅ Đã thêm: '{ten}'")

    elif lua_chon == "2":
        hien_thi_danh_sach()
        if cong_viec:
            try:
                so = int(input("\nNhập số thứ tự việc đã xong: ")) - 1
                if 0 <= so < len(cong_viec):
                    cong_viec[so][1] = True
                    print(f"✅ Đã đánh dấu hoàn thành: '{cong_viec[so][0]}'")
                else:
                    print("❌ Số thứ tự không hợp lệ!")
            except ValueError:
                print("❌ Vui lòng nhập số!")

    elif lua_chon == "3":
        hien_thi_danh_sach()
        if cong_viec:
            try:
                so = int(input("\nNhập số thứ tự việc muốn xóa: ")) - 1
                if 0 <= so < len(cong_viec):
                    da_xoa = cong_viec.pop(so)
                    print(f"🗑️ Đã xóa: '{da_xoa[0]}'")
                else:
                    print("❌ Số thứ tự không hợp lệ!")
            except ValueError:
                print("❌ Vui lòng nhập số!")

    elif lua_chon == "4":
        hien_thi_danh_sach()
