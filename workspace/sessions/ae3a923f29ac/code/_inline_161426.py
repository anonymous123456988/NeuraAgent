
import os, shutil

home = os.path.expanduser("~")
targets = [
    ("用户临时文件", os.path.join(home, "AppData", "Local", "Temp")),
    ("系统临时文件", r"C:\Windows\Temp"),
    ("Edge 缓存", os.path.join(home, "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "Cache")),
    ("缩略图缓存", os.path.join(home, "AppData", "Local", "Microsoft", "Windows", "Explorer")),
    ("pip 缓存", os.path.join(home, "AppData", "Local", "pip", "Cache")),
]

def clean(p):
    freed = 0; ok = 0; fail = 0
    if not os.path.exists(p):
        return 0, 0, 0
    for entry in os.listdir(p):
        fp = os.path.join(p, entry)
        try:
            sz = 0
            if os.path.isdir(fp) and not os.path.islink(fp):
                for r, d, fs in os.walk(fp):
                    for f in fs:
                        try: sz += os.path.getsize(os.path.join(r, f))
                        except: pass
                shutil.rmtree(fp, ignore_errors=True)
            else:
                sz = os.path.getsize(fp)
                os.remove(fp)
            freed += sz; ok += 1
        except Exception:
            fail += 1
    return freed, ok, fail

def human(n):
    for u in ["B","KB","MB","GB"]:
        if n < 1024: return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"

total = 0
print(f"{'项目':<16}{'释放':>12}  {'成功/失败'}")
print("-"*50)
for name, path in targets:
    f, ok, fail = clean(path)
    total += f
    print(f"{name:<16}{human(f):>12}  {ok}/{fail}")
print("-"*50)
print(f"{'合计释放':<16}{human(total):>12}")
