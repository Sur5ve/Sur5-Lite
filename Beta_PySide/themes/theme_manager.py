#!/usr/bin/env python3
"""
Beta Version Theme Manager
Advanced QSS-based theming system with multiple professional themes
"""

from typing import Dict, Any, Optional, List
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QObject, Signal


class ThemeManager(QObject):
    """Manages application themes with QSS styling"""
    
    # Signals
    theme_changed = Signal(str)  # theme_name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_theme: Optional[str] = None
        self._setup_themes()
        
    def _setup_themes(self):
        """Initialize all available themes"""
        self.themes = {
            "theme_1": self._create_theme_1(),
            "theme_2": self._create_theme_2(), 
            "theme_3": self._create_theme_3(),
            "theme_4": self._create_theme_4()
        }
        
    def _create_theme_1(self) -> Dict[str, str]:
        """Create Theme 1 color palette - Dark theme with modern style"""
        return {
            # Primary colors - Modern teal/cyan (matches splash screen)
            "primary": "#20B2AA",       # Teal - matches splash screen!
            "primary_hover": "#1D9A92",
            "secondary": "#2c3e50",
            "accent": "#e74c3c",
            # Danger (orange-coral) tokens
            "danger": "#ff7f50",        # CSS 'coral'
            "danger_hover": "#ffa07a",  # Light salmon hover
            
            # Background colors - Deeper with subtle gradient feel
            "bg_primary": "#0d0d0d",    # Deeper black
            "bg_secondary": "#1a1a1a",  # Subtle gradient feel
            "bg_tertiary": "#262626",   # More separation
            "bg_quaternary": "#333333", # Elevated surfaces
            
            # Text colors
            "text_primary": "#ffffff",
            "text_secondary": "#b0b0b0",
            "text_muted": "#888888",
            # Use orange-coral for error text to align with danger buttons
            "text_error": "#ff7f50",
            "text_success": "#27ae60",
            
            # Border colors - Softer
            "border": "#333333",        # Softer than #444444
            "border_focus": "#20B2AA",  # Teal focus
            "border_hover": "#444444",
            
            # Special colors - Modern shadows
            "selection": "#20B2AA",
            "selection_bg": "rgba(32, 178, 170, 0.2)",
            "shadow": "rgba(0, 0, 0, 0.25)",  # Softer shadows
            
            # New: Elevated surfaces & accent hierarchy
            "surface_elevated": "#2d2d2d",
            "shadow_soft": "rgba(0, 0, 0, 0.15)",
        }
        
    def _create_theme_2(self) -> Dict[str, str]:
        """Create Theme 2 color palette - Light theme with eye comfort focus"""
        return {
            # Primary colors
            "primary": "#2980b9",
            "primary_hover": "#3498db",
            "secondary": "#34495e",
            "accent": "#c0392b",
            # Danger tokens (CRITICAL - was missing!)
            "danger": "#d32f2f",        # Material red
            "danger_hover": "#ef5350",  # Lighter red for hover
            
            # Background colors - Warmer neutrals with slight beige tint
            "bg_primary": "#fafafa",    # Off-white, not pure white (eye comfort)
            "bg_secondary": "#f5f5f3",  # Warm gray with beige tint
            "bg_tertiary": "#eeeeeb",   # Warmer mid-tone
            "bg_quaternary": "#e5e5e2", # Warmer quaternary
            
            # Text colors - Softer black
            "text_primary": "#1a1a1a",  # Softer than pure black
            "text_secondary": "#5a6c7d",
            "text_muted": "#95a5a6",
            "text_error": "#d32f2f",
            "text_success": "#27ae60",
            
            # Border colors - Higher contrast
            "border": "#e0e0e0",        # Lighter, higher contrast
            "border_focus": "#2980b9",
            "border_hover": "#d0d0d0",  # More contrast on hover
            
            # Special colors - Softer shadows
            "selection": "#2980b9",
            "selection_bg": "rgba(41, 128, 185, 0.1)",
            "shadow": "rgba(0, 0, 0, 0.08)",  # Softer than 0.1
        }
        
    def _create_theme_3(self) -> Dict[str, str]:
        """Create Theme 3 color palette - Professional dark theme, OLED-friendly"""
        return {
            # Primary colors - Ocean blue
            "primary": "#0984e3",       # Ocean blue instead of teal
            "primary_hover": "#0771c7", # Darker ocean blue
            "secondary": "#2d3436",
            "accent": "#fd79a8",        # Pink for contrast
            # Danger tokens
            "danger": "#ff6b6b",
            "danger_hover": "#ff8787",
            
            # Background colors - True black for OLED
            "bg_primary": "#0f0f0f",    # True deep black
            "bg_secondary": "#1e1e1e",
            "bg_tertiary": "#2d2d2d",
            "bg_quaternary": "#3c3c3c",
            
            # Text colors
            "text_primary": "#ffffff",
            "text_secondary": "#a0a0a0",
            "text_muted": "#707070",
            "text_error": "#ff6b6b",
            "text_success": "#51cf66",
            
            # Border colors
            "border": "#404040",
            "border_focus": "#0984e3",  # Blue focus to match primary
            "border_hover": "#505050",
            
            # Special colors
            "selection": "#0984e3",     # Blue selection to match primary
            "selection_bg": "rgba(9, 132, 227, 0.2)",
            "shadow": "rgba(0, 0, 0, 0.4)",
        }
        
    def _create_theme_4(self) -> Dict[str, str]:
        """Create Theme 4 color palette - Blue-toned theme with warm midtones"""
        return {
            # Primary colors
            "primary": "#0984e3",
            "primary_hover": "#0771c7",
            "secondary": "#2d3436",
            "accent": "#00b894",
            # Danger tokens
            "danger": "#ff6b6b",
            "danger_hover": "#ff8787",
            
            # Background colors - Warmer midtones to reduce blue fatigue
            "bg_primary": "#0a1e2b",
            "bg_secondary": "#1e3a47",
            "bg_tertiary": "#2d5566",   # Warmer - less blue, more gray-green
            "bg_quaternary": "#3c6d7f", # Warmer - reduced blue intensity
            
            # Text colors - Warmer text
            "text_primary": "#ffffff",
            "text_secondary": "#c4d4de", # Warmer - slight peach tint
            "text_muted": "#8d9da9",    # Warmer - more gray, less blue
            "text_error": "#ff6b6b",
            "text_success": "#00d4aa",
            
            # Border colors
            "border": "#4a5f7a",
            "border_focus": "#0984e3",
            "border_hover": "#5a708a",
            
            # Special colors
            "selection": "#0984e3",
            "selection_bg": "rgba(9, 132, 227, 0.2)",
            "shadow": "rgba(0, 0, 0, 0.5)",
        }
        
    def _generate_comprehensive_qss(self, colors: Dict[str, str], font_size: int = None) -> str:
        """Generate comprehensive QSS stylesheet from color palette with dynamic font size"""
        # Resolve optional tokens with sensible fallbacks
        danger_color = colors.get('danger', colors.get('text_error', '#ff6b6b'))
        danger_hover = colors.get('danger_hover', '#ff7f7f')
        focus_outline = colors.get('border_focus', '#00d4aa')
        
        # Get current font size from application if not provided
        if font_size is None:
            app = QApplication.instance()
            font_size = app.font().pointSize() if app else 9
        
        # Calculate scaled sizes based on base font
        font_size_large = font_size + 4
        font_size_xlarge = font_size + 15
        
        return f"""
        /* Main Application Styling */
        QMainWindow {{
            background-color: {colors['bg_primary']};
            color: {colors['text_primary']};
            font-size: {font_size}pt;
        }}
        
        /* General Widget Styling */
        QWidget {{
            background-color: {colors['bg_primary']};
            color: {colors['text_primary']};
            font-family: "Segoe UI", "SF Pro Display", sans-serif;
            font-size: {font_size}pt;
        }}

        /* Global focus outline for accessibility */
        *:focus {{
            outline: 2px solid {focus_outline};
            outline-offset: 2px;
        }}
        
        /* Buttons */
        QPushButton {{
            background-color: {colors['bg_secondary']};
            border: 1px solid {colors['border']};
            border-radius: 8px;
            padding: 8px 16px;
            color: {colors['text_primary']};
            font-weight: 500;
            min-height: 34px;
        }}
        
        QPushButton:hover {{
            background-color: {colors['bg_tertiary']};
            border-color: {colors['border_hover']};
        }}
        
        QPushButton:pressed {{
            background-color: {colors['bg_quaternary']};
        }}
        
        QPushButton:disabled {{
            background-color: {colors['bg_tertiary']};
            color: {colors['text_muted']};
            border-color: {colors['border']};
        }}
        
        /* Primary buttons */
        QPushButton[class="primary"], QPushButton#primary {{
            background-color: {colors['primary']};
            border-color: {colors['primary']};
            color: white;
            font-weight: 600;
        }}
        
        QPushButton[class="primary"]:hover, QPushButton#primary:hover {{
            background-color: {colors['primary_hover']};
            border-color: {colors['primary_hover']};
        }}
        
        QPushButton[class="primary"]:disabled, QPushButton#primary:disabled {{
            background-color: {colors['text_muted']};
            border-color: {colors['text_muted']};
        }}

        /* Secondary buttons */
        QPushButton[class="secondary"], QPushButton#secondary {{
            background-color: {colors['bg_tertiary']};
            border: 1px solid {colors['border_hover']};
            color: {colors['text_primary']};
        }}

        /* Danger buttons (coral) */
        QPushButton[class="danger"], QPushButton#danger {{
            background-color: {danger_color};
            border-color: {danger_color};
            color: white;
            font-weight: 600;
        }}
        QPushButton[class="danger"]:hover, QPushButton#danger:hover {{
            background-color: {danger_hover};
            border-color: {danger_hover};
        }}
        QPushButton[class="danger"]:disabled, QPushButton#danger:disabled {{
            background-color: {colors['text_muted']};
            border-color: {colors['text_muted']};
        }}
        
        /* QMessageBox and QDialog button styling - Remove ugly blue focus box */
        QMessageBox QPushButton {{
            min-width: 80px;
            padding: 6px 16px;
        }}
        
        QMessageBox QPushButton:focus,
        QDialogButtonBox QPushButton:focus {{
            outline: none;
            border: 2px solid {focus_outline};
            border-radius: 8px;
        }}
        
        /* Style Yes/No buttons in message boxes */
        QMessageBox QPushButton[text="Yes"],
        QMessageBox QPushButton[text="&Yes"] {{
            background-color: {colors['primary']};
            color: white;
            font-weight: 600;
        }}
        
        QMessageBox QPushButton[text="Yes"]:hover,
        QMessageBox QPushButton[text="&Yes"]:hover {{
            background-color: {colors['primary_hover']};
        }}
        
        QMessageBox QPushButton[text="No"],
        QMessageBox QPushButton[text="&No"] {{
            background-color: {colors['bg_tertiary']};
            border: 1px solid {colors['border_hover']};
        }}
        
        QMessageBox QPushButton[text="No"]:hover,
        QMessageBox QPushButton[text="&No"]:hover {{
            background-color: {colors['bg_quaternary']};
        }}
        
        /* Remove default focus rectangle for all widgets in dialogs */
        QDialog QPushButton:focus,
        QDialog QComboBox:focus,
        QDialog QLineEdit:focus,
        QDialog QCheckBox:focus {{
            outline: none;
        }}
        
        /* Add subtle focus border instead of blue box */
        QDialog QPushButton:focus {{
            border: 2px solid {focus_outline};
        }}
        
        /* Text Input Fields */
        QTextEdit, QPlainTextEdit {{
            background-color: {colors['bg_secondary']};
            border: 1px solid {colors['border']};
            border-radius: 8px;
            padding: 8px;
            color: {colors['text_primary']};
            selection-background-color: {colors['selection_bg']};
        }}
        
        QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {colors['border_focus']};
        }}
        
        QLineEdit {{
            background-color: {colors['bg_secondary']};
            border: 1px solid {colors['border']};
            border-radius: 6px;
            padding: 6px 10px;
            color: {colors['text_primary']};
            min-height: 34px;
        }}
        
        QLineEdit:focus {{
            border-color: {colors['border_focus']};
        }}
        
        /* Labels */
        QLabel {{
            color: {colors['text_primary']};
            background-color: transparent;
            font-size: {font_size}pt;
        }}
        
        QLabel[class="welcome_label"] {{
            color: {colors['primary']};
            font-size: {font_size_xlarge}pt;
            font-weight: bold;
            margin-bottom: 16px;
        }}
        
        QLabel[class="instructions_label"] {{
            color: {colors['text_muted']};
            font-size: {font_size_large}pt;
            line-height: 1.5;
        }}
        
        QLabel[class="error_message"] {{
            color: {colors['text_error']};
            background-color: {colors['bg_secondary']};
            padding: 8px;
            border-radius: 6px;
        }}
        
        /* Scroll Areas */
        QScrollArea {{
            background-color: {colors['bg_primary']};
            border: none;
        }}
        
        QScrollArea[class="thread_view"] {{
            background-color: {colors['bg_secondary']};
            border: 1px solid {colors['border']};
            border-radius: 12px;
        }}
        
        /* Fix rounded corners - apply to viewport */
        QScrollArea[class="thread_view"] > QWidget {{
            background-color: {colors['bg_secondary']};
            border-radius: 12px;
        }}
        
        QScrollArea[class="thread_view"] > QWidget > QWidget {{
            background-color: {colors['bg_secondary']};
            border-radius: 12px;
        }}
        
        /* Scroll Bars */
        QScrollBar:vertical {{
            background-color: {colors['bg_tertiary']};
            width: 12px;
            border-radius: 6px;
            margin: 0;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {colors['border_hover']};
            border-radius: 6px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {colors['text_muted']};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            border: none;
            background: none;
        }}
        
        /* Horizontal scroll bar */
        QScrollBar:horizontal {{
            background-color: {colors['bg_tertiary']};
            height: 12px;
            border-radius: 6px;
            margin: 0;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {colors['border_hover']};
            border-radius: 6px;
            min-width: 20px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {colors['text_muted']};
        }}
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            border: none;
            background: none;
        }}
        
        /* Splitters */
        QSplitter::handle {{
            background-color: {colors['border']};
        }}
        
        QSplitter::handle:horizontal {{
            width: 1px;
        }}
        
        QSplitter::handle:vertical {{
            height: 1px;
        }}
        
        /* Menu Bar */
        QMenuBar {{
            background-color: {colors['bg_primary']};
            color: {colors['text_primary']};
            border-bottom: 1px solid {colors['border']};
            padding: 4px;
        }}
        
        QMenuBar::item {{
            background-color: transparent;
            padding: 6px 12px;
            border-radius: 4px;
        }}
        
        QMenuBar::item:selected {{
            background-color: {colors['bg_secondary']};
        }}
        
        QMenuBar::item:pressed {{
            background-color: {colors['bg_tertiary']};
        }}
        
        /* Menus */
        QMenu {{
            background-color: {colors['bg_secondary']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: 8px;
            padding: 4px;
        }}
        
        QMenu::item {{
            background-color: transparent;
            padding: 8px 24px;
            border-radius: 4px;
        }}
        
        QMenu::item:selected {{
            background-color: {colors['bg_tertiary']};
        }}
        
        QMenu::separator {{
            height: 1px;
            background-color: {colors['border']};
            margin: 4px 0;
        }}
        
        /* Status Bar */
        QStatusBar {{
            background-color: {colors['bg_primary']};
            color: {colors['text_secondary']};
            border-top: 1px solid {colors['border']};
            padding: 4px;
        }}
        
        /* Combo Boxes */
        QComboBox {{
            background-color: {colors['bg_secondary']};
            border: 1px solid {colors['border']};
            border-radius: 6px;
            padding: 6px 10px;
            color: {colors['text_primary']};
            min-height: 34px;
        }}
        
        QComboBox:hover {{
            border-color: {colors['border_hover']};
        }}
        
        QComboBox:focus {{
            border-color: {colors['border_focus']};
        }}
        QComboBox:disabled {{
            background-color: {colors['bg_tertiary']};
            color: {colors['text_muted']};
            border-color: {colors['border']};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        
        QComboBox::down-arrow {{
            width: 12px;
            height: 12px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {colors['bg_secondary']};
            border: 1px solid {colors['border']};
            border-radius: 8px;
            color: {colors['text_primary']};
            selection-background-color: {colors['selection_bg']};
            outline: none;
        }}
        
        /* Group Boxes - reserve space for title chip using margin-top */
        QGroupBox {{
            background-color: {colors['bg_secondary']};
            border: 1px solid {colors['border']};
            border-radius: 10px;
            margin: 0; /* inter-group spacing comes from parent layout spacing */
            margin-top: 16px; /* room for title chip */
            padding: 0; /* content inset comes from layout margins */
            font-weight: 600;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 12px; /* align title with content inset */
            padding: 2px 6px;
            color: {colors['text_primary']};
            background-color: {colors['bg_secondary']};
            border-radius: 4px;
        }}

        /* Panel row container for consistent inner spacing */
        QFrame[class="panel_row"] {{
            background-color: {colors['bg_secondary']};
            border: 1px solid {colors['border']};
            border-radius: 10px;
            padding: 10px;
            margin: 6px 0 10px 0;
        }}
        
        /* Check Boxes */
        QCheckBox {{
            color: {colors['text_primary']};
            spacing: 8px;
        }}
        
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {colors['border']};
            border-radius: 3px;
            background-color: {colors['bg_secondary']};
        }}
        
        QCheckBox::indicator:hover {{
            border-color: {colors['border_hover']};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {colors['primary']};
            border-color: {colors['primary']};
        }}
        
        /* Radio Buttons */
        QRadioButton {{
            color: {colors['text_primary']};
            spacing: 8px;
        }}
        
        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {colors['border']};
            border-radius: 8px;
            background-color: {colors['bg_secondary']};
        }}
        
        QRadioButton::indicator:hover {{
            border-color: {colors['border_hover']};
        }}
        
        QRadioButton::indicator:checked {{
            background-color: {colors['primary']};
            border-color: {colors['primary']};
        }}
        
        /* Progress Bars */
        QProgressBar {{
            background-color: {colors['bg_secondary']};
            border: 1px solid {colors['border']};
            border-radius: 6px;
            text-align: center;
            color: {colors['text_primary']};
        }}
        
        QProgressBar::chunk {{
            background-color: {colors['primary']};
            border-radius: 5px;
        }}
        
        /* Message Bubbles */
        QFrame[class="user_bubble"] {{
            background-color: {colors['primary']};
            border-radius: 16px;
            padding: 12px;
            margin: 4px;
        }}
        
        QFrame[class="assistant_bubble"] {{
            background-color: {colors['bg_tertiary']};
            border-radius: 16px;
            padding: 12px;
            margin: 4px;
        }}
        
        QFrame[class="error_indicator"] {{
            border: 2px solid {colors['text_error']};
            border-radius: 12px;
            background-color: rgba(231, 76, 60, 0.1);
        }}
        
        /* Tooltips */
        QToolTip {{
            background-color: {colors['bg_quaternary']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: 6px;
            padding: 6px;
        }}
        """
        
    def get_available_themes(self) -> List[str]:
        """Get list of available theme names"""
        return list(self.themes.keys())
        
    def apply_theme(self, theme_name: str, widget: Optional[QWidget] = None, font_size: int = None):
        """Apply a theme to the application or specific widget with dynamic font size"""
        if theme_name not in self.themes:
            print(f"⚠️ Theme '{theme_name}' not found. Available: {list(self.themes.keys())}")
            return False
            
        try:
            # Get current font size if not provided
            if font_size is None:
                app = QApplication.instance()
                font_size = app.font().pointSize() if app else 9
            
            colors = self.themes[theme_name]
            qss = self._generate_comprehensive_qss(colors, font_size)
            
            # Get the main window to apply theme to (more effective than QApplication)
            app = QApplication.instance()
            if app:
                # Apply to app first (for menus, dialogs, etc.)
                app.setStyleSheet(qss)
                
                # Also apply to main window specifically for better propagation
                main_windows = [w for w in app.topLevelWidgets() if w.objectName() != "SplashScreen"]
                for main_win in main_windows:
                    main_win.setStyleSheet(qss)
            
            # If specific widget provided, apply to it too
            if widget:
                widget.setStyleSheet(qss)
                    
            self.current_theme = theme_name
            self.theme_changed.emit(theme_name)
            
            print(f"🎨 Theme applied: {theme_name} (font: {font_size}pt)")
            return True
            
        except Exception as e:
            print(f"❌ Error applying theme '{theme_name}': {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def get_current_theme(self) -> Optional[str]:
        """Get the currently applied theme name"""
        return self.current_theme
        
    def get_theme_colors(self, theme_name: str) -> Optional[Dict[str, str]]:
        """Get color palette for a specific theme"""
        return self.themes.get(theme_name)
        
    def reload_current_theme(self):
        """Reload the currently applied theme"""
        if self.current_theme:
            self.apply_theme(self.current_theme)
