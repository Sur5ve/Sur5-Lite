#!/usr/bin/env python3
"""Processing header widget with shimmer and typing dots."""

from __future__ import annotations

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

from PySide6.QtCore import (
    Qt,
    QTimer,
    QEasingCurve,
    Property,
    QPropertyAnimation,
    QPointF,
)
from PySide6.QtGui import QPainter, QLinearGradient, QColor
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton


# Cache for reduced motion preference (detected once at startup)
_reduced_motion_cache: Optional[bool] = None


def prefers_reduced_motion() -> bool:
    """Return True when the OS prefers reduced motion (cross-platform).
    
    Supports:
    - Windows: System animation settings via ctypes
    - macOS: reduceMotion accessibility setting
    - Linux/GNOME: org.gnome.desktop.interface enable-animations
    - Linux/KDE Plasma: kdeglobals AnimationDurationFactor
    - Linux/XFCE: xfconf-query WindowScalingFactorForceInteger (animation proxy)
    - Linux/Cinnamon: org.cinnamon.desktop.interface enable-animations
    - Environment variables: REDUCE_MOTION, GTK_ENABLE_ANIMATIONS
    
    Result is cached after first call to avoid repeated subprocess invocations.
    """
    global _reduced_motion_cache
    
    # Return cached result if available
    if _reduced_motion_cache is not None:
        return _reduced_motion_cache
    
    import os
    import platform
    
    # Check environment variables first (user override, works on all platforms)
    env_reduce = os.environ.get("REDUCE_MOTION", "").lower()
    if env_reduce in ("1", "true", "yes"):
        _reduced_motion_cache = True
        return True
    
    gtk_animations = os.environ.get("GTK_ENABLE_ANIMATIONS", "").lower()
    if gtk_animations in ("0", "false", "no"):
        _reduced_motion_cache = True
        return True
    
    system = platform.system()
    
    if system == "Windows":
        _reduced_motion_cache = _check_reduced_motion_windows()
    elif system == "Linux":
        _reduced_motion_cache = _check_reduced_motion_linux()
    elif system == "Darwin":  # macOS
        _reduced_motion_cache = _check_reduced_motion_macos()
    else:
        _reduced_motion_cache = False
    
    return _reduced_motion_cache


def _check_reduced_motion_windows() -> bool:
    """Check Windows animation settings via ctypes."""
    try:
        import ctypes

        SPI_GETANIMATION = 0x0048

        class ANIMATIONINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint),
                        ("iMinAnimate", ctypes.c_int)]

        ai = ANIMATIONINFO(ctypes.sizeof(ANIMATIONINFO), 0)
        ctypes.windll.user32.SystemParametersInfoW(
            SPI_GETANIMATION, ai.cbSize, ctypes.byref(ai), 0
        )
        return ai.iMinAnimate == 0
    except Exception:
        return False


