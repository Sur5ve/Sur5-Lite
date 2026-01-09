#!/usr/bin/env python3
"""
File Dialog Helpers
Provides file dialogs for conversation save/load/export operations
"""

from typing import Optional, Tuple
from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QWidget


def show_save_conversation_dialog(parent: QWidget = None) -> Optional[str]:
    """
    Show save conversation dialog
    
    Args:
        parent: Parent widget
        
    Returns:
        Selected filepath or None if cancelled
    """
    default_dir = str(Path.home() / "Documents" / "Sur5" / "Conversations")
    
    filepath, _ = QFileDialog.getSaveFileName(
        parent,
        "Save Conversation",
        default_dir,
        "Sur5 Chat Files (*.sur5chat);;All Files (*.*)",
        "Sur5 Chat Files (*.sur5chat)"
    )
    
    if filepath:
        # Ensure .sur5chat extension
        if not filepath.endswith('.sur5chat'):
            filepath += '.sur5chat'
    
    return filepath if filepath else None


def show_load_conversation_dialog(parent: QWidget = None) -> Optional[str]:
    """
    Show load conversation dialog
    
    Args:
        parent: Parent widget
        
    Returns:
        Selected filepath or None if cancelled
    """
    default_dir = str(Path.home() / "Documents" / "Sur5" / "Conversations")
    
    filepath, _ = QFileDialog.getOpenFileName(
        parent,
        "Load Conversation",
        default_dir,
        "Sur5 Chat Files (*.sur5chat);;All Files (*.*)",
        "Sur5 Chat Files (*.sur5chat)"
    )
    
    return filepath if filepath else None


def show_export_text_dialog(parent: QWidget = None) -> Optional[str]:
    """
    Show export to text dialog
    
    Args:
        parent: Parent widget
        
    Returns:
        Selected filepath or None if cancelled
    """
    default_dir = str(Path.home() / "Documents" / "Sur5" / "Exports")
    
    filepath, _ = QFileDialog.getSaveFileName(
        parent,
        "Export Conversation to Text",
        default_dir,
        "Text Files (*.txt);;All Files (*.*)",
        "Text Files (*.txt)"
    )
    
    if filepath:
        # Ensure .txt extension
        if not filepath.endswith('.txt'):
            filepath += '.txt'
    
    return filepath if filepath else None


def show_export_markdown_dialog(parent: QWidget = None) -> Optional[str]:
    """
    Show export to markdown dialog
    
    Args:
        parent: Parent widget
        
    Returns:
        Selected filepath or None if cancelled
    """
    default_dir = str(Path.home() / "Documents" / "Sur5" / "Exports")
    
    filepath, _ = QFileDialog.getSaveFileName(
        parent,
        "Export Conversation to Markdown",
        default_dir,
        "Markdown Files (*.md);;All Files (*.*)",
        "Markdown Files (*.md)"
    )
    
    if filepath:
        # Ensure .md extension
        if not filepath.endswith('.md'):
            filepath += '.md'
    
    return filepath if filepath else None


def show_export_format_dialog(parent: QWidget = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Show export dialog with format selection
    
    Args:
        parent: Parent widget
        
    Returns:
        Tuple of (filepath, format) where format is 'text' or 'markdown'
        Returns (None, None) if cancelled
    """
    default_dir = str(Path.home() / "Documents" / "Sur5" / "Exports")
    
    filepath, selected_filter = QFileDialog.getSaveFileName(
        parent,
        "Export Conversation",
        default_dir,
        "Text Files (*.txt);;Markdown Files (*.md);;All Files (*.*)",
        "Text Files (*.txt)"
    )
    
    if not filepath:
        return None, None
    
    # Determine format from filter or extension
    if "Markdown" in selected_filter or filepath.endswith('.md'):
        if not filepath.endswith('.md'):
            filepath += '.md'
        return filepath, 'markdown'
    else:
        if not filepath.endswith('.txt'):
            filepath += '.txt'
        return filepath, 'text'

