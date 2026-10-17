"""Qt coordinator for capture, stability, cancellation and full-window results."""
import time
from PySide6.QtCore import QObject, QTimer
from .capture import WindowCapture, foreground_window, window_geometry
from .fullpage import RefreshGate
from .full_ui import FullOverlay


class WindowTranslation(QObject):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.capture = WindowCapture()
        self.overlay = FullOverlay()
        self.gate = RefreshGate()
        self.hwnd = 0
        self.epoch = 0
        self.geometry = None
        self.image_size = None
        self.waiting = False
        self.focused = False
        self.started = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)

    @property
    def active(self):
        return bool(self.hwnd)

    def invalidate(self):
        self.epoch += 1
        self.waiting = False
        self.owner.worker.cancel_pending()
        self.overlay.hide()

    def stop(self):
        self.timer.stop()
        self.invalidate()
        self.hwnd = 0
        self.focused = False
        self.gate.reset()
        try:
            self.capture.close()
        except Exception as exc:
            self.owner.tray.showMessage('截图已停止',str(exc))

    def start(self, hwnd=None):
        if self.active:
            self.stop()
            return
        target = hwnd or foreground_window()
        # A tray/settings/favorites window cannot become its own translation source.
        own = [int(w.winId()) for w in self.owner.app.topLevelWidgets()]
        if not target or (hwnd is None and target in own):
            self.owner.tray.showMessage('请选择目标窗口','先点击要阅读的窗口，再按全屏翻译快捷键。')
            return
        self.owner.cancel()
        try:
            self.geometry = window_geometry(target,self.owner.app)
            self.capture.start(target)
            self.hwnd = target
            self.started = time.monotonic()
            self.gate.reset()
            self.timer.start(150)
            self.owner.tray.showMessage('全屏翻译已开启','正在识别当前窗口；再次按快捷键或 Esc 关闭。',msecs=1800)
        except Exception as exc:
            self.stop()
            self.owner.tray.showMessage('无法开始全屏翻译',str(exc))

    def tick(self):
        if not self.active:
            return
        try:
            geometry = window_geometry(self.hwnd,self.owner.app)
            foreground = foreground_window()
            focused = foreground == self.hwnd
            if not focused:
                if self.focused:
                    self.invalidate()
                self.focused = False
                self.gate.reset()
                return
            self.focused = True
            if geometry != self.geometry:
                self.invalidate()
                self.gate.reset()
                self.geometry = geometry
            image = self.capture.snapshot()
            if image is None:
                if self.capture.closed or time.monotonic()-self.started > 10:
                    raise RuntimeError('无法获取窗口画面，请关闭全屏翻译后重试')
                return
            try:
                event = self.gate.observe(image,True,time.monotonic())
                if event == 'changed':
                    self.invalidate()
                elif event == 'ready':
                    self.image_size = image.size
                    self.waiting = True
                    self.owner.worker.submit((('full',self.epoch),image.size,image.tobytes()))
            finally:
                image.close()
        except Exception as exc:
            self.stop()
            self.owner.tray.showMessage('全屏翻译已停止',str(exc))

    def finished(self, job, data, error):
        # Recheck latest pixels before painting, not only on the refresh timer.
        self.tick()
        if not self.active or job != ('full',self.epoch) or not self.focused or foreground_window() != self.hwnd:
            return
        self.waiting = False
        if error:
            self.owner.tray.showMessage('全屏翻译失败',error)
            return
        target,area = self.geometry
        self.overlay.display(data['paragraphs'],data['obstacles'],target,area,self.image_size)
        if not data['paragraphs']:
            self.owner.tray.showMessage('未找到适合翻译的英文','当前可见内容没有识别到英文正文；滚动后将自动重试。')
