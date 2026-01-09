#!/usr/bin/env python3
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSlider, 
    QPushButton, QApplication, QTabWidget, QTextEdit, QWidget
)
from PySide6.QtCore import Qt

# Import display mapping from theme manager
try:
    from themes.theme_manager import THEME_KEY_TO_DISPLAY, THEME_DISPLAY_TO_KEY
except Exception:
    THEME_KEY_TO_DISPLAY = {
        "sur5ve": "Sur5ve",
    }
    THEME_DISPLAY_TO_KEY = {v: k for k, v in THEME_KEY_TO_DISPLAY.items()}

# Import hardware detector (Phase 3)
try:
    from utils.hardware_detector import HardwareDetector
    HAS_HARDWARE_DETECTOR = True
except ImportError:
    HAS_HARDWARE_DETECTOR = False


class PreferencesDialog(QDialog):
    """Preferences dialog with tabs for appearance and system info"""

    def __init__(self, app: QApplication, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setModal(True)
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)
        
        # Create tab widget
        tabs = QTabWidget()
        
        # Tab 1: Appearance
        appearance_tab = QWidget()
        appearance_layout = QVBoxLayout(appearance_tab)
        
        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        # Populate with display labels
        self.theme_combo.addItems(list(THEME_KEY_TO_DISPLAY.values()))
        theme_row.addWidget(self.theme_combo, 1)
        appearance_layout.addLayout(theme_row)

        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("Font size:"))
        self.font_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_slider.setRange(8, 16)
        font_row.addWidget(self.font_slider, 1)
        appearance_layout.addLayout(font_row)
        
        appearance_layout.addStretch()
        tabs.addTab(appearance_tab, "Appearance")
        
        # Tab 2: System Info (Phase 3)
        if HAS_HARDWARE_DETECTOR:
            system_tab = QWidget()
            system_layout = QVBoxLayout(system_tab)
            
            system_info_text = QTextEdit()
            system_info_text.setReadOnly(True)
            system_info_text.setPlainText(HardwareDetector.format_system_info())
            system_info_text.setStyleSheet("font-family: monospace;")
            system_layout.addWidget(system_info_text)
            
            tabs.addTab(system_tab, "System Info")
        
        layout.addWidget(tabs)
        
        # Buttons at bottom
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
            current_key = sm.get_setting("current_theme", "sur5ve")
            current_display = THEME_KEY_TO_DISPLAY.get(current_key, "Sur5ve")
            self.theme_combo.setCurrentText(current_display)
            self.font_slider.setValue(sm.get_setting("font_size", 9))
        else:
            self.font_slider.setValue(app.font().pointSize())

        def apply_now():
            # Map display back to key
            selected_display = self.theme_combo.currentText()
            selected_key = THEME_DISPLAY_TO_KEY.get(selected_display, "sur5ve")
            if hasattr(app, 'theme_manager'):
                app.theme_manager.apply_theme(selected_key, app)
            f = app.font()
            f.setPointSize(self.font_slider.value())
            app.setFont(f)
            if sm:
                sm.set_setting("current_theme", selected_key)
                sm.set_setting("font_size", self.font_slider.value())

        apply_btn.clicked.connect(apply_now)
        ok_btn.clicked.connect(lambda: (apply_now(), self.accept()))
        cancel_btn.clicked.connect(self.reject)



