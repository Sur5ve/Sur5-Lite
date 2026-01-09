#!/usr/bin/env python3
"""
Chat Container - Main chat interface with thread view, composer, and sidebar

Sur5 Lite — Open Source Edge AI
Copyright (c) 2024-2026 Sur5ve LLC
Licensed under MIT License
https://sur5ve.com
"""

from typing import Optional, Dict, Any
import json
import time

from utils.logger import create_module_logger
logger = create_module_logger(__name__)

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QFrame, QLabel, QScrollArea, QGroupBox
)
from PySide6.QtCore import Qt, Slot

from services.conversation_service import ConversationService
from services.model_service import ModelService

from .thread_view import ChatThreadView
from .composer import MessageComposer
from widgets.sidebar.model_panel import ModelPanel
from widgets.common.control_hub_tab import ControlHubTab


class ChatContainer(QWidget):
    """Main chat interface container"""
    
    def __init__(
        self, 
        conversation_service: ConversationService,
        model_service: ModelService,
        parent=None
    ):
        super().__init__(parent)
        
        # Store service references
        self.conversation_service = conversation_service
        self.model_service = model_service
        
        # refs
        self.thread_view: Optional[ChatThreadView] = None
        self.composer: Optional[MessageComposer] = None
        self.sidebar: Optional[QWidget] = None
        self.control_hub_tab: Optional[ControlHubTab] = None
        self.main_splitter: Optional[QSplitter] = None
        
        # ui
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        """Setup the chat container UI layout"""
        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # Create main splitter (resizable/collapsible sidebar)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        # Allow collapsing the sidebar and realtime resizing
        self.main_splitter.setChildrenCollapsible(True)
        self.main_splitter.setOpaqueResize(True)
        # Make the handle easier to grab
        self.main_splitter.setHandleWidth(6)
        
        # Create chat area (left side)
        chat_area = self._create_chat_area()
        self.main_splitter.addWidget(chat_area)
        
        # Create sidebar (right side)
        self.sidebar = self._create_sidebar()
        self.main_splitter.addWidget(self.sidebar)
        
        # Now set sidebar as collapsible (after widgets are added)
        self.main_splitter.setCollapsible(1, True)
        
        # Set splitter proportions (chat expands, sidebar collapsed by default)
        initial_sidebar = 0  # Collapsed by default
        self.main_splitter.setSizes([900, initial_sidebar])
        self.main_splitter.setStretchFactor(0, 1)  # Chat area is stretchable
        self.main_splitter.setStretchFactor(1, 0)  # Sidebar keeps requested size
        
        main_layout.addWidget(self.main_splitter)
        
        # Create Control Hub Tab (overlay on sidebar)
        self.control_hub_tab = ControlHubTab(parent=self)
        self.control_hub_tab.clicked.connect(self._toggle_sidebar)
        self.control_hub_tab.raise_()  # Ensure it's on top
        
        # Position will be updated in resizeEvent
        
    def _create_chat_area(self) -> QWidget:
        """Create the main chat area with thread view and composer"""
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(8)
        
        # Create thread view
        self.thread_view = ChatThreadView(parent=self)
        self.thread_view.setAccessibleName("Conversation thread")
        self.thread_view.setAccessibleDescription("Displays the conversation history and streaming responses")
        chat_layout.addWidget(self.thread_view, 1)  # Takes most space
        
        # Create composer
        self.composer = MessageComposer(parent=self)
        self.composer.setAccessibleName("Message composer")
        self.composer.setAccessibleDescription("Compose your message and press Enter to send")
        chat_layout.addWidget(self.composer, 0)  # Fixed height
        
        return chat_widget
        
    def _create_sidebar(self) -> QWidget:
        """Create the sidebar with model panel"""
        sidebar_widget = QFrame()
        sidebar_widget.setFrameStyle(QFrame.Shape.StyledPanel)
        # Allow user to resize or fully collapse; keep a generous max
        sidebar_widget.setMinimumWidth(0)
        sidebar_widget.setMaximumWidth(800)

        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(10)

        # Model Panel (contains Model, Configuration, Information groups)
        self.model_panel = ModelPanel(self.model_service, parent=self)
        sidebar_layout.addWidget(self.model_panel)
        
        # Add stretch to push content up
        sidebar_layout.addStretch()

        return sidebar_widget
        
    def _connect_signals(self):
        """Connect signals between components and services"""
        # Composer to conversation service
        if self.composer:
            self.composer.message_sent.connect(self._on_message_sent)
            
        # Conversation service to UI components
        self.conversation_service.message_received.connect(self.on_message_received)
        self.conversation_service.thinking_started.connect(self.on_thinking_started)
        self.conversation_service.response_started.connect(self.on_response_started)
        self.conversation_service.thinking_chunk.connect(self.on_thinking_chunk)
        self.conversation_service.streaming_chunk.connect(self.on_streaming_chunk)
        self.conversation_service.error_occurred.connect(self.on_conversation_error)
        
        # Model service to UI components
        self.model_service.model_loaded.connect(self.on_model_loaded)
        self.model_service.model_error.connect(self.on_model_error)
        self.model_service.generation_started.connect(self.on_generation_started)
        self.model_service.generation_finished.connect(self.on_generation_finished)
        
    def _on_message_sent(self, message: str):
        """Handle message sent from composer"""
        if message.strip():
            # Get thinking mode preference
            use_thinking = self.model_service.get_thinking_mode()
            
            # Force standard mode for models that don't support thinking
            from sur5_lite_pyside.services.dual_mode_utils import get_model_capabilities
            if self.model_service.current_model_path:
                caps = get_model_capabilities(self.model_service.current_model_path)
                if not caps.get("supports_thinking", False):
                    use_thinking = False
            
            # Send message via conversation service
            success = self.conversation_service.send_message(message, use_thinking)
            
            if success:
                # Clear composer
                if self.composer:
                    self.composer.clear()
            else:
                # Re-enable composer if send failed
                if self.composer:
                    self.composer.set_sending_state(False)
                    
    @Slot(dict)
    def on_message_received(self, message_data: Dict[str, Any]):
        """Handle new message received"""
        if not self.thread_view:
            return
        
        # Check if this is for an active streaming session
        if message_data.get("role") == "assistant" and self.thread_view.current_message_unit:
            logger.debug("Finalizing persistent MessageUnit with backend content")
            
            # Extract backend content
            thinking_content = message_data.get("thinking", "")
            response_content = message_data.get("content", "")
            timestamp = message_data.get("timestamp", time.time())
            
            # Finalize the existing MessageUnit with correct content
            self.thread_view.finalize_with_backend_content(
                thinking_content,
                response_content,
                timestamp
            )
            
            # DO NOT call add_message - content already displayed
            return
        
        # For all other messages (user, history, etc.), use add_message normally
        self.thread_view.add_message(message_data)
            
    @Slot()
    def on_thinking_started(self):
        """Handle thinking mode started"""
        if self.thread_view:
            self.thread_view.start_thinking_mode()
    
    @Slot()
    def on_response_started(self):
        """Handle standard response mode started (no thinking phase)"""
        if self.thread_view:
            # Guard: Only create MessageUnit if one doesn't already exist (prevents duplicates)
            if not self.thread_view.current_message_unit:
                self.thread_view.start_response_mode()
            
    @Slot(str)
    def on_thinking_chunk(self, thinking_chunk: str):
        """Handle thinking chunk (now includes close handling)"""
        if not self.thread_view:
            return
        
        # Parse chunk to detect close signal
        try:
            chunk_data = json.loads(thinking_chunk)
        except json.JSONDecodeError:
            chunk_data = {"close": False}
        
        # Route to thread view
        self.thread_view.update_thinking_content(thinking_chunk)
        
        # Thinking close doesn't re-enable composer (wait for response close)
            
    @Slot(str)
    def on_streaming_chunk(self, response_chunk: str):
        """Handle streaming response chunk (now includes close handling)"""
        if not self.thread_view:
            return
        
        # Parse chunk to detect close signal
        try:
            chunk_data = json.loads(response_chunk)
        except json.JSONDecodeError:
            chunk_data = {"close": False}
        
        # Route to thread view for processing
        self.thread_view.update_streaming_response(response_chunk)
        
        # Handle close signal: re-enable composer
        if chunk_data.get("close"):
            logger.debug("Stream closed, re-enabling composer")
            if self.composer:
                self.composer.set_sending_state(False)
                self.composer.focus_input()
            
    @Slot(str)
    def on_conversation_error(self, error_message: str):
        """Handle conversation error"""
        if self.thread_view:
            # Reset streaming state if error occurred during streaming
            if self.thread_view.is_streaming:
                self.thread_view.finish_response()
            self.thread_view.show_error(error_message)
            
        # Re-enable composer
        if self.composer:
            self.composer.set_sending_state(False)
            
    @Slot(str, str)
    def on_model_loaded(self, model_name: str, model_path: str):
        """Handle model loaded event"""
        # Enable composer if model is loaded
        if self.composer:
            self.composer.set_model_available(True)
            
        # Update thread view to show model status at the top
        if self.thread_view:
            self.thread_view.show_status_message(f"Sur ready: {model_name} loaded", is_model_status=True)
            
    @Slot(str)
    def on_model_error(self, error_message: str):
        """Handle model error"""
        # Disable composer if model error
        if self.composer:
            self.composer.set_model_available(False)
            
        # Show error in thread view
        if self.thread_view:
            self.thread_view.show_error(f"Model error: {error_message}")
            
    @Slot()
    def on_generation_started(self):
        """Handle generation started"""
        if self.composer:
            self.composer.set_sending_state(True)
            
    @Slot()
    def on_generation_finished(self):
        """Handle generation finished"""
        if self.composer:
            self.composer.set_sending_state(False)
            
    def clear_chat(self):
        """Clear the chat thread view"""
        if self.thread_view:
            self.thread_view.clear_messages()
            
    def get_chat_history(self):
        """Get the current chat history"""
        return self.conversation_service.get_history()
        
    def set_thinking_mode(self, enabled: bool):
        """Set thinking mode enabled/disabled"""
        self.model_service.set_thinking_mode(enabled)
        
    def get_thinking_mode(self) -> bool:
        """Get current thinking mode setting"""
        return self.model_service.get_thinking_mode()
        
    def focus_composer(self):
        """Focus the message composer input"""
        if self.composer:
            self.composer.focus_input()
    
    def _toggle_sidebar(self):
        """Toggle sidebar visibility"""
        if not self.main_splitter:
            return
            
        sizes = self.main_splitter.sizes()
        if sizes[1] == 0:  # Sidebar is collapsed
            # Expand sidebar to 420px
            new_sidebar_size = 420
            new_chat_size = max(sizes[0] - new_sidebar_size, 100)
            self.main_splitter.setSizes([new_chat_size, new_sidebar_size])
        else:  # Sidebar is visible
            # Collapse sidebar
            self.main_splitter.setSizes([sizes[0] + sizes[1], 0])
    
    def resizeEvent(self, event):
        """Handle resize to position Control Hub Tab"""
        super().resizeEvent(event)
        
        if self.control_hub_tab and self.main_splitter:
            # Position the Control Hub Tab at the right edge of the window
            # It should be visible even when sidebar is collapsed
            splitter_geo = self.main_splitter.geometry()
            
            # Get the position where the sidebar would start
            sizes = self.main_splitter.sizes()
            chat_width = sizes[0] if len(sizes) > 0 else 0
            
            # Position the tab at the right edge (works for both collapsed and expanded)
            tab_x = splitter_geo.x() + self.width() - self.control_hub_tab.width() - 8
            tab_y = splitter_geo.y() + 100  # Offset from top
            
            self.control_hub_tab.move(tab_x, tab_y)
            self.control_hub_tab.raise_()  # Ensure it stays on top
    
    def closeEvent(self, event):
        """Clean up thread before closing"""
        if self.conversation_service:
            self.conversation_service.stop_generation()
        super().closeEvent(event)
