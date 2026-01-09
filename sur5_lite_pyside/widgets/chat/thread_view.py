#!/usr/bin/env python3

"""
Chat Thread View
Displays chat messages with virtualization and modern bubble styling
"""

import time
import html
import re
import json
import logging
from typing import Any, Dict, List, Optional, Match

logger = logging.getLogger(__name__)

from PySide6.QtWidgets import (
    QApplication,
    QScrollArea,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QTextEdit,
    QTextBrowser,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QPropertyAnimation, QEasingCurve, QPoint, Property
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextDocument, QGuiApplication, QPixmap

from .processing_header import ProcessingHeader, prefers_reduced_motion_windows
from .message_unit import MessageUnit
from .skeleton_loader import SkeletonLoaderWidget
from .response_progress_controller import ResponseProgressController


class ChatThreadView(QScrollArea):

    """Scrollable chat thread with message bubbles"""

    # Signals

    message_clicked = Signal(dict)  # message_data

    def __init__(self, parent=None):

        super().__init__(parent)

        # Message storage

        self.messages: List[Dict[str, Any]] = []

        self.message_widgets: List[QWidget] = []

        # Current streaming state - simple temporary widgets
        self.current_thinking_widget: Optional[QWidget] = None
        self.current_response_widget: Optional[QWidget] = None
        self.thinking_content_label: Optional[QLabel] = None
        self.response_content_label: Optional[QLabel] = None
        self.is_streaming = False
        self.processing_header: Optional[ProcessingHeader] = None
        
        # Persistent streaming message unit (replaces temporary widgets)
        self.current_message_unit = None
        
        # Streaming content buffers
        self._thinking_raw_text = ""
        self._response_raw_text = ""
        self._response_started = False

        self._reduce_motion = prefers_reduced_motion_windows()

        self._theme_manager = None

        self._theme_colors: Dict[str, str] = {}

        # Model status tracking
        self.current_model_status_widget: Optional[QWidget] = None

        # Virtualization settings

        self.virtualization_enabled = True

        self.virtualization_threshold = 50

        self.visible_range = (0, 0)

        # ui

        self._setup_ui()

        self._setup_styling()

        self._init_theme_support()

        # Auto-scroll timer

        self.auto_scroll_timer = QTimer()

        self.auto_scroll_timer.timeout.connect(self._scroll_to_bottom)

        self.auto_scroll_timer.setSingleShot(True)

    def _setup_ui(self):
        """Setup the scroll area and content widget"""

        # scroll area cfg

        self.setWidgetResizable(True)

        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Create content widget

        self.content_widget = QWidget()

        self.content_layout = QVBoxLayout(self.content_widget)

        self.content_layout.setContentsMargins(16, 16, 16, 16)

        self.content_layout.setSpacing(12)

        self.content_layout.addStretch()  # Push messages to top initially

        self.setWidget(self.content_widget)

        # Fix rounded corners - ensure viewport respects border-radius
        # autoFillBackground=False lets QSS background show
        # and apply WA_StyledBackground to viewport for proper corner rendering

        if self.viewport():

            self.viewport().setAutoFillBackground(False)
            self.viewport().setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Also ensure content widget respects styling and doesn't paint its own background
        self.content_widget.setAutoFillBackground(False)
        # Note: WA_StyledBackground removed - it caused paint invalidation during scroll

        # Show empty state initially

        self._show_empty_state()

    def _setup_styling(self):
        """Setup QSS styling via property classes"""

        self.setProperty("class", "thread_view")
        self.setObjectName("thread_view")  # ensure stylesheet id selector matches
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def _init_theme_support(self):
        """Fetch theme manager and subscribe for updates"""

        app = QApplication.instance()

        if app and hasattr(app, "theme_manager"):

            self._theme_manager = app.theme_manager

            current = getattr(self._theme_manager, "current_theme", None)

            if current:

                colors = self._theme_manager.get_theme_colors(current) or {}

                self._theme_colors = dict(colors)

            try:

                self._theme_manager.theme_changed.connect(
                    self._on_theme_changed)

            except Exception:

                pass

        else:

            self._theme_manager = None

        self._apply_theme_to_processing_header()

    def _on_theme_changed(self, theme_name: str):
        """Update cached theme colors when theme changes"""

        if not self._theme_manager:

            return

        colors = self._theme_manager.get_theme_colors(theme_name) or {}

        self._theme_colors = dict(colors)

        self._apply_theme_to_processing_header()

    def _apply_theme_to_processing_header(self):
        """Push theme colors into the active processing header"""

        if not self.processing_header:
            return

        try:
            self.processing_header.set_theme_colors(self._theme_colors)
        except RuntimeError:
            self.processing_header = None

    def _finish_processing_header(self):
        """Safely stop and release the active processing header"""

        if not self.processing_header:
            return

        header = self.processing_header
        self.processing_header = None

        try:
            header.finish()
        except RuntimeError:
            pass

    def _ensure_processing_header(self) -> ProcessingHeader:
        """Create the shared processing header if needed"""

        if not self.processing_header:

            self.processing_header = ProcessingHeader(
                self, reduce_motion=self._reduce_motion)

            self.processing_header.set_theme_colors(self._theme_colors)

        return self.processing_header

    def _strip_thinking_tags_for_display(self, text: str) -> str:
        """Remove ALL sentinel tags from UI text (thinking, think, final_answer)"""

        if not text:
            return text

        original = text
        
        # Normalize partial closing tags that can arrive mid-stream
        normalized = re.sub(
            r"</\s*(?:thinking|think|final_answer)(?!\s*>)(?=[A-Za-z0-9])",
            "</thinking>",
            text,
            flags=re.IGNORECASE,
        )
        # Normalize opening tags missing a terminating angle bracket
        normalized = re.sub(
            r"<\s*(?:thinking|think|final_answer)(?![^>]*>)",
            "<thinking>",
            normalized,
            flags=re.IGNORECASE,
        )
        
        # remove sentinel tags
        cleaned = re.sub(
            r"<\s*/?\s*(?:thinking|think|final_answer)(?:\b[^>]*)?>",
            "",
            normalized,
            flags=re.IGNORECASE,
        )
        # Remove any leftover tag fragments
        cleaned = re.sub(
            r"<\s*/?\s*(?:thinking|think|final_answer)\b",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        
        # Log warning if tag stripping unexpectedly expanded text
        if len(cleaned) > len(original) * 1.5:
            logger.warning(f"Tag stripping expanded text: {len(original)}→{len(cleaned)}")
        
        return cleaned  # Don't strip whitespace - preserve spaces!

    def _strip_result_metadata(self, text: str) -> str:
        """Remove Final Answer markers and result tags for UI display."""

        if not text:
            return text

        without_result = re.sub(
            r"(?is)<result>(.*?)</result>",
            lambda match: match.group(1).strip(),
            text,
        )
        without_result = re.sub(
            r"(?is)<final_answer>(.*?)</final_answer>",
            lambda match: match.group(1).strip(),
            without_result,
        )
        return without_result.strip()

    def _trim_reasoning_prefix(self, text: str) -> str:
        """Strip obvious self-talk paragraphs when thinking mode is off."""

        if not text:
            return text

        paragraphs = [
            p.strip()
            for p in re.split(r"\n\s*\n", text)
            if p.strip()
        ]
        if len(paragraphs) <= 1:
            return text.strip()

        def _looks_like_reasoning(block: str, remaining: list[str]) -> bool:
            lower = block.lower()
            cues = (
                "okay,",
                "alright,",
                "first,",
                "first i'll",
                "let me",
                "i need",
                "i should",
                "i will",
                "i'll",
                "i want",
                "i must",
                "to determine",
                "before i",
            )
            if any(lower.startswith(cue) for cue in cues):
                return True
            reason_keywords = (
                "i need",
                "i should",
                "i will",
                "i'll",
                "let me",
                "i want",
                "i must",
                "the user",
                "step",
                "first",
                "plan",
            )
            if any(keyword in lower for keyword in reason_keywords):
                tail = "\n".join(remaining).lower()
                if "final answer" in tail or "<result" in tail or "answer:" in tail:
                    return True
            return False

        remaining = paragraphs
        while len(remaining) > 1 and _looks_like_reasoning(remaining[0], remaining[1:]):
            remaining = remaining[1:]

        return "\n\n".join(remaining).strip()

    def _prepare_assistant_display_text(self, text: str, *, trim_reasoning: bool) -> str:
        """Aggregate sanitization for assistant content before rendering."""

        cleaned = self._strip_thinking_tags_for_display(text)
        cleaned = self._strip_result_metadata(cleaned)
        if trim_reasoning:
            cleaned = self._trim_reasoning_prefix(cleaned)
        return cleaned.strip()

    def _show_empty_state(self):
        """Show empty state when no messages"""

        self._clear_layout()

        # Create empty state widget

        empty_widget = self._create_empty_state()

        self.content_layout.addWidget(empty_widget)

        self.content_layout.addStretch()

    def _create_empty_state(self) -> QWidget:
        """Create the empty state widget"""
        from pathlib import Path

        empty_frame = QFrame()

        empty_layout = QVBoxLayout(empty_frame)

        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_layout.setSpacing(16)

        # Logo image
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Find logo in Images folder
        base_dir = Path(__file__).parent.parent.parent.parent  # Up to App/
        logo_paths = [
            base_dir / "Images" / "sur5_logo.png",
            Path(r"C:\ProgramData\Sur5\Images\sur5_logo.png"),  # Installed location
        ]
        
        logo_loaded = False
        for logo_path in logo_paths:
            if logo_path.exists():
                pixmap = QPixmap(str(logo_path))
                if not pixmap.isNull():
                    # Scale to reasonable size
                    scaled = pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, 
                                          Qt.TransformationMode.SmoothTransformation)
                    logo_label.setPixmap(scaled)
                    logo_loaded = True
                    break
        
        if logo_loaded:
            empty_layout.addWidget(logo_label)

        # Welcome message

        welcome_label = QLabel("Welcome to Sur5 Lite")

        welcome_label.setProperty("class", "welcome_label")

        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_layout.addWidget(welcome_label)

        # Instructions

        instructions = [

            "• Open Control Hub (orange button on right side)",

            "• Load a model from the Model panel",

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
        # Prevent duplicate echo
        if self.messages:
            last = self.messages[-1]
            if last.get("role") == message_data.get("role") and last.get("content") == message_data.get("content"):
                return
        else:
            # Remove empty state on first message
            self._clear_layout()
            self.content_layout.addStretch()

        # Add to message storage
        self.messages.append(message_data)
        
        # Create message widget using MessageUnit
        if message_data["role"] == "user":
            message_widget = MessageUnit(
                role="user",
                content=message_data["content"],
                timestamp=message_data.get("timestamp", time.time())
            )

        elif message_data["role"] == "assistant":
            # Skip check is now simpler - handled by chat_container interception
            # This code path only for non-streamed messages (history, error recovery)
            
            if self.is_streaming or self.current_message_unit:
                logger.debug("Skipping add_message - handled by persistent MessageUnit")
                return
            
            # Only for non-streamed messages
            thinking_content = message_data.get("thinking", "")
            response_content = message_data.get("content", "")
            
            # Validate
            if not response_content or len(response_content.strip()) <= 5:
                response_content = "*Unable to generate response. Please try again.*"
            
            # Create MessageUnit
            message_widget = MessageUnit(
                role="assistant",
                content=response_content,
                timestamp=message_data.get("timestamp", time.time()),
                thinking_content=thinking_content,
                elapsed_ms=message_data.get("elapsed_ms")
            )

        else:
            # Fallback for other message types
            message_widget = self._create_fallback_message_widget(message_data)

        # Add to layout

        self.content_layout.insertWidget(
            self.content_layout.count() - 1, message_widget)

        self.message_widgets.append(message_widget)

        # Handle virtualization if needed

        if self.virtualization_enabled and len(
                self.messages) > self.virtualization_threshold:

            self._update_virtualization()

        # Auto-scroll to bottom (force scroll on new message)

        self._schedule_scroll_to_bottom(force=True)
        
        # CRITICAL FIX: For user messages, ensure scroll reaches bottom after layout completes
        # This fixes the issue where sending a follow-up message while scrolled up
        # doesn't snap the view down to show the new message
        if message_data["role"] == "user":
            QTimer.singleShot(50, lambda: self._schedule_scroll_to_bottom(force=True))
            QTimer.singleShot(150, lambda: self._schedule_scroll_to_bottom(force=True))

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

        bubble_frame.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Minimum)

        bubble_layout = QVBoxLayout(bubble_frame)

        bubble_layout.setContentsMargins(16, 12, 16, 12)

        bubble_layout.setSpacing(4)

        # Message content
        display_text = self._prepare_assistant_display_text(
            content, trim_reasoning=False
        )
        content_label = QLabel(display_text)

        content_label.setWordWrap(True)

        content_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)

        bubble_layout.addWidget(content_label)

        # Timestamp

        time_str = time.strftime("%H:%M", time.localtime(timestamp))

        timestamp_label = QLabel(time_str)

        timestamp_label.setStyleSheet(
            "color: rgba(255, 255, 255, 0.7); font-size: 10px;")

        timestamp_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        bubble_layout.addWidget(timestamp_label)

        container_layout.addWidget(bubble_frame)

        return container

    def _create_assistant_bubble(
            self,
            content: str,
            timestamp: float,
            thinking: str = "") -> QWidget:
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
            thinking_layout.setSpacing(6)

            header_widget = ProcessingHeader(
                thinking_frame, reduce_motion=self._reduce_motion
            )
            header_widget.set_theme_colors(self._theme_colors)
            header_widget.set_skip_available(False)
            header_widget.configure_static_display()
            thinking_layout.addWidget(header_widget)

            thinking_content = QLabel(
                self._strip_thinking_tags_for_display(thinking)
            )
            thinking_content.setWordWrap(True)
            thinking_content.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            thinking_content.setStyleSheet(
                "color: #aaaaaa; font-size: 12px; font-style: italic;"
            )
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

        bubble_frame.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Minimum)

        bubble_layout = QVBoxLayout(bubble_frame)

        bubble_layout.setContentsMargins(16, 12, 16, 12)

        bubble_layout.setSpacing(4)

        # Message content
        display_text = self._prepare_assistant_display_text(
            content, trim_reasoning=not bool(thinking)
        )
        content_label = QLabel(display_text)

        content_label.setWordWrap(True)

        content_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)

        bubble_layout.addWidget(content_label)

        # Timestamp

        time_str = time.strftime("%H:%M", time.localtime(timestamp))

        timestamp_label = QLabel(time_str)

        timestamp_label.setStyleSheet(
            "color: rgba(200, 200, 200, 0.7); font-size: 10px;")

        timestamp_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        bubble_layout.addWidget(timestamp_label)

        bubble_container_layout.addWidget(bubble_frame)

        bubble_container_layout.addStretch()

        container_layout.addWidget(bubble_container)

        return container

    def start_thinking_mode(self):
        """Start streaming by creating persistent MessageUnit"""
        logger.debug("START: Creating persistent MessageUnit for streaming")
        
        # Create single persistent MessageUnit that will handle entire lifecycle
        self.current_message_unit = MessageUnit(
            role="assistant",
            content="",  # Will be filled during finalization
            timestamp=time.time(),
            thinking_content=""  # Will be filled during finalization
        )
        
        # Set theme colors
        if self._theme_colors:
            self.current_message_unit.set_theme_colors(self._theme_colors)
        
        # Add to layout immediately
        self.content_layout.insertWidget(
            self.content_layout.count() - 1,
            self.current_message_unit
        )
        
        # Start streaming mode within MessageUnit
        self.current_message_unit.start_streaming_thinking()
        
        # Set streaming state
        self.is_streaming = True
        self._thinking_raw_text = ""
        self._response_raw_text = ""
        self._response_started = False

        self._schedule_scroll_to_bottom(force=True)

    def start_response_mode(self):
        """Start streaming for standard (non-thinking) mode - direct response"""
        logger.debug("START: Creating MessageUnit for standard response streaming")
        
        # Create MessageUnit for direct response (no thinking phase)
        self.current_message_unit = MessageUnit(
            role="assistant",
            content="",
            timestamp=time.time(),
            thinking_content=""
        )
        
        # Set theme colors
        if self._theme_colors:
            self.current_message_unit.set_theme_colors(self._theme_colors)
        
        # Add to layout immediately
        self.content_layout.insertWidget(
            self.content_layout.count() - 1,
            self.current_message_unit
        )
        
        # Start direct response streaming (skip thinking/skeleton phases)
        self.current_message_unit.start_streaming_response()
        
        # Set streaming state
        self.is_streaming = True
        self._response_started = True
        self._thinking_raw_text = ""
        self._response_raw_text = ""
        
        self._schedule_scroll_to_bottom(force=True)

    def update_thinking_content(self, thinking_chunk: str):
        """Forward thinking chunks to persistent MessageUnit"""
        if not self.current_message_unit:
            return
        
        try:
            chunk_data = json.loads(thinking_chunk)
        except json.JSONDecodeError:
            chunk_data = {"content": thinking_chunk, "close": False}
        
        if chunk_data.get("close"):
            logger.debug("THINKING CLOSE: Transitioning to skeleton")
            # Transition MessageUnit to skeleton phase
            self.current_message_unit.transition_to_skeleton()
            self._response_started = True
            self._schedule_scroll_to_bottom()
        else:
            clean_chunk = chunk_data.get("content", thinking_chunk)
            # Forward to MessageUnit
            self.current_message_unit.update_thinking_stream(clean_chunk)
            # Smart auto-scroll: follows streaming if user is near bottom
            self._schedule_scroll_to_bottom()

    def _make_thinking_collapsible(self, thinking_widget: QWidget):
        """Add collapse/expand functionality to thinking bubble."""
        if not thinking_widget:
            return
        
        # Find the thinking frame (should be the first child of the container)
        thinking_layout = thinking_widget.layout()
        if not thinking_layout or thinking_layout.count() == 0:
            return
        
        thinking_frame = thinking_layout.itemAt(0).widget()
        if not thinking_frame:
            return
        
        # Check if already made collapsible
        if thinking_frame.property("collapsible_setup"):
            return
        
        # Get the thinking frame layout
        frame_layout = thinking_frame.layout()
        if not frame_layout:
            return
        
        # Find the processing header and thinking content label
        processing_header = None
        thinking_content = None
        
        for i in range(frame_layout.count()):
            widget = frame_layout.itemAt(i).widget()
            if widget:
                if isinstance(widget, ProcessingHeader):
                    processing_header = widget
                elif isinstance(widget, QLabel):
                    thinking_content = widget
        
        if not processing_header or not thinking_content:
            return

        # Update processing header to show collapse/expand functionality
        # Set it to completed state with collapse option
        try:
            processing_header.set_skip_available(False)
            processing_header.complete()
            # Mark as collapsible
            thinking_frame.setProperty("collapsible_setup", True)
            thinking_content.setProperty("thinking_content_collapsible", True)
        except Exception:
            # If header methods fail, still mark as setup
            thinking_frame.setProperty("collapsible_setup", True)

    def update_streaming_response(self, response_chunk: str):
        """Forward response chunks to persistent MessageUnit"""
        if not self.current_message_unit:
            return
        
        try:
            chunk_data = json.loads(response_chunk)
        except json.JSONDecodeError:
            chunk_data = {"content": response_chunk, "close": False}
        
        if chunk_data.get("close"):
            logger.debug("RESPONSE CLOSE: Waiting for backend content")
            # DO NOT finalize here - wait for message_received with backend content
            # Show "Finalizing..." state while backend processes
            if self.current_message_unit:
                self.current_message_unit.show_finalizing_state()
            self._response_started = False
        else:
            clean_chunk = chunk_data.get("content", response_chunk)
            # Forward to MessageUnit (buffered internally while skeleton shows)
            self.current_message_unit.update_response_stream(clean_chunk)
            # Smart auto-scroll during response phase
            self._schedule_scroll_to_bottom()

    def finalize_with_backend_content(self, thinking_content: str, response_content: str, timestamp: float):
        """Finalize persistent MessageUnit using backend-extracted content"""
        if not self.current_message_unit:
            logger.warning("No persistent MessageUnit to finalize")
            return
        
        logger.debug(f"finalize: think={len(thinking_content)} resp={len(response_content)}")
        
        # Validate content
        if not response_content or len(response_content.strip()) <= 5:
            response_content = "*Unable to generate response. Please try again.*"
        
        # Finalize the MessageUnit with CORRECT backend content
        self.current_message_unit.finalize_streaming(thinking_content, response_content)
        
        # Add to message history
        self.messages.append({
            "role": "assistant",
            "content": response_content,
            "thinking": thinking_content,
            "timestamp": timestamp
        })
        
        # Keep reference briefly for skip logic, then clear
        QTimer.singleShot(500, self._clear_streaming_state)
        
        self._schedule_scroll_to_bottom()
        
        # Schedule additional scroll after MessageUnit animations complete (fade-out 200ms + fade-in 200ms)
        # This ensures scroll reaches the actual expanded content height, not the skeleton height
        QTimer.singleShot(500, self._schedule_scroll_to_bottom)

    def _clear_streaming_state(self):
        """Clear streaming state after finalization"""
        self.current_message_unit = None
        self.is_streaming = False
        self._thinking_raw_text = ""
        self._response_raw_text = ""
        logger.debug("Streaming state cleared")


    def _update_message_timestamp(self, message_unit: Optional[MessageUnit], timestamp: float):
        """Ensure a message bubble displays the correct timestamp."""
        if not message_unit:
            return

        message_unit.timestamp = timestamp
        if hasattr(message_unit, "timestamp_label"):
            time_str = time.strftime("%H:%M", time.localtime(timestamp))
            message_unit.timestamp_label.setText(time_str)

    def _remove_duplicate_response_widgets(self, final_content: str, timestamp: float):
        """Prevent duplicate assistant bubbles for the same streamed message."""
        if not final_content:
            return

        to_remove: List[MessageUnit] = []
        for widget in list(self.message_widgets):
            if not isinstance(widget, MessageUnit):
                continue
            if widget.thinking_mode:
                continue
            if widget is self.response_unit:
                continue

            same_timestamp = abs(widget.timestamp - timestamp) < 1.0
            same_content = widget.content.strip() == final_content.strip()

            if same_timestamp and same_content:
                to_remove.append(widget)

        for widget in to_remove:
            if self.content_layout.indexOf(widget) != -1:
                self.content_layout.removeWidget(widget)
            widget.deleteLater()
            try:
                self.message_widgets.remove(widget)
            except ValueError:
                pass

    def _finalize_streaming_message(self, message_data: Dict[str, Any]):
        """Finalize existing streaming widgets with final content"""
        logger.debug(f"finalize: think_unit={self.thinking_unit is not None} "
                     f"response_unit={self.response_unit is not None}, "
                     f"has_thinking={bool(message_data.get('thinking'))}, "
                     f"has_content={bool(message_data.get('content'))}")
        
        # Update EXISTING thinking unit (don't create new)
        final_thinking = message_data.get("thinking", "")
        final_content = message_data.get("content", "")
        timestamp = message_data.get("timestamp", time.time())

        # Remove any duplicate assistant bubbles left from earlier layouts
        self._remove_duplicate_response_widgets(final_content, timestamp)

        if self.thinking_unit and final_thinking:
            logger.debug(f"think_unit: {len(final_thinking)}")
            self.thinking_unit.set_content(final_thinking)
            self.thinking_unit.set_collapsible_header("Model reasoning - click to expand")
            self.thinking_unit.set_collapsed(True)
            if self.thinking_unit not in self.message_widgets:
                self.message_widgets.append(self.thinking_unit)
        
        # Update EXISTING response unit (don't create new)
        if self.response_unit:
            if final_content:
                self.response_unit.finalize_content(final_content)
                self._response_buffer = final_content
                if self.response_unit not in self.message_widgets:
                    self.message_widgets.append(self.response_unit)
            else:
                # No final response, remove the empty bubble
                self.response_unit.deleteLater()

        # Case: No streaming widgets were ever created, but we have final content
        # This handles non-streamed messages or errors gracefully.
        elif final_content and not self.response_unit:
            self.add_message({
                "role": "assistant",
                "content": final_content,
                "thinking": final_thinking,
                "timestamp": timestamp
            })

        # Add to message history if we have complete data
        if message_data and (final_thinking or final_content):
            # Prevent duplicates before adding
            if not self.messages or not (
                self.messages[-1].get("role") == "assistant" and
                self.messages[-1].get("content") == final_content and
                abs(self.messages[-1].get("timestamp", 0) - timestamp) < 1.0
            ):
                self.messages.append(message_data)

        # reset streaming state after finalization
        self.thinking_unit = None
        self.response_unit = None
        self.is_streaming = False
        self._thinking_buffer = ""
        self._response_buffer = ""

        self._schedule_scroll_to_bottom()

    

    def show_error(self, error_message: str):
        """Show an error message"""
        # Clean up persistent message unit if active
        if self.current_message_unit:
            self.content_layout.removeWidget(self.current_message_unit)
            self.current_message_unit.deleteLater()
            self.current_message_unit = None
        
        # Clean up old temporary widgets (for backward compatibility)
        self._finish_processing_header()
        if self.current_thinking_widget:
            self.content_layout.removeWidget(self.current_thinking_widget)
            self.current_thinking_widget.deleteLater()
            self.current_thinking_widget = None
            self.thinking_content_label = None
        if self.current_response_widget:
            self.content_layout.removeWidget(self.current_response_widget)
            self.current_response_widget.deleteLater()
            self.current_response_widget = None
            self.response_content_label = None
        
        # Reset streaming state
        self.is_streaming = False
        self._response_started = False
        self._thinking_raw_text = ""
        self._response_raw_text = ""

        error_container = QWidget()

        error_layout = QHBoxLayout(error_container)

        error_layout.setContentsMargins(0, 0, 0, 0)

        error_frame = QFrame()

        error_frame.setProperty("class", "error_indicator")

        error_frame.setMaximumWidth(500)

        error_frame_layout = QVBoxLayout(error_frame)

        error_frame_layout.setContentsMargins(12, 8, 12, 8)

        error_label = QLabel(f"Error: {error_message}")

        error_label.setProperty("class", "error_message")

        error_label.setWordWrap(True)

        error_frame_layout.addWidget(error_label)

        error_layout.addWidget(error_frame)

        error_layout.addStretch()

        self.content_layout.insertWidget(
            self.content_layout.count() - 1, error_container)

        self._schedule_scroll_to_bottom()

    def show_status_message(self, status_message: str, is_model_status: bool = False):
        """Show a status message
        
        Args:
            status_message: The message to display
            is_model_status: If True, replaces any previous model status and shows at top
        """
        
        # If this is a model status message, remove any previous model status
        if is_model_status and self.current_model_status_widget:
            self.content_layout.removeWidget(self.current_model_status_widget)
            self.current_model_status_widget.deleteLater()
            self.current_model_status_widget = None

        status_container = QWidget()

        status_layout = QHBoxLayout(status_container)

        status_layout.setContentsMargins(0, 0, 0, 0)

        status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        status_label = QLabel(status_message)

        status_label.setStyleSheet(
            "color: #888888; font-size: 12px; font-style: italic;")

        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        status_layout.addWidget(status_label)

        # Insert at top (position 0) for model status, at bottom for other messages
        insert_position = 0 if is_model_status else (self.content_layout.count() - 1)
        self.content_layout.insertWidget(insert_position, status_container)
        
        # Track model status widget
        if is_model_status:
            self.current_model_status_widget = status_container
        
        # Don't auto-scroll for model status (it's at the top)
        if not is_model_status:
            self._schedule_scroll_to_bottom()

    def clear_messages(self):
        """Clear all messages"""
        # Clean up persistent streaming widget if active
        if self.current_message_unit:
            self.content_layout.removeWidget(self.current_message_unit)
            self.current_message_unit.deleteLater()
            self.current_message_unit = None

        # Clean up old temporary widgets (for backward compatibility)
        self._finish_processing_header()
        if self.current_thinking_widget:
            self.content_layout.removeWidget(self.current_thinking_widget)
            self.current_thinking_widget.deleteLater()
            self.current_thinking_widget = None
        
        if self.current_response_widget:
            self.content_layout.removeWidget(self.current_response_widget)
            self.current_response_widget.deleteLater()
            self.current_response_widget = None

        # Reset streaming state
        self.is_streaming = False
        self._thinking_raw_text = ""
        self._response_raw_text = ""

        # Clear model status tracking (will be removed by _clear_layout anyway)
        self.current_model_status_widget = None

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

    def _schedule_scroll_to_bottom(self, force: bool = False):
        """Schedule auto-scroll to bottom
        
        Args:
            force: If True, force scroll to bottom regardless of user position
        """
        self._force_scroll = force
        # Use 0ms to defer to next event loop when Qt has updated the layout
        self.auto_scroll_timer.start(0)

    def _scroll_to_bottom(self):
        """Smart auto-scroll: only scroll if user is near the bottom
        
        This allows the thinking bubble to grow naturally while respecting
        user's manual scroll position. Matches ChatGPT/Cursor UX pattern.
        """
        scrollbar = self.verticalScrollBar()
        
        # Get current scroll position and maximum
        current_value = scrollbar.value()
        maximum_value = scrollbar.maximum()
        
        # Check if force scroll is requested
        force_scroll = getattr(self, '_force_scroll', False)
        
        # Define "near bottom" threshold (100px tolerance)
        # If user is within 100px of bottom, continue auto-scrolling
        near_bottom_threshold = 100
        
        # Calculate distance from bottom
        distance_from_bottom = maximum_value - current_value
        
        # Force scroll or only auto-scroll if user is already near the bottom
        if force_scroll or distance_from_bottom <= near_bottom_threshold:
            scrollbar.setValue(maximum_value)
            
            # Safety net: if we're forcing scroll and still not at the very bottom,
            # schedule one more attempt (catches slow layout updates)
            if force_scroll and scrollbar.value() < scrollbar.maximum():
                QTimer.singleShot(50, lambda: scrollbar.setValue(scrollbar.maximum()))
        # else: User has manually scrolled up - respect their position
        
        # Reset force flag after use
        self._force_scroll = False

    def _update_virtualization(self):
        """Update virtualization if enabled"""

        if not self.virtualization_enabled:

            return

        # For now, simple implementation - could be enhanced with more
        # sophisticated virtualization

        total_messages = len(self.messages)

        if total_messages > self.virtualization_threshold:

            # Keep last N messages visible

            visible_count = min(self.virtualization_threshold, total_messages)

            start_idx = total_messages - visible_count

            # This is a simplified approach - real virtualization would be more
            # complex

            logger.debug(
                f"Virtualization: Showing {visible_count} of {total_messages} messages")

    def _create_fallback_message_widget(
            self, message_data: Dict[str, Any]) -> QWidget:
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

    def highlight_search_result(
            self,
            message_index: int,
            search_term: str,
            is_current: bool = False):
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

    def _create_highlighted_html(
            self,
            text: str,
            search_term: str,
            is_current: bool) -> str:
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

        def replace_match(match: Match) -> str:

            matched_text = match.group()

            return f'<span style="background-color: {bg_color}; color: {text_color}; padding: 2px 4px; border-radius: 3px; font-weight: bold;">{matched_text}</span>'

        highlighted = pattern.sub(replace_match, escaped_text)

        return highlighted

    def _sanitize_stream_chunk(self, chunk: str, *, is_thinking: bool) -> str:
        """Normalize streaming chunk text by stripping tags, placeholders, and control chars."""
        if not chunk:
            return ""

        cleaned = chunk.replace("\r", "")
        cleaned = cleaned.replace("\u2028", "\n")
        cleaned = cleaned.replace("\u2029", "\n")

        # Remove known placeholders that should never surface in the UI
        placeholders = [
            "Your final response here.",
            "Your final response here",
            "<final_response>",
            "</final_response>"
        ]
        for placeholder in placeholders:
            cleaned = cleaned.replace(placeholder, "")

        # Strip XML-style tags used for reasoning
        tag_patterns = [
            (r"<\s*(?:think|thinking)\b[^>]*?>?", "thinking", False),
            (r"</\s*(?:think|thinking)\b[^>]*?>?", "thinking", True),
            (r"<\s*/?\s*(?:response|final_answer|answer|result)\b[^>]*?>?", "response", None),
        ]

        for pattern, tag_type, is_closing in tag_patterns:
            def repl(match: Match[str]) -> str:
                if tag_type == "thinking":
                    if is_closing:
                        if is_thinking:
                            self._pending_thinking_tag_fragment = False
                        else:
                            self._pending_response_tag_fragment = False
                    else:
                        if is_thinking:
                            self._pending_thinking_tag_fragment = True
                        else:
                            self._pending_response_tag_fragment = True
                return ""

            cleaned = re.sub(pattern, repl, cleaned, flags=re.IGNORECASE)

        pending_fragment = self._pending_thinking_tag_fragment if is_thinking else self._pending_response_tag_fragment
        if pending_fragment:
            if ">" in cleaned:
                cleaned = cleaned.split(">", 1)[1]
                if is_thinking:
                    self._pending_thinking_tag_fragment = False
                else:
                    self._pending_response_tag_fragment = False
            else:
                return ""

        # Remove any lingering '<th' partial fragments from streamed tags
        cleaned = re.sub(r"<\s*/?\s*th(?:ink)?", "", cleaned, flags=re.IGNORECASE)

        # Collapse excessive spaces created by removals
        cleaned = re.sub(r"\s+", lambda m: "\n" if "\n" in m.group(0) else " ", cleaned)
        return cleaned

    def _sanitize_final_text(self, text: str, *, is_thinking: bool) -> str:
        """Sanitize fully generated text before rendering in the UI."""
        if not text:
            return ""

        cleaned = html.unescape(text)
        placeholders = [
            "Your final response here.",
            "Your final response here",
            "<final_response>",
            "</final_response>",
        ]
        for placeholder in placeholders:
            cleaned = cleaned.replace(placeholder, "")

        cleaned = re.sub(r"<\s*/?\s*(?:think|thinking|response|final_answer|answer|result)\b[^>]*>", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.replace("<br>", "\n").replace("<br/>", "\n")
        cleaned = cleaned.replace("\r", "")
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
        return cleaned.strip()

    @staticmethod
    def _compute_stream_delta(cleaned_chunk: str, existing_buffer: str) -> str:
        """Return only the new portion of a cleaned chunk, avoiding duplicate re-streaming."""
        cleaned_chunk = cleaned_chunk.rstrip()
        if not cleaned_chunk:
            return ""

        if not existing_buffer:
            return cleaned_chunk

        existing_buffer = existing_buffer.rstrip()

        # If the existing buffer already contains the new chunk, nothing to append
        if cleaned_chunk in existing_buffer:
            return ""

        # If the new chunk fully contains the previous buffer, append only the new tail
        if existing_buffer and cleaned_chunk.startswith(existing_buffer):
            return cleaned_chunk[len(existing_buffer):]

        max_overlap = min(len(existing_buffer), len(cleaned_chunk))
        for overlap in range(max_overlap, 0, -1):
            if existing_buffer[-overlap:] == cleaned_chunk[:overlap]:
                return cleaned_chunk[overlap:]

        # Fallback: avoid re-streaming tiny fragments that were already appended
        for shift in range(1, min(4, len(cleaned_chunk))):
            candidate = cleaned_chunk[shift:]
            if candidate and existing_buffer.endswith(candidate[:len(candidate)]):
                return candidate

        if cleaned_chunk == existing_buffer:
            return ""

        return cleaned_chunk
