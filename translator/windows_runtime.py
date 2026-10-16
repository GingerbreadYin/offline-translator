"""Keep Windows Qt's unversioned ICU separate from inference's bundled ICU.

Our Python runtime's SQLite links to ICU with version-suffixed exports. Qt
uses Windows' built-in ICU API. The GUI never imports SQLite; the inference
process never imports Qt. Preload only in the GUI process before Qt imports.
"""
import ctypes
import os

_icu = None


def preload_system_icu():
    global _icu
    if os.name != "nt" or _icu is not None:
        return
    buffer = ctypes.create_unicode_buffer(32768)
    length = ctypes.windll.kernel32.GetSystemDirectoryW(buffer, len(buffer))
    if not 0 < length < len(buffer):
        raise OSError("无法定位 Windows 系统运行库")
    _icu = ctypes.WinDLL(os.path.join(buffer.value, "icuuc.dll"))
