#!/usr/bin/env python3
from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QHBoxLayout, QPushButton, QFileDialog
from PySide6.QtCore import Qt


class DocumentsManagerDialog(QDialog):
    """Dialog to manage knowledge sources (RAG documents)"""

    def __init__(self, document_service, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Knowledge Sources")
        self.setModal(True)
        self.ds = document_service

        layout = QVBoxLayout(self)
        self.list = QListWidget()
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setWordWrap(False)
        self.list.setUniformItemSizes(True)
        try:
            self.list.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        except Exception:
            pass
        self.list.setMaximumHeight(220)
        layout.addWidget(self.list)

        row = QHBoxLayout()
        add_btn = QPushButton("Add")
        rem_btn = QPushButton("Remove")
        clr_btn = QPushButton("Clear All")
        row.addWidget(add_btn)
        row.addWidget(rem_btn)
        row.addWidget(clr_btn)
        row.addStretch(1)
        layout.addLayout(row)

        def refresh():
            self.list.clear()
            for name in self.ds.get_document_list():
                self.list.addItem(name)

        def add_files():
            files, _ = QFileDialog.getOpenFileNames(
                self, "Add Documents", "",
                "Documents (*.txt *.pdf *.docx *.doc *.html *.htm *.md);;All files (*)"
            )
            for p in files:
                self.ds.add_document(p)

        def remove_selected():
            item = self.list.currentItem()
            if not item:
                return
            for p in self.ds.get_document_paths():
                if p.endswith(item.text()):
                    self.ds.remove_document(p)
                    break

        def clear_all():
            self.ds.clear_all_documents()

        add_btn.clicked.connect(add_files)
        rem_btn.clicked.connect(remove_selected)
        clr_btn.clicked.connect(clear_all)

        self.ds.document_added.connect(lambda *_: refresh())
        self.ds.document_removed.connect(lambda *_: refresh())
        refresh()



