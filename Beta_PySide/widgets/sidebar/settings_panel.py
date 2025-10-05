#!/usr/bin/env python3
"""
Settings Panel
UI panel for application settings and preferences
"""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QComboBox, QCheckBox,
    QSlider, QSpinBox, QFrame, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class SettingsPanel(QWidget):
    """Panel for application settings"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI components
        self.theme_combo: Optional[QComboBox] = None
        self.font_size_slider: Optional[QSlider] = None
        self.font_size_label: Optional[QLabel] = None
        self.virtualization_checkbox: Optional[QCheckBox] = None
        self.virtualization_threshold: Optional[QSpinBox] = None
        
        # Setup UI
        self._setup_ui()
        self._connect_signals()
        self._load_current_settings()
        
    def _setup_ui(self):
        """Setup the settings panel UI"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(12)
        
        # Appearance group
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QVBoxLayout(appearance_group)
        appearance_layout.setSpacing(12)
        appearance_layout.setContentsMargins(12, 12, 12, 12)
        
        # Theme selection
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Theme:")
        theme_layout.addWidget(theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems([
            "theme_1",
            "theme_2", 
            "theme_3",
            "theme_4"
        ])
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        theme_layout.addWidget(self.theme_combo)
        appearance_layout.addLayout(theme_layout)
        
        # Font size
        font_size_layout = QVBoxLayout()
        
        font_size_header = QHBoxLayout()
        font_size_header_label = QLabel("Font Size:")
        font_size_header.addWidget(font_size_header_label)
        
        self.font_size_label = QLabel("9")
        self.font_size_label.setMinimumWidth(20)
        self.font_size_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        font_size_header.addWidget(self.font_size_label)
        
        font_size_layout.addLayout(font_size_header)
        
        self.font_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_size_slider.setMinimum(8)
        self.font_size_slider.setMaximum(16)
        self.font_size_slider.setValue(9)
        self.font_size_slider.valueChanged.connect(self._on_font_size_changed)
        font_size_layout.addWidget(self.font_size_slider)
        
        appearance_layout.addLayout(font_size_layout)
        
        main_layout.addWidget(appearance_group)
        
        # Performance group
        performance_group = QGroupBox("Performance")
        performance_layout = QVBoxLayout(performance_group)
        performance_layout.setSpacing(12)
        performance_layout.setContentsMargins(12, 12, 12, 12)
        
        # Virtualization settings
        self.virtualization_checkbox = QCheckBox("Enable Message Virtualization")
        self.virtualization_checkbox.setChecked(True)
        self.virtualization_checkbox.toggled.connect(self._on_virtualization_toggled)
        performance_layout.addWidget(self.virtualization_checkbox)
        
        # Virtualization threshold
        threshold_layout = QHBoxLayout()
        threshold_label = QLabel("Threshold:")
        threshold_layout.addWidget(threshold_label)
        
        self.virtualization_threshold = QSpinBox()
        self.virtualization_threshold.setMinimum(10)
        self.virtualization_threshold.setMaximum(500)
        self.virtualization_threshold.setValue(50)
        self.virtualization_threshold.setSuffix(" messages")
        threshold_layout.addWidget(self.virtualization_threshold)
        
        performance_layout.addLayout(threshold_layout)
        
        # Performance info
        perf_info = QLabel("Virtualization improves performance with large conversations")
        perf_info.setStyleSheet("color: #888888; font-size: 10px;")
        perf_info.setWordWrap(True)
        performance_layout.addWidget(perf_info)
        
        main_layout.addWidget(performance_group)
        
        # Actions group
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.setSpacing(12)
        actions_layout.setContentsMargins(12, 12, 12, 12)
        
        # Reset settings button
        reset_button = QPushButton("Reset to Defaults")
        reset_button.setProperty("class", "secondary")
        reset_button.setMinimumHeight(34)
        reset_button.clicked.connect(self._reset_settings)
        actions_layout.addWidget(reset_button)
        
        # Export/Import buttons
        export_import_layout = QHBoxLayout()
        
        export_button = QPushButton("Export")
        export_button.clicked.connect(self._export_settings)
        export_import_layout.addWidget(export_button)
        
        import_button = QPushButton("Import")
        import_button.clicked.connect(self._import_settings)
        export_import_layout.addWidget(import_button)
        actions_layout.addLayout(export_import_layout)
        
        main_layout.addWidget(actions_group)
        
        # Information group
        info_group = QGroupBox("About")
        info_layout = QVBoxLayout(info_group)
        info_layout.setSpacing(12)
        info_layout.setContentsMargins(12, 12, 12, 12)
        
        app_info = QLabel("Beta Version AI Assistant v2.0.0")
        app_info.setStyleSheet("font-weight: bold; font-size: 11px;")
        info_layout.addWidget(app_info)
        
        framework_info = QLabel("Built with PySide6")
        framework_info.setStyleSheet("color: #888888; font-size: 10px;")
        info_layout.addWidget(framework_info)
        
        main_layout.addWidget(info_group)
        
        # Add stretch to push content to top
        main_layout.addStretch()
        
    def _connect_signals(self):
        """Connect signal handlers"""
        pass  # Signals already connected in _setup_ui
        
    def _load_current_settings(self):
        """Load current application settings"""
        try:
            app = QApplication.instance()
            if hasattr(app, 'settings_manager'):
                settings_manager = app.settings_manager
                
                # Load theme
                current_theme = settings_manager.get_setting("current_theme", "theme_1")
                index = self.theme_combo.findText(current_theme)
                if index >= 0:
                    self.theme_combo.setCurrentIndex(index)
                    
                # Load font size
                font_size = settings_manager.get_setting("font_size", 9)
                self.font_size_slider.setValue(font_size)
                self.font_size_label.setText(str(font_size))
                
                # Load virtualization settings
                virt_enabled = settings_manager.get_setting("enable_virtualization", True)
                self.virtualization_checkbox.setChecked(virt_enabled)
                
                virt_threshold = settings_manager.get_setting("virtualization_threshold", 50)
                self.virtualization_threshold.setValue(virt_threshold)
                
        except Exception as e:
            print(f"❌ Error loading settings: {e}")
            
    def _on_theme_changed(self, theme_name: str):
        """Handle theme change"""
        try:
            app = QApplication.instance()
            if hasattr(app, 'toggle_theme'):
                # Save theme setting
                if hasattr(app, 'settings_manager'):
                    app.settings_manager.set_setting("current_theme", theme_name)
                    
                # Apply theme
                if hasattr(app, 'theme_manager'):
                    app.theme_manager.apply_theme(theme_name, app)
                    
        except Exception as e:
            print(f"❌ Error changing theme: {e}")
            
    def _on_font_size_changed(self, value: int):
        """Handle font size change"""
        self.font_size_label.setText(str(value))
        
        try:
            # Update application font
            app = QApplication.instance()
            current_font = app.font()
            current_font.setPointSize(value)
            app.setFont(current_font)
            
            # Save setting
            if hasattr(app, 'settings_manager'):
                app.settings_manager.set_setting("font_size", value)
                
        except Exception as e:
            print(f"❌ Error changing font size: {e}")
            
    def _on_virtualization_toggled(self, enabled: bool):
        """Handle virtualization toggle"""
        self.virtualization_threshold.setEnabled(enabled)
        
        try:
            app = QApplication.instance()
            if hasattr(app, 'settings_manager'):
                app.settings_manager.set_setting("enable_virtualization", enabled)
                
        except Exception as e:
            print(f"❌ Error toggling virtualization: {e}")
            
    def _reset_settings(self):
        """Reset all settings to defaults"""
        try:
            app = QApplication.instance()
            if hasattr(app, 'settings_manager'):
                app.settings_manager.reset_settings()
                
                # Reload current settings
                self._load_current_settings()
                
                print("🔄 Settings reset to defaults")
                
        except Exception as e:
            print(f"❌ Error resetting settings: {e}")
            
    def _export_settings(self):
        """Export settings to file"""
        try:
            from PySide6.QtWidgets import QFileDialog
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Settings",
                "beta_settings.json",
                "JSON files (*.json);;All files (*)"
            )
            
            if file_path:
                app = QApplication.instance()
                if hasattr(app, 'settings_manager'):
                    import json
                    settings = app.settings_manager.get_all_settings()
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(settings, f, indent=2)
                        
                    print(f"📤 Settings exported to {file_path}")
                    
        except Exception as e:
            print(f"❌ Error exporting settings: {e}")
            
    def _import_settings(self):
        """Import settings from file"""
        try:
            from PySide6.QtWidgets import QFileDialog, QMessageBox
            
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Import Settings",
                "",
                "JSON files (*.json);;All files (*)"
            )
            
            if file_path:
                import json
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported_settings = json.load(f)
                    
                app = QApplication.instance()
                if hasattr(app, 'settings_manager'):
                    # Update settings
                    for key, value in imported_settings.items():
                        app.settings_manager.set_setting(key, value)
                        
                    app.settings_manager.save_settings()
                    
                    # Reload UI
                    self._load_current_settings()
                    
                    QMessageBox.information(
                        self,
                        "Import Complete",
                        "Settings imported successfully. Some changes may require restart."
                    )
                    
                    print(f"📥 Settings imported from {file_path}")
                    
        except Exception as e:
            print(f"❌ Error importing settings: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Import Failed",
                f"Failed to import settings: {str(e)}"
            )
            
    def refresh_settings(self):
        """Refresh settings display"""
        self._load_current_settings()
