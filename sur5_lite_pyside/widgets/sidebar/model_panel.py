#!/usr/bin/env python3
"""
Model Panel - UI panel for model loading and configuration

Sur5 Lite — Open Source Edge AI
Copyright (c) 2024-2026 Sur5ve LLC
Licensed under MIT License
https://sur5ve.com
"""

import os
from typing import Optional, Dict, Any

from utils.logger import create_module_logger
logger = create_module_logger(__name__)

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QPushButton, QLabel, QComboBox, QCheckBox,
    QFileDialog, QProgressBar, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Slot, QEvent

from services.model_service import ModelService


class ModelPanel(QWidget):
    """Panel for model management and configuration"""
    
    def __init__(self, model_service: ModelService, parent=None):
        super().__init__(parent)
        
        # Service reference
        self.model_service = model_service
        
        # refs
        self.model_status_label: Optional[QLabel] = None
        self.load_button: Optional[QPushButton] = None
        self.unload_button: Optional[QPushButton] = None
        self.ram_combo: Optional[QComboBox] = None
        self.thinking_checkbox: Optional[QCheckBox] = None
        self.progress_bar: Optional[QProgressBar] = None
        
        # ui
        self._setup_ui()
        self._connect_signals()
        self._update_ui_state()
        
    def _setup_ui(self):
        """Setup the model panel UI"""
        # Main layout - zero margins/spacing; ResponsiveSidebar will manage
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ============================================================
        # 1. Configuration group (MOVED TO TOP) - COMPACT VERTICAL LAYOUT
        # ============================================================
        self.config_group = config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(4)  # Tight spacing
        config_layout.setContentsMargins(8, 6, 8, 6)  # Minimal margins
        
        # --- Row 1: RAM Config label ---
        self.ram_label = QLabel("RAM Config:")
        self.ram_label.setStyleSheet("font-size: 10px; color: #aaa;")
        self.ram_label.setFixedHeight(14)
        config_layout.addWidget(self.ram_label)
        
        # --- Row 2: RAM Combo (full width, compact) ---
        try:
            from widgets.common.no_wheel_combo import NoWheelComboBox
            self.ram_combo = NoWheelComboBox()
        except Exception:
            self.ram_combo = QComboBox()
        self.ram_combo.setFixedHeight(22)
        self.ram_combo.setStyleSheet("QComboBox { font-size: 10px; padding: 1px 4px; }")
        self.ram_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.ram_combo.setAccessibleName("RAM/Context preset")
        self.ram_combo.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        
        ram_configs = self.model_service.get_ram_configurations()
        self.ram_combo.clear()
        for preset_name, meta in ram_configs.items():
            self.ram_combo.addItem(f"{preset_name}  •  {meta.get('label', '')}", preset_name)
            
        current_preset = getattr(self.model_service, 'get_ram_preset', lambda: 'Balanced')()
        for i in range(self.ram_combo.count()):
            if self.ram_combo.itemData(i) == current_preset:
                self.ram_combo.setCurrentIndex(i)
                break
                
        self.ram_combo.activated.connect(self._on_ram_preset_changed)
        config_layout.addWidget(self.ram_combo)
        
        # --- Backend Selection ---
        self.backend_label = QLabel("Inference Backend:")
        self.backend_label.setStyleSheet("font-size: 10px; color: #aaa;")
        self.backend_label.setFixedHeight(14)
        config_layout.addWidget(self.backend_label)
        
        try:
            from widgets.common.no_wheel_combo import NoWheelComboBox
            self.backend_combo = NoWheelComboBox()
        except Exception:
            self.backend_combo = QComboBox()
        self.backend_combo.setFixedHeight(22)
        self.backend_combo.setStyleSheet("QComboBox { font-size: 10px; padding: 1px 4px; }")
        self.backend_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.backend_combo.setAccessibleName("Inference backend")
        self.backend_combo.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.backend_combo.setToolTip(
            "Select inference backend:\n"
            "• Auto-detect: Choose based on model format\n"
            "• llama.cpp: Standard GGUF models (2-8 bit)\n"
            "• BitNet.cpp: 1-bit quantized models (faster, smaller)"
        )
        
        # Add backend options
        self.backend_combo.addItem("Auto-detect", "auto")
        self.backend_combo.addItem("llama.cpp", "llama.cpp")
        self.backend_combo.addItem("BitNet.cpp (coming soon)", "bitnet")
        
        # Disable BitNet option until bindings are available
        self.backend_combo.model().item(2).setEnabled(False)
        
        config_layout.addWidget(self.backend_combo)
        
        # --- Row 3: Auto-Detect (left) + Thinking Mode (right) ---
        controls_row = QHBoxLayout()
        controls_row.setContentsMargins(0, 10, 4, 0)  # Top margin + right padding
        controls_row.setSpacing(4)
        
        self.detect_button = QPushButton("Auto-Detect")
        self.detect_button.setToolTip("Detect optimal RAM preset")
        self.detect_button.setFixedHeight(18)
        self.detect_button.setFixedWidth(70)
        self.detect_button.setStyleSheet("QPushButton { font-size: 9px; padding: 1px 4px; }")
        self.detect_button.clicked.connect(self._on_auto_detect_preset)
        controls_row.addWidget(self.detect_button)
        
        controls_row.addStretch()  # Push Thinking Mode to the right
        
        self.thinking_checkbox = QCheckBox("Thinking Mode")
        self.thinking_checkbox.setChecked(True)
        self.thinking_checkbox.setToolTip("Show AI reasoning process")
        self.thinking_checkbox.setStyleSheet("""
            QCheckBox { 
                font-size: 10px; 
                spacing: 6px;
                padding-left: 4px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 2px solid #20B2AA;
                border-radius: 3px;
                background-color: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #20B2AA;
            }
        """)
        self.thinking_checkbox.setMinimumWidth(105)
        self.thinking_checkbox.toggled.connect(self._on_thinking_mode_changed)
        controls_row.addWidget(self.thinking_checkbox)
        
        config_layout.addLayout(controls_row)
        
        # --- Row 5: More info toggle (below Thinking Mode) ---
        self.more_info_btn = QPushButton("ℹ More info")
        self.more_info_btn.setCheckable(True)
        self.more_info_btn.setFlat(True)
        self.more_info_btn.setFixedHeight(16)
        self.more_info_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.more_info_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                color: #555;
                text-align: left;
                padding: 0;
                font-size: 9px;
            }
            QPushButton:hover { color: #888; }
            QPushButton:checked { color: #20B2AA; }
        """)
        self.more_info_btn.toggled.connect(self._toggle_more_info)
        config_layout.addWidget(self.more_info_btn)
        
        # --- Row 6: Collapsible info panel (hidden by default) ---
        self.config_info_frame = QFrame()
        self.config_info_frame.setObjectName("config_info_frame")
        self.config_info_frame.setStyleSheet("""
            QFrame#config_info_frame {
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        info_layout = QVBoxLayout(self.config_info_frame)
        info_layout.setContentsMargins(6, 4, 6, 4)
        info_layout.setSpacing(0)
        
        # Info content - plain text, visible
        self.config_info_label = QLabel(
            "RAM Config: Context size\n"
            "Auto-Detect: Best preset\n"
            "Thinking: Show reasoning"
        )
        self.config_info_label.setWordWrap(True)
        self.config_info_label.setStyleSheet("color: #999; font-size: 9px; background: transparent;")
        info_layout.addWidget(self.config_info_label)
        
        self.config_info_frame.setVisible(False)
        config_layout.addWidget(self.config_info_frame)
        
        # For compatibility
        self._thinking_layout_mode = "simple"
        
        main_layout.addWidget(config_group)
        
        # ============================================================
        # 2. Model info group (MOVED TO MIDDLE)
        # ============================================================
        self.info_group = info_group = QGroupBox("Information")
        info_layout = QVBoxLayout(info_group)
        
        # Use logical units based on font metrics for DPI-aware spacing
        fm = self.fontMetrics()
        base_unit = fm.height()
        logical_margin = int(base_unit * 0.75)
        logical_spacing = int(base_unit * 0.75)
        
        info_layout.setSpacing(logical_spacing)
        info_layout.setContentsMargins(logical_margin, logical_margin, logical_margin, logical_margin)
        
        self.info_label = QLabel("No model information available")
        self.info_label.setStyleSheet("color: #888888; font-size: 11px;")
        self.info_label.setWordWrap(True)
        self.info_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.info_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        info_layout.addWidget(self.info_label)
        
        main_layout.addWidget(info_group)
        
        # ============================================================
        # 3. Model group (MOVED TO BOTTOM)
        # ============================================================
        model_group = QGroupBox("Model")
        model_layout = QVBoxLayout(model_group)
        model_layout.setSpacing(8)
        model_layout.setContentsMargins(8, 8, 8, 8)
        
        # Model status with checkbox
        self.model_status_label = QLabel("No model loaded")
        self.model_status_label.setAccessibleName("Model status")
        self.model_status_label.setStyleSheet("color: #888888; font-size: 11px;")
        self.model_status_label.setWordWrap(True)
        model_layout.addWidget(self.model_status_label)
        
        # Model dropdown selector
        try:
            from widgets.common.no_wheel_combo import NoWheelComboBox
            self.model_combo = NoWheelComboBox()
        except Exception:
            self.model_combo = QComboBox()
        self.model_combo.setFixedHeight(24)
        self.model_combo.setStyleSheet("QComboBox { font-size: 10px; padding: 2px 4px; }")
        self.model_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.model_combo.setAccessibleName("Select model")
        self.model_combo.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.model_combo.setToolTip("Select a model from your models folder")
        self._populate_model_dropdown()
        self.model_combo.activated.connect(self._on_model_selected)
        model_layout.addWidget(self.model_combo)
        
        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximum(100)
        model_layout.addWidget(self.progress_bar)
        
        # Button layout (simple row) - compact
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(6)

        self.load_button = QPushButton("Choose Model")
        self.load_button.setAccessibleName("Choose model file")
        self.load_button.setToolTip("Browse for a .gguf model file")
        self.load_button.setProperty("class", "primary")
        self.load_button.setFixedHeight(26)
        self.load_button.setStyleSheet("QPushButton { font-size: 10px; padding: 2px 8px; }")
        self.load_button.clicked.connect(self._load_model)
        button_layout.addWidget(self.load_button)

        self.unload_button = QPushButton("Unload")
        self.unload_button.setAccessibleName("Unload model")
        self.unload_button.setProperty("class", "danger")
        self.unload_button.setFixedHeight(26)
        self.unload_button.setStyleSheet("QPushButton { font-size: 10px; padding: 2px 8px; }")
        self.unload_button.clicked.connect(self._unload_model)
        self.unload_button.setEnabled(False)
        button_layout.addWidget(self.unload_button)

        model_layout.addLayout(button_layout)
        
        main_layout.addWidget(model_group)
        
    def resizeEvent(self, event):
        """Handle resize events to adjust layout"""
        super().resizeEvent(event)
        # Note: _reflow_configuration removed - using simple VBoxLayout now
        self._update_info_label_width()
    
    def changeEvent(self, event):
        """Handle screen/DPI changes for per-monitor DPI awareness"""
        try:
            if event.type() == QEvent.Type.ScreenChangeEvent:
                # Screen DPI changed (dragged to different monitor)
                self._update_logical_sizing()
        except Exception as e:
            # Ignore errors during screen change events (macOS compatibility)
            pass
        finally:
            super().changeEvent(event)

    def _reflow_configuration(self):
        """DEPRECATED: No longer used - using simple VBoxLayout now.
        
        This method was previously used for dynamic grid reflow but caused
        scaling issues. Kept as stub for easy reversion if needed.
        To restore old behavior, see git history.
        """
        pass
    
    def _update_info_label_width(self):
        """Update info label max width to prevent overflow beyond card boundaries"""
        if not hasattr(self, 'info_label') or not hasattr(self, 'info_group'):
            return
        
        # Get the info group's content width (excluding padding/borders)
        info_group_width = self.info_group.width()
        
        # Account for layout margins
        layout = self.info_group.layout()
        if layout:
            margins = layout.contentsMargins()
            content_width = info_group_width - margins.left() - margins.right()
            # Add a small safety margin to prevent touching rounded corners
            safe_width = max(50, content_width - 4)
            self.info_label.setMaximumWidth(safe_width)
    
    def _update_logical_sizing(self):
        """Update logical unit-based sizing after DPI or screen change"""
        if not hasattr(self, 'info_group'):
            return
        
        # Recalculate logical units based on current font metrics
        fm = self.fontMetrics()
        base_unit = fm.height()
        logical_margin = int(base_unit * 0.75)
        logical_spacing = int(base_unit * 0.75)
        
        # Update info group layout margins and spacing
        layout = self.info_group.layout()
        if layout:
            layout.setContentsMargins(logical_margin, logical_margin, logical_margin, logical_margin)
            layout.setSpacing(logical_spacing)
        
        # Also update Configuration group for consistent spacing
        if hasattr(self, 'config_group'):
            config_layout = self.config_group.layout()
            if config_layout:
                # Config group uses slightly more generous spacing
                config_margin = int(base_unit * 0.9)
                config_spacing = int(base_unit * 0.6)
                config_layout.setContentsMargins(config_margin, config_margin, config_margin, config_margin)
                config_layout.setSpacing(config_spacing)
        
        # Trigger width recalculation
        self._update_info_label_width()
        
    def _connect_signals(self):
        """Connect model service signals"""
        self.model_service.model_loaded.connect(self._on_model_loaded)
        self.model_service.model_error.connect(self._on_model_error)
        self.model_service.loading_progress.connect(self._on_loading_progress)
    
    def _populate_model_dropdown(self):
        """Scan models folder and populate the dropdown"""
        self.model_combo.clear()
        self.model_combo.addItem("-- Select a model --", "")
        
        from pathlib import Path
        import sys
        
        # Priority 1: Environment variable (set by launcher)
        models_root = os.environ.get('SUR5_MODELS_PATH')
        
        # Priority 2: Try portable_paths
        if not models_root or not os.path.exists(models_root):
            try:
                from utils.portable_paths import get_models_root
                models_root = str(get_models_root())
            except ImportError:
                pass
        
        # Priority 3: Common locations relative to app
        if not models_root or not os.path.exists(models_root):
            if getattr(sys, 'frozen', False):
                app_root = Path(sys.executable).parent
            else:
                app_root = Path(__file__).parent.parent.parent
            
            # Check multiple locations
            candidates = [
                app_root / "Models",
                app_root / "models", 
                app_root.parent / "Models",  # Demo structure: ../Models
                app_root.parent / "models",
            ]
            for candidate in candidates:
                if candidate.exists():
                    models_root = str(candidate)
                    break
        
        if not models_root or not os.path.exists(models_root):
            logger.warning(f"Models folder not found: {models_root}")
            return
        
        # Scan for .gguf files
        from pathlib import Path
        models_path = Path(models_root)
        gguf_files = sorted(models_path.glob("*.gguf"), key=lambda f: f.name.lower())
        
        for model_file in gguf_files:
            # Get file size for display
            size_mb = model_file.stat().st_size / (1024 * 1024)
            if size_mb >= 1024:
                size_str = f"{size_mb/1024:.1f} GB"
            else:
                size_str = f"{size_mb:.0f} MB"
            
            # Display name with size
            display_name = f"{model_file.stem}  ({size_str})"
            self.model_combo.addItem(display_name, str(model_file))
        
        # Select current model if loaded
        current_path = getattr(self.model_service, 'current_model_path', None)
        if current_path:
            for i in range(self.model_combo.count()):
                if self.model_combo.itemData(i) == current_path:
                    self.model_combo.setCurrentIndex(i)
                    break
        
        logger.info(f"Populated model dropdown with {len(gguf_files)} models from {models_root}")
    
    def _on_model_selected(self, index: int):
        """Handle model selection from dropdown"""
        model_path = self.model_combo.itemData(index)
        if not model_path:
            return  # "Select a model" placeholder selected
        
        # Get current preset
        preset_key = self.ram_combo.currentData()
        
        try:
            # Persist RAM preset first
            if hasattr(self.model_service, 'set_ram_preset') and preset_key:
                self.model_service.set_ram_preset(preset_key)
            
            # Unload any existing model
            if self.model_service.is_model_loaded():
                self.model_service.unload_model()
            
            # Set new model path (lazy load on first use)
            self.model_service.set_model_path(model_path)
            model_name = os.path.basename(model_path)
            self.model_status_label.setText(f"✓ Loaded: {model_name}")
            self.model_status_label.setStyleSheet("color: #20B2AA; font-size: 11px;")
            
            # Update thinking UI state
            self._update_thinking_ui_state()
            
            logger.info(f"Model selected from dropdown: {model_name}")
            
        except Exception as e:
            logger.error(f"Error selecting model: {e}")
            self._on_model_error(str(e))
    
    def refresh_model_dropdown(self):
        """Public method to refresh the model dropdown (e.g., after adding new models)"""
        self._populate_model_dropdown()
        
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
                    
                    # Update thinking checkbox state immediately when model is selected
                    self._update_thinking_ui_state()
                    
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
        # Update info display to show new context size
        self._update_model_info()
    
    def _on_auto_detect_preset(self):
        """Auto-detect optimal preset based on hardware"""
        from sur5_lite_pyside.services.model_engine import detect_optimal_preset, save_settings, load_settings
        from PySide6.QtWidgets import QMessageBox
        
        detected_preset, reasoning = detect_optimal_preset()
        
        # Show detection results
        msg = QMessageBox(self)
        msg.setWindowTitle("Auto-Detection Results")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(f"Recommended preset: {detected_preset}")
        msg.setDetailedText(reasoning)
        msg.setStandardButtons(QMessageBox.StandardButton.Apply | QMessageBox.StandardButton.Cancel)
        
        if msg.exec() == QMessageBox.StandardButton.Apply:
            # Apply detected preset
            self.model_service.set_ram_preset(detected_preset)
            
            # Update UI dropdown
            for i in range(self.ram_combo.count()):
                if self.ram_combo.itemData(i) == detected_preset:
                    self.ram_combo.setCurrentIndex(i)
                    break
            
            # Save to settings
            settings = load_settings()
            settings["ram_config"] = detected_preset
            save_settings(settings)
            
            # Update the model info panel to reflect the new preset
            self._update_model_info()
            
            # Update status message
            label_map = self.model_service.get_ram_configurations().get(detected_preset, {})
            pretty = f"{detected_preset} • {label_map.get('label','')} (applies on next use)"
            self.model_status_label.setText(pretty)
            self.model_status_label.setStyleSheet("color: #3498db; font-size: 12px;")
            
            logger.debug(f"auto preset: {detected_preset}")
        
    def _on_thinking_mode_changed(self, enabled: bool):
        """Handle thinking mode toggle"""
        self.model_service.set_thinking_mode(enabled)
    
    def _toggle_more_info(self, expanded: bool):
        """Toggle the more info section visibility"""
        self.config_info_frame.setVisible(expanded)
        self.more_info_btn.setText("ℹ Less info" if expanded else "ℹ More info")
        
    @Slot(str, str)
    def _on_model_loaded(self, model_name: str, model_path: str):
        """Handle model loaded event"""
        self.model_status_label.setText(f"✅ Loaded: {model_name}")
        self.model_status_label.setStyleSheet("color: #27ae60; font-size: 12px; font-weight: bold;")
        
        self.progress_bar.setVisible(False)
        self.load_button.setEnabled(True)
        self.unload_button.setEnabled(True)
        
        # Update thinking checkbox state to match model's actual state
        self._update_thinking_ui_state()
        
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
        self.model_status_label.setText(f"🔄 Sur is loading: {message}")
        self.model_status_label.setStyleSheet("color: #3498db; font-size: 12px;")
        
    def _update_ui_state(self):
        """Update UI state based on model service"""
        is_loaded = self.model_service.is_model_loaded()
        
        self.load_button.setEnabled(not is_loaded)
        self.unload_button.setEnabled(is_loaded)
        
        if is_loaded:
            model_name = self.model_service.get_current_model_name()
            self.model_status_label.setText(f"✅ Sur ready: {model_name}")
            self.model_status_label.setStyleSheet("color: #27ae60; font-size: 12px; font-weight: bold;")
            self._update_model_info()
        else:
            self.model_status_label.setText("Sur awaiting model selection")
            self.model_status_label.setStyleSheet("color: #888888; font-size: 12px;")
            self.info_label.setText("No model information available")
        
        # Update thinking checkbox state based on model capabilities
        self._update_thinking_ui_state()
        
        # Hide progress bar if not loading
        if is_loaded or not is_loaded:
            self.progress_bar.setVisible(False)
    
    def _update_thinking_ui_state(self):
        """Update thinking checkbox based on current model's capabilities.
        
        Always keeps checkbox enabled so users can set preference before model loads.
        The preference is stored and applied when a compatible model is loaded.
        """
        # Always keep checkbox enabled - it's a user preference
        self.thinking_checkbox.setEnabled(True)
        
        # Check if current model supports thinking mode
        supports_thinking = self.model_service.should_show_thinking_toggle()
        
        if supports_thinking:
            # Model supports thinking - load the saved preference
            self.thinking_checkbox.setToolTip("Shows AI reasoning process when model generates response")
            thinking_enabled = self.model_service.get_thinking_mode()
            self.thinking_checkbox.setChecked(thinking_enabled)
        else:
            # No model loaded yet or model doesn't support thinking
            # Keep current checked state as user preference
            if self.model_service.current_model_path:
                self.thinking_checkbox.setToolTip("This model may not support thinking mode display")
            else:
                self.thinking_checkbox.setToolTip("Set thinking mode preference (applies when model loads)")
            
    def _update_model_info(self):
        """Update model information display"""
        try:
            model_info = self.model_service.get_model_info()
            
            info_lines = []
            
            # Truncate extremely long values to prevent overflow
            context_val = str(model_info.get('context_size', 'Unknown'))
            if len(context_val) > 30:
                context_val = context_val[:27] + "..."
            info_lines.append(f"Context: {context_val}")
            
            ram_config = str(model_info.get('ram_config', 'Unknown'))
            if len(ram_config) > 30:
                ram_config = ram_config[:27] + "..."
            info_lines.append(f"RAM Config: {ram_config}")
            
            thinking_enabled = model_info.get('thinking_enabled', False)
            info_lines.append(f"Thinking: {'Yes' if thinking_enabled else 'No'}")
            
            # Generation stats
            stats = model_info.get('generation_stats', {})
            if stats.get('total_generations', 0) > 0:
                total_gen = str(stats['total_generations'])
                if len(total_gen) > 20:
                    total_gen = total_gen[:17] + "..."
                info_lines.append(f"Generations: {total_gen}")
                
                total_tok = str(stats['total_tokens'])
                if len(total_tok) > 20:
                    total_tok = total_tok[:17] + "..."
                info_lines.append(f"Total Tokens: {total_tok}")
            
            # Store full text for tooltip if truncated
            full_text = "\n".join([
                f"Context: {model_info.get('context_size', 'Unknown')}",
                f"RAM Config: {model_info.get('ram_config', 'Unknown')}",
                f"Thinking: {'Yes' if thinking_enabled else 'No'}"
            ])
            if stats.get('total_generations', 0) > 0:
                full_text += f"\nGenerations: {stats['total_generations']}"
                full_text += f"\nTotal Tokens: {stats['total_tokens']}"
            
            self.info_label.setText("\n".join(info_lines))
            self.info_label.setToolTip(full_text)  # Full info on hover for accessibility
            
        except Exception as e:
            self.info_label.setText(f"Error getting model info: {str(e)}")
            
    def refresh_info(self):
        """Refresh model information display"""
        if self.model_service.is_model_loaded():
            self._update_model_info()
