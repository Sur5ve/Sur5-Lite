#!/usr/bin/env python3
"""
Settings Panel
UI panel for application settings and preferences

Includes cross-platform enhancement settings:
- Match system theme (auto dark/light mode)
- System tray integration
- Performance monitor toggle
- Notification preferences
"""

from typing import Optional

from utils.logger import create_module_logger
logger = create_module_logger(__name__)

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QComboBox, QCheckBox,
    QSlider, QSpinBox, QFrame, QApplication, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

# Import display mapping
try:
    from themes.theme_manager import THEME_KEY_TO_DISPLAY, THEME_DISPLAY_TO_KEY
except Exception:
    THEME_KEY_TO_DISPLAY = {
        "sur5ve": "Sur5ve",
    }
    THEME_DISPLAY_TO_KEY = {v: k for k, v in THEME_KEY_TO_DISPLAY.items()}


class SettingsPanel(QWidget):
    """Panel for application settings.
    
    Signals:
        system_tray_toggled: Emitted when system tray setting changes
        minimize_to_tray_toggled: Emitted when minimize to tray setting changes
        performance_monitor_toggled: Emitted when performance monitor setting changes
        notifications_toggled: Emitted when notification settings change
    """
    
    # Signals for settings changes that need immediate action
    system_tray_toggled = Signal(bool)
    minimize_to_tray_toggled = Signal(bool)
    performance_monitor_toggled = Signal(bool)
    notifications_toggled = Signal(bool)
    match_system_theme_toggled = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # appearance
        self.theme_combo: Optional[QComboBox] = None
        self.font_size_slider: Optional[QSlider] = None
        self.font_size_label: Optional[QLabel] = None
        self.match_system_theme_checkbox: Optional[QCheckBox] = None
        
        # interface
        self.system_tray_checkbox: Optional[QCheckBox] = None
        self.minimize_to_tray_checkbox: Optional[QCheckBox] = None
        self.performance_monitor_checkbox: Optional[QCheckBox] = None
        
        # notifications
        self.notify_complete_checkbox: Optional[QCheckBox] = None
        self.notify_only_minimized_checkbox: Optional[QCheckBox] = None
        
        # performance
        self.virtualization_checkbox: Optional[QCheckBox] = None
        self.virtualization_threshold: Optional[QSpinBox] = None
        
        # ui
        self._setup_ui()
        self._connect_signals()
        self._load_current_settings()
        
    def _setup_ui(self):
        """Setup the settings panel UI"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(12)
        
        # =========================================================
        # Appearance group
        # =========================================================
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QVBoxLayout(appearance_group)
        appearance_layout.setSpacing(12)
        appearance_layout.setContentsMargins(12, 12, 12, 12)
        
        # Theme selection
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Theme:")
        theme_layout.addWidget(theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEME_KEY_TO_DISPLAY.values()))
        self.theme_combo.currentTextChanged.connect(self._on_theme_display_changed)
        theme_layout.addWidget(self.theme_combo)
        appearance_layout.addLayout(theme_layout)
        
        # Match system theme checkbox
        self.match_system_theme_checkbox = QCheckBox("Match system theme")
        self.match_system_theme_checkbox.setToolTip(
            "Automatically switch between dark and light themes based on your OS settings"
        )
        self.match_system_theme_checkbox.toggled.connect(self._on_match_system_theme_toggled)
        appearance_layout.addWidget(self.match_system_theme_checkbox)
        
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
        
        # =========================================================
        # Interface group (NEW - Cross-Platform Enhancements)
        # =========================================================
        interface_group = QGroupBox("Interface")
        interface_layout = QVBoxLayout(interface_group)
        interface_layout.setSpacing(8)
        interface_layout.setContentsMargins(12, 12, 12, 12)
        
        # System tray checkbox
        self.system_tray_checkbox = QCheckBox("Show in system tray")
        self.system_tray_checkbox.setToolTip(
            "Show Sur5 icon in the system tray for quick access"
        )
        self.system_tray_checkbox.toggled.connect(self._on_system_tray_toggled)
        interface_layout.addWidget(self.system_tray_checkbox)
        
        # Minimize to tray checkbox
        self.minimize_to_tray_checkbox = QCheckBox("Minimize to tray on close")
        self.minimize_to_tray_checkbox.setToolTip(
            "When closing the window, minimize to system tray instead of quitting"
        )
        self.minimize_to_tray_checkbox.setEnabled(False)  # Enabled when tray is enabled
        self.minimize_to_tray_checkbox.toggled.connect(self._on_minimize_to_tray_toggled)
        interface_layout.addWidget(self.minimize_to_tray_checkbox)
        
        # Performance monitor checkbox
        self.performance_monitor_checkbox = QCheckBox("Show performance monitor")
        self.performance_monitor_checkbox.setToolTip(
            "Display CPU, RAM, and GPU usage in the status bar"
        )
        self.performance_monitor_checkbox.toggled.connect(self._on_performance_monitor_toggled)
        interface_layout.addWidget(self.performance_monitor_checkbox)
        
        main_layout.addWidget(interface_group)
        
        # =========================================================
        # Notifications group (NEW)
        # =========================================================
        notifications_group = QGroupBox("Notifications")
        notifications_layout = QVBoxLayout(notifications_group)
        notifications_layout.setSpacing(8)
        notifications_layout.setContentsMargins(12, 12, 12, 12)
        
        # Notify on generation complete
        self.notify_complete_checkbox = QCheckBox("Notify when generation completes")
        self.notify_complete_checkbox.setToolTip(
            "Show a system notification when Sur5 finishes generating a response"
        )
        self.notify_complete_checkbox.toggled.connect(self._on_notify_complete_toggled)
        notifications_layout.addWidget(self.notify_complete_checkbox)
        
        # Only when minimized
        self.notify_only_minimized_checkbox = QCheckBox("Only when minimized")
        self.notify_only_minimized_checkbox.setToolTip(
            "Only show notifications when Sur5 is minimized or in the background"
        )
        self.notify_only_minimized_checkbox.setEnabled(False)  # Enabled when notifications enabled
        self.notify_only_minimized_checkbox.toggled.connect(self._on_notify_only_minimized_toggled)
        notifications_layout.addWidget(self.notify_only_minimized_checkbox)
        
        # Note about notifications
        notify_info = QLabel("Requires system tray to be enabled")
        notify_info.setStyleSheet("color: #888888; font-size: 10px;")
        notifications_layout.addWidget(notify_info)
        
        main_layout.addWidget(notifications_group)
        
        # =========================================================
        # Performance group
        # =========================================================
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
        
        # =========================================================
        # Actions group
        # =========================================================
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
        
        # =========================================================
        # Information group
        # =========================================================
        info_group = QGroupBox("About")
        info_layout = QVBoxLayout(info_group)
        info_layout.setSpacing(12)
        info_layout.setContentsMargins(12, 12, 12, 12)
        
        app_info = QLabel("Sur5 v2.0.0")
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
        pass
        
    def _load_current_settings(self):
        """Load current application settings"""
        try:
            app = QApplication.instance()
            if hasattr(app, 'settings_manager'):
                settings_manager = app.settings_manager
                
                # Block signals during loading to prevent cascading updates
                self._block_all_signals(True)
                
                # Load theme (key) and set display
                current_theme_key = settings_manager.get_setting("current_theme", "sur5ve")
                current_display = THEME_KEY_TO_DISPLAY.get(current_theme_key, "Sur5ve")
                index = self.theme_combo.findText(current_display)
                if index >= 0:
                    self.theme_combo.setCurrentIndex(index)
                
                # Load match system theme
                match_system = settings_manager.get_setting("match_system_theme", False)
                self.match_system_theme_checkbox.setChecked(match_system)
                self.theme_combo.setEnabled(not match_system)
                    
                # Load font size
                font_size = settings_manager.get_setting("font_size", 9)
                self.font_size_slider.setValue(font_size)
                self.font_size_label.setText(str(font_size))
                
                # Load interface settings
                show_tray = settings_manager.get_setting("show_in_system_tray", False)
                self.system_tray_checkbox.setChecked(show_tray)
                
                minimize_tray = settings_manager.get_setting("minimize_to_tray", False)
                self.minimize_to_tray_checkbox.setChecked(minimize_tray)
                self.minimize_to_tray_checkbox.setEnabled(show_tray)
                
                show_perf = settings_manager.get_setting("show_performance_monitor", False)
                self.performance_monitor_checkbox.setChecked(show_perf)
                
                # Load notification settings
                notify_complete = settings_manager.get_setting("notify_generation_complete", False)
                self.notify_complete_checkbox.setChecked(notify_complete)
                
                notify_minimized = settings_manager.get_setting("notify_only_minimized", True)
                self.notify_only_minimized_checkbox.setChecked(notify_minimized)
                self.notify_only_minimized_checkbox.setEnabled(notify_complete)
                
                # Load virtualization settings
                virt_enabled = settings_manager.get_setting("enable_virtualization", True)
                self.virtualization_checkbox.setChecked(virt_enabled)
                
                virt_threshold = settings_manager.get_setting("virtualization_threshold", 50)
                self.virtualization_threshold.setValue(virt_threshold)
                
                # Unblock signals
                self._block_all_signals(False)
                
        except Exception as e:
            print(f"❌ Error loading settings: {e}")
            self._block_all_signals(False)
    
    def _block_all_signals(self, block: bool):
        """Block or unblock signals for all settings widgets."""
        widgets = [
            self.theme_combo,
            self.match_system_theme_checkbox,
            self.font_size_slider,
            self.system_tray_checkbox,
            self.minimize_to_tray_checkbox,
            self.performance_monitor_checkbox,
            self.notify_complete_checkbox,
            self.notify_only_minimized_checkbox,
            self.virtualization_checkbox,
            self.virtualization_threshold,
        ]
        for widget in widgets:
            if widget:
                widget.blockSignals(block)
            
    def _on_theme_display_changed(self, display_name: str):
        """Handle theme change from display label"""
        try:
            app = QApplication.instance()
            theme_key = THEME_DISPLAY_TO_KEY.get(display_name, "sur5ve")
            # Save theme setting
            if hasattr(app, 'settings_manager'):
                app.settings_manager.set_setting("current_theme", theme_key)
            # Apply theme
            if hasattr(app, 'theme_manager'):
                app.theme_manager.apply_theme(theme_key, app)
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
    
    def _on_match_system_theme_toggled(self, enabled: bool):
        """Handle match system theme toggle"""
        self.theme_combo.setEnabled(not enabled)
        
        try:
            app = QApplication.instance()
            if hasattr(app, 'settings_manager'):
                app.settings_manager.set_setting("match_system_theme", enabled)
            
            # If enabled, detect and apply system theme
            if enabled:
                try:
                    from utils.system_theme_detector import get_recommended_sur5_theme
                    recommended_theme = get_recommended_sur5_theme()
                    
                    if hasattr(app, 'theme_manager'):
                        app.theme_manager.apply_theme(recommended_theme, app)
                    if hasattr(app, 'settings_manager'):
                        app.settings_manager.set_setting("current_theme", recommended_theme)
                    
                    # Update combo display
                    display = THEME_KEY_TO_DISPLAY.get(recommended_theme, "Sur5 Dark")
                    index = self.theme_combo.findText(display)
                    if index >= 0:
                        self.theme_combo.blockSignals(True)
                        self.theme_combo.setCurrentIndex(index)
                        self.theme_combo.blockSignals(False)
                    
                    logger.info(f"Auto-matched system theme: {recommended_theme}")
                except ImportError:
                    logger.debug("System theme detector not available")
            
            self.match_system_theme_toggled.emit(enabled)
                
        except Exception as e:
            logger.error(f"Error toggling match system theme: {e}")
    
    def _on_system_tray_toggled(self, enabled: bool):
        """Handle system tray toggle"""
        self.minimize_to_tray_checkbox.setEnabled(enabled)
        
        if not enabled:
            self.minimize_to_tray_checkbox.setChecked(False)
        
        try:
            app = QApplication.instance()
            if hasattr(app, 'settings_manager'):
                app.settings_manager.set_setting("show_in_system_tray", enabled)
            
            self.system_tray_toggled.emit(enabled)
                
        except Exception as e:
            print(f"❌ Error toggling system tray: {e}")
    
    def _on_minimize_to_tray_toggled(self, enabled: bool):
        """Handle minimize to tray toggle"""
        try:
            app = QApplication.instance()
            if hasattr(app, 'settings_manager'):
                app.settings_manager.set_setting("minimize_to_tray", enabled)
            
            self.minimize_to_tray_toggled.emit(enabled)
                
        except Exception as e:
            print(f"❌ Error toggling minimize to tray: {e}")
    
    def _on_performance_monitor_toggled(self, enabled: bool):
        """Handle performance monitor toggle"""
        try:
            app = QApplication.instance()
            if hasattr(app, 'settings_manager'):
                app.settings_manager.set_setting("show_performance_monitor", enabled)
            
            self.performance_monitor_toggled.emit(enabled)
                
        except Exception as e:
            print(f"❌ Error toggling performance monitor: {e}")
    
    def _on_notify_complete_toggled(self, enabled: bool):
        """Handle notify on generation complete toggle"""
        self.notify_only_minimized_checkbox.setEnabled(enabled)
        
        try:
            app = QApplication.instance()
            if hasattr(app, 'settings_manager'):
                app.settings_manager.set_setting("notify_generation_complete", enabled)
            
            self.notifications_toggled.emit(enabled)
                
        except Exception as e:
            print(f"❌ Error toggling notifications: {e}")
    
    def _on_notify_only_minimized_toggled(self, enabled: bool):
        """Handle notify only when minimized toggle"""
        try:
            app = QApplication.instance()
            if hasattr(app, 'settings_manager'):
                app.settings_manager.set_setting("notify_only_minimized", enabled)
                
        except Exception as e:
            print(f"❌ Error toggling notify only minimized: {e}")
            
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
                "sur5_settings.json",
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
