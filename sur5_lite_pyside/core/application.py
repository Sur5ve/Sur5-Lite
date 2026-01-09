#!/usr/bin/env python3
"""
Sur5ve Application - Enhanced QApplication with theme management and DPI scaling

Copyright (c) 2024-2026 Sur5ve LLC
Licensed under MIT License
https://sur5ve.com

Features qasync async event loop for non-blocking UI operations.
"""

import sys
import os
import time
import asyncio
import json
import tempfile
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QFontDatabase, QIcon

# Logging
from utils.logger import create_module_logger
logger = create_module_logger(__name__)

# Progress file for launcher handoff
PROGRESS_FILE = Path(tempfile.gettempdir()) / "sur5_progress.json"


def write_launcher_progress(progress: int, message: str):
    """Write progress to temp file for launcher to read (seamless handoff)"""
    try:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump({"progress": progress, "message": message, "time": time.time()}, f)
    except Exception:
        pass


def cleanup_progress_file():
    """Remove progress file when done"""
    try:
        if PROGRESS_FILE.exists():
            PROGRESS_FILE.unlink()
    except Exception:
        pass

# Import qasync for async event loop integration
# qasync disabled on Windows (PyInstaller issues)
import platform as _platform
HAS_QASYNC = False
if _platform.system() != "Windows":
    try:
        from qasync import QEventLoop
        HAS_QASYNC = True
    except ImportError:
        pass

from .settings_manager import SettingsManager  
from .main_window import SurMainWindow
from themes.theme_manager import ThemeManager


