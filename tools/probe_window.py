"""End-to-end controlled window: WGC -> OCR -> translation -> overlay -> favorite."""
from pathlib import Path
import time
import ctypes
from ctypes import wintypes


def probe_window(resources):
    from translator.windows_runtime import preload_system_icu
    preload_system_icu()
    from PySide6.QtWidgets import QApplication, QLabel
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QCursor
    from translator.core import SettingsStore
    from translator.ui import Controller
    from translator.capture import foreground_window
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    path = Path('build/window-probe/settings.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    SettingsStore(path).save({'bindings':[f'Ctrl+Alt+F{i}' for i in (21,22,23,24,19,20)]})
    owner = Controller(app,resources,path)
    messages = []
    original_message = owner.tray.showMessage
    def message(title,body,*args,**kwargs):
        messages.append((title,body))
        original_message(title,body,*args,**kwargs)
    owner.tray.showMessage = message
    owner.settings_window.hide()
    fixture = QLabel('This project is open source.')
    fixture.setWindowTitle('翻译测试窗口')
    fixture.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
    fixture.setStyleSheet('background: white; color: black; font-family: Arial; font-size: 28px; padding: 40px;')
    fixture.resize(800,300)
    fixture.show()
    fixture.raise_()
    fixture.activateWindow()
    app.processEvents()
    hwnd = int(fixture.winId())
    # The terminal runner starts in the background. Attach briefly to let this
    # controlled fixture become foreground, then restore normal input queues.
    user32 = ctypes.windll.user32
    user32.ShowWindow.argtypes = [wintypes.HWND,ctypes.c_int]
    user32.ShowWindow(hwnd,5)
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND,ctypes.c_void_p]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.BringWindowToTop.argtypes = [wintypes.HWND]
    current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
    foreground_thread = user32.GetWindowThreadProcessId(foreground_window(),None)
    attached = user32.AttachThreadInput(current_thread,foreground_thread,True)
    try:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        fixture.activateWindow()
    finally:
        if attached:
            user32.AttachThreadInput(current_thread,foreground_thread,False)
    original_cursor = QCursor.pos()
    states = []
    def wait_for(condition,seconds=15):
        deadline = time.monotonic()+seconds
        while time.monotonic()<deadline:
            app.processEvents()
            if condition(): return
            state = (owner.full.active,owner.full.focused,fixture.isVisible(),fixture.isMinimized(),int(fixture.winId()),foreground_window(),owner.full.epoch)
            if not states or state != states[-1]: states.append(state)
            time.sleep(.02)
        raise TimeoutError(f'Window probe timed out: states={states[-15:]}, messages={messages}')
    try:
        wait_for(lambda: foreground_window()==hwnd,5)
        owner.full.start(hwnd)
        wait_for(lambda: owner.full.overlay.layer.isVisible())
        index = next(i for i,p in enumerate(owner.full.overlay.paragraphs) if 'This project' in p.result.original)
        first = owner.full.overlay.paragraphs[index].result
        assert '项目' in first.translation,first
        label,index = next((label,i) for label,i in owner.full.overlay.labels if i==index)
        QCursor.setPos(label.mapToGlobal(label.rect().center()))
        owner.action(5)
        assert any(r['original']==first.original for r in owner.favorites.list())
        epoch = owner.full.epoch
        fixture.setText('Please open the settings window.')
        wait_for(lambda: owner.full.epoch > epoch)
        assert not owner.full.overlay.layer.isVisible()
        wait_for(lambda: owner.full.overlay.layer.isVisible())
        second = next(p.result for p in owner.full.overlay.paragraphs if 'Please open' in p.result.original)
        assert '设置' in second.translation and '窗口' in second.translation,second
        owner.action(3)
        assert not owner.full.active and not owner.full.overlay.layer.isVisible()
        assert set(owner.hotkeys.registered)=={103}
        return {'window_translation':True,'changed_content_refreshed':True,
                'hover_favorite':True,'pause_hides_overlay':True,
                'first':first.translation,'second':second.translation,
                'scope':'controlled real Qt window, not user browser/manga'}
    finally:
        QCursor.setPos(original_cursor)
        fixture.close()
        owner.shutdown()
        app.removeNativeEventFilter(owner.native)
        app.processEvents()
