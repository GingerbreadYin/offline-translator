"""Single-shot translation: results persist until explicitly dismissed."""
from PySide6.QtCore import QObject
from .capture import foreground_window, capture_window_snapshot
from .full_ui import FullOverlay


class WindowTranslation(QObject):
    def __init__(self,owner):
        super().__init__(owner)
        self.owner=owner
        self.overlay=FullOverlay()
        self.hwnd=0
        self.epoch=0
        self.geometry=None
        self.image_size=None
        self.waiting=False

    @property
    def active(self):
        return bool(self.hwnd)

    def stop(self):
        self.epoch+=1
        self.hwnd=0
        self.waiting=False
        self.owner.worker.cancel_pending()
        self.overlay.hide()

    def start(self,hwnd=None):
        if self.active:
            self.stop(); return
        target=hwnd or foreground_window()
        own=[int(w.winId()) for w in self.owner.app.topLevelWidgets()]
        if not target or (hwnd is None and target in own):
            self.owner.tray.showMessage('请选择目标窗口','先点击要阅读的窗口，再按全屏翻译快捷键。'); return
        self.owner.cancel()
        self.overlay.clear()
        try:
            image,target_rect,area=capture_window_snapshot(target,self.owner.app)
            try:
                self.hwnd=target
                self.geometry=(target_rect,area)
                self.image_size=image.size
                self.waiting=True
                self.owner.worker.submit((('full',self.epoch),image.size,image.tobytes()))
            finally:
                image.close()
            self.owner.tray.showMessage('正在翻译当前截图','译文可拖动；再次按全屏键或 Esc 关闭。',msecs=1500)
        except Exception as exc:
            self.stop()
            self.owner.tray.showMessage('无法开始全屏翻译',str(exc))

    def finished(self,job,data,error):
        if not self.active or job!=('full',self.epoch): return
        self.waiting=bool(data and data.get('complete') is False)
        if error:
            self.owner.tray.showMessage('全屏翻译失败',error); return
        target,area=self.geometry
        self.overlay.display(data['paragraphs'],data['obstacles'],target,area,self.image_size)
        if not data['paragraphs']:
            self.owner.tray.showMessage('未找到适合翻译的英文','当前截图没有识别到英文正文；可重新截图。')
