# Một công việc (task)
ten_cong_viec = "Rà soát Thông tư 41/2016"   # chuỗi (string)
do_uu_tien = 2                                # số nguyên (int), 1=cao nhất
da_hoan_thanh = False                         # boolean
 
print(f"Công việc: {ten_cong_viec} | Ưu tiên: {do_uu_tien} | Hoàn thành: {da_hoan_thanh}")

# Danh sách công việc
danh_sach_cong_viec = [
    {"ten": "Rà soát Thông tư 41/2016", "trang_thai": "dang_lam"},
    {"ten": "Lập checklist kiểm toán CNTT", "trang_thai": "chua_lam"},
    {"ten": "Đối chiếu quy định tín dụng", "trang_thai": "xong"},
]
 
print("Tổng số công việc:", len(danh_sach_cong_viec))
print("Công việc đầu tiên:", danh_sach_cong_viec[0])
print("Trạng thái công việc thứ hai:", danh_sach_cong_viec[1]["trang_thai"])

for cv in danh_sach_cong_viec:
    if cv["trang_thai"] == "xong":
        print(cv["ten"], "- ĐÃ XONG")
    elif cv["trang_thai"] == "dang_lam":
        print(cv["ten"], "- đang làm")
    else:
        print(cv["ten"], "- chưa làm")

def dem_theo_trang_thai(danh_sach, trang_thai):
    """Đếm số công việc có trạng thái chỉ định."""
    dem = 0
    for cv in danh_sach:
        if cv["trang_thai"] == trang_thai:
            dem += 1
    return dem
 
so_xong = dem_theo_trang_thai(danh_sach_cong_viec, "xong")
print("Số công việc đã xong:", so_xong)


import json
 
with open("cong_viec.json", "w", encoding="utf-8") as f:
    json.dump(danh_sach_cong_viec, f, ensure_ascii=False, indent=2)
 
print("Đã lưu file cong_viec.json")
