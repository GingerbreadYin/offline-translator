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
    if args.self_test or args.worker_test:
        from tools.probe import probe, probe_worker
        data = probe_worker(resource_root()) if args.worker_test else probe(resource_root())
        report = json.dumps(data, ensure_ascii=False, indent=2)
        if args.report:
            args.report.write_text(report, encoding="utf-8")
        elif sys.stdout is not None:
            print(report)
        return
    from PySide6.QtCore import QTimer
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    from PySide6.QtWidgets import QApplication
    from translator.ui import Controller
    app = QApplication(sys.argv)
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
    controller = Controller(app, resource_root(), Path("build/smoke-settings.json") if args.ui_smoke else None)
    if args.ui_smoke:
        QTimer.singleShot(1500, controller.shutdown)
    app.aboutToQuit.connect(server.close)
    sys.exit(app.exec())


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
