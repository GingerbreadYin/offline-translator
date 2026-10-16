import hashlib
import json
import sqlite3
import zipfile
import pytest
from translator.resources import verify_resources
from tools.prepare_resources import build_dictionary, extract_translation


def test_corrupt_file_rejected_and_missing_listed(tmp_path):
    (tmp_path / "a.bin").write_bytes(b"good")
    manifest = {"files": [{"path": "a.bin", "sha256": hashlib.sha256(b"good").hexdigest()}]}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    assert verify_resources(tmp_path) == []
    (tmp_path / "a.bin").write_bytes(b"bad")
    assert verify_resources(tmp_path) == ["a.bin"]
    (tmp_path / "a.bin").unlink()
    assert verify_resources(tmp_path) == ["a.bin"]


def test_dictionary_import_handles_literal_newlines_and_forms(tmp_path):
    source = tmp_path / "words.csv"
    source.write_text('word,translation,exchange\nissue,"n. 问题\\nv. 发行",s:issues\n', encoding="utf-8")
    destination = tmp_path / "dictionary.db"
    build_dictionary(source, destination)
    with sqlite3.connect(destination) as db:
        assert db.execute("SELECT translation FROM words").fetchone()[0] == "n. 问题\nv. 发行"
        assert db.execute("SELECT form,lemma FROM forms").fetchone() == ("issues", "issue")


def test_model_zip_does_not_extract_unrelated_or_unsafe_files(tmp_path):
    path = tmp_path / "model.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("package/model/model.bin", b"model")
        z.writestr("package/sentencepiece.model", b"tokenizer")
        z.writestr("package/README.md", "license")
        z.writestr("package/stanza/large.pt", b"unneeded")
        z.writestr("package/model/../../escape", b"unsafe")
    with pytest.raises(ValueError):
        extract_translation(path, tmp_path / "translation")
    assert not (tmp_path / "escape").exists()
