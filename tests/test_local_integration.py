from pathlib import Path
import socket
import pytest
from translator.services import OfflineTranslator, Pipeline

ROOT = Path(__file__).resolve().parents[1] / "resources"
pytestmark = pytest.mark.skipif(not (ROOT / "translation/model/model.bin").exists(), reason="local model package not prepared")


def test_real_translation_has_no_tokenizer_artifacts_or_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Runtime translation must not open network sockets")
    monkeypatch.setattr(socket.socket, "connect", denied)
    translator = OfflineTranslator(ROOT / "translation")
    text = translator.translate("Please open the settings window.")
    assert "▁" not in text
    assert "设置" in text and "窗口" in text
    text = translator.translate("Visit https://example.com/project and use `git_status`.")
    assert "https://example.com/project" in text
    assert "`git_status`" in text


def test_full_real_probe_runs_without_outbound_connections(monkeypatch):
    from tools.probe import probe
    def denied(*args, **kwargs):
        raise AssertionError("OCR and translation must remain offline")
    monkeypatch.setattr(socket.socket, "connect", denied)
    report = probe(ROOT)
    assert report["offline"] is True
    assert [item["ocr"] for item in report["samples"]] == [
        "issue", "This project is open source.", "Please open the settings window."]


def test_real_worker_process_recognizes_and_returns_dictionary():
    from tools.probe import probe_worker
    report = probe_worker(ROOT)
    assert report["worker_process"] is True
    assert report["word"] == "issue"
    assert report["meanings"] > 1


def test_translation_resources_load_from_chinese_directory(tmp_path):
    import shutil
    destination = tmp_path / "中文资源目录"
    shutil.copytree(ROOT / "translation", destination)
    result = OfflineTranslator(destination).translate("This project is open source.")
    assert "项目" in result and "开源" in result
