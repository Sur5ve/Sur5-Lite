#!/usr/bin/env python3
"""
Sur5 Keyboard Shortcuts Manager
Centralized keyboard shortcut management for comprehensive keyboard control
"""

from typing import Dict, List, Tuple, Callable, Optional
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import QObject

from utils.logger import create_module_logger
logger = create_module_logger(__name__)


class KeyboardShortcutManager(QObject):
    """Centralized keyboard shortcut management system
    
    Manages all application keyboard shortcuts with conflict detection
    and provides comprehensive help documentation.
    """
    
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.shortcuts: Dict[str, QShortcut] = {}
        self.shortcut_registry: Dict[str, Tuple[str, str, str]] = {}  # key: (sequence, description, category)
        
    def register_shortcut(
        self,
        name: str,
        key_sequence: str,
        callback: Callable,
        description: str,
        category: str,
        context=None
    ) -> QShortcut:
        """Register a keyboard shortcut
        
        Args:
            name: Unique identifier for the shortcut
            key_sequence: Key sequence (e.g., "Ctrl+S", "F1")
            callback: Function to call when shortcut is activated
            description: Human-readable description
            category: Category for organization in help dialog
            context: Widget context (None = application-wide)
            
        Returns:
            QShortcut object
        """
        # Check for conflicts
        if name in self.shortcuts:
            logger.warning(f"Shortcut '{name}' already registered, skipping")
            return self.shortcuts[name]
        
        # Create shortcut
        if context is None:
            context = self.main_window
        
        shortcut = QShortcut(QKeySequence(key_sequence), context)
        shortcut.activated.connect(callback)
        
        # Store shortcut and metadata
        self.shortcuts[name] = shortcut
        self.shortcut_registry[name] = (key_sequence, description, category)
        
        return shortcut
    
    def get_shortcuts_by_category(self) -> Dict[str, List[Tuple[str, str]]]:
        """Get all shortcuts organized by category
        
        Returns:
            Dict mapping category name to list of (key_sequence, description) tuples
        """
        categories: Dict[str, List[Tuple[str, str]]] = {}
        
        for name, (sequence, description, category) in self.shortcut_registry.items():
            if category not in categories:
                categories[category] = []
            categories[category].append((sequence, description))
        
        # Sort shortcuts within each category
        for category in categories:
            categories[category].sort(key=lambda x: x[0])
        
        return categories
    
    def setup_shortcuts(self):
        """Setup all application shortcuts
        
        Organized by category:
        1. Basic Input
        2. Send/Stop
        3. Chat Management
        4. Search
        5. Navigation
        6. Text Editing
        7. Model/Settings
        8. File Operations
        9. UI Controls
        10. Help
        """
        # Get references to components
        chat_container = getattr(self.main_window, 'chat_container', None)
        composer = chat_container.composer if chat_container else None
        
        # ═══════════════════════════════════════════════════════════
        # 1. BASIC INPUT (Already working - just register for docs)
        # ═══════════════════════════════════════════════════════════
        # Note: Enter, Shift+Enter handled in composer.py eventFilter
        # We register them here for documentation only
        self.shortcut_registry["send_enter"] = (
            "Return", "Send message", "💬 Basic Input"
        )
        self.shortcut_registry["newline_shift_enter"] = (
            "Shift+Return", "New line in input", "💬 Basic Input"
        )
        self.shortcut_registry["send_ctrl_return"] = (
            "Ctrl+Return", "Send message (alternative)", "💬 Basic Input"
        )
        
        # ═══════════════════════════════════════════════════════════
        # 2. SEND/STOP
        # ═══════════════════════════════════════════════════════════
        if composer:
            # Ctrl+S - Alternative send
            self.register_shortcut(
                "send_ctrl_s",
                "Ctrl+S",
                lambda: composer._send_message() if hasattr(composer, '_send_message') else None,
                "Send message (alternative)",
                "🚀 Send/Stop"
            )
            
            # Escape - Stop generation
            self.register_shortcut(
                "stop_escape",
                "Escape",
                lambda: self._stop_generation(),
                "Stop generation",
                "🚀 Send/Stop"
            )
        
        # ═══════════════════════════════════════════════════════════
        # 3. CHAT MANAGEMENT
        # ═══════════════════════════════════════════════════════════
        # Ctrl+N - New conversation (already exists in menu)
        self.register_shortcut(
            "new_chat_ctrl_n",
            "Ctrl+N",
            lambda: self.main_window._new_conversation(),
            "New conversation",
            "💬 Chat Management"
        )
        
        # Ctrl+X - Clear chat (alias for Ctrl+N)
        self.register_shortcut(
            "clear_chat_ctrl_x",
            "Ctrl+X",
            lambda: self.main_window._new_conversation(),
            "Clear chat (alternative)",
            "💬 Chat Management"
        )
        
        # Ctrl+R - Regenerate last (PLACEHOLDER - Phase 7)
        self.register_shortcut(
            "regenerate_ctrl_r",
            "Ctrl+R",
            lambda: self._placeholder_feature("Regenerate last response"),
            "Regenerate last response",
            "💬 Chat Management"
        )
        
        # Ctrl+Shift+C - Copy last response (PLACEHOLDER - Phase 7)
        self.register_shortcut(
            "copy_last_ctrl_shift_c",
            "Ctrl+Shift+C",
            lambda: self._placeholder_feature("Copy last response"),
            "Copy last assistant response",
            "💬 Chat Management"
        )
        
        # ═══════════════════════════════════════════════════════════
        # 4. SEARCH - Handled by Edit menu QActions in main_window.py
        # ═══════════════════════════════════════════════════════════
        # Ctrl+F, F3, Shift+F3 handled by QAction
        # in the Edit menu to avoid ambiguous shortcut conflicts.
        # See main_window._create_menu_bar() for implementation.
        
        # ═══════════════════════════════════════════════════════════
        # 5. NAVIGATION (PLACEHOLDER - Phase 7)
        # ═══════════════════════════════════════════════════════════
        self.register_shortcut(
            "nav_prev_ctrl_up",
            "Ctrl+Up",
            lambda: self._placeholder_feature("Navigate to previous message"),
            "Navigate to previous message",
            "🧭 Navigation"
        )
        
        self.register_shortcut(
            "nav_next_ctrl_down",
            "Ctrl+Down",
            lambda: self._placeholder_feature("Navigate to next message"),
            "Navigate to next message",
            "🧭 Navigation"
        )
        
        self.register_shortcut(
            "scroll_up_pgup",
            "Page Up",
            lambda: self._scroll_history("up"),
            "Scroll up",
            "🧭 Navigation"
        )
        
        self.register_shortcut(
            "scroll_down_pgdn",
            "Page Down",
            lambda: self._scroll_history("down"),
            "Scroll down",
            "🧭 Navigation"
        )
        
        self.register_shortcut(
            "scroll_top_home",
            "Home",
            lambda: self._scroll_history("top"),
            "Scroll to top",
            "🧭 Navigation"
        )
        
        self.register_shortcut(
            "scroll_bottom_end",
            "End",
            lambda: self._scroll_history("bottom"),
            "Scroll to bottom",
            "🧭 Navigation"
        )
        
        # ═══════════════════════════════════════════════════════════
        # 6. TEXT EDITING
        # ═══════════════════════════════════════════════════════════
        # Note: Advanced editing (Ctrl+Backspace, Tab, etc.) handled in composer.py
        # Built-in shortcuts (Ctrl+A, Ctrl+Z, Ctrl+Y) work automatically
        # We just register them for documentation
        
        self.shortcut_registry["select_all"] = (
            "Ctrl+A", "Select all text", "✏️ Text Editing"
        )
        self.shortcut_registry["undo"] = (
            "Ctrl+Z", "Undo", "✏️ Text Editing"
        )
        self.shortcut_registry["redo"] = (
            "Ctrl+Y", "Redo", "✏️ Text Editing"
        )
        
        # Advanced editing will be in composer.py eventFilter (Phase 6)
        self.shortcut_registry["delete_word_back"] = (
            "Ctrl+Backspace", "Delete word backward", "✏️ Text Editing"
        )
        self.shortcut_registry["delete_word_forward"] = (
            "Ctrl+Delete", "Delete word forward", "✏️ Text Editing"
        )
        self.shortcut_registry["indent_tab"] = (
            "Tab", "Insert 4 spaces (indent)", "✏️ Text Editing"
        )
        self.shortcut_registry["dedent_shift_tab"] = (
            "Shift+Tab", "Remove 4 spaces (dedent)", "✏️ Text Editing"
        )
        
        # ═══════════════════════════════════════════════════════════
        # 7. MODEL/SETTINGS
        # ═══════════════════════════════════════════════════════════
        # Ctrl+P - Edit system prompt (PLACEHOLDER - needs dialog)
        self.register_shortcut(
            "edit_prompt_ctrl_p",
            "Ctrl+P",
            lambda: self._placeholder_feature("Edit system prompt"),
            "Edit system prompt",
            "⚙️ Model/Settings"
        )
        
        # Ctrl+, - Open preferences (already exists)
        # Note: Already wired in main_window.py menu, just register for docs
        self.shortcut_registry["preferences_ctrl_comma"] = (
            "Ctrl+,", "Open preferences", "⚙️ Model/Settings"
        )
        
        # Ctrl+O - Select model
        self.register_shortcut(
            "select_model_ctrl_o",
            "Ctrl+O",
            lambda: self._select_model(),
            "Select model file",
            "⚙️ Model/Settings"
        )
        
        # F5 - Refresh/reload model (PLACEHOLDER)
        self.register_shortcut(
            "refresh_model_f5",
            "F5",
            lambda: self._placeholder_feature("Refresh model"),
            "Refresh/reload model",
            "⚙️ Model/Settings"
        )
        
        # ═══════════════════════════════════════════════════════════
        # 8. FILE OPERATIONS (PLACEHOLDER - Phase 2)
        # ═══════════════════════════════════════════════════════════
        self.register_shortcut(
            "save_conv_ctrl_shift_s",
            "Ctrl+Shift+S",
            lambda: self._placeholder_feature("Save conversation as"),
            "Save conversation as...",
            "📁 File Operations"
        )
        
        self.register_shortcut(
            "export_chat_ctrl_e",
            "Ctrl+E",
            lambda: self._placeholder_feature("Export chat"),
            "Export chat history",
            "📁 File Operations"
        )
        
        self.register_shortcut(
            "import_chat_ctrl_i",
            "Ctrl+I",
            lambda: self._placeholder_feature("Import chat"),
            "Import chat history",
            "📁 File Operations"
        )
        
        # ═══════════════════════════════════════════════════════════
        # 9. UI CONTROLS (PLACEHOLDER - Phase 5)
        # ═══════════════════════════════════════════════════════════
        self.register_shortcut(
            "fullscreen_f11",
            "F11",
            lambda: self._placeholder_feature("Toggle fullscreen"),
            "Toggle fullscreen",
            "🎨 UI Controls"
        )
        
        self.register_shortcut(
            "toggle_sidebar_ctrl_b",
            "Ctrl+B",
            lambda: self._placeholder_feature("Toggle sidebar"),
            "Toggle sidebar visibility",
            "🎨 UI Controls"
        )
        
        # ═══════════════════════════════════════════════════════════
        # 10. HELP
        # ═══════════════════════════════════════════════════════════
        self.register_shortcut(
            "help_f1",
            "F1",
            lambda: self._placeholder_feature("Show help dialog"),
            "Show keyboard shortcuts & help",
            "❓ Help"
        )
        
        self.register_shortcut(
            "help_ctrl_question",
            "Ctrl+?",
            lambda: self._placeholder_feature("Show help dialog"),
            "Show keyboard shortcuts (alternative)",
            "❓ Help"
        )
        
        logger.debug(f"shortcuts: {len(self.shortcuts)}")
    
    # ═══════════════════════════════════════════════════════════════
    # Helper Methods
    # ═══════════════════════════════════════════════════════════════
    
    def _placeholder_feature(self, feature_name: str):
        """Show non-intrusive status bar message for features not yet implemented"""
        logger.debug(f"placeholder: {feature_name}")
        try:
            # Show in status bar instead of modal dialog (less intrusive)
            if hasattr(self.main_window, 'status_bar') and self.main_window.status_bar:
                self.main_window.status_bar.showMessage(
                    f"⏳ {feature_name} - Coming in a future update", 3000
                )
        except Exception as e:
            logger.debug(f"status msg err: {e}")
    
    def _stop_generation(self):
        """Stop current generation"""
        try:
            chat_container = getattr(self.main_window, 'chat_container', None)
            if chat_container and hasattr(chat_container, 'composer'):
                composer = chat_container.composer
                # Trigger the stop mechanism (same as clicking stop button)
                if hasattr(composer, 'send_button') and composer.send_button:
                    # If button shows "Stop", click it
                    if composer.send_button.text() == "Stop":
                        composer.send_button.click()
        except Exception as e:
            logger.warning(f"Stop generation error: {e}")
    
    def _scroll_history(self, direction: str):
        """Scroll chat history"""
        try:
            chat_container = getattr(self.main_window, 'chat_container', None)
            if not chat_container or not hasattr(chat_container, 'thread_view'):
                return
            
            thread_view = chat_container.thread_view
            scrollbar = thread_view.verticalScrollBar()
            
            if direction == "up":
                # Page up - scroll up by viewport height
                scrollbar.setValue(scrollbar.value() - thread_view.viewport().height())
            elif direction == "down":
                # Page down - scroll down by viewport height
                scrollbar.setValue(scrollbar.value() + thread_view.viewport().height())
            elif direction == "top":
                # Home - scroll to top
                scrollbar.setValue(scrollbar.minimum())
            elif direction == "bottom":
                # End - scroll to bottom
                scrollbar.setValue(scrollbar.maximum())
        except Exception as e:
            logger.warning(f"Scroll error: {e}")
    
    def _select_model(self):
        """Trigger model selection"""
        try:
            chat_container = getattr(self.main_window, 'chat_container', None)
            if chat_container and hasattr(chat_container, 'model_panel'):
                model_panel = chat_container.model_panel
                if hasattr(model_panel, 'load_button'):
                    model_panel.load_button.click()
        except Exception as e:
            logger.warning(f"Select model error: {e}")
    


