"""Kiểm tra môi trường OCR/RAG cho bài thực hành Buổi 5.

Mặc định chương trình chỉ kiểm tra. Dùng ``--fix`` để cài các thư viện bị thiếu
vào đúng môi trường Python đang chạy chương trình này.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Dependency:
    """Một thư viện cần cho quy trình trích xuất PDF tiếng Việt."""

    display_name: str
    package_name: str
    import_name: str
    purpose: str


DEPENDENCIES = (
    Dependency("PyMuPDF", "PyMuPDF", "fitz", "Đọc nội dung và ảnh từ PDF"),
    Dependency("Pillow", "Pillow", "PIL", "Xử lý ảnh trang PDF khi cần"),
    Dependency("Llama Cloud", "llama-cloud", "llama_cloud", "Kết nối dịch vụ Llama Cloud"),
    Dependency("Pydantic", "pydantic", "pydantic", "Kiểm tra cấu trúc dữ liệu"),
    Dependency("Streamlit", "streamlit", "streamlit", "Tạo giao diện thử nghiệm"),
    Dependency("python-dotenv", "python-dotenv", "dotenv", "Đọc cấu hình từ tệp .env"),
)


def installed_version(dependency: Dependency) -> str | None:
    """Trả về phiên bản nếu import được; không đọc cấu hình hay secret."""
    try:
        importlib.import_module(dependency.import_name)
        return importlib.metadata.version(dependency.package_name)
    except (ImportError, ModuleNotFoundError, importlib.metadata.PackageNotFoundError):
        return None


def print_table(rows: list[tuple[str, str, str]]) -> None:
    """In bảng văn bản không cần thư viện bên ngoài."""
    headers = ("Công cụ", "Trạng thái", "Phiên bản / ghi chú")
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    def line(values: tuple[str, str, str]) -> str:
        return "| " + " | ".join(value.ljust(widths[i]) for i, value in enumerate(values)) + " |"

    print(line(headers))
    print("|-" + "-|-".join("-" * width for width in widths) + "-|")
    for row in rows:
        print(line(row))


def install_missing(missing: list[Dependency]) -> int:
    """Cài duy nhất các gói đã FAIL bằng pip của môi trường hiện hành."""
    if not missing:
        print("Không có trạng thái FAIL cần khắc phục.")
        return 0

    packages = [dependency.package_name for dependency in missing]
    print("Đang khắc phục các gói FAIL: " + ", ".join(packages))
    print("Lưu ý: pip sẽ tải gói công khai từ kho đã cấu hình; không có secret nào được in ra.")
    result = subprocess.run([sys.executable, "-m", "pip", "install", *packages], check=False)
    if result.returncode == 0:
        print("Đã chạy cài đặt xong. Hãy chạy lại lệnh kiểm tra để xác nhận PASS.")
    else:
        print("Cài đặt chưa thành công. Hãy kiểm tra kết nối mạng, quyền truy cập PyPI, hoặc phiên bản Python.")
    return result.returncode


def main() -> int:
    # PowerShell cũ trên Windows có thể dùng CP1252; ép UTF-8 để bảng tiếng Việt
    # luôn in được mà không phụ thuộc vào cấu hình terminal của người học.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Kiểm tra các thư viện OCR/RAG của Buổi 5.")
    parser.add_argument("--fix", action="store_true", help="Cài các thư viện đang FAIL bằng pip.")
    args = parser.parse_args()

    rows = [("Python", "PASS", sys.version.split()[0])]
    missing: list[Dependency] = []
    for dependency in DEPENDENCIES:
        version = installed_version(dependency)
        if version is None:
            rows.append((dependency.display_name, "FAIL", f"Thiếu — {dependency.purpose}"))
            missing.append(dependency)
        else:
            rows.append((dependency.display_name, "PASS", f"{version} — {dependency.purpose}"))

    print_table(rows)
    if missing:
        print("\nHướng dẫn khắc phục:")
        for dependency in missing:
            print(f"- {dependency.display_name}: chạy lại với --fix để cài gói {dependency.package_name}.")
        if not args.fix:
            print("\nChế độ hiện tại chỉ kiểm tra, không tải/cài phần mềm.")
            print(f"Khi đã được phép cài đặt, chạy: {sys.executable} {__file__} --fix")
            return 1
    if args.fix:
        return install_missing(missing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
