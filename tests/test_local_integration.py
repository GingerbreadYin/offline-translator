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
