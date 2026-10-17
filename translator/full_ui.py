"""Local favorites list and snapshot result exports."""
from PySide6.QtWidgets import (QDialog,QLabel,QVBoxLayout,QTableWidget,QTableWidgetItem,
    QPushButton,QAbstractItemView,QHeaderView,QMessageBox)
from .overlay import FullOverlay,result_text,DragHandle,STYLE


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
