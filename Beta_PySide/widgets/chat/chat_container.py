#!/usr/bin/env python3
"""
Chat Container
Main chat interface with thread view, composer, and sidebar
"""

from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QFrame, QLabel, QScrollArea, QGroupBox
)
from PySide6.QtCore import Qt, Slot

from services.conversation_service import ConversationService
from services.model_service import ModelService
from services.document_service import DocumentService

from .thread_view import ChatThreadView
from .composer import MessageComposer
from widgets.sidebar.model_panel import ModelPanel
from widgets.sidebar.rag_panel import RAGPanel
# Settings moved to Preferences dialog; not embedded in sidebar


class ChatContainer(QWidget):
    """Main chat interface container"""
    
    def __init__(
        self, 
        conversation_service: ConversationService,
        model_service: ModelService,
        document_service: DocumentService,
        parent=None
    ):
        super().__init__(parent)
        
        # Store service references
        self.conversation_service = conversation_service
        self.model_service = model_service
        self.document_service = document_service
        
        # UI components
        self.thread_view: Optional[ChatThreadView] = None
        self.composer: Optional[MessageComposer] = None
        self.sidebar: Optional[QWidget] = None
        
        # Setup UI
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        """Setup the chat container UI layout"""
        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # Create main splitter (resizable/collapsible sidebar)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        # Allow collapsing the sidebar and realtime resizing
        main_splitter.setChildrenCollapsible(True)
        main_splitter.setCollapsible(1, True)
        main_splitter.setOpaqueResize(True)
        # Make the handle easier to grab
        main_splitter.setHandleWidth(6)
        
        # Create chat area (left side)
        chat_area = self._create_chat_area()
        main_splitter.addWidget(chat_area)
        
        # Create sidebar (right side)
        self.sidebar = self._create_sidebar()
        main_splitter.addWidget(self.sidebar)
        
        # Set splitter proportions (chat expands, sidebar user-resizable)
        initial_sidebar = 420
        main_splitter.setSizes([900, initial_sidebar])
        main_splitter.setStretchFactor(0, 1)  # Chat area is stretchable
        main_splitter.setStretchFactor(1, 0)  # Sidebar keeps requested size
        
        main_layout.addWidget(main_splitter)
        
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
        """Create the sidebar with model, RAG, and settings panels"""
        # Non-scroll sidebar container to enforce zero vertical scrolling

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

        # RAG Panel (contains RAG System, Documents groups)
        self.rag_panel = RAGPanel(self.document_service, parent=self)
        sidebar_layout.addWidget(self.rag_panel)

        # No stretch - ResponsiveSidebar manages all vertical space

        # Wire responsive behavior to keep sidebar zero-scroll
        try:
            from widgets.sidebar.responsive_sidebar import ResponsiveSidebar
            # Extract groups and docs list from panels
            model_group = self.model_panel.findChild(QGroupBox, None)
            config_group = None
            info_group = None
            # ModelPanel creates groups in order; fetch them explicitly
            groups = self.model_panel.findChildren(QGroupBox)
            for gb in groups:
                title = (gb.title() or '').lower()
                if title == 'model':
                    model_group = gb
                elif title == 'configuration':
                    config_group = gb
                elif title == 'information':
                    info_group = gb

            rag_groups = self.rag_panel.findChildren(QGroupBox)
            rag_group = None
            docs_group = None
            for gb in rag_groups:
                title = (gb.title() or '').lower()
                if 'rag system' in title:
                    rag_group = gb
                elif 'documents' in title:
                    docs_group = gb

            docs_list = self.rag_panel.document_list
            if all([model_group, config_group, info_group, rag_group, docs_group, docs_list]):
                self._responsive = ResponsiveSidebar(
                    sidebar_widget,
                    model_group,
                    config_group,
                    info_group,
                    rag_group,
                    docs_group,
                    docs_list,
                )
        except Exception:
            pass

        return sidebar_widget
        
    def _connect_signals(self):
        """Connect signals between components and services"""
        # Composer to conversation service
        if self.composer:
            self.composer.message_sent.connect(self._on_message_sent)
            
        # Conversation service to UI components
        self.conversation_service.message_received.connect(self.on_message_received)
        self.conversation_service.thinking_started.connect(self.on_thinking_started)
        self.conversation_service.thinking_chunk.connect(self.on_thinking_chunk)
        self.conversation_service.streaming_chunk.connect(self.on_streaming_chunk)
        self.conversation_service.response_complete.connect(self.on_response_complete)
        self.conversation_service.error_occurred.connect(self.on_conversation_error)
        
        # Model service to UI components
        self.model_service.model_loaded.connect(self.on_model_loaded)
        self.model_service.model_error.connect(self.on_model_error)
        self.model_service.generation_started.connect(self.on_generation_started)
        self.model_service.generation_finished.connect(self.on_generation_finished)
        
        # Document service to UI components
        self.document_service.document_added.connect(self.on_documents_updated)
        self.document_service.document_removed.connect(self.on_documents_updated)
        self.document_service.rag_status_changed.connect(self.on_rag_status_changed)
        
    def _on_message_sent(self, message: str):
        """Handle message sent from composer"""
        if message.strip():
            # Get thinking mode preference
            use_thinking = self.model_service.get_thinking_mode()
            
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
        if self.thread_view:
            self.thread_view.add_message(message_data)
            
    @Slot()
    def on_thinking_started(self):
        """Handle thinking mode started"""
        if self.thread_view:
            self.thread_view.start_thinking_mode()
            
    @Slot(str)
    def on_thinking_chunk(self, thinking_chunk: str):
        """Handle thinking content chunk"""
        if self.thread_view:
            self.thread_view.update_thinking_content(thinking_chunk)
            
    @Slot(str)
    def on_streaming_chunk(self, response_chunk: str):
        """Handle streaming response chunk"""
        if self.thread_view:
            self.thread_view.update_streaming_response(response_chunk)
            
    @Slot()
    def on_response_complete(self):
        """Handle response completion"""
        if self.thread_view:
            self.thread_view.finish_response()
            
        # Re-enable composer
        if self.composer:
            self.composer.set_sending_state(False)
            
    @Slot(str)
    def on_conversation_error(self, error_message: str):
        """Handle conversation error"""
        if self.thread_view:
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
            
        # Update thread view to show model status
        if self.thread_view:
            self.thread_view.show_status_message(f"✅ Model loaded: {model_name}")
            
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
            
    @Slot()
    def on_documents_updated(self):
        """Handle documents updated"""
        # Could update UI to reflect document changes
        pass
        
    @Slot(bool, int)
    def on_rag_status_changed(self, enabled: bool, doc_count: int):
        """Handle RAG status change"""
        # Update conversation service RAG setting
        self.conversation_service.set_rag_enabled(enabled)
        
        # Could update UI to show RAG status
        if self.thread_view:
            status = f"📚 RAG {'enabled' if enabled else 'disabled'}"
            if enabled and doc_count > 0:
                status += f" ({doc_count} documents)"
            self.thread_view.show_status_message(status)
            
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
