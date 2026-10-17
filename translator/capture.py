"""Exact-HWND Windows Graphics Capture with one bounded latest-frame slot."""
import ctypes
from ctypes import wintypes
from threading import Lock
from PIL import Image

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


class WindowCapture:
    def __init__(self):
        self.lock = Lock()
        self.latest = None
        self.control = None
        self.capture = None
        self.closed = True

    def start(self, hwnd):
        from windows_capture import WindowsCapture
        self.close()
        self.closed = False
        self.capture = WindowsCapture(window_hwnd=hwnd, cursor_capture=False,
                                      draw_border=False, minimum_update_interval=150)
        @self.capture.event
        def on_frame_arrived(frame, control):
            # Native frame lifetime ends after this callback; always own the copy.
            pixels = frame.frame_buffer[:, :, :3][:, :, ::-1].copy()
            with self.lock:
                if not self.closed:
                    self.latest = pixels
        @self.capture.event
        def on_closed():
            with self.lock:
                self.closed = True
                self.latest = None
        self.control = self.capture.start_free_threaded()

    def snapshot(self):
        with self.lock:
            if self.latest is None or self.closed:
                return None
            return Image.fromarray(self.latest.copy())

    def close(self):
        with self.lock:
            self.closed = True
            self.latest = None
        control, self.control = self.control, None
        if control is not None:
            control.stop()
        self.capture = None
