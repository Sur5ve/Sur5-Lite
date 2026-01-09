#!/usr/bin/env python3
"""
Collapsible Frame - Expandable/collapsible container with header
Used for thinking bubbles in Transparent AI mode
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve


class CollapsibleFrame(QWidget):
    """Collapsible container with animated expand/collapse"""
    
    toggled = Signal(bool)  # Emit new state when toggled
    
    def __init__(self, header_text: str = "Click to expand", parent=None):
        super().__init__(parent)
        self._expanded = False
        self._init_ui(header_text)
    
    def _init_ui(self, header_text: str):
        """Initialize UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Header button with caret icon
        self.header_button = QPushButton(header_text)
        self.header_button.setProperty("class", "collapsible_header")
        self.header_button.setCheckable(True)
        self.header_button.setChecked(self._expanded)
        self.header_button.clicked.connect(self._toggle)
        self.header_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # Update button text to include caret
        self._update_header_icon()
        
        layout.addWidget(self.header_button)
        
        # Content frame (hidden by default) - must expand to fit content
        self.content_frame = QFrame()
        self.content_frame.setProperty("class", "thinking_content")
        self.content_frame.setVisible(self._expanded)
        
        # allow vertical expansion
        from PySide6.QtWidgets import QSizePolicy
        self.content_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.setSpacing(4)
        self.content_layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)
        
        layout.addWidget(self.content_frame)
    
    def _update_header_icon(self):
        """Update header button text with caret icon"""
        caret = "▼" if self._expanded else "▶"
        # Store the base text without caret
        if not hasattr(self, '_base_header_text'):
            self._base_header_text = self.header_button.text().replace("▶ ", "").replace("▼ ", "")
        text = f"{caret} {self._base_header_text}"
        self.header_button.setText(text)
    
    def _toggle(self, checked: bool):
        """Toggle expand/collapse state"""
        self._expanded = checked
        self.content_frame.setVisible(self._expanded)
        self._update_header_icon()
        self.toggled.emit(self._expanded)
    
    def set_content(self, widget: QWidget):
        """Set or replace content widget"""
        # Clear existing content
        for i in reversed(range(self.content_layout.count())):
            item = self.content_layout.takeAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        # Add new content
        self.content_layout.addWidget(widget)
    
    def set_header(self, text: str):
        """Update header text (preserves caret)"""
        self._base_header_text = text.replace("▶ ", "").replace("▼ ", "")
        self._update_header_icon()
    
    def is_expanded(self) -> bool:
        """Check if currently expanded"""
        return self._expanded
    
    def set_expanded(self, expanded: bool):
        """Programmatically set expanded state"""
        if self._expanded != expanded:
            self.header_button.setChecked(expanded)
            self._toggle(expanded)
    
    def collapse(self):
        """Collapse the content"""
        self.set_expanded(False)
    
    def expand(self):
        """Expand the content"""
        self.set_expanded(True)




