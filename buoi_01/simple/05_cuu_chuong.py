try:
    n = int(input("In bảng cửu chương số mấy? (1 - 9): "))
except ValueError:
    print("❌ Vui lòng nhập số nguyên hợp lệ!")
    exit()

if n < 1 or n > 9:
    print("❌ Vui lòng nhập số từ 1 đến 9!")
else:
    for i in range(1, 11):
        print(n, "x", i, "=", n * i)
