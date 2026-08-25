try:
    diem = float(input("Nhập điểm (0 - 10): "))
except ValueError:
    print("❌ Vui lòng nhập số hợp lệ!")
    exit()

if diem < 0 or diem > 10:
    print("❌ Điểm phải nằm trong khoảng từ 0 đến 10!")
elif diem >= 8:
    print("Giỏi")
elif diem >= 6.5:
    print("Khá")
elif diem >= 5:
    print("Trung bình")
else:
    print("Yếu")
