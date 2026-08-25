# ============================================
# BÀI 09 - ĐỔI TIỀN TỆ
# Yêu cầu AI: "Tạo chương trình đổi tiền giữa
# VND, USD và EUR với tỷ giá cập nhật"
# ============================================

# Tỷ giá quy đổi (tham khảo)
TY_GIA = {
    "USD": 25_000,   # 1 USD = 25,000 VND
    "EUR": 27_500,   # 1 EUR = 27,500 VND
    "JPY": 165,      # 1 JPY = 165 VND
}

print("=" * 40)
print("       💱 CÔNG CỤ ĐỔI TIỀN TỆ")
print("=" * 40)
print(f"  Tỷ giá hiện tại (so với VND):")
for loai_tien, ty_gia in TY_GIA.items():
    print(f"  • 1 {loai_tien} = {ty_gia:,} VND")

while True:
    print("\n--- Chọn chiều quy đổi ---")
    print("  1. VND  →  Ngoại tệ")
    print("  2. Ngoại tệ  →  VND")
    print("  0. Thoát")

    lua_chon = input("\nChọn (0-2): ").strip()

    if lua_chon == "0":
        print("Tạm biệt! 👋")
        break

    elif lua_chon == "1":
        try:
            so_tien = float(input("Nhập số tiền VND: "))
        except ValueError:
            print("❌ Số tiền không hợp lệ!")
            continue

        if so_tien < 0:
            print("❌ Số tiền không được âm!")
            continue

        loai = input("Đổi sang (USD / EUR / JPY): ").upper().strip()
        if loai not in TY_GIA:
            print(f"❌ Loại tiền không hợp lệ! Chỉ chấp nhận: {', '.join(TY_GIA.keys())}")
            continue

        ket_qua = so_tien / TY_GIA[loai]
        print(f"\n✅ {so_tien:,.0f} VND = {ket_qua:,.2f} {loai}")

    elif lua_chon == "2":
        loai = input("Nhập loại tiền (USD / EUR / JPY): ").upper().strip()
        if loai not in TY_GIA:
            print(f"❌ Loại tiền không hợp lệ! Chỉ chấp nhận: {', '.join(TY_GIA.keys())}")
            continue

        try:
            so_tien = float(input(f"Nhập số tiền {loai}: "))
        except ValueError:
            print("❌ Số tiền không hợp lệ!")
            continue

        if so_tien < 0:
            print("❌ Số tiền không được âm!")
            continue

        ket_qua = so_tien * TY_GIA[loai]
        print(f"\n✅ {so_tien:,.2f} {loai} = {ket_qua:,.0f} VND")

    else:
        print("❌ Lựa chọn không hợp lệ! Vui lòng nhập 0, 1 hoặc 2.")
