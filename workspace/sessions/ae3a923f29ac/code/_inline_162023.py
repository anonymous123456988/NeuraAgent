
import os

home = os.path.expanduser("~")
findings = []

# ---------- 1. 启动文件夹 ----------
print("=== 1. 启动文件夹 ===")
startup_dirs = [
    os.path.join(home, "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs", "Startup"),
    r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp",
]
for d in startup_dirs:
    if os.path.exists(d):
        items = os.listdir(d)
        print(f"[{d}] -> {items if items else '空'}")
        for it in items:
            findings.append(("启动项", it, d))
    else:
        print(f"[{d}] 不存在")

# ---------- 2. 注册表 Run 键 ----------
print("\n=== 2. 注册表自启动项 (Run) ===")
try:
    import winreg
    run_keys = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
    ]
    for hive, path in run_keys:
        try:
            k = winreg.OpenKey(hive, path)
            i = 0
            while True:
                try:
                    name, val, _ = winreg.EnumValue(k, i)
                    print(f"  {name} = {val}")
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(k)
        except FileNotFoundError:
            pass
except Exception as e:
    print("注册表读取失败:", e)

# ---------- 3. Temp 目录可执行文件 ----------
print("\n=== 3. 临时目录中的可执行文件 ===")
temp_dirs = [os.path.join(home, "AppData", "Local", "Temp"), r"C:\Windows\Temp"]
susp_ext = (".exe", ".dll", ".scr", ".bat", ".vbs", ".ps1", ".cmd", ".pif")
cnt = 0
for td in temp_dirs:
    if not os.path.exists(td): continue
    for r, d, fs in os.walk(td):
        for f in fs:
            if f.lower().endswith(susp_ext):
                cnt += 1
                if cnt <= 30:
                    print("  ", os.path.join(r, f))
print(f"  共发现 {cnt} 个可执行类文件")

# ---------- 4. 网络解析配置文件检查 ----------
print("\n=== 4. 网络解析配置文件条目 ===")
cfg = r"C:\Windows\System32\drivers\etc\hosts"
try:
    with open(cfg, "r", encoding="utf-8", errors="ignore") as f:
        lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
    print(f"  有效条目数: {len(lines)}")
    for l in lines[:20]:
        print("   ", l)
    if len(lines) > 30:
        findings.append(("配置异常", f"{len(lines)} 条记录", cfg))
except Exception as e:
    print("  读取失败:", e)

# ---------- 5. 计划任务 ----------
print("\n=== 5. 非微软计划任务 ===")
task_dir = r"C:\Windows\System32\Tasks"
try:
    tasks = os.listdir(task_dir)
    non_ms = [t for t in tasks if not t.startswith("Microsoft") and not t.startswith("Windows")]
    print(f"  非系统任务数: {len(non_ms)}")
    for t in non_ms[:30]:
        print("   ", t)
except Exception as e:
    print("  任务读取失败:", e)

print("\n扫描完成")
