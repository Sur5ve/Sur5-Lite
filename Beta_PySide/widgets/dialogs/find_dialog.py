#!/usr/bin/env python3
"""
Find Dialog
Search dialog for finding text in chat history
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QCheckBox, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut


class FindDialog(QDialog):
    """Dialog for searching chat history"""
    
    # Signals
    search_requested = Signal(str, bool, bool, bool)  # term, case_sensitive, search_thinking, use_regex
    find_next_requested = Signal()
    find_previous_requested = Signal()
    closed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Find in Chat")
        self.setModal(False)  # Non-modal so user can interact with chat while searching
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        
        self._setup_ui()
        self._setup_shortcuts()
        
        # Set accessible properties
        self.setAccessibleName("Find Dialog")
        self.setAccessibleDescription("Search for text in chat history")
    
    def _setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        # Search input row
        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        
        label = QLabel("Find:")
        label.setMinimumWidth(40)
        input_row.addWidget(label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search term...")
        self.search_input.setMinimumWidth(300)
        self.search_input.setAccessibleName("Search input")
        self.search_input.setAccessibleDescription("Enter text to search for in chat history")
        input_row.addWidget(self.search_input)
        
        layout.addLayout(input_row)
        
        # Options row
        options_row = QHBoxLayout()
        options_row.setSpacing(12)
        
        self.case_checkbox = QCheckBox("Match case")
        self.case_checkbox.setAccessibleName("Match case checkbox")
        self.case_checkbox.setAccessibleDescription("Enable case-sensitive search")
        options_row.addWidget(self.case_checkbox)
        
        self.thinking_checkbox = QCheckBox("Search thinking")
        self.thinking_checkbox.setChecked(True)
        self.thinking_checkbox.setAccessibleName("Search thinking checkbox")
        self.thinking_checkbox.setAccessibleDescription("Include thinking content in search")
        options_row.addWidget(self.thinking_checkbox)
        
        self.regex_checkbox = QCheckBox("Use regex")
        self.regex_checkbox.setAccessibleName("Use regex checkbox")
        self.regex_checkbox.setAccessibleDescription("Use regular expressions for advanced search")
        options_row.addWidget(self.regex_checkbox)
        
        options_row.addStretch()
        layout.addLayout(options_row)
        
        # Buttons row
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(8)
        
        self.find_button = QPushButton("Find")
        self.find_button.setProperty("class", "primary")
        self.find_button.setMinimumWidth(80)
        self.find_button.setAccessibleName("Find button")
        self.find_button.setAccessibleDescription("Start search (Enter)")
        self.find_button.clicked.connect(self._on_find_clicked)
        buttons_row.addWidget(self.find_button)
        
        self.next_button = QPushButton("Next")
        self.next_button.setMinimumWidth(80)
        self.next_button.setEnabled(False)
        self.next_button.setAccessibleName("Find next button")
        self.next_button.setAccessibleDescription("Go to next result (F3)")
        self.next_button.clicked.connect(self._on_next_clicked)
        buttons_row.addWidget(self.next_button)
        
        self.prev_button = QPushButton("Previous")
        self.prev_button.setMinimumWidth(80)
        self.prev_button.setEnabled(False)
        self.prev_button.setAccessibleName("Find previous button")
        self.prev_button.setAccessibleDescription("Go to previous result (Shift+F3)")
        self.prev_button.clicked.connect(self._on_previous_clicked)
        buttons_row.addWidget(self.prev_button)
        
        buttons_row.addStretch()
        
        self.close_button = QPushButton("Close")
        self.close_button.setMinimumWidth(80)
        self.close_button.setAccessibleName("Close button")
        self.close_button.setAccessibleDescription("Close find dialog (Escape)")
        self.close_button.clicked.connect(self.close)
        buttons_row.addWidget(self.close_button)
        
        layout.addLayout(buttons_row)
        
        # Results label
        self.results_label = QLabel("")
        self.results_label.setAlignment(Qt.AlignCenter)
        self.results_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(self.results_label)
        
        # Connect signals
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_input.returnPressed.connect(self._on_find_clicked)
        
        # Set initial focus
        self.search_input.setFocus()
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Enter to search
        enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self)
        enter_shortcut.activated.connect(self._on_find_clicked)
        
        # F3 for next
        f3_shortcut = QShortcut(QKeySequence("F3"), self)
        f3_shortcut.activated.connect(self._on_next_clicked)
        
        # Shift+F3 for previous
        shift_f3_shortcut = QShortcut(QKeySequence("Shift+F3"), self)
        shift_f3_shortcut.activated.connect(self._on_previous_clicked)
        
        # Escape to close
        escape_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        escape_shortcut.activated.connect(self.close)
    
    def _on_find_clicked(self):
        """Handle Find button click"""
        term = self.search_input.text().strip()
        if not term:
            return
        
        case_sensitive = self.case_checkbox.isChecked()
        search_thinking = self.thinking_checkbox.isChecked()
        use_regex = self.regex_checkbox.isChecked()
        
        self.search_requested.emit(term, case_sensitive, search_thinking, use_regex)
    
    def _on_next_clicked(self):
        """Handle Next button click"""
        self.find_next_requested.emit()
    
    def _on_previous_clicked(self):
        """Handle Previous button click"""
        self.find_previous_requested.emit()
    
    def _on_text_changed(self, text: str):
        """Handle text input change"""
        # Enable/disable find button
        has_text = bool(text.strip())
        self.find_button.setEnabled(has_text)
    
    def update_results(self, current: int, total: int):
        """Update results display"""
        if total == 0:
            self.results_label.setText("No results found")
            self.next_button.setEnabled(False)
            self.prev_button.setEnabled(False)
        else:
            self.results_label.setText(f"Result {current + 1} of {total}")
            self.next_button.setEnabled(total > 1)
            self.prev_button.setEnabled(total > 1)
    
    def clear_results(self):
        """Clear results display"""
        self.results_label.setText("")
        self.next_button.setEnabled(False)
        self.prev_button.setEnabled(False)
    
    def set_search_term(self, term: str):
        """Set search term in input"""
        self.search_input.setText(term)
        self.search_input.selectAll()
    
    def get_search_term(self) -> str:
        """Get current search term"""
        return self.search_input.text().strip()
    
    def closeEvent(self, event):
        """Handle dialog close"""
        self.closed.emit()
        super().closeEvent(event)
    
    def showEvent(self, event):
        """Handle dialog show"""
        super().showEvent(event)
        # Center dialog relative to parent
        if self.parent():
            parent_geo = self.parent().geometry()
            self.move(
                parent_geo.x() + (parent_geo.width() - self.width()) // 2,
                parent_geo.y() + (parent_geo.height() - self.height()) // 2
            )
        # Focus and select text
        self.search_input.setFocus()
        self.search_input.selectAll()

