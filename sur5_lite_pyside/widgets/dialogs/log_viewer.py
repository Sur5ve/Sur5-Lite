#!/usr/bin/env python3
"""
Log Viewer Dialog
Displays application logs in a user-friendly dialog with filtering and export capabilities.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QComboBox, QLabel, QFileDialog, QApplication
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QTextCharFormat, QColor, QTextCursor

from utils.logger import get_recent_logs, get_log_file_path


class LogViewerDialog(QDialog):
    """Dialog to view and filter application logs."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sur5 Log Viewer")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)
        
        self._setup_ui()
        self._load_logs()
        
        # Auto-refresh timer (every 5 seconds when dialog is open)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._load_logs)
        self._refresh_timer.start(5000)
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Header with controls
        header = QHBoxLayout()
        
        # Filter dropdown
        header.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All Levels",
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL"
        ])
        self.filter_combo.currentTextChanged.connect(self._apply_filter)
        header.addWidget(self.filter_combo)
        
        header.addStretch()
        
        # Line count selector
        header.addWidget(QLabel("Lines:"))
        self.lines_combo = QComboBox()
        self.lines_combo.addItems(["100", "500", "1000", "5000"])
        self.lines_combo.setCurrentText("500")
        self.lines_combo.currentTextChanged.connect(self._load_logs)
        header.addWidget(self.lines_combo)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._load_logs)
        header.addWidget(refresh_btn)
        
        layout.addLayout(header)
        
        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        
        # Use monospace font
        font = QFont("Consolas", 9)
        if not font.exactMatch():
            font = QFont("Monaco", 9)
            if not font.exactMatch():
                font = QFont("Courier New", 9)
        self.log_display.setFont(font)
        
        layout.addWidget(self.log_display)
        
        # Footer with buttons
        footer = QHBoxLayout()
        
        # Log file path label
        log_path = get_log_file_path()
        path_label = QLabel(f"Log file: {log_path}")
        path_label.setStyleSheet("color: gray; font-size: 10px;")
        footer.addWidget(path_label)
        
        footer.addStretch()
        
        # Copy button
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self._copy_to_clipboard)
        footer.addWidget(copy_btn)
        
        # Export button
        export_btn = QPushButton("Export to File...")
        export_btn.clicked.connect(self._export_logs)
        footer.addWidget(export_btn)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        
        layout.addLayout(footer)
    
    def _load_logs(self):
        """Load logs from file."""
        try:
            lines = int(self.lines_combo.currentText())
            self._raw_logs = get_recent_logs(lines)
            self._apply_filter()
        except Exception as e:
            self.log_display.setPlainText(f"Error loading logs: {e}")
    
    def _apply_filter(self):
        """Apply the selected filter to the logs."""
        filter_level = self.filter_combo.currentText()
        
        if filter_level == "All Levels":
            filtered = self._raw_logs
        else:
            # Filter lines that contain the selected level
            lines = self._raw_logs.split('\n')
            filtered_lines = [
                line for line in lines
                if f"| {filter_level}" in line or line.strip() == ""
            ]
            filtered = '\n'.join(filtered_lines)
        
        # Color-code the logs
        self.log_display.clear()
        cursor = self.log_display.textCursor()
        
        for line in filtered.split('\n'):
            # Determine color based on log level
            fmt = QTextCharFormat()
            
            if "| ERROR" in line or "| CRITICAL" in line:
                fmt.setForeground(QColor("#ff5555"))  # Red
            elif "| WARNING" in line:
                fmt.setForeground(QColor("#ffb86c"))  # Orange
            elif "| DEBUG" in line:
                fmt.setForeground(QColor("#6272a4"))  # Gray
            elif "| INFO" in line:
                fmt.setForeground(QColor("#50fa7b"))  # Green
            else:
                fmt.setForeground(QColor("#f8f8f2"))  # Default
            
            cursor.insertText(line + '\n', fmt)
        
        # Scroll to bottom
        self.log_display.moveCursor(QTextCursor.MoveOperation.End)
    
    def _copy_to_clipboard(self):
        """Copy logs to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.log_display.toPlainText())
    
    def _export_logs(self):
        """Export logs to a file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Logs",
            "sur5_logs.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_display.toPlainText())
            except Exception as e:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Export Error", f"Could not export logs: {e}")
    
    def closeEvent(self, event):
        """Stop refresh timer when dialog closes."""
        self._refresh_timer.stop()
        super().closeEvent(event)


def show_log_viewer(parent=None):
    """Show the log viewer dialog."""
    dialog = LogViewerDialog(parent)
    dialog.exec()


__all__ = ["LogViewerDialog", "show_log_viewer"]


