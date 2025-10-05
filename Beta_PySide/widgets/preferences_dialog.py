#!/usr/bin/env python3
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSlider, QPushButton, QApplication
from PySide6.QtCore import Qt


class PreferencesDialog(QDialog):
    """Small preferences dialog for theme + font size"""

    def __init__(self, app: QApplication, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Appearance")
        self.setModal(True)

        layout = QVBoxLayout(self)

        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["theme_1", "theme_2", "theme_3", "theme_4"])
        theme_row.addWidget(self.theme_combo, 1)
        layout.addLayout(theme_row)

        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("Font size:"))
        self.font_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_slider.setRange(8, 16)
        font_row.addWidget(self.font_slider, 1)
        layout.addLayout(font_row)

        buttons = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        buttons.addWidget(apply_btn)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        sm = getattr(app, 'settings_manager', None)
        if sm:
            self.theme_combo.setCurrentText(sm.get_setting("current_theme", "theme_1"))
            self.font_slider.setValue(sm.get_setting("font_size", 9))
        else:
            self.font_slider.setValue(app.font().pointSize())

        def apply_now():
            if hasattr(app, 'theme_manager'):
                app.theme_manager.apply_theme(self.theme_combo.currentText(), app)
            f = app.font()
            f.setPointSize(self.font_slider.value())
            app.setFont(f)
            if sm:
                sm.set_setting("current_theme", self.theme_combo.currentText())
                sm.set_setting("font_size", self.font_slider.value())

        apply_btn.clicked.connect(apply_now)
        ok_btn.clicked.connect(lambda: (apply_now(), self.accept()))
        cancel_btn.clicked.connect(self.reject)



