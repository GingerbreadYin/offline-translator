import argparse
import json
from pathlib import Path
import sys


def resource_root():
    root = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    return root / "resources"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--ui-smoke", action="store_true")
    parser.add_argument("--worker-test", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    switch_checked = False
    def mark(stage):
        if args.ui_smoke and args.report:
            args.report.write_text(json.dumps({"stage": stage, "enable_toggle_checked": switch_checked}), encoding="utf-8")
    if args.self_test or args.worker_test:
        from tools.probe import probe, probe_worker
        data = probe_worker(resource_root()) if args.worker_test else probe(resource_root())
        report = json.dumps(data, ensure_ascii=False, indent=2)
        if args.report:
            args.report.write_text(report, encoding="utf-8")
        elif sys.stdout is not None:
            print(report)
        return
    from translator.windows_runtime import preload_system_icu
    preload_system_icu()
    from PySide6.QtCore import QTimer
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    from PySide6.QtWidgets import QApplication
    from translator.ui import Controller
    mark("imports-complete")
    app = QApplication(sys.argv)
    mark("application-created")
    app.setQuitOnLastWindowClosed(False)
    # QLocalServer prevents duplicate instances without modifying user data.
    server = QLocalServer()
    socket = QLocalSocket()
    name = "OfflineTranslator-ui-smoke-local" if args.ui_smoke else "OfflineTranslator-v01-local"
    socket.connectToServer(name)
    if socket.waitForConnected(200):
        return
    QLocalServer.removeServer(name)
    if not server.listen(name):
        raise RuntimeError("无法建立本机单实例服务")
    mark("creating-controller")
    if args.ui_smoke:
        from translator.core import SettingsStore
        SettingsStore(Path("build/smoke-settings.json")).save({"bindings": ["Ctrl+Alt+F21", "Ctrl+Alt+F22", "Ctrl+Alt+F23", "Ctrl+Alt+F24"]})
    controller = Controller(app, resource_root(), Path("build/smoke-settings.json") if args.ui_smoke else None)
    mark("controller-ready")
    if args.ui_smoke:
        def finish_smoke():
            nonlocal switch_checked
            try:
                controller.settings_window.hide()
                assert set(controller.hotkeys.registered) == {100,101,102,103}, controller.settings_window.status.text()
                controller.action(3)
                assert not controller.enabled and set(controller.hotkeys.registered) == {103}
                controller.action(0)
                assert controller.flow.state == "idle"
                controller.action(3)
                assert controller.enabled and set(controller.hotkeys.registered) == {100,101,102,103}
                switch_checked = True
                mark("shutdown-started")
                controller.shutdown()
                assert not controller.hotkeys.registered
                mark("shutdown-complete")
            except Exception:
                import traceback
                if args.report:
                    args.report.write_text(traceback.format_exc(), encoding="utf-8")
                controller.shutdown()
                app.exit(1)
        QTimer.singleShot(1500, finish_smoke)
    app.aboutToQuit.connect(server.close)
    exit_code = app.exec()
    if exit_code == 0:
        mark("event-loop-exited")
    sys.exit(exit_code)


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    try:
        main()
    except Exception:
        import traceback
        if "--report" in sys.argv:
            destination = Path(sys.argv[sys.argv.index("--report") + 1])
            destination.write_text(traceback.format_exc(), encoding="utf-8")
            sys.exit(1)
        raise
