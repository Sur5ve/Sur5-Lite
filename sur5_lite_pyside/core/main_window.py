#!/usr/bin/env python3
"""
Sur5ve Main Window - Central application window with service coordination and UI management

Copyright (c) 2024-2026 Sur5ve LLC
Licensed under MIT License
https://sur5ve.com
"""

import os
import sys
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QStatusBar, 
    QMenuBar, QMessageBox, QHBoxLayout, QSplitter, QApplication
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QAction, QKeySequence

# Logging
from utils.logger import create_module_logger
logger = create_module_logger(__name__)

# Import services
from services.model_service import ModelService
from services.conversation_service import ConversationService
from services.search_service import SearchService

# Import UI components
from widgets.chat.chat_container import ChatContainer

# Import utilities
from utils.keyboard_shortcuts import KeyboardShortcutManager
from utils.conversation_persistence import ConversationPersistence

# Import dialogs
from widgets.dialogs import (
    show_save_conversation_dialog,
    show_load_conversation_dialog,
    show_export_text_dialog,
    show_export_markdown_dialog,
    FindDialog
)

# Theme display mapping - Sur5ve is the only supported theme
try:
    from themes.theme_manager import THEME_KEY_TO_DISPLAY, THEME_DISPLAY_TO_KEY
except Exception:
    THEME_KEY_TO_DISPLAY = {
        "sur5ve": "Sur5ve",
    }
    THEME_DISPLAY_TO_KEY = {v: k for k, v in THEME_KEY_TO_DISPLAY.items()}


