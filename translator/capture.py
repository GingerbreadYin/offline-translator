"""Native window geometry and one-shot visible-pixel capture through Qt."""
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
user32.GetForegroundWindow.restype = wintypes.HWND
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsIconic.argtypes = [wintypes.HWND]
user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
user32.MonitorFromWindow.restype = wintypes.HANDLE
user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]


def foreground_window():
    return int(user32.GetForegroundWindow() or 0)


def window_geometry(hwnd, app):
    if not user32.IsWindow(hwnd) or user32.IsIconic(hwnd):
        raise ValueError('目标窗口已关闭或最小化')
    rect = wintypes.RECT()
    dwm = ctypes.windll.dwmapi.DwmGetWindowAttribute
    dwm.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    if dwm(hwnd, 9, ctypes.byref(rect), ctypes.sizeof(rect)) != 0:
        user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            raise ValueError('无法读取目标窗口位置')
    class MonitorInfo(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('monitor', wintypes.RECT),
                    ('work', wintypes.RECT), ('flags', wintypes.DWORD), ('device', wintypes.WCHAR*32)]
    info = MonitorInfo()
    info.size = ctypes.sizeof(info)
    if not user32.GetMonitorInfoW(user32.MonitorFromWindow(hwnd, 2), ctypes.byref(info)):
        raise ValueError('无法读取目标显示器')
    screen = next((s for s in app.screens() if s.name() == info.device), app.primaryScreen())
    ratio = screen.devicePixelRatio()
    geo, area = screen.geometry(), screen.availableGeometry()
    target = (round(geo.x()+(rect.left-info.monitor.left)/ratio),
              round(geo.y()+(rect.top-info.monitor.top)/ratio),
              round((rect.right-rect.left)/ratio), round((rect.bottom-rect.top)/ratio))
    return target, (area.x(),area.y(),area.width(),area.height())


def capture_window_snapshot(hwnd, app):
    """Capture visible pixels once with Qt; no native capture thread or polling."""
    from io import BytesIO
    from PIL import Image
    from PySide6.QtCore import QRect, QBuffer, QIODevice
    target,area=window_geometry(hwnd,app)
    screen=next((s for s in app.screens() if (s.availableGeometry().x(),s.availableGeometry().y(),s.availableGeometry().width(),s.availableGeometry().height())==area),app.primaryScreen())
    clipped=QRect(*target).intersected(screen.geometry())
    if clipped.isEmpty(): raise ValueError('目标窗口不在可见屏幕内')
    pix=screen.grabWindow(0)
    ratio=pix.devicePixelRatio()
    geo=screen.geometry()
    pixels=QRect(round((clipped.x()-geo.x())*ratio),round((clipped.y()-geo.y())*ratio),round(clipped.width()*ratio),round(clipped.height()*ratio))
    cropped=pix.copy(pixels)
    buffer=QBuffer(); buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not cropped.save(buffer,'PNG'): raise RuntimeError('无法读取窗口截图')
    image=Image.open(BytesIO(bytes(buffer.data()))).convert('RGB')
    return image,(clipped.x(),clipped.y(),clipped.width(),clipped.height()),area
