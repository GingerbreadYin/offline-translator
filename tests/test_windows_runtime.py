from pathlib import Path
import subprocess
import sys
import pytest


def test_qt_bootstrap_survives_conflicting_bundled_icu():
    root = Path(__file__).resolve().parents[1] / "dist/OfflineTranslator/_internal"
    if not (root / "PySide6/Qt6Core.dll").exists():
        pytest.skip("portable build not present")
    script = """
import ctypes, os
from pathlib import Path
from translator.windows_runtime import preload_system_icu
root=Path(__import__('sys').argv[1])
handles=[os.add_dll_directory(str(p)) for p in [root,root/'PySide6',root/'shiboken6']]
preload_system_icu()
ctypes.WinDLL(str(root/'PySide6/Qt6Core.dll'))
"""
    result = subprocess.run([sys.executable, "-c", script, str(root)], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
