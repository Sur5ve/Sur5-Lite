#!/usr/bin/env python3
"""
Menu Builder Module - Sur5ve Protected Core
Creates application menu bar for Sur5 Main Window

Sur5ve LLC - Proprietary Code
Licensed under MIT License
"""

from typing import Dict, Any, Callable, Optional

from PySide6.QtWidgets import QMainWindow, QMenuBar
from PySide6.QtGui import QAction, QKeySequence

# Sur5ve Theme - Single theme for brand consistency
try:
    from themes.theme_manager import THEME_KEY_TO_DISPLAY, THEME_DISPLAY_TO_KEY
except Exception:
    THEME_KEY_TO_DISPLAY = {
        "sur5ve": "Sur5ve",
    }
    THEME_DISPLAY_TO_KEY = {v: k for k, v in THEME_KEY_TO_DISPLAY.items()}


class MenuBuilder:
    """Builds application menu bar with all menus and actions"""
    
    def __init__(self, window: QMainWindow, callbacks: Dict[str, Callable]):
        """Initialize menu builder
        
        Args:
            window: Main window to attach menu bar to
            callbacks: Dictionary of callback functions for menu actions
        """
        self.window = window
        self.callbacks = callbacks
    
    def build(self) -> QMenuBar:
        """Build and return the complete menu bar"""
        menubar = self.window.menuBar()
        
        # Fix for macOS: Force menu bar in window for consistent cross-platform behavior
        menubar.setNativeMenuBar(False)
        
        self._build_file_menu(menubar)
        self._build_edit_menu(menubar)
        self._build_view_menu(menubar)
        self._build_performance_menu(menubar)
        self._build_help_menu(menubar)
        
        return menubar
    
    def _build_file_menu(self, menubar: QMenuBar) -> None:
        """Build the File menu"""
        file_menu = menubar.addMenu("&File")
        
        # New conversation
        new_action = QAction("&New Conversation", self.window)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.callbacks.get("new_conversation", lambda: None))
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        # Save conversation
        save_action = QAction("&Save Conversation", self.window)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.callbacks.get("save_conversation", lambda: None))
        file_menu.addAction(save_action)
        
        # Save conversation as
        save_as_action = QAction("Save Conversation &As...", self.window)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        save_as_action.triggered.connect(self.callbacks.get("save_conversation_as", lambda: None))
        file_menu.addAction(save_as_action)
        
        # Load conversation
        load_action = QAction("&Open Conversation...", self.window)
        load_action.setShortcut(QKeySequence.Open)
        load_action.triggered.connect(self.callbacks.get("load_conversation", lambda: None))
        file_menu.addAction(load_action)
        
        file_menu.addSeparator()
        
        # Export submenu
        export_menu = file_menu.addMenu("&Export Conversation")
        
        export_text_action = QAction("As &Text (.txt)...", self.window)
        export_text_action.setShortcut(QKeySequence("Ctrl+Shift+T"))
        export_text_action.triggered.connect(self.callbacks.get("export_text", lambda: None))
        export_menu.addAction(export_text_action)
        
        export_md_action = QAction("As &Markdown (.md)...", self.window)
        export_md_action.setShortcut(QKeySequence("Ctrl+Shift+M"))
        export_md_action.triggered.connect(self.callbacks.get("export_markdown", lambda: None))
        export_menu.addAction(export_md_action)
        
        file_menu.addSeparator()
        
        # Exit
        exit_action = QAction("E&xit", self.window)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.window.close)
        file_menu.addAction(exit_action)
    
    def _build_edit_menu(self, menubar: QMenuBar) -> None:
        """Build the Edit menu"""
        edit_menu = menubar.addMenu("&Edit")
        
        # Find
        find_action = QAction("&Find in Chat...", self.window)
        find_action.setShortcut(QKeySequence.Find)
        find_action.triggered.connect(self.callbacks.get("find", lambda: None))
        edit_menu.addAction(find_action)
        
        # Find Next
        find_next_action = QAction("Find &Next", self.window)
        find_next_action.setShortcut(QKeySequence("F3"))
        find_next_action.triggered.connect(self.callbacks.get("find_next", lambda: None))
        edit_menu.addAction(find_next_action)
        
        # Find Previous
        find_prev_action = QAction("Find &Previous", self.window)
        find_prev_action.setShortcut(QKeySequence("Shift+F3"))
        find_prev_action.triggered.connect(self.callbacks.get("find_previous", lambda: None))
        edit_menu.addAction(find_prev_action)
    
    def _build_view_menu(self, menubar: QMenuBar) -> None:
        """Build the View menu"""
        view_menu = menubar.addMenu("&View")
        
        # Theme submenu
        theme_menu = view_menu.addMenu("Theme")
        apply_theme = self.callbacks.get("apply_theme", lambda t: None)
        for key, display in THEME_KEY_TO_DISPLAY.items():
            action = QAction(display, self.window)
            action.triggered.connect(lambda checked=False, t=key: apply_theme(t))
            theme_menu.addAction(action)
        
        # Font Size submenu
        font_menu = view_menu.addMenu("Font Size")
        set_font_size = self.callbacks.get("set_font_size", lambda s: None)
        for size, label in [(9, "Small"), (11, "Medium"), (13, "Large")]:
            act = QAction(label, self.window)
            act.triggered.connect(lambda checked=False, s=size: set_font_size(s))
            font_menu.addAction(act)
    
    def _build_performance_menu(self, menubar: QMenuBar) -> None:
        """Build the Performance menu"""
        perf_menu = menubar.addMenu("&Performance")
        perf_menu.setToolTipsVisible(True)
        
        toggle_virtualization = self.callbacks.get("toggle_virtualization", lambda v: None)
        
        conv_render = QAction("Enable Message Virtualization", self.window)
        conv_render.setCheckable(True)
        conv_render.setChecked(False)
        conv_render.setToolTip(
            "UI Optimization: Renders only visible messages in long conversations.\n"
            "• Improves scrolling performance with 100+ messages\n"
            "• Does NOT affect AI model context or memory\n"
            "• Purely a visual rendering optimization"
        )
        conv_render.toggled.connect(toggle_virtualization)
        perf_menu.addAction(conv_render)
        
        show_coming_soon = self.callbacks.get("show_coming_soon", lambda msg: None)
        
        virt_threshold = QAction("Set Virtualization Threshold…", self.window)
        virt_threshold.setToolTip(
            "Configure when virtualization activates (e.g., after 50 messages).\n"
            "Lower = better performance, but activates sooner.\n"
            "This is a UI setting only."
        )
        virt_threshold.triggered.connect(lambda: show_coming_soon("Virtualization threshold configuration"))
        perf_menu.addAction(virt_threshold)
    
    def _build_help_menu(self, menubar: QMenuBar) -> None:
        """Build the Help menu"""
        help_menu = menubar.addMenu("&Help")
        
        # View Logs
        from widgets.dialogs import show_log_viewer
        logs_action = QAction("View &Logs...", self.window)
        logs_action.triggered.connect(lambda: show_log_viewer(self.window))
        help_menu.addAction(logs_action)
        
        help_menu.addSeparator()
        
        # About - Sur5ve Protected
        show_about = self.callbacks.get("show_about", lambda: None)
        about_action = QAction("&About Sur5ve", self.window)
        about_action.triggered.connect(show_about)
        help_menu.addAction(about_action)


def create_menu_bar(window: QMainWindow, callbacks: Dict[str, Callable]) -> QMenuBar:
    """Convenience function to create a menu bar
    
    Args:
        window: Main window to attach menu bar to
        callbacks: Dictionary of callback functions for menu actions
    
    Returns:
        QMenuBar: The created menu bar
    """
    builder = MenuBuilder(window, callbacks)
    return builder.build()


# Expose commonly used items
__all__ = [
    "MenuBuilder",
    "create_menu_bar",
    "THEME_KEY_TO_DISPLAY",
    "THEME_DISPLAY_TO_KEY",
]

