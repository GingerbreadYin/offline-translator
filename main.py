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
    def mark(stage):
        if args.ui_smoke and args.report:
            args.report.write_text(json.dumps({"stage": stage}), encoding="utf-8")
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
    name = "OfflineTranslator-v01-local"
    socket.connectToServer(name)
    if socket.waitForConnected(200):
        return
    QLocalServer.removeServer(name)
    if not server.listen(name):
        raise RuntimeError("无法建立本机单实例服务")
    mark("creating-controller")
    controller = Controller(app, resource_root(), Path("build/smoke-settings.json") if args.ui_smoke else None)
    mark("controller-ready")
    if args.ui_smoke:
        def finish_smoke():
            mark("shutdown-started")
            controller.shutdown()
            mark("shutdown-complete")
        QTimer.singleShot(1500, finish_smoke)
    app.aboutToQuit.connect(server.close)
    exit_code = app.exec()
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
