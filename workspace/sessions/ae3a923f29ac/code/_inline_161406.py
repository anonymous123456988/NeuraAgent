
import os, glob, shutil

home = os.path.expanduser("~")
targets = {
    "用户临时文件 (Temp)": os.path.join(home, "AppData", "Local", "Temp"),
    "系统临时文件 (Windows Temp)": r"C:\Windows\Temp",
    "Chrome 缓存": os.path.join(home, "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Cache"),
    "Edge 缓存": os.path.join(home, "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "Cache"),
    "缩略图缓存": os.path.join(home, "AppData", "Local", "Microsoft", "Windows", "Explorer"),
    "pip 缓存": os.path.join(home, "AppData", "Local", "pip", "Cache"),
    "npm 缓存": os.path.join(home, "AppData", "Roaming", "npm-cache"),
    "Windows 更新缓存": r"C:\Windows\SoftwareDistribution\Download",
    "回收站": r"C:\$Recycle.Bin",
}

def dir_size(p):
    total = 0
    if not os.path.exists(p):
        return None
    for root, dirs, files in os.walk(p):
        for f in files:
            try:
                fp = os.path.join(root, f)
                if not os.path.islink(fp):
                    total += os.path.getsize(fp)
            except Exception:
                pass
    return total

def human(n):
    if n is None: return "不存在"
    for u in ["B","KB","MB","GB","TB"]:
        if n < 1024: return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} PB"

rows = []
grand = 0
for name, path in targets.items():
    s = dir_size(path)
    if s:
        grand += s
    rows.append((name, path, human(s), s))

rows.sort(key=lambda r: -(r[3] or 0))
print(f"{'缓存类别':<26}{'大小':>12}   路径")
print("-"*90)
for name, path, hs, s in rows:
    print(f"{name:<26}{hs:>12}   {path}")
print("-"*90)
print(f"{'合计可清理':<26}{human(grand):>12}")
