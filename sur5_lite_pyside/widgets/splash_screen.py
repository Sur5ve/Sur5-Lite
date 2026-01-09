#!/usr/bin/env python3
"""
Sur5 Lite Splash Screen
Professional splash screen displayed during application initialization

Copyright (c) 2024-2026 Sur5ve LLC
Licensed under MIT License
"""

import json
import sys
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QProgressBar, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPixmap, QIcon, QColor, QPalette
from pathlib import Path


# Theme colors - single theme for brand consistency
THEME_BACKGROUNDS = {
    "sur5ve": "#282a36",  # bg_primary from Sur5ve
}

THEME_BG_SECONDARY = {
    "sur5ve": "#21222c",
}

THEME_TEXT_COLORS = {
    "sur5ve": {"primary": "#f8f8f2", "muted": "#6272a4"},
}

THEME_ACCENTS = {
    "sur5ve": "#bd93f9",
}


def get_saved_theme() -> str:
    """Read the user's saved theme preference from settings.json"""
    try:
        # Try portable paths first
        try:
            from utils.portable_paths import get_settings_file
            settings_file = get_settings_file()
        except ImportError:
            # Fallback to legacy location
            settings_file = Path(__file__).parent.parent / "settings.json"
        
        if settings_file.exists():
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                return settings.get("current_theme", "sur5ve")
    except Exception:
        pass
    
    return "sur5ve"  # sur5ve is the only supported theme


