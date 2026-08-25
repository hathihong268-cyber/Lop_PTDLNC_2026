# ============================================
# BÀI 08 - QUẢN LÝ DANH SÁCH
# Yêu cầu AI: "Tạo chương trình quản lý danh sách
# tên, có thể thêm, xóa, tìm kiếm và hiển thị"
# ============================================

danh_sach = []

print("=" * 35)
print("     📋 QUẢN LÝ DANH SÁCH TÊN")
print("=" * 35)

while True:
    print("\nChức năng:")
    print("  1. Thêm tên")
    print("  2. Xóa tên")
    print("  3. Tìm kiếm")
    print("  4. Xem danh sách")
    print("  0. Thoát")

    lua_chon = input("\nChọn (0-4): ")

    if lua_chon == "0":
        print("Tạm biệt! 👋")
        break

    elif lua_chon == "1":
        ten = input("Nhập tên cần thêm: ")
        danh_sach.append(ten)
        print(f"✅ Đã thêm '{ten}' vào danh sách!")

    elif lua_chon == "2":
        ten = input("Nhập tên cần xóa: ")
        if ten in danh_sach:
            danh_sach.remove(ten)
            print(f"✅ Đã xóa '{ten}' khỏi danh sách!")
        else:
            print(f"❌ Không tìm thấy '{ten}' trong danh sách!")

    elif lua_chon == "3":
        ten = input("Nhập tên cần tìm: ")
        if ten in danh_sach:
            vi_tri = danh_sach.index(ten) + 1
            print(f"✅ Tìm thấy '{ten}' ở vị trí số {vi_tri}!")
        else:
            print(f"❌ Không tìm thấy '{ten}'!")

    elif lua_chon == "4":
        if len(danh_sach) == 0:
            print("📭 Danh sách đang trống!")
        else:
            print(f"\n📋 Danh sách ({len(danh_sach)} người):")
            for i, ten in enumerate(danh_sach, 1):
                print(f"  {i}. {ten}")
