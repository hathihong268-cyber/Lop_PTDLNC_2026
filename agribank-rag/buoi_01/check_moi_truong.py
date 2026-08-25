"""
╔══════════════════════════════════════════════════════════╗
║        KIỂM TRA MÔI TRƯỜNG LẬP TRÌNH                    ║
║        Buổi 1 – Vibe Coding | Hà Vũ Công                ║
╚══════════════════════════════════════════════════════════╝
Chạy: python check_moi_truong.py
"""

import sys
import os
import subprocess
import platform
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

system = platform.system()

# ─────────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────────

def run(cmd):
    """Chạy lệnh shell, trả về (stdout, returncode)."""
    try:
        result = subprocess.run(
            cmd, shell=True,
            capture_output=True, text=True, timeout=8
        )
        return result.stdout.strip() or result.stderr.strip(), result.returncode
    except Exception as e:
        return str(e), 1

def ok(msg):    print(f"  ✅  {msg}")
def fail(msg):  print(f"  ❌  {msg}")
def warn(msg):  print(f"  ⚠️   {msg}")
def info(msg):  print(f"  ℹ️   {msg}")
def head(msg):  print(f"\n{'─'*55}\n  {msg}\n{'─'*55}")

results = {}  # lưu kết quả để in bảng tổng kết

