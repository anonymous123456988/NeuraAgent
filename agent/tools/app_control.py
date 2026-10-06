# -*- coding: utf-8 -*-
"""工具：软件操控(app_control / kill_process)。

AI 可以运行电脑里的任何软件(QQ/微信/浏览器/任意应用)并使用它们:
  - launch: 启动任意软件(Windows 注册表/环境 PATH; macOS open -a; Linux which + xdg-open)
  - type_text: 向软件窗口发送文本(Windows pywinauto / Linux xdotool)
  - click: 模拟鼠标点击软件界面(坐标; 可选)
  - screenshot: 截取软件当前界面画面, 渲染到控制板窗口(Windows PrintWindow / Linux import/scrot)
  - send_message: 通用消息发送流程(启动应用 -> 聚焦输入 -> 输入文本 -> 回车)
  - focus: 聚焦软件窗口

kill_process: 按进程名或 PID 结束进程(带系统关键进程黑名单保护, 管理员级红色警示)。

安全边界: 黑名单进程(system/关键服务)拒绝; 其余按用户指令执行。
"""
import asyncio
import json
import os
import platform
import shutil
import signal
import subprocess

from agent import safety
from .registry import Tool, ToolResult, ToolContext, ToolRegistry

_SYSTEM_PROCESSES = {
    "system", "systemd", "kernel", "kworker", "init", "launchd", "wininit", "services",
    "svchost", "lsass", "winlogon", "csrss", "smss", "explorer", "dock", "finder",
    "sshd", "nginx", "apache2", "mysqld", "postgres", "python", "python3",
}
# 消息类应用别名(发消息场景): 应用名 -> 启动命令
_MSG_APPS = {
    "qq": {"win": "QQ", "mac": "QQ", "nix": "qq"},
    "微信": {"win": "WeChat", "mac": "WeChat", "nix": "wechat"},
    "wechat": {"win": "WeChat", "mac": "WeChat", "nix": "wechat"},
}


def _read_lnk(lnk: str) -> str | None:
    """解析 Windows .lnk 快捷方式的目标路径(PowerShell WScript.Shell)。"""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');$s.TargetPath"],
            capture_output=True, text=True, timeout=8)
        t = (r.stdout or "").strip()
        return t or None
    except Exception:
        return None


def _locate_win_app(app: str) -> str | None:
    """Windows 应用定位: PATH -> App Paths 注册表 -> 常见安装目录 -> 开始菜单快捷方式。"""
    import glob
    name = app if app.lower().endswith(".exe") else app + ".exe"
    fnd = shutil.which(app) or shutil.which(name)
    if fnd:
        return fnd
    try:
        import winreg
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                k = winreg.OpenKey(root, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{name}")
                path, _ = winreg.QueryValueEx(k, "")
                if path and os.path.exists(path):
                    return path
            except Exception:
                pass
    except Exception:
        pass
    roots = [os.environ.get("ProgramFiles", r"C:\Program Files"),
             os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
             os.path.expanduser("~")]
    for root in roots:
        for pat in (rf"{root}\*{app}*", rf"{root}\*\*{app}*.exe"):
            for c in glob.glob(pat):
                if os.path.isfile(c) and c.lower().endswith(".exe"):
                    return c
                if os.path.isdir(c):
                    for f in glob.glob(rf"{c}\**\*.exe", recursive=True):
                        if app.lower() in os.path.basename(f).lower():
                            return f
    sm_dirs = [os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"),
                            r"Microsoft\Windows\Start Menu\Programs"),
               os.path.join(os.path.expanduser("~"),
                            r"AppData\Roaming\Microsoft\Windows\Start Menu\Programs")]
    for sm in sm_dirs:
        for lnk in glob.glob(rf"{sm}\**\*{app}*.lnk", recursive=True):
            target = _read_lnk(lnk)
            if target and os.path.exists(target):
                return target
    return None


