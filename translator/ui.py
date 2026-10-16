"""Small Windows desktop shell for the local service pipeline."""
import ctypes
from ctypes import wintypes
from io import BytesIO
import os
from pathlib import Path

from PIL import Image
from PySide6.QtCore import (QAbstractNativeEventFilter, QObject, QPoint, QRect, Qt,
                            QTimer, Signal)
from PySide6.QtGui import QColor, QCursor, QIcon, QKeySequence, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QApplication, QDialog, QFormLayout, QHBoxLayout,
    QKeySequenceEdit, QLabel, QMenu, QMessageBox, QPushButton, QScrollArea,
    QSystemTrayIcon, QVBoxLayout, QWidget)

from .core import Navigator, SettingsStore, Workflow, place_result, default_settings
from . import __version__
from .hotkeys import Hotkeys
from .worker import ProcessWorker

STYLE = """
QWidget {font-family: 'Microsoft YaHei UI'; font-size: 13px; color: #192b3d;}
QDialog, QWidget#result {background: #f8fafc;}
QLabel#title {font-size: 22px; font-weight: 600; color: #163d57;}
QPushButton {background: #e6eef4; border: 0; border-radius: 6px; padding: 9px 16px;}
QPushButton:hover {background: #d8e6f0;}
QKeySequenceEdit {padding: 8px; background: white; border: 1px solid #cbd5e1; border-radius: 5px;}
"""


class NativeFilter(QAbstractNativeEventFilter):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def nativeEventFilter(self, event_type, message):
        if event_type in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0312 and 100 <= msg.wParam <= 103:
                action = int(msg.wParam) - 100
                QTimer.singleShot(0, lambda: self.callback(action))
                return True, 0
        return False, 0


class SelectionOverlay(QWidget):
    selected = Signal(object, object, object)
    cancelled = Signal()

    def __init__(self, screen):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.screen = screen
        self.start = None
        self.end = None
        self.background = screen.grabWindow(0)
        self.setGeometry(screen.geometry())
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self.background)
        painter.fillRect(self.rect(), QColor(9, 20, 32, 110))
        painter.setPen(QColor("white"))
        painter.drawText(24, 35, "拖动框选英文，松开即翻译  ·  Esc / 主快捷键取消")
        if self.start is not None and self.end is not None:
            rect = QRect(self.start, self.end).normalized()
            painter.save()
            painter.setClipRect(rect)
            painter.drawPixmap(self.rect(), self.background)
            painter.restore()
            painter.setPen(QPen(QColor("#4dd5c6"), 2))
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start = event.position().toPoint()
            self.end = self.start
        elif event.button() == Qt.MouseButton.RightButton:
            self.cancelled.emit()

    def mouseMoveEvent(self, event):
        if self.start is not None:
            self.end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self.start is None:
            return
        rect = QRect(self.start, event.position().toPoint()).normalized().intersected(self.rect())
        if rect.width() < 3 or rect.height() < 3:
            self.cancelled.emit()
            return
        # The original screen pixmap is captured before the overlay exists.
        ratio = self.background.devicePixelRatio()
        pixels = QRect(round(rect.x()*ratio), round(rect.y()*ratio), round(rect.width()*ratio), round(rect.height()*ratio))
        pix = self.background.copy(pixels)
        from PySide6.QtCore import QBuffer, QIODevice
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        pix.save(buffer, "PNG")
        image = Image.open(BytesIO(bytes(buffer.data()))).convert("RGB")
        geo = self.screen.geometry()
        selected = (geo.x()+rect.x(), geo.y()+rect.y(), rect.width(), rect.height())
        area = self.screen.availableGeometry()
        self.selected.emit(image, selected, (area.x(), area.y(), area.width(), area.height()))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()


