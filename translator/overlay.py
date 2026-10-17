"""Movable snapshot translations with bounded width and accessible long text."""
from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QTextOption
from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QScrollArea,
                              QTextEdit, QSizePolicy, QApplication)
from .fullpage import place_translations

FLAGS = (Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
         Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
STYLE = "font-family: 'Microsoft YaHei UI'; font-size: 14px; color: #192b3d; background: #f8fafc;"


def result_text(result):
    if result.meanings:
        return (result.meanings[0].pos+' '+result.meanings[0].text).strip()
    return result.translation


class DragHandle(QLabel):
    def __init__(self,text,parent=None):
        super().__init__(text,parent)
        self.anchor = None
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setStyleSheet('color: #58718a; font-size: 11px; padding: 3px;')

    def mousePressEvent(self,event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.anchor = (event.globalPosition().toPoint(),self.window().pos())
            event.accept()

    def mouseMoveEvent(self,event):
        if self.anchor:
            point,origin = self.anchor
            self.window().move(origin+event.globalPosition().toPoint()-point)
            event.accept()

    def mouseReleaseEvent(self,event):
        self.anchor = None
        event.accept()


class ParagraphView(QTextEdit):
    def __init__(self,text,expand=False,parent=None):
        super().__init__(parent)
        self.expand = expand
        self.setReadOnly(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setPlainText(text)
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff if expand else Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setStyleSheet(STYLE+'border: 0; padding: 2px;')
        self.setMinimumWidth(0)
        if expand:
            self.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if self.expand:
            self.document().setTextWidth(max(1,self.viewport().width()))
            height = int(self.document().size().height())+12
            if height != self.height():
                self.setFixedHeight(height)


class TranslationCard(QWidget):
    def __init__(self,text,number,width):
        super().__init__(None,FLAGS)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet(STYLE+'border: 1px solid #b6c9d8;')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6,3,6,6)
        layout.setSpacing(1)
        self.handle = DragHandle(f'{number} · 拖动此处移动',self)
        self.view = ParagraphView(text,parent=self)
        layout.addWidget(self.handle)
        layout.addWidget(self.view)
        self.view.resize(max(120,width-16),100)
        self.view.document().setTextWidth(max(120,width-26))
        self.initial_size = (width,min(260,max(72,int(self.view.document().size().height())+45)))


class FullOverlay:
    def __init__(self):
        # The only full-screen layer is the mouse-transparent reference numbers.
        self.layer = QWidget(None,FLAGS | Qt.WindowType.WindowTransparentForInput)
        self.layer.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.layer.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.layer.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.panel = QWidget(None,FLAGS)
        self.panel.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.panel.setStyleSheet(STYLE+'border: 1px solid #cbd5e1;')
        layout = QVBoxLayout(self.panel)
        self.handle = DragHandle('对应译文 · 拖动此处移动',self.panel)
        layout.addWidget(self.handle)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.scroll)
        self.body = None
        self.labels, self.cards, self.markers, self.paragraphs = [],[],[],[]

    def hide(self):
        self.layer.hide()
        self.panel.hide()
        for card in self.cards: card.hide()

    def clear(self):
        self.hide()
        for card in self.cards:
            card.close(); card.deleteLater()
        for marker in self.markers: marker.deleteLater()
        if self.body is not None:
            self.scroll.takeWidget(); self.body.deleteLater()
        self.cards,self.labels,self.markers = [],[],[]
        self.paragraphs=[]
        self.body = QWidget()
        self.body.setMinimumWidth(0)
        self.body.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(3,3,3,3)
        self.scroll.setWidget(self.body)

    def display(self,paragraphs,obstacles,target,area,image_size):
        previous=len(self.paragraphs)
        if not previous or paragraphs[:previous]!=self.paragraphs:
            self.clear()
            previous=0
        else:
            tail=self.body_layout.takeAt(self.body_layout.count()-1)
        self.paragraphs = paragraphs
        self.layer.setGeometry(*area)
        tx,ty,tw,th = target
        ax,ay,aw,ah = area
        def mapped(rect):
            x,y,w,h=rect
            return (round(tx+x*tw/image_size[0]),round(ty+y*th/image_size[1]),
                    max(1,round(w*tw/image_size[0])),max(1,round(h*th/image_size[1])))
        rects = [mapped(p.rect) for p in paragraphs]
        candidates = [None]*previous+[TranslationCard(result_text(paragraphs[i].result),i+1,min(460,max(220,rects[i][2]),aw))
                                    for i in range(previous,len(paragraphs))]
        panel_width = min(360,aw)
        panel_height = min(600,ah)
        px = tx+tw if tx+tw+panel_width<=ax+aw else (tx-panel_width if tx-panel_width>=ax else ax+aw-panel_width)
        panel_rect = self.panel.geometry() if self.panel.isVisible() else QRect(px,max(ay,min(ty,ay+ah-panel_height)),panel_width,panel_height)
        reserved=[mapped(r) for r in obstacles]+[(panel_rect.x(),panel_rect.y(),panel_rect.width(),panel_rect.height())]
        reserved += [(c.x(),c.y(),c.width(),c.height()) for c in self.cards]
        placements=[None]*previous+place_translations(rects[previous:],[c.initial_size for c in candidates[previous:]],area,reserved)
        fallback = any(p is None for p in placements)
        for i,(paragraph,card,placement) in enumerate(zip(paragraphs,candidates,placements)):
            if i<previous:
                continue
            if not QRect(*area).contains(QRect(*rects[i])):
                card.deleteLater(); continue
            if placement is not None and not (fallback and panel_rect.intersects(QRect(*placement))):
                card.setGeometry(*placement)
                card.show()
                self.cards.append(card)
                self.labels.append((card.view,i))
            else:
                card.deleteLater()
                view = ParagraphView(f'{i+1}. {result_text(paragraph.result)}',expand=True)
                self.body_layout.addWidget(view)
                self.labels.append((view,i))
                x,y,w,h = rects[i]
                marker = QLabel(str(i+1),self.layer)
                marker.setStyleSheet('background: #163d57; color: white; font-size: 11px; padding: 1px;')
                marker.setGeometry(max(0,x-ax-23),y-ay,22,18)
                marker.show(); self.markers.append(marker)
        self.body_layout.addStretch()
        if self.markers: self.layer.show()
        if any(self.panel.isAncestorOf(label) for label,_ in self.labels):
            if not self.panel.isVisible(): self.panel.setGeometry(panel_rect)
            self.panel.show()

    def hovered(self,point):
        top = QApplication.widgetAt(point)
        for view,index in self.labels:
            if not view.isVisible(): continue
            window = view.window()
            if top is not None and top.window() != window: continue
            local = view.viewport().mapFromGlobal(point)
            if view.viewport().visibleRegion().contains(local):
                return self.paragraphs[index].result
        return None

    def close(self):
        self.hide()
        for card in self.cards: card.close()
        self.layer.close(); self.panel.close()
