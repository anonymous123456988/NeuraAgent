import os

home = os.path.expanduser("~")
local = os.environ.get("LOCALAPPDATA", os.path.join(home, "AppData", "Local"))
temp = os.environ.get("TEMP", os.path.join(local, "Temp"))

targets = [
    ("系统临时目录 TEMP", temp),
    ("Windows临时目录", r"C:\Windows\Temp"),
    ("IE系统网络缓存", os.path.join(local, "Microsoft", "Windows", "INetCache")),
    ("缩略图缓存", os.path.join(local, "Microsoft", "Windows", "Explorer")),
    ("CrashDumps", os.path.join(local, "CrashDumps")),
    ("Chrome缓存", os.path.join(local, "Google", "Chrome", "User Data", "Default", "Cache")),
    ("Edge缓存", os.path.join(local, "Microsoft", "Edge", "User Data", "Default", "Cache")),
    ("Windows更新缓存", r"C:\Windows\SoftwareDistribution\Download"),
]

def dir_size(path):
    total = 0
    cnt = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
                cnt += 1
            except Exception:
                pass
    return total, cnt

grand = 0
print("缓存位置 | 大小(MB) | 文件数")
print("-" * 45)
for name, p in targets:
    if os.path.exists(p):
        size, cnt = dir_size(p)
        grand += size
        print("%s | %.1f | %d" % (name, size/1048576, cnt))
    else:
        print("%s | 不存在" % name)
print("-" * 45)
print("可清理合计: %.1f MB (%.2f GB)" % (grand/1048576, grand/1073741824))