def _locate_nix_app(app: str) -> str | None:
    """Linux/macOS 应用定位: PATH / 常见目录 / .desktop 的 Exec / .app 包。"""
    import glob
    if platform.system() == "Darwin":
        for base in ("/Applications", os.path.expanduser("~/Applications")):
            hits = glob.glob(f"{base}/*{app}*.app")
            if hits:
                return f"open -a {os.path.basename(hits[0])[:-4]}"
        return None
    fnd = shutil.which(app)
    if fnd:
        return fnd
    for c in (f"/usr/bin/{app}", f"/usr/local/bin/{app}", f"/bin/{app}", f"/sbin/{app}"):
        if os.path.exists(c):
            return c
    for d in ("/usr/share/applications", "/usr/local/share/applications",
              os.path.expanduser("~/.local/share/applications")):
        for f in glob.glob(f"{d}/*{app}*.desktop"):
            for line in open(f, encoding="utf-8", errors="ignore"):
                if line.startswith("Exec="):
                    exe = line[5:].strip().split()[0]
                    if exe.startswith("/") and os.path.exists(exe):
                        return exe
                    fnd2 = shutil.which(os.path.basename(exe))
                    if fnd2:
                        return fnd2
    return None


def _platform_cmd(app: str) -> str | None:
    """解析一个应用名/命令到当前平台的启动命令; 找不到返回 None(不裸返回 app 触发系统报错弹窗)。"""
    if os.name == "nt":
        return _locate_win_app(app)
    return _locate_nix_app(app)


def _title_exclude(wt: str) -> bool:
    """窗口标题过滤: 排除设置/帮助/登录等非主窗口标题。"""
    _ex = ("设置", "帮助", "登录", "安全", "协议", "新闻", "关于", "向导", "助手", "注册", "激活", "升级")
    return not any(e in wt for e in _ex)


def _find_window_by_title(app: str):
    """快速定位应用主窗口: ① win32gui EnumWindows 毫秒级快速通道(标题匹配) ② UIA 兜底。
    返回 pywinauto 窗口对象或 None; 全程低延迟。"""
    app_low = app.lower().replace(".exe", "").strip()
    if not app_low:
        return None
    # ① 快速通道: win32gui 原生枚举(毫秒级, 避免 UIA 全桌面慢扫描)
    if os.name == "nt":
        try:
            import win32gui
            import pywinauto
            hits = []
            def _cb(h, _):
                try:
                    if not win32gui.IsWindowVisible(h):
                        return
                    wt = win32gui.GetWindowText(h) or ""
                    if not wt.strip() or not _title_exclude(wt):
                        return
                    wl = wt.lower()
                    if app_low in wl:
                        if len(wt) <= 24 or any(k in wl for k in ("聊天", "消息", "会话", "通讯", "主界面")):
                            hits.append(h)
                except Exception:
                    pass
            win32gui.EnumWindows(_cb, None)
            if hits:
                # win32 backend 比 uia 快得多; 若失败再退 uia
                try:
                    return pywinauto.Application(backend="win32").window(handle=hits[0])
                except Exception:
                    pass
        except Exception:
            pass
    # ② UIA 兜底
    try:
        from pywinauto import Desktop
        for w in Desktop(backend="uia").windows():
            wt = w.window_text() or ""
            if not wt.strip() or not _title_exclude(wt):
                continue
            wl = wt.lower()
            if app_low in wl:
                if len(wt) <= 24 or any(k in wl for k in ("聊天", "消息", "会话", "主界面", "通讯")):
                    return w
        # ③ 兜底: 前台窗口
        for w in Desktop(backend="uia").windows():
            try:
                if w.is_active() and _title_exclude(w.window_text() or ""):
                    return w
            except Exception:
                continue
    except Exception:
        pass
    return None