# ─────────────────────────────────────────────────────────
# 0. THÔNG TIN MÁY TÍNH
# ─────────────────────────────────────────────────────────
head("0. THÔNG TIN MÁY TÍNH")
print(f"  Hệ điều hành : {platform.system()} {platform.release()} ({platform.architecture()[0]})")
print(f"  Tên máy      : {platform.node()}")
print(f"  Thời gian    : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
print(f"  Thư mục hiện tại: {os.getcwd()}")

# ─────────────────────────────────────────────────────────
# 1. PYTHON
# ─────────────────────────────────────────────────────────
head("1. PYTHON")

# 1a. Kiểm tra qua sys info trước
ver = sys.version_info
label = f"Python {ver.major}.{ver.minor}.{ver.micro}"
python_ok = False

if ver.major >= 3:
    ok("Đã cài")
    python_ok = True
else:
    # Thử check lệnh 'py' (Python Install Manager)
    py_out, py_code = run("py --version")
    if py_code == 0:
        ok("Đã cài")
        python_ok = True
    else:
        fail("Chưa cài")
        python_ok = False

results["Python"] = python_ok

# Kiểm tra alias Microsoft Store
exe_path = sys.executable
if "WindowsApps" in exe_path and not python_ok:
    warn(f"Đang dùng: {exe_path}")
    warn("Đây là alias Microsoft Store, KHÔNG phải Python thật!")
    info("Sửa: Settings → Apps → Advanced app settings")
    info("         → App execution aliases → TẮT 'python'")
    info("Sau đó cài Python qua MSIX (python-manager) hoặc installer (.exe) từ python.org")
else:
    info(f"Đường dẫn hiện hành: {exe_path}")

# pip
out, code = run("pip --version")
if code != 0:
    # Thử check pip thông qua py launcher
    py_pip_out, py_pip_code = run("py -m pip --version")
    if py_pip_code == 0:
        ok("Đã cài")
        results["pip"] = True
    else:
        fail("Chưa cài")
        results["pip"] = False
else:
    ok("Đã cài")
    results["pip"] = True

# ─────────────────────────────────────────────────────────
# 2. GIT
# ─────────────────────────────────────────────────────────
head("2. GIT")
out, code = run("git --version")
if code == 0:
    ok("Đã cài")
    results["Git"] = True
else:
    fail("Chưa cài  →  Tải tại: https://git-scm.com")
    results["Git"] = False

# ─────────────────────────────────────────────────────────
# 3. NODE.JS & NPM
# ─────────────────────────────────────────────────────────
head("3. NODE.JS & NPM")
out, code = run("node --version")
if code == 0:
    ok("Đã cài")
    results["Node.js"] = True
else:
    node_found = False
    if system == "Windows":
        for p in [r"C:\Program Files\nodejs\node.exe", r"C:\Program Files (x86)\nodejs\node.exe"]:
            if os.path.exists(p):
                ok(f"Node.js đã cài tại: {p} (Nhưng chưa có trong PATH, hãy mở lại Terminal)")
                results["Node.js"] = True
                node_found = True
                break
    if not node_found:
        fail("Node.js chưa cài  →  Tải tại: https://nodejs.org")
        results["Node.js"] = False

out_npm, code_npm = run("npm --version")
if code_npm == 0:
    ok("Đã cài")
    results["npm"] = True
else:
    npm_found = False
    if system == "Windows":
        for p in [r"C:\Program Files\nodejs\npm.cmd", r"C:\Program Files (x86)\nodejs\npm.cmd"]:
            if os.path.exists(p):
                ok(f"npm đã cài tại: {p}")
                results["npm"] = True
                npm_found = True
                break
    if not npm_found:
        fail("npm không tìm thấy (thường đi kèm Node.js)")
        results["npm"] = False

# ─────────────────────────────────────────────────────────
# 4. VS CODE
# ─────────────────────────────────────────────────────────
head("4. VS CODE")
out, code = run("code --version")
if code == 0:
    ok("Đã cài")
    results["VS Code"] = True
else:
    code_found = False
    if system == "Windows":
        for p in [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Microsoft VS Code", "Code.exe"),
            r"C:\Program Files\Microsoft VS Code\Code.exe"
        ]:
            if os.path.exists(p):
                ok(f"VS Code đã cài tại: {p}")
                warn("Chưa thêm vào PATH. Gõ 'code' có thể chưa dùng được từ terminal.")
                results["VS Code"] = True
                code_found = True
                break
    if not code_found:
        fail("VS Code chưa cài hoặc chưa thêm vào PATH")
        info("Tải tại: https://code.visualstudio.com")
        info("Sau cài: mở VS Code → Ctrl+Shift+P → 'Shell Command: Install code in PATH'")
        results["VS Code"] = False

# Extensions
head("4b. VS CODE EXTENSIONS")
out, code = run("code --list-extensions")
if code == 0:
    extensions = out.lower().split("\n")
    exts_check = {
        "GitHub Copilot":   "github.copilot",
        "Python":           "ms-python.python",
        "Prettier":         "esbenp.prettier-vscode",
    }
    for name, ext_id in exts_check.items():
        if ext_id in extensions:
            ok(f"{name} ({ext_id})")
        else:
            warn(f"{name} chưa cài  →  Mở VS Code: Ctrl+Shift+X → tìm '{name}'")
else:
    warn("Không đọc được danh sách extensions (VS Code chưa trong PATH?)")

# ─────────────────────────────────────────────────────────
# 5. CURSOR IDE
# ─────────────────────────────────────────────────────────
head("5. CURSOR IDE")
out, code = run("cursor --version")
if code == 0:
    ok("Đã cài")
    results["Cursor"] = True
else:
    system = platform.system()
    cursor_found = False
    if system == "Windows":
        common_paths = [
            r"C:\Users\%USERNAME%\AppData\Local\Programs\cursor\Cursor.exe",
            r"C:\Program Files\Cursor\Cursor.exe",
        ]
        for p in common_paths:
            expanded = os.path.expandvars(p)
            if os.path.exists(expanded):
                ok(f"Cursor đã cài tại: {expanded}")
                warn("Chưa thêm vào PATH. Gõ 'cursor' có thể chưa dùng được từ terminal.")
                results["Cursor"] = True
                cursor_found = True
                break
    elif system == "Darwin": # macOS
        mac_paths = [
            "/Applications/Cursor.app",
        ]
        for p in mac_paths:
            if os.path.exists(p):
                ok(f"Cursor đã cài tại: {p}")
                results["Cursor"] = True
                cursor_found = True
                break
    elif system == "Linux":
        linux_paths = [
            "/opt/Cursor/cursor",
            "/usr/local/bin/cursor",
        ]
        for p in linux_paths:
            if os.path.exists(p):
                ok(f"Cursor đã cài tại: {p}")
                results["Cursor"] = True
                cursor_found = True
                break
                
    if not cursor_found:
        fail("Cursor chưa cài  →  Tải tại: https://cursor.sh")
        results["Cursor"] = False

# ─────────────────────────────────────────────────────────
# 6. ANTIGRAVITY IDE
# ─────────────────────────────────────────────────────────
head("6. ANTIGRAVITY IDE")
system = platform.system()
ag_found = False

if system == "Windows":
    ag_paths = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Antigravity IDE", "Antigravity IDE.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Antigravity IDE", "Antigravity.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "antigravity", "Antigravity.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "antigravity", "Antigravity.exe"),
        r"C:\Program Files\Antigravity IDE\Antigravity IDE.exe",
        r"C:\Program Files\Antigravity IDE\Antigravity.exe",
        r"C:\Program Files\Antigravity\Antigravity.exe",
        r"C:\Program Files (x86)\Antigravity IDE\Antigravity IDE.exe",
        r"C:\Program Files (x86)\Antigravity IDE\Antigravity.exe",
        r"C:\Program Files (x86)\Antigravity\Antigravity.exe",
    ]
    for p in ag_paths:
        expanded = os.path.expandvars(p)
        if os.path.exists(expanded):
            ok(f"AntiGravity đã cài tại: {expanded}")
            info("Đăng nhập bằng tài khoản Gmail cá nhân (@gmail.com)")
            results["AntiGravity"] = True
            ag_found = True
            break