class SplashScreen(QWidget):
    """Modern splash screen for Sur5 Lite application startup
    
    Features:
    - Progress tracking with ETA estimation
    - Cancel button for impatient users
    - Welcome tips during first-time loading
    """
    
    ready_to_close = Signal()
    cancel_requested = Signal()  # Emitted when user clicks cancel
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # ETA tracking
        self._start_time = None
        self._last_progress = 0
        self._progress_history = []  # List of (timestamp, progress) tuples
        
        # Set objectName so theme manager can exclude us
        self.setObjectName("SplashScreen")
        
        # Get user's saved theme
        saved_theme = get_saved_theme()
        self.is_light_theme = False  # Always dark theme
        
        # Get colors for saved theme (with fallbacks)
        self.bg_color = THEME_BACKGROUNDS.get(saved_theme, "#0d0d0d")
        self.bg_secondary = THEME_BG_SECONDARY.get(saved_theme, "#1a1a1a")
        self.text_color = THEME_TEXT_COLORS.get(saved_theme, {}).get("primary", "#ffffff")
        self.muted_color = THEME_TEXT_COLORS.get(saved_theme, {}).get("muted", "#888888")
        self.primary_color = THEME_ACCENTS.get(saved_theme, "#20B2AA")
        
        # Border color - subtle contrast
        if self.is_light_theme:
            self.border_color = "rgba(0, 0, 0, 0.1)"
            self.progress_bg = "#e0e0e0"
        else:
            self.border_color = "rgba(255, 255, 255, 0.08)"
            self.progress_bg = "#2A3441"
        
        # Window setup - FULL SCREEN to cover any white flash from main window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SplashScreen
        )
        
        # Set background via palette - dark background covers entire screen
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(self.bg_color))
        self.setAutoFillBackground(True)
        self.setPalette(palette)
        
        # Set window icon (handles both dev mode and PyInstaller frozen mode)
        try:
            icon_paths = []
            
            # PyInstaller frozen executable
            if getattr(sys, 'frozen', False):
                meipass = Path(getattr(sys, '_MEIPASS', ''))
                if meipass.exists():
                    icon_paths.append(meipass / "Images" / "sur5_icon.ico")
                exe_dir = Path(sys.executable).parent
                icon_paths.append(exe_dir / "Images" / "sur5_icon.ico")
            
            # Development mode
            base_dir = Path(__file__).parent.parent.parent
            icon_paths.append(base_dir / "Images" / "sur5_icon.ico")
            
            for icon_path in icon_paths:
                if icon_path.exists():
                    self.setWindowIcon(QIcon(str(icon_path)))
                    break
        except Exception:
            pass
        
        # FULL SCREEN - covers entire screen on any resolution
        self._make_fullscreen()
        
        # Apply dark background (no border for full screen)
        self.setStyleSheet(f"""
            SplashScreen {{
                background-color: {self.bg_color};
            }}
        """)
        
        self._setup_ui()
    
    def _make_fullscreen(self):
        """Make splash cover the entire primary screen"""
        try:
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
            if screen:
                # Get full screen geometry (including taskbar area)
                geo = screen.geometry()
                self.setGeometry(geo)
            else:
                # Fallback to a large size
                self.setGeometry(0, 0, 1920, 1080)
        except Exception:
            self.setGeometry(0, 0, 1920, 1080)
        
    def _setup_ui(self):
        """Setup the splash screen UI with professional styling - centered on full screen"""
        # Outer layout to center content on full screen
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add vertical stretch to center vertically
        outer_layout.addStretch(1)
        
        # Horizontal centering
        h_layout = QHBoxLayout()
        h_layout.addStretch(1)
        
        # Content container with fixed width for consistent appearance
        content_widget = QWidget()
        content_widget.setFixedWidth(500)
        content_widget.setStyleSheet("background: transparent;")
        
        # Main content layout
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(48, 36, 48, 32)
        main_layout.setSpacing(0)
        
        main_layout.addStretch(1)
        
        # Logo with subtle drop shadow for depth
        self.logo_label = QLabel()
        try:
            base_dir = Path(__file__).parent.parent.parent
            logo_path = base_dir / "Images" / "sur5_logo.png"
            if logo_path.exists():
                pixmap = QPixmap(str(logo_path))
                if not pixmap.isNull():
                    # Larger logo (100x100) with the extra space
                    scaled_pixmap = pixmap.scaled(
                        100, 100,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.logo_label.setPixmap(scaled_pixmap)
        except Exception:
            pass
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Add subtle glow behind logo
        logo_shadow = QGraphicsDropShadowEffect()
        logo_shadow.setBlurRadius(20)
        logo_shadow.setColor(QColor(self.primary_color))
        logo_shadow.setOffset(0, 0)
        self.logo_label.setGraphicsEffect(logo_shadow)
        main_layout.addWidget(self.logo_label)
        
        # Company label - smaller and more subtle
        main_layout.addSpacing(14)
        self.company_label = QLabel("by Sur5ve")
        company_font = QFont("Segoe UI", 10)
        company_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.5)
        self.company_label.setFont(company_font)
        self.company_label.setStyleSheet(f"color: {self.muted_color};")
        self.company_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.company_label)
        
        # Tagline - bolder with letter spacing
        main_layout.addSpacing(14)
        self.subtitle_label = QLabel("Sur5 Lite")
        tagline_font = QFont("Segoe UI", 14, QFont.Weight.DemiBold)
        tagline_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
        self.subtitle_label.setFont(tagline_font)
        self.subtitle_label.setStyleSheet(f"color: {self.text_color};")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.subtitle_label)
        
        main_layout.addSpacing(32)
        
        # Progress bar with glow effect
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {self.progress_bg};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.primary_color},
                    stop:0.5 {self._lighten_color(self.primary_color)},
                    stop:1 {self.primary_color});
                border-radius: 2px;
            }}
        """)
        
        # Add glow to progress bar
        progress_glow = QGraphicsDropShadowEffect()
        progress_glow.setBlurRadius(12)
        progress_glow.setColor(QColor(self.primary_color))
        progress_glow.setOffset(0, 0)
        self.progress_bar.setGraphicsEffect(progress_glow)
        main_layout.addWidget(self.progress_bar)
        
        # Status label
        main_layout.addSpacing(16)
        self.status_label = QLabel("Initializing...")
        status_font = QFont("Segoe UI", 10)
        self.status_label.setFont(status_font)
        self.status_label.setStyleSheet(f"color: {self.text_color};")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # ETA label - shows estimated time remaining
        main_layout.addSpacing(4)
        self.eta_label = QLabel("")
        eta_font = QFont("Segoe UI", 9)
        self.eta_label.setFont(eta_font)
        self.eta_label.setStyleSheet(f"color: {self.muted_color};")
        self.eta_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.eta_label)
        
        # Cancel button - hidden by default, shown during long operations
        main_layout.addSpacing(12)
        from PySide6.QtWidgets import QPushButton
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFixedWidth(100)
        self.cancel_button.setFixedHeight(28)
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.muted_color};
                border: 1px solid {self.muted_color};
                border-radius: 4px;
                font-size: 10px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.05);
                color: {self.text_color};
                border-color: {self.text_color};
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
        """)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        self.cancel_button.hide()  # Hidden by default
        
        # Center the cancel button
        cancel_layout = QHBoxLayout()
        cancel_layout.addStretch(1)
        cancel_layout.addWidget(self.cancel_button)
        cancel_layout.addStretch(1)
        main_layout.addLayout(cancel_layout)
        
        main_layout.addStretch(2)
        
        # Professional footer with version and copyright
        self.version_label = QLabel("Sur5 Lite v2.0  •  © 2025 Sur5ve LLC")
        version_font = QFont("Segoe UI", 8)
        version_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.3)
        self.version_label.setFont(version_font)
        self.version_label.setStyleSheet(f"color: {self.muted_color};")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.version_label)
        
        # Add content widget to horizontal layout
        h_layout.addWidget(content_widget)
        h_layout.addStretch(1)
        
        # Add horizontal layout to outer layout
        outer_layout.addLayout(h_layout)
        outer_layout.addStretch(1)
    
    def _lighten_color(self, hex_color: str) -> str:
        """Lighten a hex color for gradient highlights"""
        try:
            color = QColor(hex_color)
            h, s, l, a = color.getHslF()
            l = min(1.0, l + 0.15)  # Lighten by 15%
            color.setHslF(h, s, l, a)
            return color.name()
        except Exception:
            return hex_color
        
    def _center_on_screen(self):
        """Center the splash screen on the primary screen"""
        try:
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                self.move((geo.width() - self.width()) // 2, (geo.height() - self.height()) // 2)
        except Exception:
            pass
            
    def update_progress(self, value: int, status: str = ""):
        """Update progress bar and status text with ETA calculation"""
        import time
        
        # timing on first update
        if self._start_time is None:
            self._start_time = time.time()
            
        # Track progress history for ETA
        current_time = time.time()
        self._progress_history.append((current_time, value))
        
        # Keep only recent history (last 10 samples)
        if len(self._progress_history) > 10:
            self._progress_history = self._progress_history[-10:]
        
        self.progress_bar.setValue(value)
        if status:
            self.status_label.setText(status)
        
        # Calculate and show ETA
        eta_text = self._calculate_eta(value)
        if eta_text:
            self.eta_label.setText(eta_text)
        
        # Show cancel button after a few seconds
        elapsed = current_time - self._start_time
        if elapsed > 3 and value < 90:
            self.cancel_button.show()
        
        self._last_progress = value
        self.repaint()
    
    def _calculate_eta(self, current_progress: int) -> str:
        """Calculate estimated time remaining based on progress history"""
        import time
        
        if current_progress >= 100 or len(self._progress_history) < 2:
            return ""
        
        # Use linear regression on recent samples
        history = self._progress_history
        oldest_time, oldest_progress = history[0]
        newest_time, newest_progress = history[-1]
        
        time_elapsed = newest_time - oldest_time
        progress_made = newest_progress - oldest_progress
        
        if progress_made <= 0 or time_elapsed <= 0:
            return ""
        
        # Rate: progress per second
        rate = progress_made / time_elapsed
        remaining_progress = 100 - current_progress
        
        if rate > 0:
            eta_seconds = remaining_progress / rate
            
            if eta_seconds < 5:
                return "Almost done..."
            elif eta_seconds < 60:
                return f"~{int(eta_seconds)} seconds remaining"
            elif eta_seconds < 120:
                return f"~1 minute remaining"
            else:
                minutes = int(eta_seconds / 60)
                return f"~{minutes} minutes remaining"
        
        return ""
    
    def _on_cancel_clicked(self):
        """Handle cancel button click"""
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("Cancelling...")
        self.status_label.setText("Cancelling startup...")
        self.cancel_requested.emit()
        
    def set_status(self, status: str):
        """Set status message without changing progress"""
        self.status_label.setText(status)
        self.repaint()
    
    def show_cancel_button(self, show: bool = True):
        """Explicitly show or hide the cancel button"""
        if show:
            self.cancel_button.show()
        else:
            self.cancel_button.hide()
        
    def finish(self):
        """Close the splash screen gracefully"""
        self.ready_to_close.emit()
        QTimer.singleShot(200, self.close)