def _activate_window(win) -> bool:
    """快速精准聚焦窗口: set_focus + SetForegroundWindow + 最小化恢复。"""
    if win is None:
        return False
    try:
        win.set_focus()
    except Exception:
        pass
    try:
        import win32gui, win32con
        h = int(win.handle) if hasattr(win, "handle") else None
        if h:
            if win32gui.IsIconic(h):
                win32gui.ShowWindow(h, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(h)
        return True
    except Exception:
        return False


def _detect_and_focus(app: str) -> dict | None:
    """检测应用是否已在运行(前台窗口 + 后台进程双通道), 已运行且【有可见窗口】则聚焦复用。
    返回 {"status", "method", "focused", "reuse"} 或 None(未运行)。
    v3.32 修复"打开QQ没打开": 仅进程命中而无可见窗口时 reuse=False —— 不误判为
    "已在运行", 调用方将继续启动新实例, 保证"打开QQ"一定有结果。
    进程检测只按映像名/进程名匹配(兼容 QQ.exe/QQScLauncher/Weixin 变体), 不匹配
    Agent 自身进程(cmdline 含 app 关键词的无关进程不会误判)。"""
    import time
    app_low = app.lower().replace(".exe", "").strip()
    if not app_low:
        return None
    # ---- Windows: 进程检测(映像名模糊) + 窗口检测 ----
    if os.name == "nt":
        running = False
        try:
            # 全量 tasklist CSV: 映像名字段含 app_low 即算命中(排除 Agent 自身 python/node 进程)
            r = subprocess.run(["tasklist", "/FO", "CSV"], capture_output=True, text=True, timeout=8)
            for _line in (r.stdout or "").splitlines():
                _fields = [_f.strip().strip('"') for _f in _line.split(',')]
                _img = (_fields[0] if _fields else "").lower()
                if _img.startswith(("python", "node", "java", "php", "nginx")):
                    continue
                if app_low in _img:
                    running = True
                    break
        except Exception:
            pass
        if not running:
            try:
                import psutil
                for p in psutil.process_iter(["name"]):
                    try:
                        _nm = (p.info.get("name") or "").lower()
                        if _nm.startswith(("python", "node", "java", "php", "nginx")):
                            continue
                        if app_low in _nm:
                            running = True
                            break
                    except Exception:
                        continue
            except Exception:
                pass
        # 窗口优先判定(毫秒级): 找到可见主窗 -> 聚焦并复用
        win = _find_window_by_title(app) if running else None
        if win:
            focused = _activate_window(win)
            return {"status": "already_running", "method": "window", "focused": focused,
                    "reuse": True}
        if running:
            # 仅后台进程/无窗口: 不判定复用, 调用方继续启动(保证有结果)
            return {"status": "process_only", "method": "process", "focused": False,
                    "reuse": False}
        return None
    # ---- Linux/macOS: 进程检测(pgrep 精确进程名, 规避子串误匹配自身) ----
    try:
        r = subprocess.run(["pgrep", "-x", app_low], capture_output=True, text=True, timeout=6)
        if (r.stdout or "").strip():
            return {"status": "process_only", "method": "process", "focused": False,
                    "reuse": False}
    except Exception:
        pass
    return None


def _launch_cmd(command: str, args: str = "") -> subprocess.Popen:
    """平台相关启动, 返回进程对象。"""
    if os.name == "nt":
        return subprocess.Popen(f'start "" "{command}" {args}', shell=True)
    if platform.system() == "Darwin":
        return subprocess.Popen(f"{command} {args}".strip(), shell=True, start_new_session=True)
    # Linux: 带 GUI 命令用 xdg-open 兜底(后台), 纯命令直接执行
    if command.startswith("/") and os.path.exists(command):
        return subprocess.Popen(f"{command} {args}".strip(), shell=True, start_new_session=True,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return subprocess.Popen(f"xdg-open '{command}' >/dev/null 2>&1 &", shell=True)


async def _launch_app(args: dict, ctx: ToolContext) -> ToolResult:
    app = str(args.get("app", "")).strip()
    argv = str(args.get("args", "")).strip()
    if not app:
        return ToolResult(ok=False, error="缺少 app 参数", error_type="invalid_args")
    # v3.30/3.32: 复用已打开实例 —— 前台窗口+后台进程双通道检测;
    # 检测到【可见窗口】才直接聚焦复用; 仅后台进程(无窗口)不判定复用, 继续启动新实例,
    # 保证"打开QQ"等指令一定有结果, 不再出现"说打开了但没打开"。
    try:
        det = _detect_and_focus(app)
    except Exception:
        det = None
    if det and det.get("reuse"):
        await ctx.emitter.notify(
            f"{app} 已在运行, 已直接聚焦现有实例",
            level="info")
        return ToolResult(data={"app": app, "status": "already_running",
                                "detect": det, "launched": False, "reused": True})
    # 安全: 不允许用 shell 元字符注入
    for meta in (";", "&&", "|", ">", "<", "$", "`"):
        if meta in app or meta in argv:
            return ToolResult(ok=False, error="应用名/参数不允许包含 shell 元字符", error_type="forbidden")
    cmd = _platform_cmd(app)
    if not cmd:
        tried = ("环境 PATH / 注册表 App Paths / 常见安装目录 / 开始菜单快捷方式"
                 if os.name == "nt" else "环境 PATH / 常见目录 / 桌面快捷方式(.desktop)")
        return ToolResult(ok=False,
                          error=f"未找到「{app}」的可执行程序（已尝试: {tried}）。"
                                 "请确认软件已安装，或在 config.json 的 ai.app_paths 中配置其安装路径后重试。",
                          error_type="exec")
    try:
        proc = _launch_cmd(cmd, argv)
        pid = proc.pid if proc else None
    except Exception as e:
        return ToolResult(ok=False, error=f"启动失败: {e}", error_type="exec", retryable=True)
    await ctx.emitter.notify(f"已启动软件: {app}", level="info")
    return ToolResult(data={"app": app, "command": cmd, "pid": pid, "status": "launched", "launched": True})


def _find_screenshot_tool() -> str | None:
    """探测可用的窗口截图工具(Linux)。"""
    for tool in ("import", "scrot", "gnome-screenshot", "xwd"):
        p = shutil.which(tool)
        if p:
            return p
    return None


async def _screenshot(args: dict, ctx: ToolContext) -> ToolResult:
    if os.name == "nt":
        # Windows: 预留 PrintWindow/前台窗口截图(需 pywin32; 无则提示安装)
        try:
            import pywintypes  # noqa
            from PIL import ImageGrab  # noqa
            img = ImageGrab.grab()
            buf = __import__("io").BytesIO()
            img.convert("RGB").save(buf, format="PNG")
            b64 = __import__("base64").b64encode(buf.getvalue()).decode()
            return ToolResult(data={"image_base64": b64, "mime": "image/png", "source": "screen"})
        except Exception as e:
            return ToolResult(ok=False, error=f"Windows 截图需安装 pywin32+Pillow: {e}", error_type="exec")
    tool = _find_screenshot_tool()
    if not tool:
        return ToolResult(ok=False, error="未检测到截图工具(需安装 x11-apps 的 import / scrot)", error_type="exec")
    out = os.path.join(ctx.downloads_dir, "appview.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    try:
        if tool.endswith("scrot"):
            r = subprocess.run([tool, out], capture_output=True, timeout=8)
        else:
            r = subprocess.run([tool, "-window", "root", out], capture_output=True, timeout=8)
        if r.returncode != 0 or not os.path.exists(out):
            return ToolResult(ok=False, error=f"截图失败: {r.stderr.decode('utf-8','replace')[:200]}", error_type="exec")
        import base64
        with open(out, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return ToolResult(data={"image_base64": b64, "mime": "image/png",
                                "source": "software_screen", "file": out})
    except Exception as e:
        return ToolResult(ok=False, error=f"截图失败: {e}", error_type="exec", retryable=True)


def _typing_tool() -> str | None:
    if os.name == "nt":
        return "pywinauto" if shutil.which("python") else None
    return shutil.which("xdotool")


async def _type_text(args: dict, ctx: ToolContext) -> ToolResult:
    text = str(args.get("text", ""))
    if not text:
        return ToolResult(ok=False, error="缺少 text 参数", error_type="invalid_args")
    if os.name == "nt":
        try:
            from pywinauto import keyboard
            keyboard.send_keys(text, with_spaces=True)
            return ToolResult(data={"typed": text, "method": "pywinauto"})
        except Exception as e:
            return ToolResult(ok=False, error=f"Windows 键入需安装 pywinauto: {e}", error_type="exec")
    xdt = _typing_tool()
    if not xdt:
        return ToolResult(ok=False, error="未检测到 xdotool(可 apt install xdotool), 无法向软件发送按键", error_type="exec")
    try:
        r = subprocess.run([xdt, "type", "--delay", "40", text], capture_output=True, timeout=15)
        if r.returncode != 0:
            return ToolResult(ok=False, error=r.stderr.decode("utf-8", "replace")[:200], error_type="exec")
        return ToolResult(data={"typed": text, "method": "xdotool"})
    except Exception as e:
        return ToolResult(ok=False, error=f"键入失败: {e}", error_type="exec", retryable=True)


def _gui_send_msg(app: str, to: str, text: str):
    """Windows 真实 GUI 发送消息: 定位应用主窗 -> 搜索接收人 -> 进入会话 -> 聚焦输入 -> 输入文本 -> 回车 -> 截图证据。
    小AI 全程监管: 仅向目标窗口发送, 不做任何其他系统操作。"""
    import time
    from pywinauto import Desktop, keyboard as kb
    steps = []
    app_low = app.lower()
    # 1) 定位应用主窗口(多轮等待): ① pywinauto UIA 桌面遍历 ② 按进程 PID 关联窗口(兼容新版 QQ/微信标题) ③ 前台窗口兜底
    win = None
    qq_pids = set()
    try:
        import psutil
        for p in psutil.process_iter(["name", "pid"]):
            try:
                nm = (p.info.get("name") or "").lower()
                if ("qq" in nm and "qq" in app_low) or ("wechat" in nm or "weixin" in nm) and ("wechat" in app_low or "微信" in app_low):
                    qq_pids.add(p.info["pid"])
            except Exception:
                pass
    except Exception:
        pass
    for _ in range(14):
        try:
            for w in Desktop(backend="uia").windows():
                wt = w.window_text() or ""
                if "QQ" in app_low and "QQ" in wt and not any(e in wt for e in ("设置", "帮助", "登录", "安全", "协议", "新闻", "关于", "向导", "助手")):
                    if ("聊天" in wt or "消息" in wt or "会话" in wt or wt.strip() == "QQ"
                            or ("QQ" in wt and len(wt) <= 20)):
                        win = w
                        break
                if "wechat" in app_low or "微信" in app_low:
                    if "微信" in wt and ("聊天" in wt or "通讯" in wt):
                        win = w
                        break
        except Exception:
            pass
        if win:
            break
        # ② win32gui 按 PID 枚举可见窗口
        if not win and qq_pids:
            try:
                import win32gui
                def _cb(h, _):
                    global _hits
                    if win32gui.IsWindowVisible(h):
                        try:
                            _, pid = win32gui.GetWindowThreadProcessId(h)
                        except Exception:
                            pid = 0
                        if pid in qq_pids and win32gui.GetWindowText(h).strip():
                            _hits.append(h)
                _hits = []
                win32gui.EnumWindows(_cb, None)
                if _hits:
                    import pywinauto
                    win = pywinauto.Application(backend="uia").window(handle=_hits[0])
                    win.set_focus()
                    break
            except Exception:
                pass
        time.sleep(0.25)          # v3.31 快速轮询: 低延迟收敛
    if not win:
        # ②.5 系统托盘激活: 点击右下角通知区域 QQ 图标, 唤出主窗后再找一轮
        try:
            from pywinauto import mouse
            tray = None
            for w in Desktop(backend="uia").windows():
                if "Shell_TrayWnd" in str(w.class_name()):
                    tray = w
                    break
            if tray:
                for b in tray.descendants():
                    try:
                        nm = b.window_text() or ""
                        if "QQ" in nm and "notify" in str(b.class_name()).lower():
                            rect = b.rectangle()
                            mouse.click(coords=(rect.mid_point().x, rect.mid_point().y))
                            time.sleep(0.5)
                            break
                    except Exception:
                        continue
            for w in Desktop(backend="uia").windows():
                wt = w.window_text() or ""
                if "QQ" in app_low and "QQ" in wt and not any(e in wt for e in ("设置", "帮助", "登录")):
                    if "聊天" in wt or "消息" in wt or wt.strip() == "QQ":
                        win = w
                        break
        except Exception:
            pass
    if not win:
        # ③ 兜底: 最近前台窗口
        try:
            from pywinauto import Desktop
            for w in Desktop(backend="uia").windows():
                if w.is_active():
                    win = w
                    break
        except Exception:
            pass
    if not win:
        raise RuntimeError("未找到 " + app + " 主窗口")
    win.set_focus()
    time.sleep(0.4)
    steps.append("2. 已聚焦 " + app + " 主窗口")
    # 2) 打开搜索并输入接收人
    kb.send_keys("^f")
    time.sleep(0.25)
    kb.send_keys(to, with_spaces=True)
    time.sleep(0.3)
    kb.send_keys("{ENTER}")          # 进入/选中会话
    time.sleep(0.4)
    steps.append("3. 已搜索并进入 " + to + " 的会话")
    # 3) 聚焦消息输入框(QQ 输入框为 Edit/RichEdit/ATL 控件, 点击后输入; 找不到则 Tab)
    _focused = False
    try:
        if hasattr(win, "descendants"):
            for _ctrl in win.descendants():
                try:
                    _ct = str(_ctrl.class_name() or "")
                    if "Edit" in _ct or "RichEdit" in _ct or "ATL:30" in _ct:
                        _ctrl.click_input()
                        _focused = True
                        break
                except Exception:
                    continue
    except Exception:
        pass
    if not _focused:
        kb.send_keys("{TAB}", pause=0.05)
    time.sleep(0.3)
    kb.send_keys(text, with_spaces=True, pause=0.02)
    time.sleep(0.3)
    kb.send_keys("{ENTER}")
    time.sleep(0.6)
    steps.append("4. 已输入消息并回车发送")
    # 4) 截图证据
    try:
        img = win.capture_as_image()
        import io, base64
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return steps, b64
    except Exception:
        return steps, None


async def _send_message(args: dict, ctx: ToolContext) -> ToolResult:
    """通用消息发送: 启动消息应用 -> 聚焦输入 -> 输入文本 -> 回车。"""
    app = str(args.get("app", "")).strip() or "QQ"
    to = str(args.get("to", "")).strip()
    text = str(args.get("text", "")).strip()
    if not text:
        return ToolResult(ok=False, error="缺少 text 参数(要发送的消息内容)", error_type="invalid_args")
    alias = _MSG_APPS.get(app.lower())
    launch_name = (alias or {}).get("win" if os.name == "nt" else ("mac" if platform.system() == "Darwin" else "nix"), app) if alias else app
    # 1) 启动/复用应用: 已运行(前台窗口+后台进程)则直接复用, 不重复打开新实例
    try:
        det = _detect_and_focus(launch_name)
    except Exception:
        det = None
    if det and det.get("reuse"):
        await ctx.emitter.notify(f"检测到 {app} 已在运行, 直接复用现有实例", level="info")
        steps = [f"1. 已复用运行中的 {app}({det['method']})"]
    else:
        cmd = _platform_cmd(launch_name)
        if not cmd:
            return ToolResult(ok=False,
                              error=f"未找到消息应用「{app}」的可执行程序（已尝试: 环境 PATH / 注册表 App Paths / 常见安装目录 / 开始菜单快捷方式）。"
                                     "请确认已安装，或在 config.json 的 ai.app_paths 中配置路径。",
                              error_type="exec")
        try:
            _launch_cmd(cmd)
        except Exception as e:
            return ToolResult(ok=False, error=f"启动 {app} 失败: {e}", error_type="exec", retryable=True)
        await ctx.emitter.notify(f"已启动 {app}, 准备发送消息", level="info")
        # 2) 等待应用启动(复用路径已跳过等待, 低延迟)
        await asyncio.sleep(1.0)
        steps = [f"1. 已启动 {app}"]
    # 3) 真实 GUI 发送(Windows): 定位主窗 -> 搜索联系人 -> 进入会话 -> 聚焦输入 -> 回车 -> 截图证据
    sent_ok = False
    screenshot = None
    if os.name == "nt" and to:
        try:
            steps2, screenshot = _gui_send_msg(app, to, text)
            steps += steps2
            sent_ok = True
        except Exception as e:
            steps.append("GUI 精确发送失败(" + str(e)[:100] + "), 降级为全局键入")
    if not sent_ok:
        typed = text if not to else f"{to}\t{text}"
        if os.name == "nt":
            try:
                from pywinauto import keyboard
                keyboard.send_keys(typed, with_spaces=True)
                keyboard.send_keys("{ENTER}")
                steps.append("2. 已输入消息内容并回车(Windows pywinauto)")
            except Exception as e:
                return ToolResult(ok=False, error=f"发送失败(需安装 pywinauto): {e}", error_type="exec")
        else:
            xdt = _typing_tool()
            if not xdt:
                return ToolResult(ok=False, error="未检测到 xdotool, 无法自动输入(可在电脑上手动完成, 或 apt install xdotool)",
                                  error_type="exec")
            try:
                subprocess.run([xdt, "type", "--delay", "60", typed], capture_output=True, timeout=15)
                subprocess.run([xdt, "key", "Return"], capture_output=True, timeout=8)
                steps.append("2. 已输入消息内容并回车(xdotool)")
            except Exception as e:
                return ToolResult(ok=False, error=f"发送失败: {e}", error_type="exec", retryable=True)
        steps.append("3. 消息已发送")
    # 截图证据 -> 控制板图片窗口(证明消息确实已在应用内发出)
    if screenshot:
        try:
            await ctx.emitter.panel("msg_evidence", "image", "消息发送证据截图",
                                    {"image_base64": screenshot, "mime": "image/png",
                                     "note": f"{app} 界面实时截图: 已发送给 {to}"}, status="ok")
        except Exception:
            pass
    return ToolResult(data={"app": app, "to": to or "(当前会话)", "text": text,
                            "steps": steps, "status": "sent",
                            "evidence": bool(screenshot), "gui_sent": sent_ok}, admin=True)


async def _kill_process(args: dict, ctx: ToolContext) -> ToolResult:
    """按进程名或 PID 结束进程。系统关键进程受黑名单保护。"""
    name = str(args.get("name", "")).strip().lower()
    pid = args.get("pid")
    if not name and pid is None:
        return ToolResult(ok=False, error="需要提供 name(进程名) 或 pid", error_type="invalid_args")
    if name:
        base = name.split(".")[0]
        if base in _SYSTEM_PROCESSES or name in _SYSTEM_PROCESSES:
            return ToolResult(ok=False, error=f"进程 {name} 属于系统关键进程, 已保护拒绝", error_type="forbidden")
        for meta in (";", "&&", "|", "rm ", "format"):
            if meta in name:
                return ToolResult(ok=False, error="进程名含非法字符", error_type="forbidden")
    target_desc = f"进程 {name}" if name else f"PID {pid}"
    try:
        if os.name == "nt":
            cmdline = f'taskkill /IM {name} /F' if name else f'taskkill /PID {pid} /F'
            r = subprocess.run(cmdline, shell=True, capture_output=True, text=True, timeout=10)
            if r.returncode != 0:
                return ToolResult(ok=False, error=f"结束失败: {r.stderr.strip() or r.stdout.strip()}", error_type="exec")
        else:
            if name:
                # pkill -x 精确匹配进程名(避免 -f 误杀命令行含同名的无关进程/NEURA 自身)
                r = subprocess.run(["pkill", "-x", name], capture_output=True, timeout=8)
                if r.returncode != 0 and not name.endswith(".exe"):
                    r = subprocess.run(["pkill", "-x", name + ".exe"], capture_output=True, timeout=8)
            else:
                r = subprocess.run(["kill", "-TERM", str(int(pid))], capture_output=True, timeout=8)
            if r.returncode != 0:
                return ToolResult(ok=False, error="未找到该进程(名称不匹配)或结束失败", error_type="exec")
    except Exception as e:
        return ToolResult(ok=False, error=f"结束进程失败: {e}", error_type="exec", retryable=True)
    await ctx.emitter.notify(f"已结束{target_desc}", level="warn")
    return ToolResult(data={"killed": target_desc, "status": "killed"}, admin=True)


async def _app_control(args: dict, ctx: ToolContext) -> ToolResult:
    """AI 操控软件总入口: action=launch/type_text/screenshot/send_message/focus。"""
    action = str(args.get("action", "launch"))
    app = str(args.get("app", "")).strip()
    if action == "launch":
        return await _launch_app(args, ctx)
    if action == "screenshot":
        return await _screenshot(args, ctx)
    if action == "type_text":
        return await _type_text(args, ctx)
    if action == "send_message":
        return await _send_message(args, ctx)
    if action == "focus":
        win = _find_window_by_title(app)
        if not win:
            return ToolResult(ok=False, error=f"未找到「{app}」的窗口(前台/后台窗口均未检测到), 请先打开该软件",
                              error_type="exec")
        ok = _activate_window(win)
        return ToolResult(data={"focused": app, "ok": ok, "method": "window"})
        xdt = _typing_tool()
        if not xdt:
            return ToolResult(ok=False, error="未检测到 xdotool", error_type="exec")
        subprocess.run([xdt, "search", "--name", app, "windowactivate"], capture_output=True, timeout=8)
        return ToolResult(data={"focused": app})
    return ToolResult(ok=False, error=f"不支持的动作: {action}", error_type="invalid_args")


def register(registry: ToolRegistry):
    registry.register(Tool(
        name="app_control",
        description="运行并操控电脑里的任何软件(QQ/微信/浏览器/任意应用): action=launch 打开软件(已打开则自动检测前台窗口/后台进程并直接复用现有实例, 不重复打开) / send_message 给联系人发送消息(自动启动或复用应用并输入回车) / type_text 向当前软件输入文本 / screenshot 截取软件界面画面(渲染到控制板) / focus 聚焦软件窗口。用户说'打开/运行XX软件'、'用QQ给XX发消息'、'截取XX界面'时使用。",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["launch", "send_message", "type_text", "screenshot", "focus"]},
                "app": {"type": "string", "description": "软件名, 如 QQ/微信/chrome/notepad 或任意已安装应用"},
                "args": {"type": "string", "description": "启动附加参数(可选)"},
                "to": {"type": "string", "description": "send_message 的接收人/群"},
                "text": {"type": "string", "description": "要输入或发送的文本"},
            },
            "required": ["action"],
        },
        handler=_app_control,
        category="app",
    ))
    registry.register(Tool(
        name="kill_process",
        description="按进程名或 PID 结束进程(如'杀死QQ'、'结束notepad进程')。系统关键进程受保护拒绝。管理员级操作。",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "进程名(如 QQ/notepad/chrome)"},
                "pid": {"type": "integer", "description": "进程ID(可选)"},
            },
        },
        handler=_kill_process,
        category="app",
    ))