class Sur5Application(QApplication):
    """Enhanced QApplication for Sur5 Lite with comprehensive initialization"""

    def __init__(self, argv, *, auto_init: bool = True):
        super().__init__(argv)

        # Lazy-initialized managers; created in initialize()
        self.settings_manager: Optional[SettingsManager] = None
        self.theme_manager: Optional[ThemeManager] = None
        self.main_window: Optional[SurMainWindow] = None

        if auto_init:
            self.initialize()

    def initialize(self):
        """Perform deferred application setup when needed."""
        if self.settings_manager is not None:
            return

        self.settings_manager = SettingsManager()
        self.theme_manager = ThemeManager()

        self._setup_application()
        self._load_theme()

    def _setup_application(self):
        """Configure application-wide settings"""
        # app metadata
        self.setApplicationName("Sur5 Lite")
        self.setApplicationVersion("2.0.0")
        self.setOrganizationName("Sur5ve LLC")
        self.setOrganizationDomain("sur5ve.com")
        
        # behavior
        self.setQuitOnLastWindowClosed(True)
        
        # Set application icon (appears in window title bar, taskbar, Alt+Tab)
        self._setup_application_icon()
        
        # Load and set fonts
        self._setup_fonts()
        
        # Note: DPI scaling policy is already set in run_sur5_app() before QApplication creation
        # (setting it here would cause a warning on macOS)
        
    def _setup_application_icon(self):
        """Set the application icon for all windows"""
        try:
            # Multiple possible base directories (checked in priority order):
            # 1. SUR5_INSTALL_DIR environment variable (set by magic launcher)
            # 2. PyInstaller frozen mode: sys._MEIPASS (bundled data location)
            # 3. PyInstaller frozen mode: exe directory (for files next to exe)
            # 4. Entry script directory (launch_sur5.py location)
            # 5. Development mode: relative to this file
            # 6. System-wide installation fallbacks
            icon_paths = []
            
            # Environment variable (highest priority - set by magic launcher)
            install_dir = os.environ.get('SUR5_INSTALL_DIR')
            if install_dir:
                icon_paths.extend([
                    Path(install_dir) / "Images" / "sur5_icon.ico",
                    Path(install_dir) / "Images" / "sur5_logo.png",
                ])
            
            # PyInstaller frozen executable
            if getattr(sys, 'frozen', False):
                # _MEIPASS is where PyInstaller extracts bundled data
                meipass = Path(getattr(sys, '_MEIPASS', ''))
                if meipass.exists():
                    icon_paths.append(meipass / "Images" / "sur5_icon.ico")
                    icon_paths.append(meipass / "Images" / "sur5_logo.png")
                
                # Also check next to the .exe file
                exe_dir = Path(sys.executable).parent
                icon_paths.append(exe_dir / "Images" / "sur5_icon.ico")
                icon_paths.append(exe_dir / "Images" / "sur5_logo.png")
            
            # Entry script directory (where launch_sur5.py is located)
            try:
                import __main__
                if hasattr(__main__, '__file__') and __main__.__file__:
                    entry_dir = Path(__main__.__file__).parent.resolve()
                    icon_paths.extend([
                        entry_dir / "Images" / "sur5_icon.ico",
                        entry_dir / "Images" / "sur5_logo.png",
                    ])
            except Exception:
                pass
            
            # Development mode - relative to this file (application.py)
            base_dir = Path(__file__).parent.parent.parent
            icon_paths.extend([
                base_dir / "Images" / "sur5_icon.ico",
                base_dir / "Images" / "sur5_logo.png",
            ])
            
            # System-wide installation fallbacks (Windows paths)
            icon_paths.extend([
                Path(r"C:\ProgramData\Sur5\Images\sur5_icon.ico"),
                Path(r"C:\ProgramData\Sur5\Images\sur5_logo.png"),
            ])
            
            # Linux/macOS installation fallbacks
            icon_paths.extend([
                Path("/opt/Sur5/Images/sur5_icon.ico"),
                Path("/Applications/Sur5/Images/sur5_icon.ico"),
            ])
            
            for icon_path in icon_paths:
                if icon_path.exists():
                    icon = QIcon(str(icon_path))
                    if not icon.isNull():
                        self.setWindowIcon(icon)
                        logger.info(f"Application icon loaded: {icon_path}")
                        return
                    else:
                        logger.warning(f"Icon file found but QIcon failed: {icon_path}")
            
            logger.warning(f"No icon found. Checked: {[str(p) for p in icon_paths]}")
        except Exception as e:
            logger.warning(f"Could not set application icon: {e}")
    
    def _setup_fonts(self):
        """Load custom fonts and restore saved font size.
        
        Loads bundled fonts from fonts/ directory if available,
        then uses an extended font fallback chain for cross-platform support.
        """
        if not self.settings_manager:
            return

        try:
            db = QFontDatabase()
            
            # Load bundled fonts from fonts/ directory
            self._load_bundled_fonts(db)

            # Extended font fallback chain for cross-platform support
            # Order: Distinctive fonts first, then platform-specific, then generic
            # Prioritizes unique, modern typography over generic defaults
            preferred_fonts = [
                # Distinctive, modern fonts (preferred for unique aesthetics)
                "IBM Plex Sans",          # Tech-forward, distinctive, excellent readability
                "Atkinson Hyperlegible",  # Accessibility-focused, unique letterforms
                "Source Sans Pro",        # Adobe's elegant, professional open-source font
                "Fira Sans",              # Mozilla's beautiful humanist sans-serif
                
                # Quality alternatives with character
                "Outfit",                 # Modern geometric with personality
                "DM Sans",                # Clean but distinctive Google Font
                "Lexend",                 # Designed for reading comfort
                "Nunito",                 # Rounded, friendly, professional
                
                # Platform-specific fallbacks (if distinctive fonts unavailable)
                # Windows
                "Segoe UI",
                # macOS
                "SF Pro Display", "SF Pro Text", ".AppleSystemUIFont", "Helvetica Neue",
                # Ubuntu / Canonical
                "Ubuntu",
                # GNOME / GTK
                "Cantarell",
                # Cross-distribution standard (Google Noto)
                "Noto Sans",
                # Widely available on most Linux distros
                "DejaVu Sans",
                # Fedora, RHEL, CentOS
                "Liberation Sans",
                
                # Generic fallbacks (avoid if possible)
                "Roboto",
                "Open Sans",
                "Lato",
                # System defaults (last resort)
                "System",
                "Arial",
                "sans-serif",
            ]

            # Get saved font size from settings (default: 9pt)
            saved_font_size = self.settings_manager.get_setting("font_size", 9)

            selected_font = None
            for font_name in preferred_fonts:
                if db.hasFamily(font_name):
                    selected_font = font_name
                    break

            if selected_font is None:
                selected_font = self.font().family()

            default_font = QFont(selected_font, saved_font_size)
            self.setFont(default_font)
            logger.debug(f"font: {selected_font} {saved_font_size}pt")

        except Exception as e:
            logger.warning(f"Font setup warning: {e}")

    def _load_bundled_fonts(self, db: QFontDatabase):
        """Load bundled fonts from the fonts/ directory.
        
        Args:
            db: QFontDatabase instance to register fonts with
        """
        try:
            # Get fonts directory (relative to app root)
            try:
                from utils.portable_paths import get_app_root
                fonts_dir = get_app_root() / "fonts"
            except ImportError:
                from pathlib import Path
                fonts_dir = Path(__file__).parent.parent.parent / "fonts"
            
            if not fonts_dir.exists():
                return
            
            # Load all TTF and OTF files
            loaded_count = 0
            for font_file in fonts_dir.glob("*.ttf"):
                font_id = db.addApplicationFont(str(font_file))
                if font_id != -1:
                    families = db.applicationFontFamilies(font_id)
                    loaded_count += 1
                    if families:
                        logger.debug(f"bundled font: {families[0]}")
            
            for font_file in fonts_dir.glob("*.otf"):
                font_id = db.addApplicationFont(str(font_file))
                if font_id != -1:
                    loaded_count += 1
            
            if loaded_count > 0:
                logger.info(f"Loaded {loaded_count} bundled fonts from {fonts_dir}")
                
        except Exception as e:
            logger.warning(f"Could not load bundled fonts: {e}")

    def _load_theme(self):
        """Load and apply the current theme with saved font size"""
        if not self.settings_manager or not self.theme_manager:
            return

        try:
            current_theme = self.settings_manager.get_setting("current_theme", "sur5ve")
            # Get saved font size (already loaded in _setup_fonts)
            font_size = self.font().pointSize()
            # Apply theme with font size
            self.theme_manager.apply_theme(current_theme, font_size=font_size)
            logger.debug(f"theme: {current_theme} font={font_size}pt")
        except Exception as e:
            logger.warning(f"Theme loading warning: {e}")
            # Fallback to default theme
            if self.theme_manager:
                self.theme_manager.apply_theme("sur5ve", font_size=9)

    def create_main_window(self) -> SurMainWindow:
        """Create and configure the main window"""
        self.initialize()

        if self.main_window is None:
            self.main_window = SurMainWindow()

            # Apply current theme to main window with current font size
            if self.settings_manager and self.theme_manager:
                current_theme = self.settings_manager.get_setting("current_theme", "sur5ve")
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
        if not self.settings_manager or not self.theme_manager:
            return

        current_theme = self.settings_manager.get_setting("current_theme", "sur5ve")

        # Sur5ve is the only supported theme
        new_theme = "sur5ve"

        # Get current font size
        font_size = self.font().pointSize()

        self.settings_manager.set_setting("current_theme", new_theme)
        self.theme_manager.apply_theme(new_theme, font_size=font_size)

        logger.debug(f"theme: {new_theme} font={font_size}pt")



