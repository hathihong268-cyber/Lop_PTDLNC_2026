try:
    a = int(input("Nhập số a: "))
    b = int(input("Nhập số b: "))
except ValueError:
    print("❌ Vui lòng nhập số nguyên hợp lệ!")
    exit()

print("Tổng:", a + b)
print("Hiệu:", a - b)
print("Tích:", a * b)

if b == 0:
    print("Thương: ❌ Không thể chia cho 0!")
else:
    print("Thương:", a / b)