class ResultWindow(QWidget):
    closed = Signal()

    def __init__(self):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setObjectName("result")
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet(STYLE + "QWidget#result {border: 1px solid #b6c9d8; border-radius: 9px;}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 12)
        header = QHBoxLayout()
        self.caption = QLabel("离线翻译")
        self.caption.setStyleSheet("color: #58718a; font-size: 11px;")
        close = QPushButton("×")
        close.setFixedSize(28, 26)
        close.setStyleSheet("padding: 0; font-size: 18px;")
        close.clicked.connect(self.closed)
        header.addWidget(self.caption)
        header.addStretch()
        header.addWidget(close)
        layout.addLayout(header)
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.text.setTextFormat(Qt.TextFormat.PlainText)
        self.text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.text.setStyleSheet("font-size: 16px; padding: 2px; background: #f8fafc; border: 0;")
        scroll = QScrollArea()
        scroll.setStyleSheet("background: #f8fafc; border: 0;")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self.text)
        layout.addWidget(scroll)

    def display(self, text, caption, selection, area):
        self.text.setText(text)
        self.caption.setText(caption)
        height = min(280, max(92, 78 + ((len(text) // 24) + text.count("\n")) * 23))
        x, y, width, height = place_result(selection, (390, height), area)
        self.setGeometry(x, y, width, height)
        self.show()


class SettingsWindow(QDialog):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.setWindowTitle("离线翻译 · 设置")
        self.setMinimumWidth(490)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        title = QLabel("离线框选翻译")
        title.setObjectName("title")
        layout.addWidget(title)
        description = QLabel("按主快捷键 → 拖动框选 → 松开自动翻译\n再次按主快捷键关闭译文。单词按另外两键切换义项。")
        description.setStyleSheet("padding: 10px 0; color: #58718a;")
        layout.addWidget(description)
        form = QFormLayout()
        self.edits = []
        for label, binding in zip(("框选 / 关闭", "上一个词义", "下一个词义", "启用 / 暂停"), owner.settings["bindings"]):
            edit = QKeySequenceEdit(QKeySequence(binding))
            edit.setMaximumSequenceLength(1)
            self.edits.append(edit)
            form.addRow(label, edit)
        layout.addLayout(form)
        warning = QLabel("支持单键与组合键；系统保留键或已占用键无法绑定。\n单键可能影响其他软件输入，推荐组合键。Esc 保留为取消。\n设置窗口打开时快捷键暂停；保存或关闭窗口后启用。")
        warning.setStyleSheet("color: #58718a; font-size: 11px; padding: 8px 0;")
        layout.addWidget(warning)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        save = QPushButton("保存快捷键")
        save.clicked.connect(self.save)
        self.start_button = QPushButton("开始框选")
        self.start_button.clicked.connect(self.start)
        buttons.addWidget(save)
        buttons.addWidget(self.start_button)
        layout.addLayout(buttons)
        resources_ok = (owner.resources / "dictionary.db").exists() and (owner.resources / "translation/model/model.bin").exists()
        self.status.setText("资源已准备，日常使用无需联网。软件关闭窗口后继续常驻托盘。" if resources_ok else "资源缺失，请运行资源准备脚本或使用完整发行包。")

    def save(self):
        bindings = [e.keySequence().toString(QKeySequence.SequenceFormat.PortableText) for e in self.edits]
        previous = self.owner.settings["bindings"][:]
        try:
            self.owner.hotkeys.apply(bindings, enabled=self.owner.enabled)
            settings = {"bindings": bindings, "schema_version": 2}
            try:
                self.owner.store.save(settings)
            except OSError:
                self.owner.hotkeys.apply(previous, enabled=self.owner.enabled)
                raise
            self.owner.settings = settings
            self.status.setText("快捷键已保存。" + ("翻译已启用。" if self.owner.enabled else "翻译仍处于暂停状态。"))
            self.hide()
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "无法保存", str(exc))

    def start(self):
        self.hide()
        QTimer.singleShot(180, self.owner.toggle)

    def showEvent(self, event):
        self.owner.hotkeys.close()
        super().showEvent(event)

    def hideEvent(self, event):
        if getattr(self.owner, "shutting_down", False):
            super().hideEvent(event)
            return
        try:
            self.owner.hotkeys.apply(self.owner.settings["bindings"], enabled=self.owner.enabled)
        except ValueError as exc:
            self.status.setText(str(exc))
            if hasattr(self.owner, "tray"):
                self.owner.tray.showMessage("快捷键未启用", str(exc))
        super().hideEvent(event)


class Controller(QObject):
    def __init__(self, app, resources, settings_path=None):
        super().__init__()
        self.app, self.resources = app, Path(resources)
        self.enabled = True
        self.shutting_down = False
        self.store = SettingsStore(settings_path or Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "OfflineTranslator/settings.json")
        try:
            self.settings = self.store.load()
        except ValueError as exc:
            QMessageBox.warning(None, "配置错误", str(exc))
            self.settings = default_settings()
        self.flow = Workflow()
        self.worker = ProcessWorker(config=str(resources))
        self.hotkeys = Hotkeys()
        self.native = NativeFilter(self.action)
        app.installNativeEventFilter(self.native)
        self.result = ResultWindow()
        self.result.closed.connect(self.cancel)
        self.overlays = []
        self.navigator = Navigator([])
        self.last_result = None
        self.selection, self.area = (0, 0, 10, 10), (0, 0, 1920, 1080)
        self.settings_window = SettingsWindow(self)
        icon = QPixmap(32, 32)
        icon.fill(QColor("#163d57"))
        painter = QPainter(icon)
        painter.setPen(QColor("white"))
        painter.drawText(icon.rect(), Qt.AlignmentFlag.AlignCenter, "译")
        painter.end()
        self.tray = QSystemTrayIcon(QIcon(icon), self)
        self.tray.setToolTip(f"离线框选翻译 v{__version__} · 已启用")
        menu = QMenu()
        self.enable_action = menu.addAction("启用翻译", self.toggle_enabled)
        self.enable_action.setCheckable(True)
        self.enable_action.setChecked(True)
        self.capture_action = menu.addAction("开始框选", self.toggle)
        menu.addAction("设置", self.open_settings)
        menu.addSeparator()
        menu.addAction("退出", self.shutdown)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.open_settings() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
        self.tray.show()
        try:
            self.hotkeys.apply(self.settings["bindings"])
        except ValueError as exc:
            self.settings_window.status.setText(str(exc))
        self.escape_timer = QTimer(self)
        self.escape_timer.timeout.connect(self.check_escape)
        self.escape_timer.start(60)
        self.worker_timer = QTimer(self)
        self.worker_timer.timeout.connect(self.poll_worker)
        self.worker_timer.start(40)
        self.settings_window.show()

    def update_enabled_status(self):
        status = "已启用" if self.enabled else "已暂停"
        self.tray.setToolTip(f"离线框选翻译 v{__version__} · {status}")
        self.enable_action.setChecked(self.enabled)
        self.capture_action.setEnabled(self.enabled)
        self.settings_window.start_button.setEnabled(self.enabled)
        self.settings_window.status.setText(f"当前：{status}。启用／暂停快捷键：{self.settings['bindings'][3]}。")

    def toggle_enabled(self):
        requested = not self.enabled
        try:
            if not self.settings_window.isVisible():
                self.hotkeys.apply(self.settings["bindings"], enabled=requested)
        except ValueError as exc:
            self.enable_action.setChecked(self.enabled)
            self.tray.showMessage("无法恢复快捷键", str(exc))
            return
        self.enabled = requested
        if not self.enabled:
            self.cancel()
        self.update_enabled_status()

    def poll_worker(self):
        try:
            for job, result, error in self.worker.poll():
                self.finished(job, result, error)
        except (RuntimeError, OSError) as exc:
            self.worker_timer.stop()
            if self.flow.state == "processing":
                self.finished(self.flow.generation, None, str(exc))
            self.tray.showMessage("离线引擎错误", str(exc))

    def open_settings(self):
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def check_escape(self):
        if self.flow.state != "idle" and ctypes.windll.user32.GetAsyncKeyState(0x1B) & 0x8000:
            self.cancel()

    def action(self, action):
        if action == 3:
            self.toggle_enabled()
        elif not self.enabled:
            return
        elif action == 0:
            self.toggle()
        elif self.flow.state == "showing" and self.navigator.meanings:
            self.navigator.move(-1 if action == 1 else 1)
            self.show_result()

    def clear_overlays(self):
        for overlay in self.overlays:
            overlay.hide()
            overlay.deleteLater()
        self.overlays = []

    def cancel(self):
        self.flow.cancel()
        self.worker.cancel_pending()
        self.clear_overlays()
        self.result.hide()
        self.navigator = Navigator([])
        self.last_result = None

    def toggle(self):
        if not self.enabled:
            return
        if self.flow.state != "idle":
            self.cancel()
            return
        self.flow.toggle()
        for screen in self.app.screens():
            overlay = SelectionOverlay(screen)
            overlay.selected.connect(self.selected)
            overlay.cancelled.connect(self.cancel)
            self.overlays.append(overlay)
        for overlay in self.overlays:
            overlay.show()
        screen = self.app.screenAt(QCursor.pos())
        for overlay in self.overlays:
            if overlay.screen == screen:
                overlay.activateWindow()

    def selected(self, image, selection, area):
        if not self.enabled or self.flow.state != "selecting":
            image.close()
            return
        self.clear_overlays()
        self.selection, self.area = selection, area
        job = self.flow.begin()
        self.result.display("正在识别与翻译…", "本机离线处理 · 再按主快捷键取消", selection, area)
        self.worker.submit((job, image.size, image.tobytes()))
        image.close()

    def finished(self, job, result, error):
        if not self.flow.finish(job):
            return
        self.last_result = result
        if error:
            self.navigator = Navigator([])
            self.result.display(error, "处理失败 · 可关闭后重新框选", self.selection, self.area)
            return
        self.navigator = Navigator(result.meanings)
        self.show_result()

    def show_result(self):
        if not self.last_result:
            return
        meaning = self.navigator.current
        if meaning:
            text = f"{self.last_result.original} · {meaning.pos} {meaning.text}".strip()
            caption = f"默认词典顺序 · {self.navigator.index+1}/{len(self.navigator.meanings)} · 上/下词义快捷键切换"
        else:
            text, caption = self.last_result.translation, "英 → 中 · 本机离线翻译"
        self.result.display(text, caption, self.selection, self.area)

    def shutdown(self):
        self.shutting_down = True
        self.cancel()
        self.hotkeys.close()
        self.escape_timer.stop()
        self.worker_timer.stop()
        self.tray.hide()
        self.worker.close()
        self.app.quit()
