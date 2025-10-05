#!/usr/bin/env python3
"""
Model Panel
UI panel for model loading and configuration
"""

import os
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QComboBox, QCheckBox,
    QFileDialog, QProgressBar, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Slot

from services.model_service import ModelService


class ModelPanel(QWidget):
    """Panel for model management and configuration"""
    
    def __init__(self, model_service: ModelService, parent=None):
        super().__init__(parent)
        
        # Service reference
        self.model_service = model_service
        
        # UI components
        self.model_status_label: Optional[QLabel] = None
        self.load_button: Optional[QPushButton] = None
        self.unload_button: Optional[QPushButton] = None
        self.ram_combo: Optional[QComboBox] = None
        self.thinking_checkbox: Optional[QCheckBox] = None
        self.progress_bar: Optional[QProgressBar] = None
        
        # Setup UI
        self._setup_ui()
        self._connect_signals()
        self._update_ui_state()
        
    def _setup_ui(self):
        """Setup the model panel UI"""
        # Main layout - zero margins/spacing; ResponsiveSidebar will manage
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Model group
        model_group = QGroupBox("Model")
        model_layout = QVBoxLayout(model_group)
        model_layout.setSpacing(12)
        model_layout.setContentsMargins(12, 12, 12, 12)
        
        # Model status
        self.model_status_label = QLabel("No model loaded")
        self.model_status_label.setAccessibleName("Model status")
        self.model_status_label.setStyleSheet("color: #888888; font-size: 12px;")
        self.model_status_label.setWordWrap(True)
        model_layout.addWidget(self.model_status_label)
        
        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximum(100)
        model_layout.addWidget(self.progress_bar)
        
        # Button layout (simple row)
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)

        self.load_button = QPushButton("Choose Model")
        self.load_button.setAccessibleName("Choose model")
        self.load_button.setProperty("class", "primary")
        self.load_button.setMinimumHeight(34)
        self.load_button.clicked.connect(self._load_model)
        button_layout.addWidget(self.load_button)

        self.unload_button = QPushButton("Unload")
        self.unload_button.setAccessibleName("Unload model")
        self.unload_button.setProperty("class", "danger")
        self.unload_button.setMinimumHeight(34)
        self.unload_button.clicked.connect(self._unload_model)
        self.unload_button.setEnabled(False)
        button_layout.addWidget(self.unload_button)

        model_layout.addLayout(button_layout)
        
        main_layout.addWidget(model_group)
        
        # Configuration group
        self.config_group = config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(10)
        config_layout.setContentsMargins(12, 12, 12, 12)
        
        # RAM configuration row (presets)
        ram_layout = QHBoxLayout()
        ram_layout.setContentsMargins(0, 0, 0, 0)
        ram_layout.setSpacing(8)
        ram_label = QLabel("RAM Config:")
        ram_layout.addWidget(ram_label)

        try:
            from widgets.common.no_wheel_combo import NoWheelComboBox
            self.ram_combo = NoWheelComboBox()
        except Exception:
            self.ram_combo = QComboBox()
        self.ram_combo.setMinimumHeight(34)
        self.ram_combo.setAccessibleName("RAM/Context preset")
        self.ram_combo.setAccessibleDescription("Choose memory/context configuration for the model")
        self.ram_combo.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        ram_configs = self.model_service.get_ram_configurations()
        self.ram_combo.clear()
        for preset_name, meta in ram_configs.items():
            self.ram_combo.addItem(f"{preset_name}  •  {meta.get('label', '')}", preset_name)
        # Default to current preset
        current_preset = getattr(self.model_service, 'get_ram_preset', lambda: 'Balanced')()
        # Find by data role
        for i in range(self.ram_combo.count()):
            if self.ram_combo.itemData(i) == current_preset:
                self.ram_combo.setCurrentIndex(i)
                break
        # React only to explicit user selections from the popup (prevents accidental wheel changes)
        self.ram_combo.activated.connect(self._on_ram_preset_changed)
        ram_layout.addWidget(self.ram_combo)

        config_layout.addLayout(ram_layout)
        
        # Thinking mode
        # Thinking mode row with tooltip and optional More Info toggle
        thinking_row = QHBoxLayout()
        thinking_row.setContentsMargins(0, 0, 0, 0)
        thinking_row.setSpacing(8)

        self.thinking_checkbox = QCheckBox("Enable Thinking Mode")
        self.thinking_checkbox.setChecked(True)
        self.thinking_checkbox.setToolTip("Shows AI reasoning process. UI-only; does not affect model context.")
        self.thinking_checkbox.toggled.connect(self._on_thinking_mode_changed)
        thinking_row.addWidget(self.thinking_checkbox)

        from PySide6.QtWidgets import QToolButton
        self.more_info_btn = QToolButton()
        self.more_info_btn.setText("More info ▾")
        self.more_info_btn.setCheckable(True)
        thinking_row.addWidget(self.more_info_btn)
        thinking_row.addStretch(1)
        config_layout.addLayout(thinking_row)
        
        # Configuration info - hidden by default
        # Note: "More info" is NOT required for ADA WCAG 2.1/2.2 compliance
        # The tooltip on the checkbox already provides the necessary information
        config_info = QLabel("Thinking mode shows AI reasoning process")
        config_info.setStyleSheet("color: #888888; font-size: 11px;")
        config_info.setWordWrap(True)
        config_info.setVisible(False)
        config_info.setContentsMargins(0, 12, 0, 0)  # Increased top margin to prevent overlap
        self.more_info_btn.toggled.connect(config_info.setVisible)
        config_layout.addWidget(config_info)
        
        # Store reference for responsive layout
        self.config_info_label = config_info
        
        main_layout.addWidget(config_group)
        
        # Model info group
        self.info_group = info_group = QGroupBox("Information")
        info_layout = QVBoxLayout(info_group)
        info_layout.setSpacing(12)
        info_layout.setContentsMargins(12, 12, 12, 12)
        
        self.info_label = QLabel("No model information available")
        self.info_label.setStyleSheet("color: #888888; font-size: 11px;")
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        
        main_layout.addWidget(info_group)
        
        # No stretch - ResponsiveSidebar manages spacing
        
    def _connect_signals(self):
        """Connect model service signals"""
        self.model_service.model_loaded.connect(self._on_model_loaded)
        self.model_service.model_error.connect(self._on_model_error)
        self.model_service.loading_progress.connect(self._on_loading_progress)
        
    def _load_model(self):
        """Load a model file"""
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("Model files (*.gguf *.bin *.safetensors);;All files (*)")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                model_path = selected_files[0]
                # Use preset key (itemData) to avoid label parsing issues
                preset_key = self.ram_combo.currentData()

                # Do NOT load synchronously. Set the path and unload existing
                # to follow lazy-load on first message (Tkinter pattern).
                try:
                    # Persist RAM preset first (deferred apply)
                    if hasattr(self.model_service, 'set_ram_preset') and preset_key:
                        self.model_service.set_ram_preset(preset_key)

                    # Unload any existing model
                    if self.model_service.is_model_loaded():
                        self.model_service.unload_model()

                    # Set new model path (will load on first use)
                    self.model_service.set_model_path(model_path)
                    self.model_status_label.setText(f"Model selected: {os.path.basename(model_path)} (will load on first use)")
                    self.model_status_label.setStyleSheet("color: #3498db; font-size: 12px;")
                    self.progress_bar.setVisible(False)
                    self.load_button.setEnabled(True)
                    # Enable composer to allow first prompt to trigger load
                    from widgets.chat.composer import MessageComposer
                except Exception as e:
                    self.progress_bar.setVisible(False)
                    self.load_button.setEnabled(True)
                    self._on_model_error(str(e))
                    
    def _unload_model(self):
        """Unload the current model"""
        self.model_service.unload_model()
        self._update_ui_state()
        
    def _on_ram_preset_changed(self):
        """Handle RAM preset change"""
        preset = self.ram_combo.currentData()
        if hasattr(self.model_service, 'set_ram_preset'):
            self.model_service.set_ram_preset(preset)
        # Update status label to reflect deferred apply
        label_map = self.model_service.get_ram_configurations().get(preset, {})
        pretty = f"{preset} • {label_map.get('label','')} (applies on next use)"
        if self.model_status_label:
            self.model_status_label.setText(pretty)
            self.model_status_label.setStyleSheet("color: #3498db; font-size: 12px;")
        
    def _on_thinking_mode_changed(self, enabled: bool):
        """Handle thinking mode toggle"""
        self.model_service.set_thinking_mode(enabled)
        
    @Slot(str, str)
    def _on_model_loaded(self, model_name: str, model_path: str):
        """Handle model loaded event"""
        self.model_status_label.setText(f"✅ Loaded: {model_name}")
        self.model_status_label.setStyleSheet("color: #27ae60; font-size: 12px; font-weight: bold;")
        
        self.progress_bar.setVisible(False)
        self.load_button.setEnabled(True)
        self.unload_button.setEnabled(True)
        
        # Update model info
        self._update_model_info()
        
    @Slot(str)
    def _on_model_error(self, error_message: str):
        """Handle model error"""
        self.model_status_label.setText(f"❌ Error: {error_message}")
        self.model_status_label.setStyleSheet("color: #e74c3c; font-size: 12px; font-weight: bold;")
        
        self.progress_bar.setVisible(False)
        self.load_button.setEnabled(True)
        self.unload_button.setEnabled(False)
        
    @Slot(str, int)
    def _on_loading_progress(self, message: str, progress: int):
        """Handle loading progress"""
        self.progress_bar.setValue(progress)
        self.model_status_label.setText(f"🔄 {message}")
        self.model_status_label.setStyleSheet("color: #3498db; font-size: 12px;")
        
    def _update_ui_state(self):
        """Update UI state based on model service"""
        is_loaded = self.model_service.is_model_loaded()
        
        self.load_button.setEnabled(not is_loaded)
        self.unload_button.setEnabled(is_loaded)
        
        if is_loaded:
            model_name = self.model_service.get_current_model_name()
            self.model_status_label.setText(f"✅ Loaded: {model_name}")
            self.model_status_label.setStyleSheet("color: #27ae60; font-size: 12px; font-weight: bold;")
            self._update_model_info()
        else:
            self.model_status_label.setText("No model loaded")
            self.model_status_label.setStyleSheet("color: #888888; font-size: 12px;")
            self.info_label.setText("No model information available")
            
        # Update thinking mode checkbox
        thinking_enabled = self.model_service.get_thinking_mode()
        self.thinking_checkbox.setChecked(thinking_enabled)
        
        # Hide progress bar if not loading
        if is_loaded or not is_loaded:
            self.progress_bar.setVisible(False)
            
    def _update_model_info(self):
        """Update model information display"""
        try:
            model_info = self.model_service.get_model_info()
            
            info_lines = []
            info_lines.append(f"Context: {model_info.get('context_size', 'Unknown')}")
            info_lines.append(f"RAM Config: {model_info.get('ram_config', 'Unknown')}")
            info_lines.append(f"Thinking: {'Yes' if model_info.get('thinking_enabled', False) else 'No'}")
            
            # Generation stats
            stats = model_info.get('generation_stats', {})
            if stats.get('total_generations', 0) > 0:
                info_lines.append(f"Generations: {stats['total_generations']}")
                info_lines.append(f"Total Tokens: {stats['total_tokens']}")
                
            self.info_label.setText("\n".join(info_lines))
            
        except Exception as e:
            self.info_label.setText(f"Error getting model info: {str(e)}")
            
    def refresh_info(self):
        """Refresh model information display"""
        if self.model_service.is_model_loaded():
            self._update_model_info()