def _check_reduced_motion_linux() -> bool:
    """Check Linux desktop environment animation settings.
    
    Checks in order: GNOME -> KDE Plasma -> XFCE -> Cinnamon -> False
    """
    import subprocess
    
    # 1. GNOME: Check via gsettings
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "enable-animations"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            if result.stdout.strip() == "false":
                return True
    except Exception:
        pass
    
    # 2. KDE Plasma: Check via kreadconfig5/kreadconfig6
    for kread_cmd in ["kreadconfig6", "kreadconfig5"]:
        try:
            result = subprocess.run(
                [kread_cmd, "--file", "kdeglobals", "--group", "KDE", 
                 "--key", "AnimationDurationFactor"],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                factor = result.stdout.strip()
                # Factor of 0 means animations disabled
                if factor and float(factor) == 0:
                    return True
        except Exception:
            pass
    
    # 3. XFCE: Check via xfconf-query (no direct animation setting, check theme hints)
    try:
        result = subprocess.run(
            ["xfconf-query", "-c", "xfwm4", "-p", "/general/use_compositing"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            # Compositing disabled often means reduced animations preferred
            if result.stdout.strip().lower() == "false":
                return True
    except Exception:
        pass
    
    # 4. Cinnamon: Check via gsettings
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.cinnamon.desktop.interface", "enable-animations"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            if result.stdout.strip() == "false":
                return True
    except Exception:
        pass
    
    # 5. MATE: Check via gsettings
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.mate.interface", "enable-animations"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            if result.stdout.strip() == "false":
                return True
    except Exception:
        pass
    
    return False


def _check_reduced_motion_macos() -> bool:
    """Check macOS reduceMotion accessibility setting."""
    try:
        import subprocess
        result = subprocess.run(
            ["defaults", "read", "com.apple.universalaccess", "reduceMotion"],
            capture_output=True, text=True, timeout=2
        )
        return result.stdout.strip() == "1"
    except Exception:
        return False


def clear_reduced_motion_cache() -> None:
    """Clear the reduced motion cache to force re-detection.
    
    Useful if system settings change while the app is running.
    """
    global _reduced_motion_cache
    _reduced_motion_cache = None


# Backwards compatibility alias
prefers_reduced_motion_windows = prefers_reduced_motion


def _hex_to_qcolor(hex_str: str) -> QColor:
    color = QColor(hex_str)
    return color if color.isValid() else QColor(255, 255, 255)


def _luminance(qc: QColor) -> float:
    def _channel(value: int) -> float:
        normalized = value / 255.0
        if normalized <= 0.04045:
            return normalized / 12.92
        return ((normalized + 0.055) / 1.055) ** 2.4

    r, g, b = _channel(qc.red()), _channel(qc.green()), _channel(qc.blue())
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _color_with_alpha(qc: QColor, alpha_0_255: int) -> QColor:
    color = QColor(qc)
    color.setAlpha(max(0, min(255, alpha_0_255)))
    return color


def _compute_shimmer_band(theme_colors: Dict[str, str]) -> QColor:
    bg = _hex_to_qcolor(theme_colors.get("bg_secondary", "#1a1a1a"))
    primary = _hex_to_qcolor(theme_colors.get("primary", "#20B2AA"))
    text = _hex_to_qcolor(theme_colors.get("text_primary", "#ffffff"))

    override = theme_colors.get("shimmer_override")
    if isinstance(override, (list, tuple)) and len(override) == 4:
        r, g, b, a = override
        return QColor(int(r), int(g), int(b), int(a))

    is_dark = _luminance(bg) < 0.5

    if is_dark:
        return _color_with_alpha(text, 40)

    candidate = _color_with_alpha(primary, 35)
    if abs(_luminance(primary) - _luminance(bg)) < 0.1:
        candidate = _color_with_alpha(QColor(0, 0, 0), 30)
    return candidate


class ProcessingHeader(QWidget):
    """UI-only header shown while a response is processing."""

    def __init__(
            self,
            parent: Optional[QWidget] = None,
            *,
            reduce_motion: bool = False):
        super().__init__(parent)
        self.setObjectName("ProcessingHeader")
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        self._reduce_motion = reduce_motion
        self._animating = False
        self._active = False
        self._gradient_pos = 0.0
        self._debounce_shown = False
        self._dot_state = 0
        self._skip_available = True
        self._theme_colors: Dict[str, str] = {}

        self.setAccessibleName("Processing status")
        self.setAccessibleDescription("Model is preparing a response.")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        self.label = QLabel("Sur is processing", self)
        self.label.setObjectName("ProcessingHeaderLabel")

        self.dot_label = QLabel("", self)
        self.dot_label.setObjectName("ProcessingHeaderDots")
        fm = self.dot_label.fontMetrics()
        self.dot_label.setMinimumWidth(fm.horizontalAdvance("..."))
        self.dot_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.stop_btn = QPushButton("Stop", self)
        self.stop_btn.setObjectName("ProcessingStop")
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.stop_btn.setVisible(False)

        self.skip_btn = QPushButton("Skip >", self)
        self.skip_btn.setObjectName("ProcessingSkip")
        self.skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.skip_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.skip_btn.setVisible(False)

        layout.addWidget(self.label, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.dot_label, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch(1)
        layout.addWidget(self.stop_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.skip_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(250)
        self._debounce.timeout.connect(self._start_if_needed)

        self._dots = QTimer(self)
        self._dots.setInterval(350)
        self._dots.timeout.connect(self._advance_dots)

        self._shimmer = QPropertyAnimation(self, b"gradientPos")
        self._shimmer.setDuration(1200)
        self._shimmer.setLoopCount(-1)
        self._shimmer.setStartValue(0.0)
        self._shimmer.setEndValue(1.0)
        self._shimmer.setEasingCurve(QEasingCurve.Type.Linear)

        if self._reduce_motion:
            self._dots.stop()
            self._shimmer.stop()

        self.setProperty("aria-role", "status")
        self.setProperty("aria-hidden", "true")
        self.setProperty("aria-busy", "false")

        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.skip_btn.clicked.connect(self._on_skip_clicked)

    def getGradientPos(self) -> float:
        return self._gradient_pos

    def setGradientPos(self, value: float) -> None:
        self._gradient_pos = value
        self.update()

    gradientPos = Property(float, getGradientPos, setGradientPos)

    def set_theme_colors(self, theme_colors: Optional[Dict[str, str]]):
        self._theme_colors = dict(theme_colors or {})
        self.update()

    def set_skip_available(self, available: bool):
        self._skip_available = bool(available)
        if not self._active:
            self.stop_btn.setVisible(False)
            self.stop_btn.setEnabled(False)
            self.skip_btn.setVisible(False)
            self.skip_btn.setEnabled(False)
            return
        # Show both Stop and Skip buttons when active
        self.stop_btn.setEnabled(True)
        self.stop_btn.setVisible(True)
        self.skip_btn.setEnabled(self._skip_available)
        self.skip_btn.setVisible(self._skip_available)

    def configure_static_display(self, text: Optional[str] = None):
        self._stop_all()
        self._active = False
        if text is not None:
            self.label.setText(text)
        self.stop_btn.setVisible(False)
        self.stop_btn.setEnabled(False)
        self.skip_btn.setVisible(False)
        self.skip_btn.setEnabled(False)
        self.setProperty("aria-busy", "false")
        self.show()

    def begin(self):
        self._debounce_shown = False
        self._dot_state = 1  # Start at 1 dot instead of 0 to keep dots always visible
        self._active = True
        self.dot_label.setText(".")  # Show first dot immediately instead of clearing
        self.setProperty("aria-busy", "true")
        # Show Stop button immediately, Skip after threshold
        self.stop_btn.setEnabled(True)
        self.stop_btn.setVisible(True)
        self.skip_btn.setEnabled(self._skip_available)
        self.skip_btn.setVisible(self._skip_available)
        self.show()
        self._debounce.start()

    def on_first_token(self):
        self._stop_all()
        self.stop_btn.setVisible(False)
        self.skip_btn.setVisible(False)
        self.setProperty("aria-busy", "false")

    def finish(self):
        self._stop_all()
        self._active = False
        self.stop_btn.setVisible(False)
        self.skip_btn.setVisible(False)
        self.setProperty("aria-busy", "false")
        self.hide()

    def _start_if_needed(self):
        if self._debounce_shown:
            return
        self._debounce_shown = True
        self._animating = True
        logger.debug(f"anim start reduce_motion={self._reduce_motion}")
        if not self._reduce_motion:
            self._dots.start()
            self._shimmer.start()
            logger.debug("Dot and shimmer animations started")
        else:
            # Reduced motion: still cycle dots, but disable shimmer effect
            self._dots.start()
            self._shimmer.stop()
            logger.debug("Shimmer disabled (reduced motion mode), dots still cycle")

    def _advance_dots(self):
        # Guard: only update if header is active
        if not self._active or not self._animating:
            return
        self._dot_state = (self._dot_state % 3) + 1  # Cycles: 1 → 2 → 3 → 1
        self.dot_label.setText("." * self._dot_state)

    def _stop_all(self):
        self._debounce.stop()
        self._dots.stop()
        self._shimmer.stop()
        self._animating = False
        # Preserve dots (at least one) to avoid mid-cycle blanking
        self.dot_label.setText("." * max(1, self._dot_state or 1))
        self.update()

    def _on_stop_clicked(self):
        # Stop shimmer immediately
        self.on_first_token()
        
        # Request immediate stop from conversation service
        window = self.window()
        try:
            if hasattr(window, "conversation_service"):
                service = window.conversation_service
                service.stop_generation_immediate()
        except Exception:
            pass
        
        self.stop_btn.setEnabled(False)
        self.stop_btn.setVisible(False)
        self.skip_btn.setEnabled(False)
        self.skip_btn.setVisible(False)

    def _on_skip_clicked(self):
        # Stop shimmer immediately
        self.on_first_token()
        
        # Request skip from conversation service
        window = self.window()
        try:
            if hasattr(window, "conversation_service"):
                service = window.conversation_service
                service.skip_thinking()
        except Exception:
            pass
        
        self.skip_btn.setEnabled(False)
        self.skip_btn.setVisible(False)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._reduce_motion or not self._animating:
            return

        rect = self.rect()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = rect.width()
        start_x = rect.left() + width * self._gradient_pos
        end_x = rect.left() + width * (self._gradient_pos + 0.2)

        gradient = QLinearGradient(
            QPointF(
                start_x, rect.top()), QPointF(
                end_x, rect.bottom()))
        band = _compute_shimmer_band(self._theme_colors)
        transparent = QColor(0, 0, 0, 0)
        gradient.setColorAt(0.0, transparent)
        gradient.setColorAt(0.5, band)
        gradient.setColorAt(1.0, transparent)

        painter.fillRect(rect, gradient)
