"""Non-activating translation layers, numbered fallback panel and learning list."""
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QScrollArea, QDialog,
    QTableWidget, QTableWidgetItem, QPushButton, QAbstractItemView, QHeaderView, QMessageBox)
from .fullpage import place_translations

FLAGS = (Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
         Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
STYLE = "font-family: 'Microsoft YaHei UI'; font-size: 14px; color: #192b3d; background: #f8fafc;"


def result_text(result):
    if result.meanings:
        return (result.meanings[0].pos + ' ' + result.meanings[0].text).strip()
    return result.translation


class FullOverlay:
    def __init__(self):
        self.layer = QWidget(None, FLAGS | Qt.WindowType.WindowTransparentForInput)
        self.layer.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.layer.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.layer.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.panel = QWidget(None, FLAGS)
        self.panel.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.panel.setStyleSheet(STYLE + 'border: 1px solid #cbd5e1;')
        self.panel_layout = QVBoxLayout(self.panel)
        self.title = QLabel('对应译文 · 鼠标指向条目后按收藏键')
        self.title.setWordWrap(True)
        self.panel_layout.addWidget(self.title)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.panel_layout.addWidget(self.scroll)
        self.body = None
        self.labels = []
        self.markers = []
        self.paragraphs = []

    def hide(self):
        self.layer.hide()
        self.panel.hide()

    def clear(self):
        self.hide()
        for label, _ in self.labels:
            label.deleteLater()
        for marker in self.markers:
            marker.deleteLater()
        self.labels, self.markers = [], []
        if self.body is not None:
            self.scroll.takeWidget()
            self.body.deleteLater()
        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(4,4,4,4)
        self.scroll.setWidget(self.body)

    def display(self, paragraphs, obstacles, target, area, image_size):
        self.clear()
        self.paragraphs = paragraphs
        self.layer.setGeometry(*area)
        tx,ty,tw,th = target
        ax,ay,aw,ah = area
        sx, sy = tw/image_size[0], th/image_size[1]
        def mapped(rect):
            x,y,w,h = rect
            return round(tx+x*sx), round(ty+y*sy), max(1,round(w*sx)), max(1,round(h*sy))
        rects = [mapped(p.rect) for p in paragraphs]
        visible = [i for i,r in enumerate(rects) if QRect(*area).contains(QRect(*r))]
        sizes = []
        for p, rect in zip(paragraphs, rects):
            width = min(460, max(180,rect[2]),aw)
            label = QLabel(result_text(p.result))
            label.setWordWrap(True)
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setStyleSheet(STYLE+'padding: 5px; border: 1px solid #b6c9d8; border-radius: 4px;')
            label.setFixedWidth(width)
            sizes.append((width, max(32,label.heightForWidth(width))))
            label.deleteLater()
        placements = place_translations(rects, sizes, area, [mapped(r) for r in obstacles])
        fallback = False
        for i,p in enumerate(paragraphs):
            if i not in visible:
                continue
            label = QLabel(result_text(p.result))
            label.setWordWrap(True)
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setStyleSheet(STYLE+'padding: 5px; border: 1px solid #b6c9d8; border-radius: 4px;')
            placement = placements[i]
            if placement:
                x,y,w,h = placement
                label.setParent(self.layer)
                label.setGeometry(x-ax,y-ay,w,h)
            else:
                fallback = True
                label.setText(f'{i+1}. {result_text(p.result)}')
                self.body_layout.addWidget(label)
                marker = QLabel(str(i+1),self.layer)
                marker.setStyleSheet('background: #163d57; color: white; font-size: 11px; padding: 1px;')
                x,y,w,h = rects[i]
                marker.setGeometry(max(0,x-ax-23),y-ay,22,18)
                marker.show()
                self.markers.append(marker)
            label.show()
            self.labels.append((label,i))
        if self.labels:
            self.layer.show()
        if fallback:
            width = min(330,aw)
            # Prefer space outside the target; for maximized windows use the screen edge.
            if tx+tw+width <= ax+aw:
                px = tx+tw
            elif tx-width >= ax:
                px = tx-width
            else:
                px = ax+aw-width
            height = min(600,ah)
            self.panel.setGeometry(px,max(ay,min(ty,ay+ah-height)),width,height)
            # A maximized target leaves no external margin. Move any inline
            # translation that would be covered by the panel into that panel.
            for label,i in self.labels:
                if label.parentWidget() == self.layer:
                    global_rect = QRect(label.mapToGlobal(label.rect().topLeft()),label.size())
                    if self.panel.geometry().intersects(global_rect):
                        label.setText(f'{i+1}. {result_text(paragraphs[i].result)}')
                        label.setMinimumHeight(label.height())
                        label.setMaximumHeight(16777215)
                        self.body_layout.addWidget(label)
                        x,y,w,h = rects[i]
                        marker = QLabel(str(i+1),self.layer)
                        marker.setStyleSheet('background: #163d57; color: white; font-size: 11px; padding: 1px;')
                        marker.setGeometry(max(0,x-ax-23),y-ay,22,18)
                        marker.show()
                        self.markers.append(marker)
                        label.show()
            self.panel.show()
        self.body_layout.addStretch()

    def hovered(self, point):
        in_panel = self.panel.isVisible() and self.panel.geometry().contains(point)
        for label,index in self.labels:
            if in_panel and not self.panel.isAncestorOf(label):
                continue
            if label.isVisible() and label.visibleRegion().contains(label.mapFromGlobal(point)):
                return self.paragraphs[index].result
        return None

    def close(self):
        self.layer.close()
        self.panel.close()


class FavoritesWindow(QDialog):
    def __init__(self, store):
        super().__init__()
        self.store = store
        self.setWindowTitle('离线翻译 · 收藏列表')
        self.resize(850,520)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('收藏仅保存在本机 · 相同原文不重复，重新收藏不同义项会更新译文'))
        self.table = QTableWidget(0,3)
        self.table.setHorizontalHeaderLabels(['英文原文','中文译文','收藏时间'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)
        delete = QPushButton('删除选中收藏')
        delete.clicked.connect(self.delete_selected)
        layout.addWidget(delete)

    def refresh(self):
        try:
            self.rows = self.store.list()
        except Exception as exc:
            QMessageBox.warning(self,'无法读取收藏',str(exc))
            return
        self.table.setRowCount(len(self.rows))
        for row,data in enumerate(self.rows):
            for col,key in enumerate(('original','translation','saved_at')):
                item = QTableWidgetItem(data[key])
                item.setToolTip(data[key])
                self.table.setItem(row,col,item)
        self.table.resizeRowsToContents()

    def showEvent(self,event):
        self.refresh()
        super().showEvent(event)

    def delete_selected(self):
        indices = {item.row() for item in self.table.selectedItems()}
        try:
            for index in indices:
                self.store.delete(self.rows[index]['id'])
            self.refresh()
        except Exception as exc:
            QMessageBox.warning(self,'无法删除收藏',str(exc))