class SurMainWindow(QMainWindow):
    """Main application window with comprehensive service integration"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize services
        self.model_service = ModelService()
        self.conversation_service = ConversationService(self.model_service)
        self.search_service = SearchService()
        
        # Initialize persistence
        self.persistence = ConversationPersistence()
        self.current_filepath: Optional[str] = None  # Track current save file
        
        # Initialize search dialog
        self.find_dialog: Optional[FindDialog] = None
        
        # UI components
        self.central_widget: Optional[QWidget] = None
        self.chat_container: Optional[ChatContainer] = None
        self.status_bar: Optional[QStatusBar] = None
        
        # Cross-platform enhancement components
        self.system_tray_manager = None
        self.notification_service = None
        self.performance_monitor = None
        
        # Setup UI
        self._setup_window()
        self._create_central_widget()
        self._create_menu_bar()
        self._create_status_bar()
        
        # Setup keyboard shortcuts (AFTER UI components are created)
        self._setup_keyboard_shortcuts()
        
        # Setup cross-platform enhancements
        self._setup_cross_platform_enhancements()
        
        # Connect services
        self._connect_services()
        
        # Initialize application state
        self._initialize_application_state()
        
        # Finalize window launch (maximize and bring to front)
        # Use QTimer to ensure this happens after the event loop starts
        QTimer.singleShot(0, self._finalize_window_launch)
        
    def _setup_window(self):
        """Configure main window properties"""
        self.setWindowTitle("Sur5 Lite — Open Source Edge AI")
        self.setMinimumSize(1000, 700)
        
        # Explicitly set window icon from QApplication
        # Qt doesn't always inherit the app icon to windows on Windows
        app = QApplication.instance()
        if app and not app.windowIcon().isNull():
            self.setWindowIcon(app.windowIcon())
        
        # Window will be maximized, so resize is not critical but kept as fallback
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            target_w = int(geo.width() * 0.75)
            target_h = int(geo.height() * 0.75)
            self.resize(max(1000, target_w), max(700, target_h))
        else:
            self.resize(1400, 900)
        
        # Apply advanced Windows 11 title bar styling
        self._setup_advanced_title_bar()
        
        # Don't schedule maximization yet - it will be done after full UI construction
        
    def _finalize_window_launch(self):
        """Finalize window launch state - called after UI is fully constructed"""
        # Check if running in hidden/prewarm mode (for demo magic trick)
        # In this mode, the app stays completely invisible until the USB launcher reveals it
        if os.environ.get('SUR5_START_HIDDEN', '0') == '1':
            # Stay completely hidden - don't show anything
            # The magic_launcher.py will make us visible when USB is clicked
            logger.info("Demo mode: Window initialized but staying hidden (prewarm)")
            return
        
        # Normal mode: Maximize the window
        self.showMaximized()
        
        # Bring window to front and activate
        self.raise_()
        self.activateWindow()
        
        # Additional: Force window to front using Windows API (delayed to avoid flash)
        QTimer.singleShot(100, self._force_foreground_windows)
        
        # Signal launcher that window is NOW truly visible (for seamless handoff)
        # This is the REAL 100% - window is painted and visible
        # Use longer delay (1.5s) to ensure window is FULLY rendered on slow hardware
        QTimer.singleShot(1500, self._signal_launcher_ready)
    
    def _signal_launcher_ready(self):
        """Signal to magic launcher that window is truly visible and painted"""
        if os.environ.get("SUR5_SKIP_SPLASH", "0") == "1":
            # Write the REAL 100% progress - window is NOW visible
            try:
                import json
                import tempfile
                from pathlib import Path
                progress_file = Path(tempfile.gettempdir()) / "sur5_progress.json"
                with open(progress_file, 'w', encoding='utf-8') as f:
                    json.dump({"progress": 100, "message": "Window ready!", "time": __import__('time').time()}, f)
                logger.info("Signaled launcher: Window is now visible (100%)")
            except Exception as e:
                logger.warning(f"Could not signal launcher: {e}")
    
    def reveal_from_hidden(self):
        """Reveal the window from hidden prewarm mode - called by magic launcher"""
        logger.info("Revealing window from hidden prewarm mode")
        self.showMaximized()
        self.raise_()
        self.activateWindow()
        QTimer.singleShot(100, self._force_foreground_windows)
    
    def _force_foreground_windows(self):
        """Windows-specific: Force this window to foreground after it's fully rendered"""
        try:
            import platform
            if platform.system() != "Windows":
                return
            
            import ctypes
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            
            # Get current foreground window's thread
            foreground = user32.GetForegroundWindow()
            if foreground and foreground != hwnd:
                fg_thread = user32.GetWindowThreadProcessId(foreground, None)
                cur_thread = user32.GetCurrentThreadId()
                
                # Attach our thread to foreground thread to allow focus change
                user32.AttachThreadInput(fg_thread, cur_thread, True)
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
                user32.AttachThreadInput(fg_thread, cur_thread, False)
            
            # Also activate via Qt
            self.raise_()
            self.activateWindow()
        except Exception:
            pass
    
    def _setup_advanced_title_bar(self):
        """Setup advanced Windows 11 title bar with custom colors"""
        try:
            import platform
            if platform.system() != "Windows":
                return
            
            from ctypes import windll, c_int, byref
            
            # Wait for window to be fully created
            QTimer.singleShot(100, self._apply_advanced_title_bar_delayed)
            
        except Exception as e:
            logger.debug(f"Advanced title bar not available: {e}")
    
    def _apply_advanced_title_bar_delayed(self):
        """Apply title bar styling after window is fully initialized"""
        try:
            import platform
            if platform.system() != "Windows":
                return
            
            app = QApplication.instance()
            current_theme = "sur5ve"
            if hasattr(app, 'theme_manager') and app.theme_manager.current_theme:
                current_theme = app.theme_manager.current_theme
            
            self._apply_advanced_title_bar(current_theme)
            
        except Exception as e:
            logger.debug(f"Could not apply title bar styling: {e}")
    
    def _apply_advanced_title_bar(self, theme_name: str):
        """Apply bleeding-edge Windows 11 title bar styling with optimal UI/UX contrast"""
        try:
            import platform
            if platform.system() != "Windows":
                return
            
            from ctypes import windll, c_int, byref
            hwnd = int(self.winId())
            
            # Get theme colors
            app = QApplication.instance()
            theme_colors = {}
            if hasattr(app, 'theme_manager'):
                theme_colors = app.theme_manager.get_theme_colors(theme_name) or {}
            
            # Determine if dark theme
            is_dark = "light" not in theme_name.lower()
            
            # 1. Enable dark mode base (Windows 10 build 19041+)
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                byref(c_int(1 if is_dark else 0)), 4
            )
            
            # 2. Custom caption color with optimal UI/UX (Windows 11 22000+)
            try:
                DWMWA_CAPTION_COLOR = 35
                
                if is_dark:
                    # Dark themes: Use deep background for reduced eye strain
                    bg_primary = theme_colors.get("bg_primary", "#1a1a1a")
                    caption_color = bg_primary
                else:
                    # Light theme: Use soft, warm off-white (NOT pure white)
                    # Pure white causes eye strain - use warm gray/beige
                    caption_color = "#f5f5f3"  # Soft warm gray (same as bg_secondary)
                
                color_bgr = self._hex_to_bgr(caption_color)
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_CAPTION_COLOR,
                    byref(c_int(color_bgr)), 4
                )
            except Exception:
                pass  # Windows 11 only feature
            
            # 3. Set text color with WCAG AAA contrast (7:1 minimum)
            try:
                DWMWA_TEXT_COLOR = 36
                
                if is_dark:
                    # Dark themes: Pure white for maximum readability
                    text_color = 0x00FFFFFF
                else:
                    # Light theme: Soft black (not pure black) for reduced eye strain
                    # Pure black on white is too harsh - use #1a1a1a (26,26,26)
                    text_color = 0x001a1a1a  # Soft black (same as text_primary in light theme)
                
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_TEXT_COLOR,
                    byref(c_int(text_color)), 4
                )
            except Exception:
                pass  # Windows 11 only
            
            # 4. Set border color with theme-appropriate accent
            try:
                DWMWA_BORDER_COLOR = 34
                
                if is_dark:
                    # Dark themes: Use vibrant accent for visual pop
                    primary_color = theme_colors.get("primary", "#20B2AA")
                    border_color = primary_color
                else:
                    # Light theme: Use softer, more subdued border
                    # Bright borders on light backgrounds cause eye strain
                    border_color = "#d0d0d0"  # Soft gray border
                
                border_bgr = self._hex_to_bgr(border_color)
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_BORDER_COLOR,
                    byref(c_int(border_bgr)), 4
                )
            except Exception:
                pass  # Windows 11 only
            
            # 5. Ensure rounded corners (Windows 11)
            try:
                DWMWA_WINDOW_CORNER_PREFERENCE = 33
                DWMWCP_ROUND = 2
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
                    byref(c_int(DWMWCP_ROUND)), 4
                )
            except Exception:
                pass  # Windows 11 only
            
            logger.debug(f"Advanced title bar applied: {theme_name} (dark={is_dark}, eye-comfort optimized)")
            
        except Exception as e:
            # Fail silently - not all Windows versions support this
            pass
    
    def _hex_to_bgr(self, hex_color: str) -> int:
        """Convert hex color to Windows BGR COLORREF format"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        # Windows uses BGR format
        return (b << 16) | (g << 8) | r
            
    def _create_central_widget(self):
        """Create and configure the central widget layout"""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create chat container with services
        self.chat_container = ChatContainer(
            conversation_service=self.conversation_service,
            model_service=self.model_service,
            parent=self
        )
        
        main_layout.addWidget(self.chat_container)
        
        # Persist and restore splitter sizes for better UX across sessions
        try:
            app = QApplication.instance()
            if hasattr(app, 'settings_manager'):
                sizes = app.settings_manager.get_setting('splitter_sizes', None)
                if sizes and getattr(self.chat_container, 'findChild', None):
                    from PySide6.QtWidgets import QSplitter
                    splitter = self.chat_container.findChild(QSplitter)
                    if splitter and isinstance(sizes, list):
                        splitter.setSizes([int(x) for x in sizes if isinstance(x, (int, float))])
        except Exception:
            pass
        
    def _create_menu_bar(self):
        """Create application menu bar"""
        menubar = self.menuBar()
        
        # Fix for macOS: Force menu bar in window for consistent cross-platform behavior
        menubar.setNativeMenuBar(False)
        
        # File Menu
        file_menu = menubar.addMenu("&File")
        
        # New conversation
        new_action = QAction("&New Conversation", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self._new_conversation)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        # Save conversation
        save_action = QAction("&Save Conversation", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self._save_conversation)
        file_menu.addAction(save_action)
        
        # Save conversation as
        save_as_action = QAction("Save Conversation &As...", self)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        save_as_action.triggered.connect(self._save_conversation_as)
        file_menu.addAction(save_as_action)
        
        # Load conversation
        load_action = QAction("&Open Conversation...", self)
        load_action.setShortcut(QKeySequence.Open)
        load_action.triggered.connect(self._load_conversation)
        file_menu.addAction(load_action)
        
        file_menu.addSeparator()
        
        # Export submenu
        export_menu = file_menu.addMenu("&Export Conversation")
        
        export_text_action = QAction("As &Text (.txt)...", self)
        export_text_action.setShortcut(QKeySequence("Ctrl+Shift+T"))
        export_text_action.triggered.connect(self._export_conversation_text)
        export_menu.addAction(export_text_action)
        
        export_md_action = QAction("As &Markdown (.md)...", self)
        export_md_action.setShortcut(QKeySequence("Ctrl+Shift+M"))
        export_md_action.triggered.connect(self._export_conversation_markdown)
        export_menu.addAction(export_md_action)
        
        file_menu.addSeparator()
        
        # Exit
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit Menu
        edit_menu = menubar.addMenu("&Edit")
        
        # Find
        find_action = QAction("&Find in Chat...", self)
        find_action.setShortcut(QKeySequence.Find)
        find_action.triggered.connect(self._open_find_dialog)
        edit_menu.addAction(find_action)
        
        # Find Next
        find_next_action = QAction("Find &Next", self)
        find_next_action.setShortcut(QKeySequence("F3"))
        find_next_action.triggered.connect(self._find_next)
        edit_menu.addAction(find_next_action)
        
        # Find Previous
        find_prev_action = QAction("Find &Previous", self)
        find_prev_action.setShortcut(QKeySequence("Shift+F3"))
        find_prev_action.triggered.connect(self._find_previous)
        edit_menu.addAction(find_prev_action)
        
        # View Menu (quick switches)
        view_menu = menubar.addMenu("&View")
        
        # Theme submenu - display labels, apply internal keys
        theme_menu = view_menu.addMenu("Theme")
        for key, display in THEME_KEY_TO_DISPLAY.items():
            action = QAction(display, self)
            action.triggered.connect(lambda checked=False, t=key: self._apply_theme(t))
            theme_menu.addAction(action)
        
        # Font Size submenu
        font_menu = view_menu.addMenu("Font Size")
        for size, label in [(9, "Small"), (11, "Medium"), (13, "Large")]:
            act = QAction(label, self)
            act.triggered.connect(lambda checked=False, s=size: self._set_font_size(s))
            font_menu.addAction(act)

        # Performance Menu
        perf_menu = menubar.addMenu("&Performance")
        perf_menu.setToolTipsVisible(True)
        
        conv_render = QAction("Enable Message Virtualization", self)
        conv_render.setCheckable(True)
        conv_render.setChecked(False)
        conv_render.setToolTip(
            "UI Optimization: Renders only visible messages in long conversations.\n"
            "• Improves scrolling performance with 100+ messages\n"
            "• Does NOT affect AI model context or memory\n"
            "• Purely a visual rendering optimization"
        )
        conv_render.toggled.connect(self._toggle_virtualization)
        perf_menu.addAction(conv_render)
        
        virt_threshold = QAction("Set Virtualization Threshold…", self)
        virt_threshold.setToolTip(
            "Configure when virtualization activates (e.g., after 50 messages).\n"
            "Lower = better performance, but activates sooner.\n"
            "This is a UI setting only."
        )
        virt_threshold.triggered.connect(lambda: self._show_coming_soon("Virtualization threshold configuration"))
        perf_menu.addAction(virt_threshold)
        
        # Help Menu
        help_menu = menubar.addMenu("&Help")
        
        # View Logs
        from widgets.dialogs import show_log_viewer
        logs_action = QAction("View &Logs...", self)
        logs_action.triggered.connect(lambda: show_log_viewer(self))
        help_menu.addAction(logs_action)
        
        help_menu.addSeparator()
        
        about_action = QAction("&About Sur5", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
    def _create_status_bar(self):
        """Create application status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Select a model to begin (loads on first message)")
    
    def _setup_keyboard_shortcuts(self):
        """Setup comprehensive keyboard shortcuts system"""
        try:
            self.shortcut_manager = KeyboardShortcutManager(self)
            self.shortcut_manager.setup_shortcuts()
            logger.info("Keyboard shortcuts initialized")
        except Exception as e:
            logger.warning(f"Error setting up keyboard shortcuts: {e}")
            # Don't crash if shortcuts fail
            self.shortcut_manager = None
    
    def _setup_cross_platform_enhancements(self):
        """Setup cross-platform enhancement features.
        
        Initializes:
        - System tray manager
        - Notification service
        - Performance monitor widget
        
        All features are optional and fail gracefully.
        """
        app = QApplication.instance()
        settings_manager = getattr(app, 'settings_manager', None)
        
        # Initialize system tray
        try:
            from widgets.system_tray import SystemTrayManager, is_system_tray_available
            
            if is_system_tray_available():
                self.system_tray_manager = SystemTrayManager(self)
                
                # Connect signals
                self.system_tray_manager.new_conversation_requested.connect(
                    self._new_conversation
                )
                self.system_tray_manager.quit_requested.connect(self.close)
                
                # Load setting and apply
                if settings_manager:
                    show_tray = settings_manager.get_setting("show_in_system_tray", False)
                    minimize_tray = settings_manager.get_setting("minimize_to_tray", False)
                    self.system_tray_manager.set_enabled(show_tray)
                    self.system_tray_manager.minimize_to_tray = minimize_tray
                
                logger.info("System tray manager initialized")
            else:
                logger.info("System tray not available on this platform")
        except ImportError as e:
            logger.debug(f"System tray not available: {e}")
        except Exception as e:
            logger.warning(f"Error initializing system tray: {e}")
        
        # Initialize notification service
        try:
            from services.notification_service import NotificationService
            
            self.notification_service = NotificationService(
                tray_manager=self.system_tray_manager
            )
            self.notification_service.set_main_window(self)
            
            # Load settings
            if settings_manager:
                notify_complete = settings_manager.get_setting(
                    "notify_generation_complete", False
                )
                notify_minimized = settings_manager.get_setting(
                    "notify_only_minimized", True
                )
                self.notification_service.set_enabled(notify_complete)
                self.notification_service.set_notify_on_generation_complete(notify_complete)
                self.notification_service.set_only_when_minimized(notify_minimized)
            
            logger.info("Notification service initialized")
        except ImportError as e:
            logger.debug(f"Notification service not available: {e}")
        except Exception as e:
            logger.warning(f"Error initializing notification service: {e}")
        
        # Initialize performance monitor
        try:
            from widgets.performance_monitor import PerformanceMonitorWidget
            
            self.performance_monitor = PerformanceMonitorWidget()
            
            # Add to status bar
            if self.status_bar:
                self.status_bar.addPermanentWidget(self.performance_monitor)
            
            # Load setting
            if settings_manager:
                show_perf = settings_manager.get_setting("show_performance_monitor", False)
                self.performance_monitor.set_enabled(show_perf)
            
            logger.info("Performance monitor initialized")
        except ImportError as e:
            logger.debug(f"Performance monitor not available: {e}")
        except Exception as e:
            logger.warning(f"Error initializing performance monitor: {e}")
        
    def _connect_services(self):
        """Connect signals from services to UI components"""
        # Model service signals
        self.model_service.model_loaded.connect(self._on_model_loaded)
        self.model_service.model_error.connect(self._on_model_error)
        self.model_service.loading_progress.connect(self._on_model_loading_progress)
        
        # Conversation service signals
        self.conversation_service.message_received.connect(self._on_message_received)
        self.conversation_service.thinking_started.connect(self._on_thinking_started)
        self.conversation_service.error_occurred.connect(self._on_conversation_error)
        
        # Connect to chat container if available
        if self.chat_container:
            # Model events
            self.model_service.model_loaded.connect(self.chat_container.on_model_loaded)
            self.model_service.model_error.connect(self.chat_container.on_model_error)
            
            # Conversation events
            # NOTE: ChatContainer handles its own signal connections in _connect_signals()
            # self.conversation_service.message_received.connect(self.chat_container.on_message_received)  # Already connected in ChatContainer
        
    def _initialize_application_state(self):
        """Initialize application state - NO AUTO-LOADING (matches Tkinter pattern)"""
        # Load model path from settings (like Tkinter) - but DON'T load the model yet
        app = QApplication.instance()
        model_path = ""
        
        if hasattr(app, 'settings_manager'):
            model_path = app.settings_manager.get_setting("model_path", "") or ""
        
        # Resolve relative model paths using SUR5_MODELS_PATH (for USB demo)
        if model_path and not os.path.isabs(model_path) and not os.path.exists(model_path):
            # Try to find the model in SUR5_MODELS_PATH
            models_dir = os.environ.get('SUR5_MODELS_PATH', '')
            if models_dir:
                resolved_path = os.path.join(models_dir, model_path)
                if os.path.exists(resolved_path):
                    model_path = resolved_path
                    logger.info(f"Resolved model path via SUR5_MODELS_PATH: {model_path}")
        
        # If no valid path in settings, use auto-detection
        if not model_path or not os.path.exists(model_path):
            try:
                from core.settings_manager import get_default_model_path
                detected_path = get_default_model_path()
                
                if detected_path and os.path.exists(detected_path):
                    model_path = detected_path
                    # Persist the auto-detected path so it's available to all services
                    if hasattr(app, 'settings_manager'):
                        app.settings_manager.set_setting("model_path", model_path)
                    logger.info(f"Model auto-detected and saved: {os.path.basename(model_path)}")
                else:
                    logger.warning(f"No model found - expected at: {detected_path}")
                    self.status_bar.showMessage("Ready - Select a model to begin")
                    return
            except Exception as e:
                logger.warning(f"Error detecting model path: {e}")
                self.status_bar.showMessage("Ready - Select a model to begin")
                return
        
        # Store model path in model service (like Tkinter stores in self.model_path)
        if model_path and os.path.exists(model_path):
            self.model_service.set_model_path(model_path)
            model_name = os.path.basename(model_path)
            logger.info(f"Model path set: {model_name} (will load on first message)")
            self.status_bar.showMessage(f"Ready - Model: {model_name} (will load on first use)")
        else:
            logger.warning(f"No valid model found at: {model_path}")
            self.status_bar.showMessage("Ready - Select a model to begin")
            
    # Menu action handlers
    def _new_conversation(self):
        """Start a new conversation"""
        if self.conversation_service:
            self.conversation_service.clear_history()
            if self.chat_container:
                self.chat_container.clear_chat()
            self.current_filepath = None  # Reset save file
            self.setWindowTitle("Sur5 Lite — Open Source Edge AI")
            self.status_bar.showMessage("New conversation started")
    
    def _save_conversation(self):
        """Save conversation (Ctrl+S) - quick save or save as"""
        if self.current_filepath:
            # Quick save to existing file
            self._do_save_conversation(self.current_filepath)
        else:
            # No file yet, prompt for location
            self._save_conversation_as()
    
    def _save_conversation_as(self):
        """Save conversation as new file (Ctrl+Shift+S)"""
        filepath = show_save_conversation_dialog(self)
        if filepath:
            self._do_save_conversation(filepath)
    
    def _do_save_conversation(self, filepath: str):
        """Perform the actual save operation"""
        try:
            # Get conversation data from service
            conversation_data = self.conversation_service.export_conversation()
            
            # Save using persistence
            success = self.persistence.save_conversation(conversation_data, filepath)
            
            if success:
                self.current_filepath = filepath
                filename = os.path.basename(filepath)
                self.setWindowTitle(f"Sur5 Lite - {filename}")
                self.status_bar.showMessage(f"Conversation saved: {filename}", 3000)
                logger.info(f"Saved conversation: {filepath}")
            else:
                QMessageBox.warning(
                    self,
                    "Save Failed",
                    f"Could not save conversation to:\n{filepath}"
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Error saving conversation:\n{str(e)}"
            )
            logger.error(f"Save error: {e}")
    
    def _load_conversation(self):
        """Load conversation from file (Ctrl+O)"""
        filepath = show_load_conversation_dialog(self)
        if not filepath:
            return
        
        try:
            # Load using persistence
            conversation_data, error = self.persistence.load_conversation(filepath)
            
            if error:
                QMessageBox.warning(
                    self,
                    "Load Failed",
                    f"Could not load conversation:\n{error}"
                )
                return
            
            # Import into conversation service
            self.conversation_service.import_conversation(conversation_data)
            
            # Clear and rebuild chat UI
            if self.chat_container:
                self.chat_container.clear_chat()
                
                # Reload all messages
                history = conversation_data.get("history", [])
                for msg in history:
                    self.chat_container.on_message_received(msg)
            
            # Update window state
            self.current_filepath = filepath
            filename = os.path.basename(filepath)
            self.setWindowTitle(f"Sur5ve - {filename}")
            self.status_bar.showMessage(f"Conversation loaded: {filename}", 3000)
            logger.info(f"Loaded conversation: {filepath}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Load Error",
                f"Error loading conversation:\n{str(e)}"
            )
            logger.error(f"Load error: {e}")
    
    def _export_conversation_text(self):
        """Export conversation as text file (Ctrl+Shift+T)"""
        filepath = show_export_text_dialog(self)
        if not filepath:
            return
        
        try:
            # Get conversation data
            conversation_data = self.conversation_service.export_conversation()
            
            # Export using persistence
            success = self.persistence.export_to_text(conversation_data, filepath)
            
            if success:
                filename = os.path.basename(filepath)
                self.status_bar.showMessage(f"Exported to text: {filename}", 3000)
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Conversation exported to:\n{filepath}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Export Failed",
                    f"Could not export conversation to:\n{filepath}"
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Error exporting conversation:\n{str(e)}"
            )
            logger.error(f"Export error: {e}")
    
    def _export_conversation_markdown(self):
        """Export conversation as markdown file (Ctrl+Shift+M)"""
        filepath = show_export_markdown_dialog(self)
        if not filepath:
            return
        
        try:
            # Get conversation data
            conversation_data = self.conversation_service.export_conversation()
            
            # Export using persistence
            success = self.persistence.export_to_markdown(conversation_data, filepath)
            
            if success:
                filename = os.path.basename(filepath)
                self.status_bar.showMessage(f"Exported to Markdown: {filename}", 3000)
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Conversation exported to:\n{filepath}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Export Failed",
                    f"Could not export conversation to:\n{filepath}"
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Error exporting conversation:\n{str(e)}"
            )
            logger.error(f"Export error: {e}")
    
    def _open_find_dialog(self):
        """Open find dialog (Ctrl+F)"""
        if not self.find_dialog:
            self.find_dialog = FindDialog(self)
            
            # Connect signals
            self.find_dialog.search_requested.connect(self._perform_search)
            self.find_dialog.find_next_requested.connect(self._find_next)
            self.find_dialog.find_previous_requested.connect(self._find_previous)
            self.find_dialog.closed.connect(self._on_find_dialog_closed)
        
        # Update search service with current conversation
        history = self.conversation_service.get_history()
        self.search_service.set_conversation_history(history)
        
        # Show dialog
        self.find_dialog.show()
        self.find_dialog.raise_()
        self.find_dialog.activateWindow()
    
    def _perform_search(self, term: str, case_sensitive: bool, search_thinking: bool, use_regex: bool):
        """Perform search in chat"""
        try:
            # Update conversation history
            history = self.conversation_service.get_history()
            self.search_service.set_conversation_history(history)
            
            # Perform search
            result_count = self.search_service.search(
                term, case_sensitive, search_thinking, use_regex
            )
            
            if result_count == 0:
                self.status_bar.showMessage("No results found", 3000)
                if self.find_dialog:
                    self.find_dialog.update_results(0, 0)
            else:
                # Highlight first result
                current_result = self.search_service.get_current_result()
                if current_result:
                    self._highlight_current_result()
                    self.status_bar.showMessage(
                        f"Found {result_count} results", 3000
                    )
                    if self.find_dialog:
                        self.find_dialog.update_results(
                            self.search_service.get_current_result_index(),
                            result_count
                        )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Search Error",
                f"Error performing search:\n{str(e)}"
            )
            logger.error(f"Search error: {e}")
    
    def _find_next(self):
        """Find next search result (F3)"""
        if not self.search_service.has_results():
            # No active search, open find dialog
            self._open_find_dialog()
            return
        
        # Navigate to next result
        if self.search_service.find_next():
            self._highlight_current_result()
            self._update_search_status()
    
    def _find_previous(self):
        """Find previous search result (Shift+F3)"""
        if not self.search_service.has_results():
            # No active search, open find dialog
            self._open_find_dialog()
            return
        
        # Navigate to previous result
        if self.search_service.find_previous():
            self._highlight_current_result()
            self._update_search_status()
    
    def _highlight_current_result(self):
        """Highlight the current search result in the chat"""
        current_result = self.search_service.get_current_result()
        if not current_result or not self.chat_container:
            return
        
        # Clear previous highlights
        if hasattr(self.chat_container, 'thread_view'):
            thread_view = self.chat_container.thread_view
            thread_view.clear_search_highlights()
            
            # Highlight all results (non-current in yellow)
            search_term = self.search_service.search_term
            for result in self.search_service.results:
                is_current = result == current_result
                thread_view.highlight_search_result(
                    result.message_index, search_term, is_current
                )
    
    def _update_search_status(self):
        """Update status bar and find dialog with search info"""
        summary = self.search_service.get_search_summary()
        self.status_bar.showMessage(summary, 2000)
        
        if self.find_dialog:
            self.find_dialog.update_results(
                self.search_service.get_current_result_index(),
                self.search_service.get_result_count()
            )
    
    def _on_find_dialog_closed(self):
        """Handle find dialog close"""
        # Clear search highlights
        if self.chat_container and hasattr(self.chat_container, 'thread_view'):
            self.chat_container.thread_view.clear_search_highlights()
        
        # Clear search service
        self.search_service.clear_search()
        self.status_bar.showMessage("Search closed", 2000)
            
    def _toggle_theme(self):
        """Toggle application theme"""
        app = QApplication.instance()
        if hasattr(app, 'toggle_theme'):
            app.toggle_theme()
            self.status_bar.showMessage("Theme toggled", 2000)

    def _apply_theme(self, theme_name: str):
        """Apply theme and preserve font size"""
        app = QApplication.instance()
        if hasattr(app, 'theme_manager'):
            # Save current font size before theme change
            current_font_size = app.font().pointSize()
            
            # Apply the theme WITH font size (so QSS includes it)
            app.theme_manager.apply_theme(theme_name, font_size=current_font_size)
            
            # Also set app font to ensure it's applied
            f = app.font()
            f.setPointSize(current_font_size)
            app.setFont(f)
            
            # Save to settings
            if hasattr(app, 'settings_manager'):
                app.settings_manager.set_setting("current_theme", theme_name)
            
            # Update title bar to match new theme
            self._apply_advanced_title_bar(theme_name)
            
            # Force repaint all widgets to apply theme changes immediately
            self._force_repaint_all_widgets()
            
            # Show display label in status
            display = THEME_KEY_TO_DISPLAY.get(theme_name, theme_name)
            self.status_bar.showMessage(f"Theme: {display}", 2000)
            logger.debug(f"Theme applied: {theme_name} (font size: {current_font_size}pt)")

    def _set_font_size(self, size: int):
        """Set font size for entire application"""
        app = QApplication.instance()
        
        # Set app font
        f = app.font()
        f.setPointSize(size)
        app.setFont(f)
        
        # Save font size to settings for persistence
        if hasattr(app, 'settings_manager'):
            app.settings_manager.set_setting("font_size", size)
        
        # Re-apply current theme with new font size (regenerates QSS)
        if hasattr(app, 'theme_manager') and app.theme_manager.current_theme:
            app.theme_manager.apply_theme(app.theme_manager.current_theme, font_size=size)
        
        # Force repaint to apply new font size immediately
        self._force_repaint_all_widgets()
        
        self.status_bar.showMessage(f"Font size: {size}pt", 2000)
        logger.debug(f"Font size changed: {size}pt")
    
    def _force_repaint_all_widgets(self):
        """Force all widgets to repaint/update after theme or font change"""
        try:
            # Update the main window
            self.update()
            self.repaint()
            
            # Recursively update all child widgets
            def update_widget_tree(widget):
                if widget:
                    # Some widgets (QListView, etc.) have different update signatures
                    try:
                        widget.update()
                    except TypeError:
                        # Widget needs different update call, skip gracefully
                        pass
                    widget.updateGeometry()
                    for child in widget.findChildren(QWidget):
                        try:
                            child.update()
                        except TypeError:
                            pass
                        child.updateGeometry()
            
            update_widget_tree(self)
            
            # Process pending events to ensure updates take effect
            QApplication.processEvents()
        except Exception as e:
            logger.debug(f"Warning during widget repaint: {e}")

    def _toggle_virtualization(self, enabled: bool):
        # Placeholder hook for settings panel/renderer; stored in app settings if available
        app = QApplication.instance()
        if hasattr(app, 'settings_manager'):
            app.settings_manager.set_setting("enable_virtualization", enabled)

    def _open_preferences(self):
        try:
            from widgets.preferences_dialog import PreferencesDialog
            dlg = PreferencesDialog(QApplication.instance(), self)
            dlg.exec()
        except Exception as e:
            QMessageBox.information(self, "Appearance", f"Preferences dialog error: {e}")

            
    def _show_about(self):
        """Show about dialog with proper styling"""
        about_text = """
        <h2>Sur5 Lite</h2>
        <p><b>Version 2.0.0</b> — Your Private AI Companion</p>
        <p>An Edge AI assistant that runs entirely on your device.</p>
        <p>No cloud, no API keys, complete privacy.</p>
        <br>
        <p><b>Created by Sur5ve LLC</b></p>
        <p><a href="https://sur5ve.com">https://sur5ve.com</a></p>
        <br>
        <p><i>Licensed under MIT License</i></p>
        <p>For commercial licensing: support@sur5ve.com</p>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("About Sur5 Lite")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(about_text)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        # Remove focus outline from OK button
        msg.setStyleSheet("""
            QPushButton {
                min-width: 80px;
                min-height: 30px;
            }
            QPushButton:focus {
                outline: none;
                border: 2px solid #bd93f9;
            }
        """)
        
        msg.exec()
    
    def _show_info_dialog(self, title: str, content: str):
        """Show informational dialog"""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(content)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setStyleSheet("""
            QPushButton {
                min-width: 80px;
                min-height: 30px;
            }
            QPushButton:focus {
                outline: none;
                border: 2px solid #20B2AA;
            }
        """)
        msg.exec()
    
    def _show_coming_soon(self, feature_name: str):
        """Show coming soon message"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Coming Soon")
        msg.setText(f"<h3>{feature_name}</h3><p>This feature will be available in a future update.</p>")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setStyleSheet("""
            QPushButton {
                min-width: 80px;
                min-height: 30px;
            }
            QPushButton:focus {
                outline: none;
                border: 2px solid #20B2AA;
            }
        """)
        msg.exec()
        
    # Service event handlers
    @Slot(str, str)
    def _on_model_loaded(self, model_name: str, model_path: str):
        """Handle model loaded event"""
        self.status_bar.showMessage(f"Sur ready: {model_name}")
        logger.info(f"Model loaded: {model_name}")
        
    @Slot(str)
    def _on_model_error(self, error_message: str):
        """Handle model error event"""
        self.status_bar.showMessage(f"❌ Sur error: {error_message}")
        logger.error(f"Model error: {error_message}")
        
    @Slot(str, int)
    def _on_model_loading_progress(self, message: str, progress: int):
        """Handle model loading progress"""
        self.status_bar.showMessage(f"Sur is loading model... {progress}%")
        
            
    @Slot(dict)
    def _on_message_received(self, message_data: dict):
        """Handle new message received"""
        # Show completion status for assistant messages
        if message_data.get("role") == "assistant":
            self.status_bar.showMessage("Response complete", 3000)
            
            # Send notification if enabled
            if self.notification_service:
                model_name = ""
                if hasattr(self, 'model_service') and self.model_service:
                    model_name = self.model_service.get_current_model_name() or ""
                self.notification_service.notify_generation_complete(model_name)
        
        # Message is already handled by chat_container
        
    @Slot()
    def _on_thinking_started(self):
        """Handle thinking mode started"""
        self.status_bar.showMessage("Processing...")

    @Slot(str)
    def _on_conversation_error(self, error_message: str):
        """Handle conversation error"""
        self.status_bar.showMessage(f"❌ Error: {error_message}")
        logger.error(f"Conversation error: {error_message}")
        
    def closeEvent(self, event):
        """Handle window close event"""
        try:
            # Check if we should minimize to tray instead of closing
            if self.system_tray_manager and self.system_tray_manager.handle_close_event():
                event.ignore()
                return
            
            # Save settings before closing
            app = QApplication.instance()
            if hasattr(app, 'settings_manager'):
                app.settings_manager.save_settings()
                # Persist splitter sizes from chat container
                try:
                    from PySide6.QtWidgets import QSplitter
                    if self.chat_container:
                        splitter = self.chat_container.findChild(QSplitter)
                        if splitter:
                            app.settings_manager.set_setting('splitter_sizes', splitter.sizes())
                except Exception:
                    pass
            
            # Cleanup cross-platform enhancements
            if self.system_tray_manager:
                self.system_tray_manager.cleanup()
                
            # Clean up services
            if hasattr(self, 'model_service'):
                self.model_service.cleanup()
                
            logger.info("Sur5 application closed gracefully")
            
        except Exception as e:
            logger.warning(f"Error during shutdown: {e}")
            
        event.accept()
