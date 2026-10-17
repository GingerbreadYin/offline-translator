import json
from PIL import Image
import pytest


def test_four_key_upgrade_preserves_custom_bindings_and_avoids_new_collision(tmp_path):
    from translator.core import SettingsStore
    path = tmp_path / 'settings.json'
    path.write_text(json.dumps({'bindings': ['Ctrl+Shift+A', 'F7', 'F8', 'Ctrl+Q']}))
    settings = SettingsStore(path).load()
    assert settings['bindings'][:4] == ['Ctrl+Shift+A', 'F7', 'F8', 'Ctrl+Q']
    assert len(settings['bindings']) == 6
    assert len(set(settings['bindings'])) == 6
    SettingsStore(path).save(settings)
    assert SettingsStore(path).load() == settings


def test_favorites_persist_deduplicate_update_meaning_and_delete(tmp_path):
    from translator.favorites import FavoritesStore
    path = tmp_path / '中文目录' / 'favorites.db'
    store = FavoritesStore(path)
    assert store.save(' issue ', 'n. 问题') == 'saved'
    assert store.save('issue', 'n. 问题') == 'exists'
    assert store.save('issue', 'v. 发行') == 'updated'
    rows = FavoritesStore(path).list()
    assert len(rows) == 1
    assert rows[0]['original'] == 'issue' and rows[0]['translation'] == 'v. 发行'
    assert rows[0]['saved_at']
    store.delete(rows[0]['id'])
    assert store.list() == []
    with pytest.raises(ValueError): store.save('', '测试')


def test_grouping_preserves_columns_and_skips_code_and_urls():
    from translator.fullpage import group_lines
    # RapidOCR polygons, text, confidence. Right column must not merge into left.
    def line(x, y, width, text):
        return ([[x,y],[x+width,y],[x+width,y+20],[x,y+20]], text, .99)
    blocks = group_lines([
        line(20,40,260,'This project is open source.'),
        line(420,40,220,'Please open the settings window.'),
        line(20,65,230,'You can use it offline.'),
        line(20,130,250,'https://example.com/project'),
        line(20,170,250,'const answer = foo();'),
    ])
    assert [b.text for b in blocks] == [
        'This project is open source. You can use it offline.',
        'Please open the settings window.']
    assert blocks[0].rect == (20,40,260,45)


def test_layout_never_places_translation_over_other_original_text():
    from translator.fullpage import place_translations
    # First paragraph has space above; second has none.
    placements = place_translations([(20,100,250,30),(20,15,250,30)],
                                    [(220,40),(220,40)], (0,0,800,600))
    assert placements[0] == (20,52,220,40)
    assert placements[1] is None


def test_full_translation_caches_text_but_keeps_new_coordinates():
    from translator.fullpage import Paragraph
    from translator.services import Pipeline
    from translator.core import Result
    pipeline = Pipeline('.')
    pipeline.verified = True
    pipeline.recognize_lines = lambda image: []
    calls = []
    class Lookup:
        def lookup(self, text):
            calls.append(text)
            return Result(text, translation='这是一个测试。')
    pipeline.lookup = Lookup()
    first = [Paragraph('This is a test.', (20,30,200,20))]
    second = [Paragraph('This is a test.', (20,80,200,20))]
    a = pipeline.translate_paragraphs(first)
    b = pipeline.translate_paragraphs(second)
    assert calls == ['This is a test.']
    assert a[0].rect == (20,30,200,20) and b[0].rect == (20,80,200,20)
    assert b[0].result.translation == '这是一个测试。'


def test_cancelled_full_job_does_not_translate_remaining_paragraphs():
    from translator.services import Pipeline
    from translator.fullpage import Paragraph
    from translator.core import Result
    pipeline = Pipeline('.')
    calls = []
    class Lookup:
        def lookup(self,text):
            calls.append(text)
            return Result(text,translation='测试')
    pipeline.lookup = Lookup()
    with pytest.raises(InterruptedError):
        pipeline.translate_paragraphs([Paragraph('First.',(0,0,1,1)),Paragraph('Second.',(0,10,1,1))],
                                      cancelled=lambda: bool(calls))
    assert calls == ['First.']
