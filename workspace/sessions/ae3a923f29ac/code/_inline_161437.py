
import os, ctypes

root = r"C:\$Recycle.Bin"
before = 0
for r, d, fs in os.walk(root):
    for f in fs:
        try: before += os.path.getsize(os.path.join(r, f))
        except: pass

def human(n):
    for u in ["B","KB","MB","GB"]:
        if n < 1024: return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"

print("回收站清理前:", human(before))

flags = 1 | 2 | 4
try:
    res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
    print("SHEmptyRecycleBin 返回码:", res, "(0=成功)")
except Exception as e:
    print("API 调用失败:", e)

after = 0
for r, d, fs in os.walk(root):
    for f in fs:
        try: after += os.path.getsize(os.path.join(r, f))
        except: pass
print("回收站清理后:", human(after))
print("本次释放:", human(max(0, before - after)))
