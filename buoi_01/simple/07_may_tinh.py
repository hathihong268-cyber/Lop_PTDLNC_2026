# ============================================
# BÀI 07 - MÁY TÍNH ĐƠN GIẢN
# Yêu cầu AI: "Tạo một máy tính có menu cho phép
# người dùng chọn phép tính và tính nhiều lần"
# ============================================

print("=" * 35)
print("       🧮 MÁY TÍNH ĐƠN GIẢN")
print("=" * 35)

while True:
    print("\nChọn phép tính:")
    print("  1. Cộng  (+)")
    print("  2. Trừ   (-)")
    print("  3. Nhân  (*)")
    print("  4. Chia  (/)")
    print("  0. Thoát")

    lua_chon = input("\nNhập lựa chọn (0-4): ").strip()

    if lua_chon == "0":
        print("Tạm biệt! 👋")
        break

    if lua_chon not in ["1", "2", "3", "4"]:
        print("❌ Lựa chọn không hợp lệ! Vui lòng nhập 0, 1, 2, 3 hoặc 4.")
        continue

    try:
        a = float(input("Nhập số thứ nhất: "))
        b = float(input("Nhập số thứ hai: "))
    except ValueError:
        print("❌ Vui lòng nhập số hợp lệ!")
        continue

    if lua_chon == "1":
        ket_qua = a + b
        phep_tinh = "+"
    elif lua_chon == "2":
        ket_qua = a - b
        phep_tinh = "-"
    elif lua_chon == "3":
        ket_qua = a * b
        phep_tinh = "*"
    elif lua_chon == "4":
        if b == 0:
            print("❌ Không thể chia cho 0!")
            continue
        ket_qua = a / b
        phep_tinh = "/"

    print(f"\n✅ Kết quả: {a} {phep_tinh} {b} = {ket_qua}")
