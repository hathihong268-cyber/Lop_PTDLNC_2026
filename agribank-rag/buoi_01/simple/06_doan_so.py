import random

so_bi_mat = random.randint(1, 10)

print("Đoán số từ 1 đến 10")

while True:
    try:
        du_doan = int(input("Đoán: "))
    except ValueError:
        print("❌ Vui lòng nhập số nguyên!")
        continue

    if du_doan < 1 or du_doan > 10:
        print("❌ Vui lòng đoán số từ 1 đến 10!")
    elif du_doan < so_bi_mat:
        print("Lớn hơn!")
    elif du_doan > so_bi_mat:
        print("Nhỏ hơn!")
    else:
        print("Đúng rồi! 🎉")
        break
