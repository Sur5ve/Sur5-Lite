#!/usr/bin/env python3
"""
Chat Thread View
Displays chat messages with virtualization and modern bubble styling
"""

import time
import html
import re
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QFrame, QTextEdit, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QTextDocument, QTextCharFormat, QColor


class ChatThreadView(QScrollArea):
    """Scrollable chat thread with message bubbles"""
    
    # Signals
    message_clicked = Signal(dict)  # message_data
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Message storage
        self.messages: List[Dict[str, Any]] = []
        self.message_widgets: List[QWidget] = []
        
        # Current streaming state
        self.current_thinking_widget: Optional[QWidget] = None
        self.current_response_widget: Optional[QWidget] = None
        self.is_streaming = False
        
        # Virtualization settings
        self.virtualization_enabled = True
        self.virtualization_threshold = 50
        self.visible_range = (0, 0)
        
        # Setup UI
        self._setup_ui()
        self._setup_styling()
        
        # Auto-scroll timer
        self.auto_scroll_timer = QTimer()
        self.auto_scroll_timer.timeout.connect(self._scroll_to_bottom)
        self.auto_scroll_timer.setSingleShot(True)
        
    def _setup_ui(self):
        """Setup the scroll area and content widget"""
        # Configure scroll area
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Create content widget
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(16, 16, 16, 16)
        self.content_layout.setSpacing(12)
        self.content_layout.addStretch()  # Push messages to top initially
        
        self.setWidget(self.content_widget)
        
        # Fix rounded corners - ensure viewport respects border-radius
        if self.viewport():
            self.viewport().setAutoFillBackground(True)
        
        # Show empty state initially
        self._show_empty_state()
        
    def _setup_styling(self):
        """Setup QSS styling via property classes"""
        self.setProperty("class", "thread_view")
        
    def _show_empty_state(self):
        """Show empty state when no messages"""
        self._clear_layout()
        
        # Create empty state widget
        empty_widget = self._create_empty_state()
        self.content_layout.addWidget(empty_widget)
        self.content_layout.addStretch()
        
    def _create_empty_state(self) -> QWidget:
        """Create the empty state widget"""
        empty_frame = QFrame()
        empty_layout = QVBoxLayout(empty_frame)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(16)
        
        # Welcome message
        welcome_label = QLabel("👋 Welcome to Beta Version!")
        welcome_label.setProperty("class", "welcome_label")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(welcome_label)
        
        # Instructions
        instructions = [
            "• Load a model from the Model panel",
            "• Add documents to the RAG panel for context",
            "• Start chatting with your AI assistant",
            "• Enable thinking mode to see AI reasoning"
        ]
        
        for instruction in instructions:
            instruction_label = QLabel(instruction)
            instruction_label.setProperty("class", "instructions_label")
            instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(instruction_label)
            
        return empty_frame
        
    def add_message(self, message_data: Dict[str, Any]):
        """Add a message to the thread"""
        # Prevent duplicate echo: if the last message is identical (role+content), skip
        if self.messages:
            last = self.messages[-1]
            if last.get("role") == message_data.get("role") and last.get("content") == message_data.get("content"):
                return
        else:
            # Remove empty state on first message
            self._clear_layout()
            # Re-establish bottom stretch so new messages append at the bottom
            self.content_layout.addStretch()
            
        # Add to message storage
        self.messages.append(message_data)
        
        # Create message widget
        if message_data["role"] == "user":
            message_widget = self._create_user_bubble(
                message_data["content"],
                message_data.get("timestamp", time.time())
            )
        elif message_data["role"] == "assistant":
            message_widget = self._create_assistant_bubble(
                message_data["content"],
                message_data.get("timestamp", time.time()),
                message_data.get("thinking", "")
            )
        else:
            # Fallback for other message types
            message_widget = self._create_fallback_message_widget(message_data)
            
        # Add to layout
        self.content_layout.insertWidget(self.content_layout.count() - 1, message_widget)
        self.message_widgets.append(message_widget)
        
        # Handle virtualization if needed
        if self.virtualization_enabled and len(self.messages) > self.virtualization_threshold:
            self._update_virtualization()
            
        # Auto-scroll to bottom
        self._schedule_scroll_to_bottom()
        
    def _create_user_bubble(self, content: str, timestamp: float) -> QWidget:
        """Create a user message bubble"""
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add left spacer for right alignment
        container_layout.addStretch()
        
        # Create bubble frame
        bubble_frame = QFrame()
        bubble_frame.setProperty("class", "user_bubble")
        bubble_frame.setMaximumWidth(600)
        bubble_frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        
        bubble_layout = QVBoxLayout(bubble_frame)
        bubble_layout.setContentsMargins(16, 12, 16, 12)
        bubble_layout.setSpacing(4)
        
        # Message content
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bubble_layout.addWidget(content_label)
        
        # Timestamp
        time_str = time.strftime("%H:%M", time.localtime(timestamp))
        timestamp_label = QLabel(time_str)
        timestamp_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 10px;")
        timestamp_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        bubble_layout.addWidget(timestamp_label)
        
        container_layout.addWidget(bubble_frame)
        return container
        
    def _create_assistant_bubble(self, content: str, timestamp: float, thinking: str = "") -> QWidget:
        """Create an assistant message bubble with optional thinking content"""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(8)
        
        # Thinking bubble (if present)
        if thinking:
            thinking_container = QWidget()
            thinking_container_layout = QHBoxLayout(thinking_container)
            thinking_container_layout.setContentsMargins(0, 0, 0, 0)
            
            thinking_frame = QFrame()
            thinking_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(100, 100, 100, 0.3);
                    border-radius: 12px;
                    padding: 8px;
                    border: 1px dashed rgba(150, 150, 150, 0.5);
                }
            """)
            thinking_frame.setMaximumWidth(550)
            
            thinking_layout = QVBoxLayout(thinking_frame)
            thinking_layout.setContentsMargins(12, 8, 12, 8)
            
            thinking_header = QLabel("🤔 Thinking...")
            thinking_header.setStyleSheet("font-weight: bold; color: #888888; font-size: 11px;")
            thinking_layout.addWidget(thinking_header)
            
            thinking_content = QLabel(thinking)
            thinking_content.setWordWrap(True)
            thinking_content.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            thinking_content.setStyleSheet("color: #aaaaaa; font-size: 12px; font-style: italic;")
            thinking_layout.addWidget(thinking_content)
            
            thinking_container_layout.addWidget(thinking_frame)
            thinking_container_layout.addStretch()
            container_layout.addWidget(thinking_container)
        
        # Main response bubble
        bubble_container = QWidget()
        bubble_container_layout = QHBoxLayout(bubble_container)
        bubble_container_layout.setContentsMargins(0, 0, 0, 0)
        
        bubble_frame = QFrame()
        bubble_frame.setProperty("class", "assistant_bubble")
        bubble_frame.setMaximumWidth(600)
        bubble_frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        
        bubble_layout = QVBoxLayout(bubble_frame)
        bubble_layout.setContentsMargins(16, 12, 16, 12)
        bubble_layout.setSpacing(4)
        
        # Message content
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bubble_layout.addWidget(content_label)
        
        # Timestamp
        time_str = time.strftime("%H:%M", time.localtime(timestamp))
        timestamp_label = QLabel(time_str)
        timestamp_label.setStyleSheet("color: rgba(200, 200, 200, 0.7); font-size: 10px;")
        timestamp_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        bubble_layout.addWidget(timestamp_label)
        
        bubble_container_layout.addWidget(bubble_frame)
        bubble_container_layout.addStretch()
        container_layout.addWidget(bubble_container)
        
        return container
        
    def start_thinking_mode(self):
        """Start thinking mode display"""
        if self.is_streaming:
            return
            
        self.is_streaming = True
        
        # Create thinking indicator widget
        thinking_container = QWidget()
        thinking_layout = QHBoxLayout(thinking_container)
        thinking_layout.setContentsMargins(0, 0, 0, 0)
        
        thinking_frame = QFrame()
        thinking_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(100, 100, 100, 0.3);
                border-radius: 12px;
                border: 1px dashed rgba(150, 150, 150, 0.5);
            }
        """)
        thinking_frame.setMaximumWidth(550)
        
        thinking_frame_layout = QVBoxLayout(thinking_frame)
        thinking_frame_layout.setContentsMargins(12, 8, 12, 8)
        
        # Thinking header
        header_label = QLabel("🤔 Thinking...")
        header_label.setStyleSheet("font-weight: bold; color: #888888; font-size: 11px;")
        thinking_frame_layout.addWidget(header_label)
        
        # Thinking content (initially empty)
        self.thinking_content_label = QLabel("")
        self.thinking_content_label.setWordWrap(True)
        self.thinking_content_label.setStyleSheet("color: #aaaaaa; font-size: 12px; font-style: italic;")
        thinking_frame_layout.addWidget(self.thinking_content_label)
        
        thinking_layout.addWidget(thinking_frame)
        thinking_layout.addStretch()
        
        # Add to layout
        self.content_layout.insertWidget(self.content_layout.count() - 1, thinking_container)
        self.current_thinking_widget = thinking_container
        
        self._schedule_scroll_to_bottom()
        
    def update_thinking_content(self, thinking_chunk: str):
        """Update thinking content during streaming"""
        if self.thinking_content_label:
            current_text = self.thinking_content_label.text()
            self.thinking_content_label.setText(current_text + thinking_chunk)
            self._schedule_scroll_to_bottom()
            
    def update_streaming_response(self, response_chunk: str):
        """Update streaming response content"""
        if not self.current_response_widget:
            # Create response bubble for streaming
            self._create_streaming_response_bubble()
            
        if self.response_content_label:
            current_text = self.response_content_label.text()
            self.response_content_label.setText(current_text + response_chunk)
            self._schedule_scroll_to_bottom()
            
    def _create_streaming_response_bubble(self):
        """Create a bubble for streaming response"""
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        bubble_frame = QFrame()
        bubble_frame.setProperty("class", "assistant_bubble")
        bubble_frame.setMaximumWidth(600)
        
        bubble_layout = QVBoxLayout(bubble_frame)
        bubble_layout.setContentsMargins(16, 12, 16, 12)
        
        # Response content label
        self.response_content_label = QLabel("")
        self.response_content_label.setWordWrap(True)
        self.response_content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bubble_layout.addWidget(self.response_content_label)
        
        container_layout.addWidget(bubble_frame)
        container_layout.addStretch()
        
        # Add to layout
        self.content_layout.insertWidget(self.content_layout.count() - 1, container)
        self.current_response_widget = container
        
    def finish_response(self):
        """Finish streaming response"""
        self.is_streaming = False
        
        # Clean up temporary widgets
        if self.current_thinking_widget:
            self.current_thinking_widget = None
            self.thinking_content_label = None
            
        if self.current_response_widget:
            self.current_response_widget = None
            self.response_content_label = None
            
    def show_error(self, error_message: str):
        """Show an error message"""
        error_container = QWidget()
        error_layout = QHBoxLayout(error_container)
        error_layout.setContentsMargins(0, 0, 0, 0)
        
        error_frame = QFrame()
        error_frame.setProperty("class", "error_indicator")
        error_frame.setMaximumWidth(500)
        
        error_frame_layout = QVBoxLayout(error_frame)
        error_frame_layout.setContentsMargins(12, 8, 12, 8)
        
        error_label = QLabel(f"❌ {error_message}")
        error_label.setProperty("class", "error_message")
        error_label.setWordWrap(True)
        error_frame_layout.addWidget(error_label)
        
        error_layout.addWidget(error_frame)
        error_layout.addStretch()
        
        self.content_layout.insertWidget(self.content_layout.count() - 1, error_container)
        self._schedule_scroll_to_bottom()
        
    def show_status_message(self, status_message: str):
        """Show a status message"""
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        status_label = QLabel(status_message)
        status_label.setStyleSheet("color: #888888; font-size: 12px; font-style: italic;")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        status_layout.addWidget(status_label)
        
        self.content_layout.insertWidget(self.content_layout.count() - 1, status_container)
        self._schedule_scroll_to_bottom()
        
    def clear_messages(self):
        """Clear all messages"""
        self.messages.clear()
        self.message_widgets.clear()
        self._clear_layout()
        self._show_empty_state()
        
    def _clear_layout(self):
        """Clear all widgets from the layout"""
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
    def _schedule_scroll_to_bottom(self):
        """Schedule auto-scroll to bottom"""
        self.auto_scroll_timer.start(50)  # Small delay for smooth scrolling
        
    def _scroll_to_bottom(self):
        """Scroll to the bottom of the chat"""
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def _update_virtualization(self):
        """Update virtualization if enabled"""
        if not self.virtualization_enabled:
            return
            
        # For now, simple implementation - could be enhanced with more sophisticated virtualization
        total_messages = len(self.messages)
        if total_messages > self.virtualization_threshold:
            # Keep last N messages visible
            visible_count = min(self.virtualization_threshold, total_messages)
            start_idx = total_messages - visible_count
            
            # This is a simplified approach - real virtualization would be more complex
            print(f"📊 Virtualization: Showing {visible_count} of {total_messages} messages")
            
    def _create_fallback_message_widget(self, message_data: Dict[str, Any]) -> QWidget:
        """Create a fallback widget for unknown message types"""
        fallback_frame = QFrame()
        fallback_layout = QVBoxLayout(fallback_frame)
        fallback_layout.setContentsMargins(8, 8, 8, 8)
        
        role_label = QLabel(f"Role: {message_data.get('role', 'unknown')}")
        role_label.setStyleSheet("font-weight: bold;")
        fallback_layout.addWidget(role_label)
        
        content_label = QLabel(str(message_data.get('content', '')))
        content_label.setProperty("class", "error_message")
        content_label.setWordWrap(True)
        fallback_layout.addWidget(content_label)
        
        return fallback_frame
        
    def _add_error_indicator(self, message_widget, error_message: str):
        """Add error indicator to a message widget"""
        message_widget.setProperty("class", "error_indicator")
    
    # ─────────────────── Search Highlighting ───────────────────
    def highlight_search_result(self, message_index: int, search_term: str, is_current: bool = False):
        """
        Highlight search term in a message
        
        Args:
            message_index: Index of message to highlight
            search_term: Term to highlight
            is_current: Whether this is the current search result
        """
        if message_index < 0 or message_index >= len(self.message_widgets):
            return
        
        message_widget = self.message_widgets[message_index]
        
        # Find all QLabel widgets in the message
        labels = message_widget.findChildren(QLabel)
        
        for label in labels:
            # CRITICAL FIX: Always get clean plain text first
            # Store original text if not already stored
            if not hasattr(label, '_original_text'):
                label._original_text = label.text()
            
            # Use stored original text (not the potentially HTML-escaped text)
            original_text = label._original_text
            
            if not original_text or not search_term:
                continue
            
            # Create highlighted HTML from ORIGINAL plain text
            highlighted_html = self._create_highlighted_html(
                original_text, search_term, is_current
            )
            
            if highlighted_html:
                label.setText(highlighted_html)
                label.setTextFormat(Qt.TextFormat.RichText)
        
        # Scroll to the message
        self.ensureWidgetVisible(message_widget)
    
    def clear_search_highlights(self):
        """Remove all search highlighting from messages"""
        for message_widget in self.message_widgets:
            labels = message_widget.findChildren(QLabel)
            
            for label in labels:
                # CRITICAL FIX: Restore original plain text
                if hasattr(label, '_original_text'):
                    label.setText(label._original_text)
                    label.setTextFormat(Qt.TextFormat.PlainText)
    
    def scroll_to_message(self, message_index: int):
        """Scroll to a specific message"""
        if message_index < 0 or message_index >= len(self.message_widgets):
            return
        
        message_widget = self.message_widgets[message_index]
        self.ensureWidgetVisible(message_widget)
    
    def _create_highlighted_html(self, text: str, search_term: str, is_current: bool) -> str:
        """
        Create HTML with highlighted search terms
        
        Args:
            text: Original PLAIN text (not HTML)
            search_term: Term to highlight
            is_current: Whether this is the current result (different highlight color)
            
        Returns:
            HTML string with highlights
        """
        import html
        import re
        
        # CRITICAL FIX: Escape the entire text ONCE at the start
        escaped_text = html.escape(text)
        
        # Define highlight colors
        if is_current:
            bg_color = "#ff9800"  # Orange for current result
            text_color = "#000000"  # Black text
        else:
            bg_color = "#ffeb3b"  # Yellow for other results
            text_color = "#000000"  # Black text
        
        # Case-insensitive search and replace
        # Escape the search term for regex
        escaped_search_term = re.escape(html.escape(search_term))
        pattern = re.compile(escaped_search_term, re.IGNORECASE)
        
        # Replace matches with highlighted spans
        def replace_match(match):
            matched_text = match.group()
            return f'<span style="background-color: {bg_color}; color: {text_color}; padding: 2px 4px; border-radius: 3px; font-weight: bold;">{matched_text}</span>'
        
        highlighted = pattern.sub(replace_match, escaped_text)
        
        return highlighted
