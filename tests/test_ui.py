from pathlib import Path
import pytest
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from translator.core import SettingsStore
from translator.ui import SelectionOverlay, ResultWindow, SettingsWindow


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_capture_dpi_conversion_uses_original_pixels(app):
    class Screen:
        def grabWindow(self, _):
            pix = QPixmap(800, 600)
            pix.fill(QColor("red"))
            pix.setDevicePixelRatio(2)
            return pix
        def geometry(self):
            return QRect(-400, 0, 400, 300)
        def availableGeometry(self):
            return self.geometry()
    overlay = SelectionOverlay(Screen())
    captured = []
    overlay.selected.connect(lambda image, rect, area: captured.append((image, rect)))
    QTest.mousePress(overlay, Qt.MouseButton.LeftButton, pos=QPoint(20, 30))
    QTest.mouseRelease(overlay, Qt.MouseButton.LeftButton, pos=QPoint(119, 79))
    image, rect = captured[0]
    assert rect == (-380, 30, 100, 50)
    assert image.size == (200, 100)
    assert image.getpixel((0, 0)) == (255, 0, 0)
    image.close()
    overlay.close()


def test_result_treats_angle_brackets_as_literal_and_clamps(app):
    window = ResultWindow()
    window.display("<script>英文</script>", "测试", (100, 0, 40, 20), (0, 0, 300, 200))
    assert window.text.text() == "<script>英文</script>"
    assert window.text.textFormat() == Qt.TextFormat.PlainText
    assert window.geometry().right() < 300
    window.close()


def test_result_background_stays_readable_with_dark_system_palette(app):
    from PySide6.QtGui import QPalette
    original = app.palette()
    dark = QPalette(original)
    dark.setColor(QPalette.ColorRole.Base, QColor("#202020"))
    dark.setColor(QPalette.ColorRole.Window, QColor("#202020"))
    app.setPalette(dark)
    window = ResultWindow()
    window.display("issue · n. 发行", "默认词典顺序", (100, 200, 40, 20), (0, 0, 800, 600))
    app.processEvents()
    pixel = window.text.grab().toImage().pixelColor(8, 8)
    window.close()
    app.setPalette(original)
    assert pixel.red() > 220 and pixel.green() > 220 and pixel.blue() > 220


def test_editing_shortcuts_suspends_global_keys_and_close_restores(app, tmp_path):
    class Keys:
        def __init__(self): self.bindings = ["F6", "F7", "F8", "F9"]
        def close(self): self.bindings = []
        def apply(self, bindings, enabled=True): self.bindings = bindings[:]
    class Owner:
        settings = {"bindings": ["F6", "F7", "F8", "F9"]}
        enabled = True
        hotkeys = Keys()
        resources = tmp_path
        store = SettingsStore(tmp_path / "settings.json")
        def toggle(self): pass
    owner = Owner()
    window = SettingsWindow(owner)
    window.show()
    app.processEvents()
    assert owner.hotkeys.bindings == []
    window.close()
    app.processEvents()
    assert owner.hotkeys.bindings == ["F6", "F7", "F8", "F9"]


@pytest.fixture
def controller(app, tmp_path, monkeypatch):
    import translator.ui as ui
    from translator.hotkeys import Hotkeys
    class Backend:
        def __init__(self): self.active, self.occupied = {}, set()
        def register(self, id_, modifiers, key):
            if key in self.occupied: return False
            self.active[id_] = (modifiers, key)
            return True
        def unregister(self, id_): self.active.pop(id_, None)
    class Worker:
        def __init__(self, **kwargs): self.pending = None
        def cancel_pending(self): self.pending = None
        def poll(self): return []
        def close(self): pass
    backend = Backend()
    monkeypatch.setattr(ui, "Hotkeys", lambda: Hotkeys(backend))
    monkeypatch.setattr(ui, "ProcessWorker", Worker)
    owner = ui.Controller(app, tmp_path, tmp_path / "settings.json")
    owner.settings_window.hide()
    app.processEvents()
    yield owner, backend
    owner.shutdown()
    app.removeNativeEventFilter(owner.native)
    owner.settings_window.close()
    owner.result.close()
    app.processEvents()


def test_pause_cancels_result_and_resume_restores_four_keys(controller):
    from translator.core import Result
    owner, backend = controller
    owner.flow.toggle()
    job = owner.flow.begin()
    owner.result.display("正在翻译", "测试", (100,200,40,20), (0,0,800,600))
    owner.action(3)
    assert not owner.enabled
    assert owner.flow.state == "idle"
    assert not owner.result.isVisible()
    assert set(backend.active) == {103}
    owner.finished(job, Result("test", translation="测试"), "")
    assert owner.last_result is None
    owner.action(0)
    assert owner.flow.state == "idle" and not owner.overlays
    owner.action(3)
    assert owner.enabled and set(backend.active) == {100,101,102,103}
    assert "已启用" in owner.tray.toolTip()


def test_failed_resume_and_settings_close_preserve_paused_scope(controller, app):
    owner, backend = controller
    owner.action(3)
    backend.occupied.add(20)
    owner.action(3)
    assert not owner.enabled and set(backend.active) == {103}
    backend.occupied.clear()
    owner.settings_window.show()
    app.processEvents()
    assert not backend.active
    owner.settings_window.hide()
    app.processEvents()
    assert not owner.enabled and set(backend.active) == {103}


def test_fourth_native_hotkey_reaches_enable_toggle(controller, app):
    import ctypes
    from ctypes import wintypes
    owner, _ = controller
    message = wintypes.MSG()
    message.message, message.wParam = 0x312, 103
    assert owner.native.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(message)) == (True, 0)
    app.processEvents()
    assert not owner.enabled