elif system == "Darwin": # macOS
    ag_paths = [
        "/Applications/Antigravity.app",
        "/Applications/Antigravity IDE.app",
    ]
    for p in ag_paths:
        if os.path.exists(p):
            ok(f"AntiGravity đã cài tại: {p}")
            info("Đăng nhập bằng tài khoản Gmail cá nhân (@gmail.com)")
            results["AntiGravity"] = True
            ag_found = True
            break
elif system == "Linux":
    ag_paths = [
        "/opt/Antigravity/antigravity",
        "/usr/local/bin/antigravity",
    ]
    for p in ag_paths:
        if os.path.exists(p):
            ok(f"AntiGravity đã cài tại: {p}")
            results["AntiGravity"] = True
            ag_found = True
            break

if not ag_found:
    fail("AntiGravity chưa cài hoặc chưa tìm thấy")
    info("Tải tại: https://antigravity.google/download")
    info("Đăng nhập bằng Gmail cá nhân (KHÔNG dùng tài khoản Workspace)")
    results["AntiGravity"] = False

# ─────────────────────────────────────────────────────────
# 7. CLAUDE CODE CLI
# ─────────────────────────────────────────────────────────
head("7. CLAUDE CODE CLI")
out, code = run("claude --version")
if code == 0:
    ok("Đã cài")
    results["Claude Code CLI"] = True
else:
    claude_found = False
    if system == "Windows":
        p = os.path.join(os.environ.get("APPDATA", ""), "npm", "claude.cmd")
        if os.path.exists(p):
            ok(f"Claude Code CLI đã cài tại: {p}")
            results["Claude Code CLI"] = True
            claude_found = True
            
    if not claude_found:
        fail("Claude Code CLI chưa cài")
        info("Cài đặt: npm install -g @anthropic-ai/claude-code")
        info("Sau đó: claude --version để kiểm tra")
        results["Claude Code CLI"] = False



# ─────────────────────────────────────────────────────────
# TỔNG KẾT
# ─────────────────────────────────────────────────────────
head("📊 TỔNG KẾT")
passed = sum(1 for v in results.values() if v)
total  = len(results)

print(f"\n  {'Công cụ':<22} {'Trạng thái':>12}")
print(f"  {'─'*22} {'─'*12}")
for name, ok_flag in results.items():
    icon = "✅ Đã cài" if ok_flag else "❌ Chưa cài"
    print(f"  {name:<22} {icon:>12}")

print(f"\n  Kết quả: {passed}/{total} công cụ đã sẵn sàng")

if passed == total:
    print("\n  🎉 TUYỆT VỜI! Máy của bạn đã sẵn sàng hoàn toàn!")
elif passed >= total * 0.7:
    print("\n  👍 Ổn! Còn một vài thứ cần cài thêm, xem chi tiết ở trên.")
else:
    print("\n  🔧 Cần cài thêm nhiều thứ. Làm theo hướng dẫn từng mục ở trên.")

print(f"\n{'═'*55}")