def run_sur5_app() -> int:
    """Main entry point preserving the behavior of the original run_app()"""
    # Fix Windows console encoding for Unicode characters (emojis, special chars)
    if sys.platform == "win32":
        try:
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except Exception:
            pass
    
    # Startup timing diagnostics
    start_time = time.time()
    
    def log_timing(step: str):
        """Helper to log timing for each step"""
        elapsed = time.time() - start_time
        logger.debug(f"{elapsed:.2f}s {step}")
    
    log_timing("Starting Sur5 Lite...")
    
    # FIX BUG 2: Removed deprecated AA_EnableHighDpiScaling (enabled by default in Qt6)
    # Only set the rounding policy which IS still valid in Qt6
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    log_timing("DPI scaling configured")

    # Create application without auto-initialization so the splash appears sooner
    app = Sur5Application(sys.argv, auto_init=False)
    log_timing("QApplication created")

    try:
        # Check if headless test mode
        is_headless = os.environ.get("SUR5_HEADLESS_TEST", "0") == "1"
        
        # Check if hidden/prewarm mode (for demo magic trick)
        # In this mode, the app initializes completely invisibly - no splash, no window
        is_hidden_mode = os.environ.get("SUR5_START_HIDDEN", "0") == "1"
        if is_hidden_mode:
            logger.info("Demo prewarm mode: Initializing invisibly (no splash, no window)")
        
        # Check if launcher is handling splash (seamless handoff mode)
        # When set, we skip our splash but write progress to file for launcher
        skip_splash = os.environ.get("SUR5_SKIP_SPLASH", "0") == "1"
        if skip_splash:
            logger.info("Launcher handoff mode: Skipping splash, writing progress to file")
            write_launcher_progress(5, "Starting Sur5 Lite...")

        # Show splash screen (skip in headless mode, hidden mode, or launcher handoff mode)
        splash = None
        if not is_headless and not is_hidden_mode and not skip_splash:
            from widgets.splash_screen import SplashScreen

            splash = SplashScreen()
            
            # Track if startup was cancelled
            startup_cancelled = [False]
            
            def on_startup_cancelled():
                startup_cancelled[0] = True
                splash.close()
                app.quit()
            
            splash.cancel_requested.connect(on_startup_cancelled)
            splash.show()
            app.processEvents()  # Force splash to render immediately
            log_timing("Splash screen displayed")

            splash.update_progress(15, "Loading Sur5 Lite components...")
            app.processEvents()
            
            if startup_cancelled[0]:
                return 0  # User cancelled

            app.initialize()
            log_timing("Application initialized (settings, theme)")
            
            if startup_cancelled[0]:
                return 0  # User cancelled

            splash.update_progress(45, "Applying theme system...")
            app.processEvents()
        else:
            # Write progress for launcher handoff (no splash visible)
            write_launcher_progress(15, "Loading Sur5 Lite components...")
            app.initialize()
            write_launcher_progress(45, "Applying theme system...")
            log_timing("Application initialized (headless/handoff)")

        # Run startup health checks
        if splash:
            if startup_cancelled[0]:
                return 0  # User cancelled
            splash.update_progress(55, "Running health checks...")
            app.processEvents()
        else:
            write_launcher_progress(55, "Running health checks...")
        
        try:
            from utils.health_check import run_all_checks
            health_results = run_all_checks()
            if health_results["critical_failed"]:
                logger.warning(f"Health check warnings: {health_results['summary_message']}")
            else:
                logger.info(f"Health checks: {health_results['summary_message']}")
            log_timing("Health checks completed")
        except ImportError:
            logger.debug("Health checks not available")
        except Exception as e:
            logger.warning(f"Health check error: {e}")

        # Create and configure main window
        if splash:
            if startup_cancelled[0]:
                return 0  # User cancelled
            splash.update_progress(65, "Loading model engine...")
            app.processEvents()
        else:
            write_launcher_progress(65, "Loading model engine...")

        main_window = app.create_main_window()
        log_timing("Main window created")

        if splash:
            splash.update_progress(85, "Setting up AI interface...")
            app.processEvents()

            splash.update_progress(100, "Ready!")
            app.processEvents()
        else:
            write_launcher_progress(85, "Setting up AI interface...")
            # Don't write 100% here - main_window._signal_launcher_ready() will do it
            # when the window is TRULY visible and painted
            write_launcher_progress(95, "Opening window...")

        # Close splash and show main window
        # The main window will automatically show itself via _finalize_window_launch()
        # which is scheduled in main_window.__init__()
        # Splash stays on top (full screen) until main window is fully rendered
        if splash:
            QTimer.singleShot(300, splash.finish)
        
        total_time = time.time() - start_time
        log_timing("Window shown - Application ready!")
        logger.info(f"Sur5 Lite launched successfully in {total_time:.2f}s")
        
        # Clean up launcher handoff progress file after a delay
        # This gives the launcher time to read the 100% progress before we delete it
        QTimer.singleShot(2000, cleanup_progress_file)

        # Optional headless smoke test: auto-quit after a few seconds
        if is_headless:
            logger.info("Headless test mode enabled - closing in 4 seconds...")
            QTimer.singleShot(4000, app.quit)

        # Start event loop with qasync for async support
        if HAS_QASYNC:
            logger.debug("Using qasync event loop for non-blocking UI")
            loop = QEventLoop(app)
            asyncio.set_event_loop(loop)
            
            with loop:
                return loop.run_forever()
        else:
            # Fallback to standard Qt event loop
            logger.debug("Using standard Qt event loop (qasync not available)")
            return app.exec()

    except Exception as e:
        logger.error(f"Application error: {e}")

        # Show error dialog if possible
        try:
            QMessageBox.critical(
                None,
                "Sur5 Lite Startup Error",
                f"Failed to launch Sur5 Lite:\n\n{str(e)}",
            )
        except Exception:
            pass

        return 1



if __name__ == "__main__":
    sys.exit(run_sur5_app())
