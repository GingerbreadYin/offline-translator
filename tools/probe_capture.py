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
    from translator.capture import capture_window_snapshot
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
    from PySide6.QtTest import QTest
    QTest.qWait(150)
    try:
        image,target,area=capture_window_snapshot(int(label.winId()),app)
        try:
            assert image.width>500 and image.height>100
            return {'component':'Qt single screenshot','window_capture':True,'size':image.size}
        finally:
            image.close()
    finally:
        label.close()
        app.processEvents()


if __name__ == '__main__':
    print(json.dumps(probe_capture()))
