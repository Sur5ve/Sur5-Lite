#!/usr/bin/env python3
"""
Message Composer
Input area for composing and sending messages
"""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QTextEdit, 
    QPushButton, QLabel, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer, QEvent
from PySide6.QtGui import QKeySequence, QShortcut, QFont


class MessageComposer(QWidget):
    """Message input and send controls"""
    
    # Signals
    message_sent = Signal(str)  # message_content
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI components
        self.text_input: Optional[QTextEdit] = None
        self.send_button: Optional[QPushButton] = None
        self.char_counter: Optional[QLabel] = None
        
        # State
        self.model_available = False
        self.is_sending = False
        self.max_chars = 4000
        self._sending_guard = False
        
        # Setup UI
        self._setup_ui()
        self._setup_shortcuts()
        self._setup_styling()
        
    def _setup_ui(self):
        """Setup the composer UI layout"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)
        
        # Input frame
        input_frame = QFrame()
        input_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        input_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(12, 12, 12, 12)
        input_layout.setSpacing(8)
        
        # Text input area
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Type your message here... (Enter to send, Shift+Enter for newline)")
        self.text_input.setMaximumHeight(120)
        self.text_input.setMinimumHeight(60)
        self.text_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        # Accessibility
        self.text_input.setAccessibleName("Message input")
        self.text_input.setAccessibleDescription("Type your message. Press Enter to send, Shift+Enter for a new line.")
        
        # Enable rich text features
        self.text_input.setAcceptRichText(False)  # Plain text only
        
        # Connect text change signal
        self.text_input.textChanged.connect(self._on_text_changed)
        # Keyboard handling: Enter to send, Shift+Enter to newline
        self.text_input.installEventFilter(self)
        
        input_layout.addWidget(self.text_input)
        
        # Bottom controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)
        
        # Character counter
        self.char_counter = QLabel("0 / 4000")
        self.char_counter.setStyleSheet("color: #888888; font-size: 11px;")
        controls_layout.addWidget(self.char_counter)
        
        # Spacer
        controls_layout.addStretch()
        
        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.setProperty("class", "primary")
        self.send_button.setMinimumWidth(80)
        self.send_button.setEnabled(False)
        self.send_button.clicked.connect(self._send_message)
        # Accessibility
        self.send_button.setAccessibleName("Send message")
        self.send_button.setAccessibleDescription("Send the message in the input field")
        controls_layout.addWidget(self.send_button)
        
        input_layout.addLayout(controls_layout)
        main_layout.addWidget(input_frame)
        
        # Initial state
        self._update_send_button_state("", 0)
        
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Ctrl+Enter to send (legacy, keep for parity)
        send_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        send_shortcut.activated.connect(self._send_message)
        
        # Alternative shortcut
        send_shortcut2 = QShortcut(QKeySequence("Ctrl+Enter"), self)
        send_shortcut2.activated.connect(self._send_message)

        # Optional: Alt+Enter to insert newline explicitly
        # Handled via eventFilter with Shift+Enter, so not required here
        
    def _setup_styling(self):
        """Setup styling"""
        self.setMinimumHeight(100)
        self.setMaximumHeight(180)
        
    def _on_text_changed(self):
        """Handle text input changes"""
        text = self.text_input.toPlainText()
        char_count = len(text)
        text_stripped = text.strip()
        
        # Update character counter
        self.char_counter.setText(f"{char_count} / {self.max_chars}")
        
        # Update counter color based on limit
        if char_count > self.max_chars:
            self.char_counter.setStyleSheet("color: #e74c3c; font-size: 11px; font-weight: bold;")
        elif char_count > self.max_chars * 0.9:
            self.char_counter.setStyleSheet("color: #f39c12; font-size: 11px; font-weight: bold;")
        else:
            self.char_counter.setStyleSheet("color: #888888; font-size: 11px;")
            
        # Update send button state
        self._update_send_button_state(text_stripped, char_count)
        
    def _update_send_button_state(self, text_stripped: str, char_count: int):
        """Update send button enabled state"""
        # Allow sending even if a model is not yet marked as available; this triggers lazy load
        can_send = (
            not self.is_sending and 
            len(text_stripped) > 0 and 
            char_count <= self.max_chars
        )
        
        self.send_button.setEnabled(can_send)
        
        # Update button text based on state
        if self.is_sending:
            self.send_button.setText("Sending...")
        elif not self.model_available:
            # Show that sending will load the model lazily
            self.send_button.setText("Send (loads model)")
        elif char_count > self.max_chars:
            self.send_button.setText("Too Long")
        elif len(text_stripped) == 0:
            self.send_button.setText("Send")
        else:
            self.send_button.setText("Send")
            
    def _send_message(self):
        """Send the current message"""
        if not self.send_button.isEnabled() or self._sending_guard:
            return
            
        text = self.text_input.toPlainText().strip()
        if not text:
            return
            
        # Guard and set sending state BEFORE emitting to avoid double-send
        self._sending_guard = True
        self.set_sending_state(True)

        # Emit message
        self.message_sent.emit(text)
        
    def clear(self):
        """Clear the input field"""
        self.text_input.clear()
        self._update_send_button_state("", 0)
        
    def set_model_available(self, available: bool):
        """Set whether a model is available for sending"""
        self.model_available = available
        
        # Update button state
        current_text = self.text_input.toPlainText().strip()
        char_count = len(self.text_input.toPlainText())
        self._update_send_button_state(current_text, char_count)
        
        # Update placeholder text
        if available:
            self.text_input.setPlaceholderText("Type your message here... (Enter to send, Shift+Enter for newline)")
        else:
            self.text_input.setPlaceholderText("Load a model to start chatting...")
            
    def set_sending_state(self, is_sending: bool):
        """Set the sending state"""
        self.is_sending = is_sending
        
        # Disable input during sending
        self.text_input.setEnabled(not is_sending)
        
        # Update button state
        current_text = self.text_input.toPlainText().strip()
        char_count = len(self.text_input.toPlainText())
        self._update_send_button_state(current_text, char_count)
        
        # Reset guard when sending finishes
        if not is_sending:
            self._sending_guard = False
        
    def focus_input(self):
        """Focus the text input field"""
        self.text_input.setFocus()
        
    def get_text(self) -> str:
        """Get the current input text"""
        return self.text_input.toPlainText()
        
    def set_text(self, text: str):
        """Set the input text"""
        self.text_input.setPlainText(text)
        
    def append_text(self, text: str):
        """Append text to the current input"""
        current = self.text_input.toPlainText()
        self.text_input.setPlainText(current + text)
        
    def set_max_chars(self, max_chars: int):
        """Set the maximum character limit"""
        self.max_chars = max_chars
        self._on_text_changed()  # Refresh state
        
    def get_char_count(self) -> int:
        """Get current character count"""
        return len(self.text_input.toPlainText())
        
    def is_empty(self) -> bool:
        """Check if input is empty"""
        return len(self.text_input.toPlainText().strip()) == 0

    # --- Accessibility and keyboard handling ---
    def eventFilter(self, obj, event):
        """Intercept key presses on the text input to implement Enter semantics."""
        if obj is self.text_input and event.type() == QEvent.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            if key in (Qt.Key_Return, Qt.Key_Enter):
                if modifiers & Qt.ShiftModifier:
                    # Allow newline
                    return False
                # Send on plain Enter
                self._send_message()
                return True
        return super().eventFilter(obj, event)
