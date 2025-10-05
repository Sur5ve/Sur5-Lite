#!/usr/bin/env python3
"""
Beta Version PySide6 Application
Enhanced QApplication with theme management, DPI scaling, and proper initialization
"""

import sys
import os
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QFontDatabase

from .settings_manager import SettingsManager  
from .main_window import BetaMainWindow
from themes.theme_manager import ThemeManager


class BetaApplication(QApplication):
    """Enhanced QApplication for Beta Version with comprehensive initialization"""
    
    def __init__(self, argv):
        super().__init__(argv)
        
        # Initialize managers
        self.settings_manager = SettingsManager()
        self.theme_manager = ThemeManager()
        self.main_window: Optional[BetaMainWindow] = None
        
        # Setup application
        self._setup_application()
        self._load_theme()
        
    def _setup_application(self):
        """Configure application-wide settings"""
        # Application metadata
        self.setApplicationName("Beta Version")
        self.setApplicationVersion("2.0.0")
        self.setOrganizationName("Redacted")
        self.setOrganizationDomain("redacted.app")
        
        # Application behavior
        self.setQuitOnLastWindowClosed(True)
        
        # Load and set fonts
        self._setup_fonts()
        
        # Opt-in to per-monitor DPI awareness for crisp scaling across displays
        try:
            self.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        except Exception:
            pass
        
    def _setup_fonts(self):
        """Load custom fonts and restore saved font size"""
        try:
            # Try to load system fonts or custom fonts
            font_families = QFontDatabase.families()
            
            # Prefer modern fonts
            preferred_fonts = [
                "Segoe UI", "SF Pro Display", "Roboto", 
                "Inter", "System", "Arial"
            ]
            
            # Get saved font size from settings (default: 9pt)
            saved_font_size = self.settings_manager.get_setting("font_size", 9)
            
            for font_name in preferred_fonts:
                if font_name in font_families:
                    default_font = QFont(font_name, saved_font_size)
                    self.setFont(default_font)
                    print(f"✏️ Font loaded: {font_name}, {saved_font_size}pt")
                    break
                    
        except Exception as e:
            print(f"⚠️ Font setup warning: {e}")
            
    def _load_theme(self):
        """Load and apply the current theme with saved font size"""
        try:
            current_theme = self.settings_manager.get_setting("current_theme", "theme_1")
            # Get saved font size (already loaded in _setup_fonts)
            font_size = self.font().pointSize()
            # Apply theme with font size
            self.theme_manager.apply_theme(current_theme, font_size=font_size)
            print(f"🎨 Theme loaded: {current_theme} with font {font_size}pt")
        except Exception as e:
            print(f"⚠️ Theme loading warning: {e}")
            # Fallback to default theme
            self.theme_manager.apply_theme("theme_1", font_size=9)
            
    def create_main_window(self) -> BetaMainWindow:
        """Create and configure the main window"""
        if self.main_window is None:
            self.main_window = BetaMainWindow()
            
            # Apply current theme to main window with current font size
            current_theme = self.settings_manager.get_setting("current_theme", "theme_1")
            font_size = self.font().pointSize()
            self.theme_manager.apply_theme(current_theme, font_size=font_size)
            
        return self.main_window
        
    def get_settings_manager(self) -> SettingsManager:
        """Get the settings manager instance"""
        return self.settings_manager
        
    def get_theme_manager(self) -> ThemeManager:
        """Get the theme manager instance"""
        return self.theme_manager
        
    def toggle_theme(self):
        """Toggle between light and dark themes"""
        current_theme = self.settings_manager.get_setting("current_theme", "theme_1")
        
        # Simple toggle between dark and light
        if current_theme == "theme_1":
            new_theme = "theme_2"
        else:
            new_theme = "theme_1"
        
        # Get current font size
        font_size = self.font().pointSize()
            
        self.settings_manager.set_setting("current_theme", new_theme)
        self.theme_manager.apply_theme(new_theme, font_size=font_size)
            
        print(f"🎨 Theme switched to: {new_theme} (font: {font_size}pt)")


def run_beta_app() -> int:
    """
    Main entry point preserving the behavior of the original run_app()
    """
    # Set DPI scaling BEFORE creating QApplication (fixes warning)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    # Create application
    app = BetaApplication(sys.argv)
    
    try:
        # Check if headless test mode
        is_headless = os.environ.get("BETA_HEADLESS_TEST", "0") == "1"
        
        # Show splash screen (skip in headless mode)
        splash = None
        if not is_headless:
            from widgets.splash_screen import SplashScreen
            splash = SplashScreen()
            splash.show()
            app.processEvents()  # Force splash to render
            
            # Simulate initialization steps with progress
            splash.update_progress(20, "Loading Beta Version components...")
            app.processEvents()
            QTimer.singleShot(150, lambda: None)  # Small delay
            app.processEvents()
            
            splash.update_progress(40, "Initializing theme system...")
            app.processEvents()
        
        # Create and configure main window
        splash.update_progress(60, "Loading model engine...") if splash else None
        app.processEvents() if splash else None
        
        main_window = app.create_main_window()
        
        splash.update_progress(80, "Setting up AI interface...") if splash else None
        app.processEvents() if splash else None
        
        # Finalize and show main window
        splash.update_progress(100, "Ready!") if splash else None
        app.processEvents() if splash else None
        
        # Close splash and show main window
        if splash:
            QTimer.singleShot(300, splash.finish)
            QTimer.singleShot(500, main_window.show)
        else:
            main_window.show()
        
        print("✅ Beta Version PySide6 Application Launched Successfully!")
        
        # Optional headless smoke test: auto-quit after a few seconds
        if is_headless:
            print("🧪 Headless test mode enabled – closing in 4 seconds...")
            QTimer.singleShot(4000, app.quit)
        
        # Start event loop
        return app.exec()
        
    except Exception as e:
        print(f"❌ Application error: {e}")
        
        # Show error dialog if possible
        try:
            QMessageBox.critical(
                None, 
                "Beta Version Startup Error", 
                f"Failed to launch Beta Version:\n\n{str(e)}"
            )
        except:
            pass
            
        return 1


if __name__ == "__main__":
    sys.exit(run_beta_app())
