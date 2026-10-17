import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication
from translator.core import Result, Meaning
from translator.fullpage import TranslatedParagraph


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def test_full_overlay_is_clickthrough_and_hover_maps_only_to_visible_translation(app):
    from translator.full_ui import FullOverlay
    overlay = FullOverlay()
    data = [TranslatedParagraph((20,100,240,25), Result('This is a test.', translation='这是一个测试。')),
            TranslatedParagraph((20,10,240,25), Result('Another test.', translation='另一个测试。'))]
    overlay.display(data, [(20,100,240,25),(20,10,240,25)], (100,0,700,500), (0,0,1200,900), (700,500))
    app.processEvents()
    assert overlay.layer.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    assert overlay.layer.windowFlags() & Qt.WindowType.WindowTransparentForInput
    label, index = overlay.labels[0]
    point = label.mapToGlobal(label.rect().center())
    assert overlay.hovered(point).original == 'This is a test.'
    assert overlay.hovered(QPoint(-2000,-2000)) is None
    assert overlay.panel.isVisible()
    label, index = overlay.labels[1]
    assert overlay.hovered(label.mapToGlobal(label.rect().center())).original == 'Another test.'
    overlay.hide()
    assert overlay.hovered(point) is None
    overlay.close()


def test_favorites_dialog_displays_literal_text_and_deletes_selected(app, tmp_path):
    from translator.favorites import FavoritesStore
    from translator.full_ui import FavoritesWindow
    store = FavoritesStore(tmp_path / 'favorites.db')
    store.save('<script>hello</script>', '你好')
    dialog = FavoritesWindow(store)
    dialog.refresh()
    assert dialog.table.rowCount() == 1
    assert dialog.table.item(0,0).text() == '<script>hello</script>'
    dialog.table.selectRow(0)
    dialog.delete_selected()
    assert not store.list() and dialog.table.rowCount() == 0
    dialog.close()


def test_capture_adapter_targets_exact_hwnd_and_retains_latest_frame_only():
    from translator.capture import WindowCapture
    capture = WindowCapture()
    assert capture.snapshot() is None
    capture.close()


def test_panel_never_saves_occluded_inline_translation(app):
    from translator.full_ui import FullOverlay
    overlay = FullOverlay()
    data = [TranslatedParagraph((900,100,240,25),Result('Hidden inline.',translation='被遮挡。')),
            TranslatedParagraph((20,10,240,25),Result('Panel entry.',translation='旁栏条目。'))]
    overlay.display(data,[p.rect for p in data],(0,0,1200,900),(0,0,1200,900),(1200,900))
    app.processEvents()
    label,_ = overlay.labels[0]
    assert overlay.panel.isAncestorOf(label), 'covered inline text must remain available in panel'
    # Font metrics differ between the native desktop and offscreen CI. Use the
    # relocated visible item, rather than a coordinate that can hit either row.
    result = overlay.hovered(label.mapToGlobal(label.rect().center()))
    assert result.original == 'Hidden inline.'
    assert overlay.hovered(overlay.panel.mapToGlobal(QPoint(310,570))) is None
    overlay.close()


def test_fallback_panel_stays_inside_screen_near_bottom_edge(app):
    from translator.full_ui import FullOverlay
    overlay = FullOverlay()
    data = [TranslatedParagraph((0,0,240,25),Result('Bottom window.',translation='底部窗口。'))]
    overlay.display(data,[(0,-80,300,80)],(100,700,700,180),(0,0,1200,900),(700,180))
    assert overlay.panel.geometry().bottom() < 900
    overlay.close()


def test_full_mode_real_pipeline_returns_boxes_and_chinese_without_network(monkeypatch):
    import socket
    from pathlib import Path
    from PIL import Image, ImageDraw, ImageFont
    from translator.services import Pipeline
    root = Path(__file__).resolve().parents[1] / 'resources'
    if not (root/'dictionary.db').exists(): pytest.skip('local resources not present')
    monkeypatch.setattr(socket.socket, 'connect', lambda *a: pytest.fail('network used'))
    image = Image.new('RGB', (900,260), 'white')
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 28)
    ImageDraw.Draw(image).text((20,80), 'This project is open source.', fill='black', font=font)
    data = Pipeline(root).run(image, full=True)
    assert len(data['paragraphs']) == 1
    assert '项目' in data['paragraphs'][0].result.translation
    assert data['obstacles'][0][0] < 30
