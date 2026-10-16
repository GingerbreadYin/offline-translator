import sqlite3
import threading
from pathlib import Path

import pytest

from translator.core import Workflow, Navigator, parse_meanings, place_result, SettingsStore, validate_bindings
from translator.services import Dictionary, Lookup


def test_cancelled_job_never_replaces_new_result():
    flow = Workflow()
    flow.toggle()
    first = flow.begin()
    flow.toggle()
    assert flow.state == "idle"
    flow.toggle()
    second = flow.begin()
    assert not flow.finish(first)
    assert flow.state == "processing"
    assert flow.finish(second)
    assert flow.state == "showing"


def test_toggle_cancels_selection_and_showing():
    flow = Workflow()
    flow.toggle()
    assert flow.state == "selecting"
    flow.toggle()
    assert flow.state == "idle"
    flow.toggle()
    job = flow.begin()
    flow.finish(job)
    flow.toggle()
    assert flow.state == "idle"


def test_meaning_parser_preserves_abbreviations_and_parentheses():
    meanings = parse_meanings("n. 问题, 议题\nv. 发行, 发布\nadj. 与 U.S. 有关的（美式, 口语）")
    assert [(m.pos, m.text) for m in meanings] == [
        ("n.", "问题"), ("n.", "议题"), ("v.", "发行"), ("v.", "发布"),
        ("adj.", "与 U.S. 有关的（美式, 口语）")]


def test_navigator_wraps_and_empty_or_single_does_not_move():
    nav = Navigator(parse_meanings("n. 问题, 议题"))
    assert nav.current.text == "问题"
    assert nav.move(-1).text == "议题"
    assert nav.move(1).text == "问题"
    assert Navigator([]).move(1) is None
    one = Navigator(parse_meanings("n. 问题"))
    assert one.move(-1).text == "问题"


@pytest.mark.parametrize("selection,size,area,expected", [
    ((100, 100, 40, 20), (200, 60), (0, 0, 800, 600), (100, 32, 200, 60)),
    ((100, 2, 40, 20), (200, 60), (0, 0, 800, 600), (100, 30, 200, 60)),
    ((-50, 100, 30, 20), (200, 60), (-800, 0, 800, 600), (-200, 32, 200, 60)),
    ((0, 0, 50, 20), (1000, 900), (0, 0, 800, 600), (0, 0, 800, 600)),
])
def test_placement_respects_negative_monitors_and_edges(selection, size, area, expected):
    assert place_result(selection, size, area) == expected


def test_settings_atomic_and_duplicate_bindings_rejected(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    defaults = store.load()
    defaults["bindings"] = ["F8", "F9", "F10"]
    store.save(defaults)
    assert store.load()["bindings"] == ["F8", "F9", "F10"]
    with pytest.raises(ValueError):
        validate_bindings(["Ctrl+Q", "Ctrl+Q", "F9"])
    with pytest.raises(ValueError):
        validate_bindings(["Esc", "F9", "F10"])
    with pytest.raises(ValueError):
        validate_bindings(["Ctrl", "F9", "F10"])


def test_corrupt_settings_report_error_without_overwriting(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("broken", encoding="utf-8")
    with pytest.raises(ValueError):
        SettingsStore(path).load()
    assert path.read_text() == "broken"


def make_dictionary(tmp_path):
    path = tmp_path / "words.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE words(word TEXT PRIMARY KEY, translation TEXT, exchange TEXT)")
        db.executemany("INSERT INTO words VALUES (?,?,?)", [
            ("issue", "n. 问题, 议题\nv. 发行", "s:issues"),
            ("run", "v. 跑", "p:ran/i:running"),
            ("running", "n. 运转", "0:run"),
        ])
        db.execute("CREATE TABLE forms(form TEXT, lemma TEXT)")
        db.executemany("INSERT INTO forms VALUES (?,?)", [("issues", "issue"), ("ran", "run"), ("running", "run")])
    return Dictionary(path)


def test_dictionary_exact_then_forms_and_thread_safe(tmp_path):
    dictionary = make_dictionary(tmp_path)
    assert dictionary.find("ISSUE")[0].text == "问题"
    assert dictionary.find("running")[0].text == "运转"
    assert dictionary.find("ran")[0].text == "跑"
    assert dictionary.find("UnknownProperName") == []
    results = []
    thread = threading.Thread(target=lambda: results.extend(dictionary.find("issues")))
    thread.start()
    thread.join()
    assert results[0].text == "问题"


def test_lookup_only_translates_missing_words_and_sentences(tmp_path):
    class LocalTranslator:
        def translate(self, text):
            return {"UnknownProperName": "未知名称", "This is a test.": "这是一个测试。"}[text]
    lookup = Lookup(make_dictionary(tmp_path), LocalTranslator())
    assert lookup.lookup("issue").meanings[0].pos == "n."
    result = lookup.lookup("UnknownProperName")
    assert not result.meanings
    assert result.translation == "未知名称"
    assert lookup.lookup("This is a test.").translation == "这是一个测试。"
    with pytest.raises(ValueError):
        lookup.lookup("   ")
