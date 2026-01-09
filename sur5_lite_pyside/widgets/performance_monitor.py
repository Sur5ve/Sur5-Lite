#!/usr/bin/env python3
"""
Performance Monitor Widget
Real-time CPU, RAM, and GPU usage display integrated into the status bar.

Design:
- Status bar widget (NOT a floating window)
- Collapsible with single click
- Uses existing hardware_detector.py for metrics
- Only polls when visible (0% CPU when hidden)
- Toggle via Settings or keyboard shortcut

Naming: "Performance Monitor" (NOT "Developer Tools" - accessible to all users)

Resource Impact:
- When OFF: 0% CPU, 0 bytes RAM
- When ON: ~0.1-0.3% CPU, ~1-2 MB RAM (polling every 2 seconds)
"""

from typing import Optional, Dict, Any

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
    QFrame, QPushButton, QProgressBar, QApplication
)
from PySide6.QtGui import QFont

# Try to import hardware detector
try:
    from utils.hardware_detector import HardwareDetector
    HAS_HARDWARE_DETECTOR = True
except ImportError:
    HAS_HARDWARE_DETECTOR = False

# Try to import psutil for direct access
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class CompactProgressBar(QProgressBar):
    """Compact progress bar styled for status bar display."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setTextVisible(False)
        self.setFixedHeight(8)
        self.setFixedWidth(60)
        self.setMinimum(0)
        self.setMaximum(100)
        
        # Style will be applied by theme, but set a default
        self.setStyleSheet("""
            QProgressBar {
                background-color: rgba(100, 100, 100, 0.3);
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #20B2AA;
                border-radius: 4px;
            }
        """)


class PerformanceMonitorWidget(QWidget):
    """Compact performance monitor widget for status bar.
    
    Displays CPU, RAM, GPU usage and token speed in a collapsible format.
    
    Signals:
        visibility_changed: Emitted when monitor visibility changes
    """
    
    visibility_changed = Signal(bool)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._enabled = False
        self._expanded = False
        self._token_speed = 0.0
        self._poll_interval = 2000  # 2 seconds
        
        # Performance data cache
        self._cpu_percent = 0
        self._ram_percent = 0
        self._ram_used_gb = 0.0
        self._ram_total_gb = 0.0
        self._gpu_percent = 0
        self._gpu_name = ""
        self._gpu_used_gb = 0.0
        self._gpu_total_gb = 0.0
        self._cpu_cores = 0
        
        # Timer for polling
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_metrics)
        
        # ui
        self._setup_ui()
        
        # Initially hidden
        self.setVisible(False)
    
    def _setup_ui(self) -> None:
        """Setup the performance monitor UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 2, 4, 2)
        main_layout.setSpacing(2)
        
        # Collapsed view (single line)
        self._collapsed_widget = QWidget()
        collapsed_layout = QHBoxLayout(self._collapsed_widget)
        collapsed_layout.setContentsMargins(0, 0, 0, 0)
        collapsed_layout.setSpacing(8)
        
        # Toggle button
        self._toggle_btn = QPushButton("▶")
        self._toggle_btn.setFixedSize(16, 16)
        self._toggle_btn.setFlat(True)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._toggle_expanded)
        self._toggle_btn.setToolTip("Expand performance monitor")
        collapsed_layout.addWidget(self._toggle_btn)
        
        # Performance label
        self._perf_label = QLabel("Performance")
        self._perf_label.setStyleSheet("font-weight: bold;")
        collapsed_layout.addWidget(self._perf_label)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        collapsed_layout.addWidget(sep)
        
        # CPU compact
        self._cpu_label_compact = QLabel("CPU:")
        collapsed_layout.addWidget(self._cpu_label_compact)
        self._cpu_bar_compact = CompactProgressBar()
        collapsed_layout.addWidget(self._cpu_bar_compact)
        self._cpu_percent_label = QLabel("0%")
        self._cpu_percent_label.setMinimumWidth(35)
        collapsed_layout.addWidget(self._cpu_percent_label)
        
        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setFrameShadow(QFrame.Shadow.Sunken)
        collapsed_layout.addWidget(sep2)
        
        # RAM compact
        self._ram_label_compact = QLabel("RAM:")
        collapsed_layout.addWidget(self._ram_label_compact)
        self._ram_bar_compact = CompactProgressBar()
        collapsed_layout.addWidget(self._ram_bar_compact)
        self._ram_percent_label = QLabel("0%")
        self._ram_percent_label.setMinimumWidth(35)
        collapsed_layout.addWidget(self._ram_percent_label)
        
        # Separator
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.VLine)
        sep3.setFrameShadow(QFrame.Shadow.Sunken)
        collapsed_layout.addWidget(sep3)
        
        # Token speed
        self._speed_label = QLabel("0.0 t/s")
        self._speed_label.setToolTip("Tokens per second")
        collapsed_layout.addWidget(self._speed_label)
        
        collapsed_layout.addStretch()
        
        main_layout.addWidget(self._collapsed_widget)
        
        # Expanded view
        self._expanded_widget = QWidget()
        self._expanded_widget.setVisible(False)
        expanded_layout = QVBoxLayout(self._expanded_widget)
        expanded_layout.setContentsMargins(20, 4, 4, 4)
        expanded_layout.setSpacing(4)
        
        # CPU detailed
        cpu_row = QHBoxLayout()
        self._cpu_detail_label = QLabel("CPU:")
        self._cpu_detail_label.setMinimumWidth(40)
        cpu_row.addWidget(self._cpu_detail_label)
        self._cpu_bar_expanded = QProgressBar()
        self._cpu_bar_expanded.setMinimum(0)
        self._cpu_bar_expanded.setMaximum(100)
        self._cpu_bar_expanded.setTextVisible(True)
        self._cpu_bar_expanded.setFixedHeight(18)
        cpu_row.addWidget(self._cpu_bar_expanded, 1)
        self._cpu_cores_label = QLabel("")
        self._cpu_cores_label.setMinimumWidth(80)
        cpu_row.addWidget(self._cpu_cores_label)
        expanded_layout.addLayout(cpu_row)
        
        # RAM detailed
        ram_row = QHBoxLayout()
        self._ram_detail_label = QLabel("RAM:")
        self._ram_detail_label.setMinimumWidth(40)
        ram_row.addWidget(self._ram_detail_label)
        self._ram_bar_expanded = QProgressBar()
        self._ram_bar_expanded.setMinimum(0)
        self._ram_bar_expanded.setMaximum(100)
        self._ram_bar_expanded.setTextVisible(True)
        self._ram_bar_expanded.setFixedHeight(18)
        ram_row.addWidget(self._ram_bar_expanded, 1)
        self._ram_detail_info = QLabel("")
        self._ram_detail_info.setMinimumWidth(120)
        ram_row.addWidget(self._ram_detail_info)
        expanded_layout.addLayout(ram_row)
        
        # GPU detailed (only shown if GPU available)
        self._gpu_row_widget = QWidget()
        gpu_row = QHBoxLayout(self._gpu_row_widget)
        gpu_row.setContentsMargins(0, 0, 0, 0)
        self._gpu_detail_label = QLabel("GPU:")
        self._gpu_detail_label.setMinimumWidth(40)
        gpu_row.addWidget(self._gpu_detail_label)
        self._gpu_bar_expanded = QProgressBar()
        self._gpu_bar_expanded.setMinimum(0)
        self._gpu_bar_expanded.setMaximum(100)
        self._gpu_bar_expanded.setTextVisible(True)
        self._gpu_bar_expanded.setFixedHeight(18)
        gpu_row.addWidget(self._gpu_bar_expanded, 1)
        self._gpu_detail_info = QLabel("")
        self._gpu_detail_info.setMinimumWidth(180)
        gpu_row.addWidget(self._gpu_detail_info)
        self._gpu_row_widget.setVisible(False)
        expanded_layout.addWidget(self._gpu_row_widget)
        
        # Speed detailed
        speed_row = QHBoxLayout()
        speed_label = QLabel("Speed:")
        speed_label.setMinimumWidth(40)
        speed_row.addWidget(speed_label)
        self._speed_detail_label = QLabel("0.0 tokens/sec")
        speed_row.addWidget(self._speed_detail_label)
        speed_row.addStretch()
        expanded_layout.addLayout(speed_row)
        
        main_layout.addWidget(self._expanded_widget)
    
    def _toggle_expanded(self) -> None:
        """Toggle between collapsed and expanded view."""
        self._expanded = not self._expanded
        self._expanded_widget.setVisible(self._expanded)
        self._toggle_btn.setText("▼" if self._expanded else "▶")
        self._toggle_btn.setToolTip(
            "Collapse performance monitor" if self._expanded 
            else "Expand performance monitor"
        )
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the performance monitor.
        
        Args:
            enabled: Whether to show and poll metrics
        """
        self._enabled = enabled
        self.setVisible(enabled)
        
        if enabled:
            self._poll_metrics()  # Initial poll
            self._poll_timer.start(self._poll_interval)
            print("✓ Performance monitor enabled")
        else:
            self._poll_timer.stop()
            print("✓ Performance monitor disabled")
        
        self.visibility_changed.emit(enabled)
    
    def set_token_speed(self, tokens_per_second: float) -> None:
        """Update the token generation speed display.
        
        Args:
            tokens_per_second: Current token generation speed
        """
        self._token_speed = tokens_per_second
        self._update_speed_display()
    
    def _update_speed_display(self) -> None:
        """Update speed labels."""
        speed_text = f"{self._token_speed:.1f} t/s"
        self._speed_label.setText(speed_text)
        self._speed_detail_label.setText(f"{self._token_speed:.1f} tokens/sec")
    
    @Slot()
    def _poll_metrics(self) -> None:
        """Poll system metrics."""
        if not self._enabled:
            return
        
        try:
            self._update_cpu_metrics()
            self._update_ram_metrics()
            self._update_gpu_metrics()
            self._update_display()
        except Exception as e:
            print(f"⚠️ Error polling metrics: {e}")
    
    def _update_cpu_metrics(self) -> None:
        """Update CPU metrics."""
        if HAS_PSUTIL:
            try:
                self._cpu_percent = int(psutil.cpu_percent(interval=None))
                self._cpu_cores = psutil.cpu_count(logical=True) or 0
            except Exception:
                pass
        elif HAS_HARDWARE_DETECTOR:
            try:
                cpu_info = HardwareDetector.get_cpu_info()
                self._cpu_cores = cpu_info.get("cores_logical", 0)
            except Exception:
                pass
    
    def _update_ram_metrics(self) -> None:
        """Update RAM metrics."""
        if HAS_PSUTIL:
            try:
                mem = psutil.virtual_memory()
                self._ram_percent = int(mem.percent)
                self._ram_used_gb = mem.used / (1024**3)
                self._ram_total_gb = mem.total / (1024**3)
            except Exception:
                pass
        elif HAS_HARDWARE_DETECTOR:
            try:
                ram_info = HardwareDetector.get_ram_info()
                self._ram_percent = int(ram_info.get("percent_used", 0))
                self._ram_total_gb = ram_info.get("total_gb", 0)
                self._ram_used_gb = self._ram_total_gb * (self._ram_percent / 100)
            except Exception:
                pass
    
    def _update_gpu_metrics(self) -> None:
        """Update GPU metrics."""
        if HAS_HARDWARE_DETECTOR:
            try:
                gpu_info = HardwareDetector.get_gpu_info()
                if gpu_info:
                    self._gpu_name = gpu_info.get("name", "")
                    self._gpu_percent = int(gpu_info.get("gpu_load_percent", 0))
                    self._gpu_used_gb = gpu_info.get("memory_used_mb", 0) / 1024
                    self._gpu_total_gb = gpu_info.get("memory_total_mb", 0) / 1024
                    self._gpu_row_widget.setVisible(True)
                else:
                    self._gpu_row_widget.setVisible(False)
            except Exception:
                self._gpu_row_widget.setVisible(False)
        else:
            self._gpu_row_widget.setVisible(False)
    
    def _update_display(self) -> None:
        """Update all display elements."""
        # Collapsed view
        self._cpu_bar_compact.setValue(self._cpu_percent)
        self._cpu_percent_label.setText(f"{self._cpu_percent}%")
        
        self._ram_bar_compact.setValue(self._ram_percent)
        self._ram_percent_label.setText(f"{self._ram_percent}%")
        
        # Expanded view
        self._cpu_bar_expanded.setValue(self._cpu_percent)
        self._cpu_bar_expanded.setFormat(f"{self._cpu_percent}%")
        if self._cpu_cores:
            self._cpu_cores_label.setText(f"({self._cpu_cores} cores)")
        
        self._ram_bar_expanded.setValue(self._ram_percent)
        self._ram_bar_expanded.setFormat(f"{self._ram_percent}%")
        self._ram_detail_info.setText(
            f"({self._ram_used_gb:.1f} / {self._ram_total_gb:.1f} GB)"
        )
        
        if self._gpu_row_widget.isVisible():
            self._gpu_bar_expanded.setValue(self._gpu_percent)
            self._gpu_bar_expanded.setFormat(f"{self._gpu_percent}%")
            gpu_short_name = self._gpu_name[:20] + "..." if len(self._gpu_name) > 20 else self._gpu_name
            self._gpu_detail_info.setText(
                f"({gpu_short_name} - {self._gpu_used_gb:.1f} / {self._gpu_total_gb:.1f} GB)"
            )
        
        self._update_speed_display()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics as dictionary.
        
        Returns:
            Dictionary with current performance metrics
        """
        return {
            "cpu_percent": self._cpu_percent,
            "cpu_cores": self._cpu_cores,
            "ram_percent": self._ram_percent,
            "ram_used_gb": self._ram_used_gb,
            "ram_total_gb": self._ram_total_gb,
            "gpu_percent": self._gpu_percent,
            "gpu_name": self._gpu_name,
            "gpu_used_gb": self._gpu_used_gb,
            "gpu_total_gb": self._gpu_total_gb,
            "token_speed": self._token_speed,
        }


class MinimalSpeedWidget(QWidget):
    """Minimal token speed widget for when full monitor is disabled.
    
    Shows just the token speed in the status bar.
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._token_speed = 0.0
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)
        
        self._speed_label = QLabel("0.0 t/s")
        self._speed_label.setToolTip("Token generation speed")
        layout.addWidget(self._speed_label)
    
    def set_token_speed(self, tokens_per_second: float) -> None:
        """Update the token speed display."""
        self._token_speed = tokens_per_second
        self._speed_label.setText(f"{tokens_per_second:.1f} t/s")


# Factory function for easy integration
def create_performance_monitor(parent: Optional[QWidget] = None) -> PerformanceMonitorWidget:
    """Create a performance monitor widget.
    
    Args:
        parent: Parent widget
        
    Returns:
        PerformanceMonitorWidget instance
    """
    return PerformanceMonitorWidget(parent)


def create_minimal_speed_widget(parent: Optional[QWidget] = None) -> MinimalSpeedWidget:
    """Create a minimal speed widget.
    
    Args:
        parent: Parent widget
        
    Returns:
        MinimalSpeedWidget instance
    """
    return MinimalSpeedWidget(parent)






