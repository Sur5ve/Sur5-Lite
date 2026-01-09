#!/usr/bin/env python3
"""
Skeleton Loader Widget with Shimmer Animation
Modern loading placeholder for Tier 2 response bubble
"""

from typing import Dict, Optional
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QPainter, QLinearGradient, QColor, QPen
from PySide6.QtWidgets import QWidget

# Import cross-platform reduced motion detection from processing_header
from .processing_header import prefers_reduced_motion


class SkeletonLoaderWidget(QWidget):
    """
    Skeleton loader with shimmer animation for response generation
    
    Features:
    - 3 placeholder lines with responsive widths (100%, 95%, 80%)
    - Shimmer gradient animation sweeping left-to-right
    - Theme-aware colors
    - Respects OS reduced-motion preferences
    """
    
    def __init__(self, line_count: int = 3, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.line_count = line_count
        self._shimmer_position = 0.0
        self._reduce_motion = prefers_reduced_motion()
        
        # Theme colors (defaults, will be overridden)
        self._skeleton_bg = QColor("#262626")
        self._shimmer_color = QColor(255, 255, 255, 38)  # 15% alpha
        
        # Line specifications
        self.line_widths = [1.0, 0.95, 0.80]  # Percentage of container width
        self.line_height = 16
        self.line_spacing = 8
        self.corner_radius = 6
        
        # Calculate total height
        total_height = (self.line_height * line_count) + (self.line_spacing * (line_count - 1))
        self.setMinimumHeight(total_height)
        self.setMaximumHeight(total_height)
        
        # shimmer
        self._shimmer_animation = None
        if not self._reduce_motion:
            self._setup_shimmer_animation()
    
    def _setup_shimmer_animation(self):
        """Setup shimmer gradient animation"""
        self._shimmer_animation = QPropertyAnimation(self, b"shimmer_position")
        self._shimmer_animation.setDuration(1500)  # 1.5 seconds
        self._shimmer_animation.setStartValue(-1.0)
        self._shimmer_animation.setEndValue(1.0)
        self._shimmer_animation.setEasingCurve(QEasingCurve.Type.Linear)
        self._shimmer_animation.setLoopCount(-1)  # Infinite loop
        self._shimmer_animation.start()
    
    def set_theme_colors(self, theme_colors: Dict[str, str]):
        """
        Set theme-aware colors for skeleton and shimmer
        
        Args:
            theme_colors: Dictionary with keys like 'bg_tertiary', 'text_primary', 'primary'
        """
        # Parse skeleton background color
        bg_tertiary = theme_colors.get("bg_tertiary", "#262626")
        self._skeleton_bg = QColor(bg_tertiary)
        
        # Determine shimmer color based on theme brightness
        text_primary = theme_colors.get("text_primary", "#ffffff")
        primary = theme_colors.get("primary", "#20B2AA")
        
        # Calculate luminance to determine if theme is dark or light
        luminance = self._calculate_luminance(self._skeleton_bg)
        
        if luminance < 0.5:  # Dark theme
            # Use text_primary with 15% alpha
            text_color = QColor(text_primary)
            self._shimmer_color = QColor(
                text_color.red(),
                text_color.green(),
                text_color.blue(),
                38  # 15% of 255
            )
        else:  # Light theme
            # Use primary with 12% alpha
            primary_color = QColor(primary)
            self._shimmer_color = QColor(
                primary_color.red(),
                primary_color.green(),
                primary_color.blue(),
                31  # 12% of 255
            )
        
        self.update()  # Trigger repaint
    
    def _calculate_luminance(self, color: QColor) -> float:
        """Calculate relative luminance of a color"""
        def channel(value: int) -> float:
            normalized = value / 255.0
            if normalized <= 0.04045:
                return normalized / 12.92
            return ((normalized + 0.055) / 1.055) ** 2.4
        
        r = channel(color.red())
        g = channel(color.green())
        b = channel(color.blue())
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    
    @Property(float)
    def shimmer_position(self) -> float:
        """Get shimmer position (for animation)"""
        return self._shimmer_position
    
    @shimmer_position.setter
    def shimmer_position(self, value: float):
        """Set shimmer position and trigger repaint"""
        self._shimmer_position = value
        self.update()
    
    def paintEvent(self, event):
        """Draw skeleton lines with shimmer effect"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        y_offset = 0
        
        for i in range(self.line_count):
            # Calculate line width
            line_width = int(width * self.line_widths[i])
            
            # Draw skeleton bar background
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._skeleton_bg)
            painter.drawRoundedRect(
                0, y_offset,
                line_width, self.line_height,
                self.corner_radius, self.corner_radius
            )
            
            # Draw shimmer gradient (if not reduced motion)
            if not self._reduce_motion:
                # Calculate shimmer gradient position
                # Shimmer moves from -1 (off-screen left) to 1 (off-screen right)
                gradient_center = (self._shimmer_position + 1.0) / 2.0  # Normalize to 0-1
                gradient_start = gradient_center - 0.2  # Gradient width = 40% of container
                gradient_end = gradient_center + 0.2
                
                # Create linear gradient
                gradient = QLinearGradient(
                    line_width * gradient_start, 0,
                    line_width * gradient_end, 0
                )
                
                # Gradient colors: transparent -> shimmer -> transparent
                gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
                gradient.setColorAt(0.5, self._shimmer_color)
                gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
                
                # Draw shimmer overlay
                painter.setBrush(gradient)
                painter.drawRoundedRect(
                    0, y_offset,
                    line_width, self.line_height,
                    self.corner_radius, self.corner_radius
                )
            
            # Move to next line
            y_offset += self.line_height + self.line_spacing
        
        painter.end()
    
    def stop_animation(self):
        """Stop shimmer animation"""
        if self._shimmer_animation:
            self._shimmer_animation.stop()
    
    def start_animation(self):
        """Start shimmer animation (if not reduced motion)"""
        if self._shimmer_animation and not self._reduce_motion:
            self._shimmer_animation.start()


