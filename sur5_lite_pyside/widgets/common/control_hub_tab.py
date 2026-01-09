#!/usr/bin/env python3
"""
Control Hub Tab
Vertical tab widget for toggling sidebar visibility
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QFontMetrics


class ControlHubTab(QWidget):
    """Vertical tab for controlling sidebar visibility"""
    
    # Signals
    clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # FIX: Calculate DPI-aware size to ensure physical minimum of 7mm (Windows HIG)
        # Formula: width_px = (7mm / 25.4) * dpi, with minimum of 30px
        try:
            from PySide6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            dpi = screen.logicalDotsPerInch() if screen else 96.0
            # Calculate minimum width for 7mm physical size
            min_physical_mm = 7.0
            calculated_width = max(30, int((min_physical_mm / 25.4) * dpi))
        except Exception:
            calculated_width = 30  # Safe fallback
        
        self.setFixedWidth(calculated_width)
        self.setMinimumHeight(120)
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
        # State
        self._hovered = False
        
        # Styling - will be overridden by theme
        self.setProperty("class", "control_hub_tab")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        # Set cursor
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def paintEvent(self, event):
        """Custom paint for vertical text"""
        # Let QSS paint the background first
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set font
        font = QFont(self.font())
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        
        # Set text color (white for visibility on danger background)
        painter.setPen(QPen(QColor(255, 255, 255)))
        
        # Draw vertical text
        text = "CONTROL HUB"
        
        # Save painter state
        painter.save()
        
        # Translate to center and rotate
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(-90)
        
        # Get text metrics for centering
        fm = QFontMetrics(font)
        text_width = fm.horizontalAdvance(text)
        text_height = fm.height()
        
        # Draw text centered
        painter.drawText(
            -text_width / 2,
            text_height / 4,
            text
        )
        
        painter.restore()
        
    def enterEvent(self, event):
        """Handle mouse enter"""
        self._hovered = True
        self.update()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """Handle mouse leave"""
        self._hovered = False
        self.update()
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)



