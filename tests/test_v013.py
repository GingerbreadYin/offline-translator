import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from translator.core import Result
from translator.fullpage import TranslatedParagraph


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def test_full_inline_window_can_be_dragged_and_favorite_follows_it(app):
    from translator.full_ui import FullOverlay
    overlay = FullOverlay()
    overlay.display([TranslatedParagraph((30,140,250,25),Result('A test.',translation='这是测试。'))],
                    [],(100,0,700,500),(0,0,1200,900),(700,500))
    app.processEvents()
    card = overlay.cards[0]
    original = card.pos()
    QTest.mousePress(card.handle,Qt.MouseButton.LeftButton,pos=QPoint(10,10))
    QTest.mouseMove(card.handle,QPoint(70,40))
    QTest.mouseRelease(card.handle,Qt.MouseButton.LeftButton,pos=QPoint(70,40))
    assert card.pos() != original
    app.processEvents()
    assert overlay.hovered(card.view.mapToGlobal(card.view.rect().center())).original == 'A test.'
    overlay.close()


def test_long_url_and_paragraph_are_wrapped_inside_scrollable_panel(app):
    from translator.full_ui import FullOverlay
    overlay = FullOverlay()
    text = 'https://example.com/'+'longpath'*100+' 中文长释义。'*50
    overlay.display([TranslatedParagraph((20,5,200,20),Result('Long text.',translation=text))],
                    [],(0,0,1200,900),(0,0,1200,900),(1200,900))
    app.processEvents()
    view,_ = overlay.labels[0]
    assert view.toPlainText().endswith('中文长释义。')
    assert view.width() <= overlay.scroll.viewport().width()
    assert view.document().idealWidth() <= view.viewport().width()+5
    assert overlay.scroll.verticalScrollBar().maximum() > 0
    overlay.scroll.verticalScrollBar().setValue(overlay.scroll.verticalScrollBar().maximum())
    app.processEvents()
    assert view.visibleRegion().contains(view.mapFromGlobal(overlay.scroll.viewport().mapToGlobal(overlay.scroll.viewport().rect().center())))
    overlay.close()


def test_snapshot_result_does_not_inspect_foreground_again(app, monkeypatch):
    from PIL import Image
    import translator.window_translation as module
    class Worker:
        def cancel_pending(self): pass
        def submit(self,request): self.request=request
    class Tray:
        def showMessage(self,*a,**kw): pass
    from PySide6.QtCore import QObject
    class Owner(QObject):
        def __init__(self):
            super().__init__(); self.app=app; self.worker=Worker(); self.tray=Tray()
        def cancel(self): self.full.stop()
    owner=Owner(); full=owner.full=module.WindowTranslation(owner)
    monkeypatch.setattr(module,'capture_window_snapshot',lambda h,a:(Image.new('RGB',(700,500),'white'),(100,0,700,500),(0,0,1200,900)))
    full.start(1234)
    job=owner.worker.request[0]
    monkeypatch.setattr(module,'foreground_window',lambda: pytest.fail('snapshot must not track focus'))
    full.finished(job,{'paragraphs':[TranslatedParagraph((20,100,240,25),Result('A test.',translation='测试'))],'obstacles':[]},'')
    assert full.active and full.overlay.cards[0].isVisible()
    full.start()
    assert not full.active and not full.overlay.cards[0].isVisible()
    full.overlay.close()


def test_worker_ready_means_model_warmup_completed(monkeypatch):
    from translator.services import Pipeline
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]/'resources'
    if not (root/'dictionary.db').exists(): pytest.skip('local resources not present')
    pipeline=Pipeline(root)
    pipeline.warmup()
    import rapidocr_onnxruntime,ctranslate2
    def cold_load(*a,**kw): pytest.fail('request must reuse the prewarmed engine')
    monkeypatch.setattr(rapidocr_onnxruntime,'RapidOCR',cold_load)
    monkeypatch.setattr(ctranslate2,'Translator',cold_load)
    from PIL import Image,ImageDraw,ImageFont
    image=Image.new('RGB',(800,100),'white')
    ImageDraw.Draw(image).text((20,20),'issue',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',32),fill='black')
    assert pipeline.run(image).meanings
    assert '设置' in pipeline.lookup.translator.translate('Please open the settings window.')


def test_progress_update_preserves_dragged_card_position(app):
    from translator.full_ui import FullOverlay
    overlay=FullOverlay()
    first=TranslatedParagraph((20,150,240,25),Result('First.',translation='第一条。'))
    second=TranslatedParagraph((20,350,240,25),Result('Second.',translation='第二条。'))
    overlay.display([first],[],(0,0,900,800),(0,0,1200,900),(900,800))
    card=overlay.cards[0];card.move(130,120)
    overlay.display([first,second],[],(0,0,900,800),(0,0,1200,900),(900,800))
    assert overlay.cards[0] is card and card.pos()==QPoint(130,120)
    overlay.close()


def test_later_progress_panel_never_covers_earlier_inline_card(app):
    from translator.full_ui import FullOverlay
    from PySide6.QtCore import QRect
    overlay=FullOverlay()
    first=TranslatedParagraph((900,200,240,25),Result('First.',translation='第一条。'))
    second=TranslatedParagraph((20,5,200,20),Result('Second.',translation='第二条。'))
    obstacles=[first.rect,second.rect]
    overlay.display([first],obstacles,(0,0,1200,900),(0,0,1200,900),(1200,900))
    overlay.display([first,second],obstacles,(0,0,1200,900),(0,0,1200,900),(1200,900))
    assert all(not card.geometry().intersects(overlay.panel.geometry()) for card in overlay.cards)
    assert len(overlay.labels)==2
    overlay.close()
