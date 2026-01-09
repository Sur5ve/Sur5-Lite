#!/usr/bin/env python3
"""
Message Unit - Static chat bubble for final display only
"""

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QTextBrowser,
    QSizePolicy,
    QGraphicsOpacityEffect,
    QMenu,
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QGuiApplication, QColor, QFont, QCursor
import time
import logging
from typing import Dict

from .collapsible_frame import CollapsibleFrame

logger = logging.getLogger(__name__)


class MessageUnit(QWidget):
    """Static message bubble with copy button and collapsible thinking"""

    copy_requested = Signal(str)

    def __init__(
        self,
        role: str,
        content: str,
        timestamp: float,
        thinking_content: str = "",
        elapsed_ms: int = None,
        parent=None,
    ):
        super().__init__(parent)
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.thinking_content = thinking_content
        self.elapsed_ms = elapsed_ms
        self.collapsible_frame = None

        # Streaming state
        self.is_streaming = False
        self.streaming_phase = None  # "thinking", "skeleton", "final"
        self._thinking_buffer = ""
        self._response_buffer = ""

        # Streaming widgets (created on demand)
        self._processing_header = None
        self._skeleton_loader = None
        self._progress_label = None
        self._thinking_browser_streaming = None  # Different from final collapsible
        self._response_progress = None

        # Animation references (prevent garbage collection)
        self._fade_out_anim = None
        self._fade_in_anim = None
        self._opacity_effect_skeleton = None
        self._opacity_effect_content = None

        # Theme colors (for streaming widgets)
        self._theme_colors = {}

        # Reduce motion preference
        from .processing_header import prefers_reduced_motion_windows
        self._reduce_motion = prefers_reduced_motion_windows()

        # Typing indicator (shown before first token arrives in non-thinking mode)
        self._typing_indicator = None
        self._typing_timer = None
        self._typing_dots = 0

        self._init_ui()

    def _create_thinking_browser(self) -> QTextBrowser:
        """Create and configure a thinking content browser"""
        thinking_browser = QTextBrowser()
        thinking_browser.setReadOnly(True)
        thinking_browser.setFrameShape(QFrame.Shape.NoFrame)
        thinking_browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        thinking_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        thinking_browser.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth)
        thinking_browser.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        thinking_browser.setProperty("class", "thinking_content")
        thinking_browser.setSizeAdjustPolicy(QTextBrowser.SizeAdjustPolicy.AdjustToContents)
        thinking_browser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        thinking_browser.setMinimumHeight(30)
        
        # Connect size adjustment
        thinking_browser.document().documentLayout().documentSizeChanged.connect(
            lambda: self._adjust_browser_height(thinking_browser)
        )
        
        return thinking_browser

    def _init_ui(self):
        """Initialize UI - SIMPLIFIED AND WORKING"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 4, 8, 4)

        # Set full-width row background based on role
        self.setAutoFillBackground(True)
        palette = self.palette()
        if self.role == "user":
            # User messages: slightly lighter background
            palette.setColor(self.backgroundRole(), QColor("#1a1a1a"))  # bg_secondary
        else:  # assistant
            # Assistant messages: match main chat background
            palette.setColor(self.backgroundRole(), QColor("#0d0d0d"))  # bg_primary
        self.setPalette(palette)
        
        # prevent WA_StyledBackground scroll paint bug
        # Do NOT set WA_StyledBackground on MessageUnit - use palette only
        # self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)  # Explicitly disabled

        self.bubble_frame = QFrame()
        self.bubble_frame.setProperty("class", f"{self.role}_bubble")
        self.bubble_frame.setMaximumWidth(700)  # Reduced to prevent horizontal overflow

        bubble_layout = QVBoxLayout(self.bubble_frame)
        bubble_layout.setContentsMargins(16, 12, 16, 12)
        bubble_layout.setSpacing(8)

        # Add "Sur" branding header for assistant messages
        if self.role == "assistant":
            header_layout = QHBoxLayout()
            header_layout.setContentsMargins(0, 0, 0, 4)
            
            sur_label = QLabel("Sur")
            sur_label.setProperty("class", "sur_branding")
            sur_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
            sur_label.setFont(sur_font)
            
            # prevent paint invalidation
            sur_label.setAutoFillBackground(False)
            
            # Use theme-aware color - will be styled via QSS
            header_layout.addWidget(sur_label)
            header_layout.addStretch()
            
            bubble_layout.addLayout(header_layout)

        # Add collapsible thinking section if thinking content present
        if self.thinking_content:
            self.collapsible_frame = CollapsibleFrame("Model reasoning - click to expand")
            
            # Create thinking content browser
            thinking_browser = self._create_thinking_browser()
            thinking_browser.setPlainText(self.thinking_content)
            
            self.collapsible_frame.set_content(thinking_browser)
            self.collapsible_frame.collapse()  # Default collapsed
            bubble_layout.addWidget(self.collapsible_frame)

        # Main content browser - dynamically expands to fit ALL content (always present)
        self.content_browser = QTextBrowser()
        self.content_browser.setReadOnly(True)
        self.content_browser.setFrameShape(QFrame.Shape.NoFrame)
        self.content_browser.setOpenExternalLinks(False)
        self.content_browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content_browser.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth)  # Ensure word wrapping
        self.content_browser.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.content_browser.setProperty("class", "message_content")
        self.content_browser.setSizeAdjustPolicy(QTextBrowser.SizeAdjustPolicy.AdjustToContents)
        
        # size policy for vertical expansion
        self.content_browser.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        
        # Connect document size changes to trigger height adjustment
        self.content_browser.document().documentLayout().documentSizeChanged.connect(
            self._on_document_size_changed
        )
        
        self.content_browser.setMinimumHeight(30)
        
        bubble_layout.addWidget(self.content_browser)

        # Controls (timestamp + copy button)
        controls_layout = QHBoxLayout()

        time_str = time.strftime("%H:%M", time.localtime(self.timestamp))
        # Add elapsed time if available (inline format: "14:23 • 2.4s")
        if self.elapsed_ms is not None:
            elapsed_sec = self.elapsed_ms / 1000.0
            time_str += f" • {elapsed_sec:.1f}s"
        self.timestamp_label = QLabel(time_str)
        self.timestamp_label.setStyleSheet("color: rgba(230, 230, 230, 0.95); font-size: 10px; font-weight: 500;")

        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setMaximumWidth(50)
        self.copy_btn.setMaximumHeight(24)
        self.copy_btn.setToolTip("Copy response (right-click for options)")
        self.copy_btn.setProperty("class", "message_copy_btn")
        self.copy_btn.clicked.connect(self._on_copy_clicked)
        self.copy_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.copy_btn.customContextMenuRequested.connect(self._show_copy_menu)

        controls_layout.addWidget(self.timestamp_label)
        controls_layout.addStretch()
        controls_layout.addWidget(self.copy_btn)

        bubble_layout.addLayout(controls_layout)

        # Alignment: user messages on right, assistant on left
        if self.role == "user":
            main_layout.addStretch()
            main_layout.addWidget(self.bubble_frame)
        else:
            main_layout.addWidget(self.bubble_frame)
            main_layout.addStretch()

        # Initial render
        if self.content:
            self.content_browser.setMarkdown(self.content)
        self._adjust_height()

    def _adjust_height(self):
        """Adjust height to fit ALL content without internal scrolling"""
        try:
            doc = self.content_browser.document()
            if not doc:
                return
                
            doc_height = doc.size().height()
            
            # Calculate target height with padding
            target_height = max(int(doc_height) + 20, 30)
            
            # Set minimum height to match content - allows natural expansion
            self.content_browser.setMinimumHeight(target_height)
            self.content_browser.setMaximumHeight(16777215)  # Reset max height
            
            # Force layout update
            self.content_browser.updateGeometry()
            self.bubble_frame.updateGeometry()
            self.updateGeometry()
        except Exception as e:
            logger.warning(f"Error adjusting height: {e}")
    
    def _on_document_size_changed(self, new_size):
        """Handle document size changes to dynamically adjust height"""
        self._adjust_height()

    def _adjust_browser_height(self, browser: QTextBrowser):
        """Adjust browser height to fit content (for thinking browser)"""
        doc = browser.document()
        doc_height = doc.size().height()
        target_height = max(int(doc_height) + 20, 30)
        browser.setFixedHeight(target_height)
        browser.updateGeometry()

    def _on_copy_clicked(self):
        """Copy response content to clipboard"""
        QGuiApplication.clipboard().setText(self.content_browser.toPlainText())
        original_text = self.copy_btn.text()
        self.copy_btn.setText("Copied")
        QTimer.singleShot(1500, lambda: self.copy_btn.setText(original_text))
    
    def _show_copy_menu(self, pos):
        """Show copy options menu (right-click)"""
        menu = QMenu(self)
        
        # Copy response only (default)
        copy_response = menu.addAction("Copy response")
        copy_response.triggered.connect(self._on_copy_clicked)
        
        # Copy with thinking (only if thinking content exists)
        if self.thinking_content:
            copy_all = menu.addAction("Copy with thinking")
            copy_all.triggered.connect(self._on_copy_with_thinking)
        
        # Show menu at cursor position
        menu.exec(QCursor.pos())
    
    def _on_copy_with_thinking(self):
        """Copy both thinking and response content to clipboard"""
        full_content = ""
        if self.thinking_content:
            full_content += f"## Model Thinking\n\n{self.thinking_content}\n\n"
        full_content += f"## Response\n\n{self.content_browser.toPlainText()}"
        
        QGuiApplication.clipboard().setText(full_content)
        original_text = self.copy_btn.text()
        self.copy_btn.setText("Copied")
        QTimer.singleShot(1500, lambda: self.copy_btn.setText(original_text))

    def set_content(self, content: str):
        """Replace content entirely"""
        self.content = content
        self.content_browser.setMarkdown(self.content)
        self._adjust_height()

    def set_collapsible_header(self, text: str):
        """Update collapsible header text"""
        if self.collapsible_frame:
            self.collapsible_frame.set_header(text)

    def set_collapsed(self, collapsed: bool):
        """Set collapsed state"""
        if self.collapsible_frame:
            if collapsed:
                self.collapsible_frame.collapse()
            else:
                self.collapsible_frame.expand()

    def set_theme_colors(self, colors: Dict[str, str]):
        """Set theme colors for streaming widgets"""
        self._theme_colors = dict(colors) if colors else {}

    def start_streaming_thinking(self):
        """Initialize for thinking streaming mode"""
        self.is_streaming = True
        self.streaming_phase = "thinking"
        
        # Hide final content browser temporarily
        self.content_browser.hide()
        
        # Hide controls temporarily
        if hasattr(self, 'copy_btn'):
            self.copy_btn.hide()
        if hasattr(self, 'timestamp_label'):
            self.timestamp_label.hide()
        
        # Create processing header in bubble
        from .processing_header import ProcessingHeader
        self._processing_header = ProcessingHeader(
            self.bubble_frame,
            reduce_motion=self._reduce_motion
        )
        self._processing_header.set_theme_colors(self._theme_colors)
        self._processing_header.set_skip_available(True)
        self._processing_header.begin()
        self.bubble_frame.layout().insertWidget(0, self._processing_header)
        
        # Create thinking content label for streaming
        self._thinking_browser_streaming = QLabel("")
        self._thinking_browser_streaming.setWordWrap(True)
        self._thinking_browser_streaming.setProperty("class", "thinking_content")
        self.bubble_frame.layout().insertWidget(1, self._thinking_browser_streaming)

    def update_thinking_stream(self, chunk: str):
        """Append thinking chunk during streaming"""
        if self.streaming_phase != "thinking":
            return
        
        self._thinking_buffer += chunk
        if self._thinking_browser_streaming:
            self._thinking_browser_streaming.setText(self._thinking_buffer)

    def start_streaming_response(self):
        """Initialize for direct response streaming (no thinking phase)"""
        self.is_streaming = True
        self.streaming_phase = "response"
        
        # Hide content browser initially (will show when first token arrives)
        self.content_browser.hide()
        self.content_browser.setText("")
        
        # Show typing indicator until first token arrives
        self._show_typing_indicator()
        
        # Hide thinking-related elements
        if hasattr(self, 'thinking_frame') and self.thinking_frame:
            self.thinking_frame.hide()
        
        # Hide controls temporarily during streaming (will show on finalize)
        if hasattr(self, 'copy_btn'):
            self.copy_btn.hide()
        if hasattr(self, 'timestamp_label'):
            self.timestamp_label.hide()
        
        logger.debug("MessageUnit: Started direct response streaming with typing indicator")
    
    def _show_typing_indicator(self):
        """Show animated typing dots before first token arrives"""
        # Get theme colors
        primary = self._theme_colors.get("primary", "#20B2AA")
        text_muted = self._theme_colors.get("text_muted", "#888888")
        
        # Create typing indicator label
        self._typing_indicator = QLabel("●")
        self._typing_indicator.setStyleSheet(f"""
            font-size: 20px;
            color: {primary};
            letter-spacing: 6px;
            padding: 8px 4px;
        """)
        self._typing_indicator.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # Insert at beginning of bubble layout
        self.bubble_frame.layout().insertWidget(0, self._typing_indicator)
        
        # Start animation timer (if motion is allowed)
        if not self._reduce_motion:
            self._typing_timer = QTimer(self)
            self._typing_timer.timeout.connect(self._animate_typing_dots)
            self._typing_timer.start(350)  # Update every 350ms
            self._typing_dots = 1
        else:
            # Reduced motion: show static dots
            self._typing_indicator.setText("●●●")
        
        logger.debug("MessageUnit: Typing indicator shown")
    
    def _animate_typing_dots(self):
        """Animate the typing dots (● → ●● → ●●● → ●)"""
        if not self._typing_indicator:
            return
        self._typing_dots = (self._typing_dots % 3) + 1
        self._typing_indicator.setText("●" * self._typing_dots)
    
    def _hide_typing_indicator(self):
        """Hide typing indicator (called when first token arrives)"""
        if self._typing_timer:
            self._typing_timer.stop()
            self._typing_timer.deleteLater()
            self._typing_timer = None
        if self._typing_indicator:
            self._typing_indicator.hide()
            self._typing_indicator.deleteLater()
            self._typing_indicator = None
        logger.debug("MessageUnit: Typing indicator hidden")

    def transition_to_skeleton(self):
        """Transition from thinking to skeleton loader phase"""
        logger.debug("🎭 MessageUnit.transition_to_skeleton() CALLED")
        self.streaming_phase = "skeleton"
        
        # Hide/finish processing header
        if self._processing_header:
            self._processing_header.finish()
            self._processing_header.hide()
            logger.debug("  - Processing header hidden")
        
        # Hide thinking streaming widget
        if self._thinking_browser_streaming:
            self._thinking_browser_streaming.hide()
            logger.debug("  - Thinking browser hidden")
        
        # Create skeleton loader
        from .skeleton_loader import SkeletonLoaderWidget
        self._skeleton_loader = SkeletonLoaderWidget(line_count=3)
        self._skeleton_loader.set_theme_colors(self._theme_colors)
        self.bubble_frame.layout().addWidget(self._skeleton_loader)
        logger.debug("  - Skeleton loader created and added")
        
        # Create progress label
        text_muted = self._theme_colors.get("text_muted", "#888888")
        self._progress_label = QLabel("Analyzing context")
        self._progress_label.setWordWrap(True)
        self._progress_label.setStyleSheet(f"font-size: 12px; color: {text_muted};")
        self.bubble_frame.layout().addWidget(self._progress_label)
        logger.debug("  - Progress label created")
        
        # Start progress controller
        from .response_progress_controller import ResponseProgressController
        self._response_progress = ResponseProgressController(self._progress_label, parent=self)
        self._response_progress.start()
        logger.debug("  - Progress controller started")

    def update_response_stream(self, chunk: str):
        """Buffer response chunks during streaming"""
        # Allow both skeleton phase AND direct response phase
        if self.streaming_phase not in ("skeleton", "response"):
            return
        
        # Hide typing indicator on first token (for direct response mode)
        if not self._response_buffer and chunk and self._typing_indicator:
            self._hide_typing_indicator()
            self.content_browser.show()
            logger.debug("MessageUnit: First token received, showing content browser")
        
        self._response_buffer += chunk
        
        # FIX: In skeleton phase, just buffer content - don't transition yet!
        # The skeleton stays visible until finalize_streaming() is called with final content.
        # This creates the proper UX: thinking streams → skeleton appears → final response revealed
        if self.streaming_phase == "skeleton":
            # Just buffer, skeleton animation continues
            logger.debug(f"buffering: {len(self._response_buffer)}")
            return
        
        # For direct response mode, update browser immediately
        if self.streaming_phase == "response":
            self.content_browser.setText(self._response_buffer)
            self._adjust_height()
    
    def _transition_skeleton_to_response(self):
        """Transition from skeleton phase to live response streaming"""
        logger.debug("🔄 MessageUnit: Transitioning skeleton → live response streaming")
        
        # Hide and cleanup skeleton loader
        if hasattr(self, '_skeleton_loader') and self._skeleton_loader:
            self._skeleton_loader.hide()
            self._skeleton_loader.deleteLater()
            self._skeleton_loader = None
        
        # Hide progress label
        if hasattr(self, '_progress_label') and self._progress_label:
            self._progress_label.hide()
            self._progress_label.deleteLater()
            self._progress_label = None
        
        # Stop progress controller
        if hasattr(self, '_response_progress') and self._response_progress:
            self._response_progress.stop()
            self._response_progress = None
        
        # Switch to response phase and show content browser
        self.streaming_phase = "response"
        self.content_browser.show()
        self.content_browser.setText(self._response_buffer)
        self._adjust_height()
        logger.debug("✅ Now in live response streaming mode")

    def show_finalizing_state(self):
        """Show 'Finalizing...' state while backend processes the response"""
        logger.debug("⏳ MessageUnit.show_finalizing_state() CALLED - Showing post-processing loader")
        
        # Stop the progress controller (no more cycling microcopy)
        if self._response_progress:
            self._response_progress.stop()
            self._response_progress = None
            logger.debug("  - Stopped progress controller")
        
        # Update progress label to show finalization message
        if self._progress_label:
            self._progress_label.setText("Sur is finalizing response...")
            logger.debug("  - Updated label to 'Sur is finalizing response...'")
        
        # Keep skeleton loader visible - it will be hidden during finalize_streaming()

    def finalize_streaming(self, final_thinking: str, final_response: str):
        """Complete streaming and show final content with transition"""
        logger.debug(f"finalize: think={len(final_thinking)} resp={len(final_response)}")
        self.is_streaming = False
        self.streaming_phase = "final"
        
        # Stop progress controller
        if self._response_progress:
            self._response_progress.stop()
            self._response_progress = None
            logger.debug("  - Progress controller stopped")
        
        # Start fade-out animation for skeleton/progress
        if self._skeleton_loader:
            logger.debug("  - Starting skeleton fade-out animation")
            # use QGraphicsOpacityEffect for fade
            self._opacity_effect_skeleton = QGraphicsOpacityEffect(self._skeleton_loader)
            self._skeleton_loader.setGraphicsEffect(self._opacity_effect_skeleton)
            
            self._fade_out_anim = QPropertyAnimation(self._opacity_effect_skeleton, b"opacity")
            self._fade_out_anim.setDuration(200)
            self._fade_out_anim.setStartValue(1.0)
            self._fade_out_anim.setEndValue(0.0)
            self._fade_out_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._fade_out_anim.finished.connect(lambda: self._show_final_content(final_thinking, final_response))
            self._fade_out_anim.start()
        else:
            logger.debug("  - No skeleton loader, showing final content immediately")
            self._show_final_content(final_thinking, final_response)

    def _show_final_content(self, final_thinking: str, final_response: str):
        """Show final content after fade-out completes"""
        logger.debug("✨ MessageUnit._show_final_content() CALLED")
        
        # Clean up typing indicator if still present
        self._hide_typing_indicator()
        
        # Delete streaming widgets
        if self._processing_header:
            self._processing_header.deleteLater()
            self._processing_header = None
            logger.debug("  - Deleted processing header")
        
        if self._thinking_browser_streaming:
            self._thinking_browser_streaming.deleteLater()
            self._thinking_browser_streaming = None
            logger.debug("  - Deleted thinking browser")
        
        if self._skeleton_loader:
            self._skeleton_loader.deleteLater()
            self._skeleton_loader = None
            logger.debug("  - Deleted skeleton loader")
        
        if self._progress_label:
            self._progress_label.deleteLater()
            self._progress_label = None
            logger.debug("  - Deleted progress label")
        
        # Update thinking_content and content
        self.thinking_content = final_thinking
        self.content = final_response
        logger.debug(f"set: think={len(final_thinking)} resp={len(final_response)}")
        
        # Create collapsible thinking if needed
        if self.thinking_content and not self.collapsible_frame:
            self.collapsible_frame = CollapsibleFrame("Model reasoning - click to expand")
            
            # Use helper method to create thinking browser
            thinking_browser = self._create_thinking_browser()
            thinking_browser.setPlainText(self.thinking_content)
            
            self.collapsible_frame.set_content(thinking_browser)
            self.collapsible_frame.collapse()
            
            # Insert at position 0 (before content browser, which is hidden)
            self.bubble_frame.layout().insertWidget(0, self.collapsible_frame)
            logger.debug("  - Created collapsible thinking frame")
        
        # Show controls
        if hasattr(self, 'copy_btn'):
            self.copy_btn.show()
        if hasattr(self, 'timestamp_label'):
            self.timestamp_label.show()
        logger.debug("  - Showed controls")
        
        # Show and populate main content browser
        self.content_browser.setMarkdown(final_response)
        self._adjust_height()
        self.content_browser.show()
        logger.debug("  - Populated and showed content browser")
        
        # use QGraphicsOpacityEffect for fade-in
        self._opacity_effect_content = QGraphicsOpacityEffect(self.content_browser)
        self.content_browser.setGraphicsEffect(self._opacity_effect_content)
        
        self._fade_in_anim = QPropertyAnimation(self._opacity_effect_content, b"opacity")
        self._fade_in_anim.setDuration(200)
        self._fade_in_anim.setStartValue(0.0)
        self._fade_in_anim.setEndValue(1.0)
        self._fade_in_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        
        # CRITICAL FIX: Remove graphics effect after animation completes to prevent scroll artifacts
        self._fade_in_anim.finished.connect(self._on_fade_in_complete)
        
        self._fade_in_anim.start()
        logger.debug("  - Started fade-in animation")

    def _on_fade_in_complete(self):
        """Called when fade-in animation completes - removes graphics effect to prevent scroll artifacts"""
        # remove effect after anim to avoid scroll issues
        if self.content_browser:
            self.content_browser.setGraphicsEffect(None)
            logger.debug("Removed opacity effect from content browser after fade-in")
        
        # Clean up animation references
        self._opacity_effect_content = None
        self._fade_in_anim = None

    def cancel_streaming(self):
        """Cancel streaming if interrupted (e.g., user navigates away or stops generation)"""
        if not self.is_streaming:
            return
        
        logger.debug("🛑 MessageUnit.cancel_streaming() CALLED")
        self.is_streaming = False
        
        # Stop animations if running
        if self._fade_out_anim and self._fade_out_anim.state() == QPropertyAnimation.State.Running:
            self._fade_out_anim.stop()
            logger.debug("  - Stopped fade-out animation")
        if self._fade_in_anim and self._fade_in_anim.state() == QPropertyAnimation.State.Running:
            self._fade_in_anim.stop()
            logger.debug("  - Stopped fade-in animation")
        
        # Clean up streaming widgets
        if self._response_progress:
            self._response_progress.stop()
            self._response_progress = None
            logger.debug("  - Stopped progress controller")
        
        # Show final content with whatever we have buffered
        self._show_final_content(self._thinking_buffer, self._response_buffer)
        logger.debug("  - Showed partial content after cancellation")
