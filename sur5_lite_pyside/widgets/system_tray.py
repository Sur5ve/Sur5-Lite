#!/usr/bin/env python3
"""
System Tray Integration
Allows Sur5 to minimize to system tray for background operation.

Features:
- Tray icon with context menu (Show, New Conversation, Quit)
- Double-click to show/hide main window
- Optional: Show notification when generation completes
- Setting to enable/disable in Settings panel

Resource Impact: ~0.001% CPU (idle icon), ~200KB RAM
"""

from pathlib import Path
from typing import Optional, TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow


class SystemTrayManager(QObject):
    """Manages system tray icon and interactions.
    
    Signals:
        show_requested: Emitted when user requests to show the main window
        hide_requested: Emitted when user requests to hide the main window
        new_conversation_requested: Emitted when user requests a new conversation
        quit_requested: Emitted when user requests to quit the application
    """
    
    # Signals
    show_requested = Signal()
    hide_requested = Signal()
    new_conversation_requested = Signal()
    quit_requested = Signal()
    
    def __init__(self, main_window: "QMainWindow", parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self._main_window = main_window
        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._tray_menu: Optional[QMenu] = None
        self._enabled = False
        self._minimize_to_tray = False
        
        # Create tray icon (but don't show yet)
        self._setup_tray_icon()
    
    def _setup_tray_icon(self) -> None:
        """Create and configure the system tray icon."""
        # Check if system tray is available
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("⚠️ System tray not available on this platform")
            return
        
        # Create tray icon
        self._tray_icon = QSystemTrayIcon(self._main_window)
        
        # Load icon
        icon = self._load_tray_icon()
        if icon:
            self._tray_icon.setIcon(icon)
        
        # Set tooltip
        self._tray_icon.setToolTip("Sur5 Lite — Open Source Edge AI")
        
        # Create context menu
        self._tray_menu = QMenu()
        
        # Show/Hide action
        self._show_action = QAction("Show Sur5", self._tray_menu)
        self._show_action.triggered.connect(self._on_show_clicked)
        self._tray_menu.addAction(self._show_action)
        
        self._tray_menu.addSeparator()
        
        # New Conversation action
        new_conv_action = QAction("New Conversation", self._tray_menu)
        new_conv_action.triggered.connect(self._on_new_conversation_clicked)
        self._tray_menu.addAction(new_conv_action)
        
        self._tray_menu.addSeparator()
        
        # Quit action
        quit_action = QAction("Quit Sur5", self._tray_menu)
        quit_action.triggered.connect(self._on_quit_clicked)
        self._tray_menu.addAction(quit_action)
        
        self._tray_icon.setContextMenu(self._tray_menu)
        
        # signals
        self._tray_icon.activated.connect(self._on_tray_activated)
    
    def _load_tray_icon(self) -> Optional[QIcon]:
        """Load the tray icon from resources."""
        try:
            # Try to find icon in common locations
            base_paths = [
                Path(__file__).parent.parent.parent / "Images",
                Path(__file__).parent.parent / "Images",
                Path(__file__).parent / "Images",
            ]
            
            icon_names = ["sur5_icon.ico", "sur5_icon.png", "icon.ico", "icon.png"]
            
            for base_path in base_paths:
                for icon_name in icon_names:
                    icon_path = base_path / icon_name
                    if icon_path.exists():
                        icon = QIcon(str(icon_path))
                        if not icon.isNull():
                            return icon
            
            # Fallback to application icon
            app = QApplication.instance()
            if app and not app.windowIcon().isNull():
                return app.windowIcon()
            
        except Exception as e:
            print(f"⚠️ Could not load tray icon: {e}")
        
        return None
    
    @property
    def is_available(self) -> bool:
        """Check if system tray is available."""
        return self._tray_icon is not None
    
    @property
    def is_enabled(self) -> bool:
        """Check if system tray is currently enabled."""
        return self._enabled
    
    @property
    def minimize_to_tray(self) -> bool:
        """Check if minimize to tray on close is enabled."""
        return self._minimize_to_tray
    
    @minimize_to_tray.setter
    def minimize_to_tray(self, value: bool) -> None:
        """Set minimize to tray on close behavior."""
        self._minimize_to_tray = value
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the system tray icon.
        
        Args:
            enabled: Whether to show the tray icon
        """
        if not self.is_available:
            return
        
        self._enabled = enabled
        
        if enabled:
            self._tray_icon.show()
            print("✓ System tray enabled")
        else:
            self._tray_icon.hide()
            print("✓ System tray disabled")
    
    def show_notification(self, title: str, message: str, 
                         icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
                         duration_ms: int = 5000) -> bool:
        """Show a system tray notification.
        
        Args:
            title: Notification title
            message: Notification message
            icon: Icon type (Information, Warning, Critical, NoIcon)
            duration_ms: Duration to show notification in milliseconds
            
        Returns:
            True if notification was shown, False otherwise
        """
        if not self.is_available or not self._enabled:
            return False
        
        if not self._tray_icon.supportsMessages():
            print("⚠️ System tray does not support messages")
            return False
        
        self._tray_icon.showMessage(title, message, icon, duration_ms)
        return True
    
    def update_show_action_text(self) -> None:
        """Update the show/hide action text based on window visibility."""
        if not self.is_available:
            return
        
        if self._main_window.isVisible() and not self._main_window.isMinimized():
            self._show_action.setText("Hide Sur5")
        else:
            self._show_action.setText("Show Sur5")
    
    @Slot(QSystemTrayIcon.ActivationReason)
    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation (click, double-click, etc.)."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_window_visibility()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Single click - some platforms use this instead of double-click
            # On Windows, this is left-click; we'll use it to show the window
            if not self._main_window.isVisible() or self._main_window.isMinimized():
                self._show_window()
    
    def _toggle_window_visibility(self) -> None:
        """Toggle main window visibility."""
        if self._main_window.isVisible() and not self._main_window.isMinimized():
            self._hide_window()
        else:
            self._show_window()
    
    def _show_window(self) -> None:
        """Show and activate the main window."""
        self._main_window.show()
        self._main_window.showNormal()  # Restore if minimized
        self._main_window.raise_()
        self._main_window.activateWindow()
        self.update_show_action_text()
        self.show_requested.emit()
    
    def _hide_window(self) -> None:
        """Hide the main window to tray."""
        self._main_window.hide()
        self.update_show_action_text()
        self.hide_requested.emit()
    
    @Slot()
    def _on_show_clicked(self) -> None:
        """Handle show/hide action clicked."""
        self._toggle_window_visibility()
    
    @Slot()
    def _on_new_conversation_clicked(self) -> None:
        """Handle new conversation action clicked."""
        self._show_window()
        self.new_conversation_requested.emit()
    
    @Slot()
    def _on_quit_clicked(self) -> None:
        """Handle quit action clicked."""
        self.quit_requested.emit()
    
    def handle_close_event(self) -> bool:
        """Handle main window close event.
        
        Call this from the main window's closeEvent.
        
        Returns:
            True if the close event should be ignored (minimize to tray),
            False if the application should actually close.
        """
        if self._enabled and self._minimize_to_tray:
            self._hide_window()
            self.show_notification(
                "Sur5 Minimized",
                "Sur5 is still running in the system tray.",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
            return True  # Ignore close event
        
        return False  # Allow close event
    
    def cleanup(self) -> None:
        """Clean up tray icon before application exit."""
        if self._tray_icon:
            self._tray_icon.hide()
            self._tray_icon = None


def is_system_tray_available() -> bool:
    """Check if system tray is available on this platform.
    
    Returns:
        True if system tray is available
    """
    return QSystemTrayIcon.isSystemTrayAvailable()






