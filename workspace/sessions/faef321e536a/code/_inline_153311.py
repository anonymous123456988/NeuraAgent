
import ctypes
from ctypes import wintypes
import time

user32 = ctypes.windll.user32

# QQ 主窗口候选 (pid=9376, title='QQ', class='Chrome_WidgetWin_1')
hwnds = [263392, 8389306, 2100000, 6293462, 263320]

SW_SHOWNORMAL = 1
SW_RESTORE = 9

user32.ShowWindow.restype = ctypes.c_bool
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetForegroundWindow.restype = ctypes.c_bool
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.IsWindowVisible.argtypes = [wintypes.HWND]

# 获取窗口矩形，判断哪个是主面板（尺寸较大）
class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

for h in hwnds:
    r = RECT()
    ok = user32.GetWindowRect(h, ctypes.byref(r))
    w = r.right - r.left
    ht = r.bottom - r.top
    print(f"hwnd={h} rect=({r.left},{r.top},{r.right},{r.bottom}) size={w}x{ht}")

print("\n=== 逐个恢复显示 ===")
for h in hwnds:
    user32.ShowWindow(h, SW_RESTORE)
    time.sleep(0.2)
    user32.ShowWindow(h, SW_SHOWNORMAL)
    time.sleep(0.2)
    user32.SetForegroundWindow(h)
    time.sleep(0.3)
    print(f"hwnd={h} visible={bool(user32.IsWindowVisible(h))}")
