"""Controlled native-window capture check, without reading other applications."""
import json
from pathlib import Path
import time
import ctypes
from ctypes import wintypes


def probe_capture():
    from translator.windows_runtime import preload_system_icu
    preload_system_icu()
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QLabel
    from windows_capture import WindowsCapture
    app = QApplication.instance() or QApplication([])
    label = QLabel('Offline Translator capture fixture\nThis project is open source.')
    label.setStyleSheet('background: white; color: black; font-size: 28px; padding: 30px;')
    label.resize(720, 240)
    label.show()
    # A hidden console runner can pass SW_HIDE to the first native window.
    # Explicitly show this fixture after that initial startup-show instruction.
    show = ctypes.windll.user32.ShowWindow
    show.argtypes = [wintypes.HWND,ctypes.c_int]
    show(int(label.winId()),5)
    app.processEvents()
    frames = []
    capture = WindowsCapture(window_hwnd=int(label.winId()), cursor_capture=False, draw_border=False)
    @capture.event
    def on_frame_arrived(frame, control):
        frames.append((frame.width, frame.height))
    @capture.event
    def on_closed():
        pass
    control = capture.start_free_threaded()
    started = time.monotonic()
    try:
        while not frames and time.monotonic() - started < 10:
            app.processEvents()
            time.sleep(.02)
        if not frames:
            raise RuntimeError('Windows Capture returned no frames')
        return {'component': 'windows-capture 2.0.1', 'window_capture': True, 'size': frames[-1]}
    finally:
        control.stop()
        label.close()
        app.processEvents()


if __name__ == '__main__':
    print(json.dumps(probe_capture()))
