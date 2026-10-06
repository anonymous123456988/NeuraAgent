
import ctypes
from ctypes import wintypes
import time

user32 = ctypes.windll.user32

# 枚举所有顶层窗口，找到 QQ 主窗口
EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
GetClassNameW = user32.GetClassNameW
IsWindowVisible = user32.IsWindowVisible
GetWindowThreadProcessId = user32.GetWindowThreadProcessId

results = []

def cb(hwnd, lparam):
    length = GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    GetWindowTextW(hwnd, buf, length + 1)
    title = buf.value
    cls = ctypes.create_unicode_buffer(256)
    GetClassNameW(hwnd, cls, 256)
    pid = wintypes.DWORD()
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if title or 'QQ' in cls.value:
        results.append((hwnd, title, cls.value, pid.value, bool(IsWindowVisible(hwnd))))
    return True

EnumWindows(EnumWindowsProc(cb), 0)

print("=== 所有含标题/QQ类名的窗口 ===")
for hwnd, title, cls, pid, vis in results:
    if title or 'QQ' in cls.upper():
        print(f"hwnd={hwnd} pid={pid} visible={vis} class={cls!r} title={title!r}")
