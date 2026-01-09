#!/usr/bin/env python3
"""
Conversation Service - Manages AI conversation flow and coordinates with model service

Copyright (c) 2024-2026 Sur5ve LLC
Licensed under MIT License
https://sur5ve.com
"""

import re
import time
import threading
import json
import uuid
from typing import Dict, List, Any, Optional, Callable
from PySide6.QtCore import QObject, Signal, Slot, QElapsedTimer, QThread, QMetaObject, Qt

from sur5_lite_pyside.utils.logger import create_module_logger
from sur5_lite_pyside.services.model_service import ModelService

# Module logger
logger = create_module_logger(__name__)
from sur5_lite_pyside.services.dual_mode_utils import (
    extract_thinking_and_response, 
    format_chat_messages_thinking,
    format_chat_messages_standard,
    clean_response_text,
    clean_thinking_text,
    is_dual_mode_model,
    get_dual_mode_preference,
    is_template_enabled,
    get_prompt_template,
    apply_prompt_template
)


class GenerationWorker(QObject):
    """Worker for running generation in QThread with proper signal handling"""
    
    # Signals - these will be emitted from the QThread
    chunk_ready = Signal(str, str, bool, bool)  # kind, content, delta, close
    generation_complete = Signal()
    generation_error = Signal(str)
    
    def __init__(self, conversation_service, messages: List[Dict], context: str, thinking_mode: bool):
        super().__init__()
        self.conversation_service = conversation_service
        self.messages = messages
        self.context = context
        self.thinking_mode = thinking_mode
        self._stop_flag = False
    
    def stop(self):
        """Signal the worker to stop"""
        self._stop_flag = True
    
    @Slot()
    def run(self):
        """Run generation in QThread - this is thread-safe"""
        try:
            if self.thinking_mode:
                self.conversation_service._generate_thinking_response_internal(
                    self.messages,
                    self.context,
                    self
                )
            else:
                self.conversation_service._generate_standard_response_internal(
                    self.messages,
                    self.context,
                    self
                )
            
            if not self._stop_flag:
                self.generation_complete.emit()
                
        except Exception as e:
            if not self._stop_flag:
                self.generation_error.emit(str(e))


class ConversationService(QObject):
    """Service for managing AI conversations"""
    
    # Signals
    message_received = Signal(dict)  # Emits message data
    streaming_chunk = Signal(str)   # Emits streaming response chunk (now JSON with close flag)
    thinking_chunk = Signal(str)    # Emits thinking process chunk (now JSON with close flag)
    thinking_started = Signal()     # Emits when thinking starts
    response_started = Signal()     # Emits when response starts
    skip_initiated = Signal()       # Emits when skip is requested (for telemetry)
    stop_requested = Signal()       # Emits when stop is requested (full abort)
    error_occurred = Signal(str)    # Emits error message
    
    def __init__(self, model_service: ModelService, parent=None):
        super().__init__(parent)
        
        self.model_service = model_service
        self.conversation_history: List[Dict[str, Any]] = []
        self.is_generating = False
        self.max_history_length = 50
        
        # Streaming state
        self.current_thinking = ""
        self.current_response = ""
        
        # Single-stream lifecycle tracking (Option B)
        self._current_message_uuid = None  # Track current stream for correlation
        self._skip_requested = False       # Track skip state
        self._stop_requested = False       # Track stop state (full abort)
        self._original_turn_uuid = None    # Track original turn for telemetry
        
        # QThread management
        self._worker = None
        self._thread = None
        
        # Connect to model service signals
        self.model_service.model_loaded.connect(self._on_model_loaded)
        self.model_service.model_error.connect(self._on_model_error)
        
    def send_message(
        self,
        user_message: str,
        thinking_mode: bool = True,
        context: str = ""
    ) -> bool:
        """Send a message and get AI response"""
        if self.is_generating:
            self.error_occurred.emit("Already generating a response")
            return False
            
        if not user_message.strip():
            self.error_occurred.emit("Empty message")
            return False
        
        # check if model supports thinking
        # If not, force standard mode regardless of UI toggle
        model_path = self.model_service.current_model_path
        if model_path and thinking_mode:
            from .prompt_patterns import get_model_capabilities
            capabilities = get_model_capabilities(model_path)
            if not capabilities.get("supports_thinking", False):
                logger.info(f"Model doesn't support thinking - using standard mode")
                thinking_mode = False
        
        # Add user message to history
        user_msg_data = {
            "role": "user",
            "content": user_message,
            "timestamp": time.time()
        }
        self.conversation_history.append(user_msg_data)
        self.message_received.emit(user_msg_data)
        
        # Start generation timer
        self._generation_timer = QElapsedTimer()
        self._generation_timer.start()
        
        # Generate response in QThread (proper Qt threading for Windows)
        self.is_generating = True
        
        # Prepare messages for generation
        messages = [{"role": msg["role"], "content": msg["content"]} 
                   for msg in self.conversation_history]
        
        # Clean up previous thread if it exists (with timeout to prevent hangs)
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            if not self._thread.wait(3000):  # 3-second timeout
                logger.warning("Thread didn't stop gracefully, terminating...")
                self._thread.terminate()
                self._thread.wait(1000)
            self._thread.deleteLater()
        
        # Create worker and thread
        self._worker = GenerationWorker(self, messages, context, thinking_mode)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        
        # signals
        self._thread.started.connect(self._worker.run)
        self._worker.chunk_ready.connect(self._handle_worker_chunk)
        self._worker.generation_complete.connect(self._on_generation_complete)
        self._worker.generation_error.connect(self._on_generation_error)
        
        # Cleanup
        self._worker.generation_complete.connect(self._thread.quit)
        self._worker.generation_error.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        
        # Start the thread
        self._thread.start()
        return True
            
    @Slot(str, str, bool, bool)
    def _handle_worker_chunk(self, kind: str, content: str, delta: bool, close: bool):
        """Handle chunks from worker thread - this runs on main thread"""
        chunk_data = {
            "type": kind,
            "content": content,
            "delta": delta,
            "close": close,
            "uuid": self._current_message_uuid or str(time.time())
        }
        
        signal = self.thinking_chunk if kind == "thinking" else self.streaming_chunk
        signal.emit(json.dumps(chunk_data))
        
        if close:
            logger.debug(f"{kind} closed uuid={self._current_message_uuid}")
            # Stop timer and store elapsed time when response stream closes
            if kind == "response" and hasattr(self, '_generation_timer'):
                self._generation_elapsed_ms = self._generation_timer.elapsed()
                logger.info(f"Generation completed in {self._generation_elapsed_ms}ms")
    
    def _emit_chunk(self, kind: str, content: str = "", delta: bool = True, close: bool = False):
        """Emit structured JSON chunk (thread-safe)."""
        # If called from worker thread, use worker's signal
        if self._worker and threading.current_thread() != threading.main_thread():
            self._worker.chunk_ready.emit(kind, content, delta, close)
        else:
            # Direct call from main thread (legacy path)
            self._handle_worker_chunk(kind, content, delta, close)
    
    @Slot()
    def _on_generation_complete(self):
        """Handle successful generation completion"""
        # Cleanup is handled by _cleanup_thread
        pass
    
    @Slot(str)
    def _on_generation_error(self, error_msg: str):
        """Handle generation error"""
        self.error_occurred.emit(error_msg)
        self.is_generating = False
    
    @Slot()
    def _cleanup_thread(self):
        """Clean up the worker thread"""
        # reset is_generating
        self.is_generating = False
        
        if self._thread:
            self._thread.deleteLater()
            self._thread = None
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
    
    def skip_thinking(self):
        """Skip reasoning and generate concise answer."""
        # Bail early if nothing is running
        if not self.is_generating or self._skip_requested:
            logger.warning("Skip ignored: not generating or already skipped")
            return
        
        logger.info("Skip requested - will stop generation and provide concise answer")
        
        # Set skip flag FIRST
        self._skip_requested = True
        self._original_turn_uuid = self._current_message_uuid
        
        # Stop the LLM from emitting more tokens
        if hasattr(self.model_service, 'stop_generation'):
            self.model_service.stop_generation()
        
        # Emit signal for logging/telemetry (optional)
        self.skip_initiated.emit()
        
        # DON'T emit close chunks here - let the generation thread handle it

    def stop_generation_immediate(self):
        """Stop generation immediately (full abort)."""
        # Bail early if nothing is running
        if not self.is_generating or self._stop_requested:
            logger.warning("Stop ignored: not generating or already stopped")
            return
        
        logger.info("Stop requested - aborting generation immediately")
        
        # Set stop flag FIRST
        self._stop_requested = True
        
        # Stop the LLM from emitting more tokens
        if hasattr(self.model_service, 'stop_generation'):
            self.model_service.stop_generation()
        
        # Emit signal for UI coordination
        self.stop_requested.emit()
        
        # Emit close chunks immediately to cleanup UI
        if self._current_message_uuid:
            self._emit_chunk("thinking", "", delta=False, close=True)
            self._emit_chunk("response", "", delta=False, close=True)
        
        # Mark as not generating
        self.is_generating = False

    def clear_conversation(self):
        """Clear conversation history"""
        self.conversation_history.clear()
        logger.info("Conversation history cleared")
        
    def stop_generation(self):
        """Stop current generation"""
        if self.is_generating:
            # Note: llama-cpp-python doesn't support stopping mid-generation
            # This is a limitation we need to work around
            self.is_generating = False
            logger.debug("stop requested")
            
            # Emit close chunks to cleanup UI
            if self._current_message_uuid:
                self._emit_chunk("thinking", "", delta=False, close=True)
                self._emit_chunk("response", "", delta=False, close=True)
            
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history"""
        return self.conversation_history.copy()
        
            
    def _generate_thinking_response_internal(self, messages: List[Dict], context: str, worker=None):
        """Generate response with thinking - handles skip after generation (QThread-safe)"""
        try:
            # Generate UUID at start for correlation
            self._current_message_uuid = str(uuid.uuid4())
            logger.debug(f"stream start uuid={self._current_message_uuid}")
            
            # Reset streaming state for new generation
            self.current_thinking = ""
            self.current_response = ""
            self._raw_accumulated_buffer = ""
            self._emitted_thinking = ""
            self._emitted_response = ""
            self._thinking_start_time = time.time()
            self._response_start_time = None
            self._pending_tag_fragment = ""  # buffer for incomplete tags
            self._skip_requested = False  # Reset at start
            
            # Emit thinking started
            self.thinking_started.emit()
            
            # Get the user's prompt (last message)
            user_message = messages[-1]["content"] if messages else ""
            model_path = self.model_service.current_model_path
            
            # Cache model capabilities and format
            from .dual_mode_utils import get_model_capabilities
            from .prompt_patterns import _detect_model_type
            capabilities = get_model_capabilities(model_path) if model_path else {}
            self._reasoning_format = capabilities.get('format', 'xml_tags')
            self._uses_harmony = capabilities.get('uses_harmony', False)
            self._harmony_channels = capabilities.get('harmony_channels', {})
            self._closing_only_think = capabilities.get('closing_only_think', False)
            self._final_markers = capabilities.get('final_markers', [])
            self._model_type = _detect_model_type(model_path) if model_path else ""
            
            # Harmony streaming: initialize carryover buffer and length tracking
            if self._uses_harmony:
                self._harmony_carry = ""
                self._h_thinking_len = 0
                self._h_final_len = 0
            
            # Apply prompt templating for dual-mode models
            # skip template for SmolLM2 - uses system prompt
            enhanced_prompt = user_message
            if context:
                enhanced_prompt = f"{context}\n\n{user_message}"
            
            template_enabled_globally = get_dual_mode_preference("enable_prompt_templating", True)
            is_dual_mode = is_dual_mode_model(model_path) if model_path else False
            
            # Skip prompt template for small models (too small for double-prompting)
            if self._reasoning_format in ('smollm_simulated', 'gemma_simulated'):
                pass
            elif is_dual_mode and template_enabled_globally and is_template_enabled(model_path):
                template = get_prompt_template(model_path, thinking_mode=True)
                if template:
                    enhanced_prompt = apply_prompt_template(enhanced_prompt, template)
                    logger.debug("applied think template")
            
            # Format messages for thinking mode
            formatted_messages = messages.copy()
            if formatted_messages:
                formatted_messages[-1] = {"role": "user", "content": enhanced_prompt}
            
            # System prompt based on model capabilities
            if self._reasoning_format in ('smollm_simulated', 'gemma_simulated'):
                # Smaller models need simpler but still detailed prompts
                base_system_prompt = """You are a helpful and knowledgeable AI assistant.

When answering questions:
- Provide detailed, complete explanations
- Include relevant facts, context, and examples
- Explain step-by-step when helpful
- Give thorough, informative responses

Never give one-word or overly brief answers. Always explain fully."""
            else:
                base_system_prompt = """You are a thorough and knowledgeable AI assistant who provides comprehensive, detailed explanations. 

When answering:
- Explore topics deeply with multiple perspectives
- Include relevant examples, analogies, and context
- Explain concepts thoroughly with step-by-step reasoning
- Provide scientific details and background information where applicable
- Aim for completeness and depth rather than brevity

Your goal is to give users rich, informative answers that truly help them understand the topic."""
            
            formatted_messages = format_chat_messages_thinking(
                formatted_messages, 
                system_prompt=base_system_prompt,
                model_capabilities=capabilities
            )
            
            # thinking mode emits thinking_started only
            # The response_started signal is ONLY for standard (non-thinking) mode
            
            # Generate with streaming (BLOCKING until complete or stopped)
            full_response = self.model_service.generate_chat_response(
                messages=formatted_messages,
                stream_callback=self._handle_thinking_stream
            )
            
            # check skip flag after generation
            if self._skip_requested:
                logger.debug("skip detected")
                
                # NOW safe to emit close chunks (no more tokens coming)
                self._emit_chunk("thinking", "", delta=False, close=True)
                self._emit_chunk("response", "", delta=False, close=True)
                
                # Generate concise response on SAME thread
                logger.debug("gen concise")
                self._generate_concise_response(messages, context)
                return  # Exit early - concise handler will emit message_received
            
            # Extract thinking and response
            thinking_content, response_content = extract_thinking_and_response(full_response)
            
            logger.debug(f"extract: resp={len(full_response)} think={len(thinking_content) or 0} final={len(response_content) or 0}")
            
            # fallback to accumulated buffers
            if not response_content and self.current_response:
                response_content = self.current_response
                logger.debug(f"using resp buffer: {len(response_content)}")
                
            if not thinking_content and self.current_thinking:
                thinking_content = self.current_thinking
                logger.debug(f"using think buffer: {len(thinking_content)}")
            
            if not response_content:
                response_content = clean_response_text(full_response)
                logger.debug(f"clean_response_text: {len(response_content)}")
                
            # if no response, use last paragraphs of thinking
            if not response_content and thinking_content:
                logger.warning("Model only generated thinking, no response - extracting answer from thinking content")
                # Last resort: Use last 2 paragraphs of thinking as response
                paragraphs = thinking_content.split('\n\n')
                if len(paragraphs) >= 2:
                    response_content = '\n\n'.join(paragraphs[-2:])
                    thinking_content = '\n\n'.join(paragraphs[:-2])
                    logger.debug(f"used last 2 paras as resp: {len(response_content)}")
                else:
                    # If only one paragraph, use it as response
                    response_content = thinking_content
                    thinking_content = ""
                    logger.debug(f"used all think as resp: {len(response_content)}")
            
            # clean up meta-commentary
            # Remove phrases like "Thinking:", "Final response:", "So finalizing:", etc.
            
            def strip_meta_commentary(text, user_prompt=""):
                """Remove model's internal reasoning commentary and prompt echoes"""
                if not text:
                    return text
                
                original_text = text
                    
                # ONLY remove these patterns if they appear as STANDALONE labels
                # Not as part of actual content
                
                # Remove "Thinking:" ONLY at the very start
                if text.lower().startswith("thinking:"):
                    text = text[9:].lstrip()
                
                # Remove "Final response:" ONLY at the very start
                if text.lower().startswith("final response:"):
                    text = text[15:].lstrip()
                
                # Remove "So finalizing:" ONLY at the very start
                for prefix in ["so finalizing:", "now finalizing:", "therefore finalizing:"]:
                    if text.lower().startswith(prefix):
                        text = text[len(prefix):].lstrip()
                        break
                
                # Remove placeholder text (be very specific)
                text = text.replace("Your final response here.", "")
                text = text.replace("Your final response here", "")
                text = text.replace("[Your final response here]", "")
                
                # remove prompt echo only if response is short
                # Skip entirely for responses with real content
                if user_prompt and len(text.strip()) <= 100:  # Only check suspiciously short responses
                    if text.strip().endswith(user_prompt.strip()):
                        potential_remaining = text.strip()[:-len(user_prompt.strip())].strip()
                        if len(potential_remaining) > 20:  # Lower threshold for short responses
                            text = potential_remaining
                            logger.debug("Removed user prompt echo from short response")
                        else:
                            logger.warning("Skipped echo removal - would leave insufficient content")
                else:
                    if user_prompt and text.strip().endswith(user_prompt.strip()):
                        logger.debug("Response ends with user prompt but has substantial content (>100 chars) - keeping as-is")
                
                cleaned = text.strip()
                
                # Debug: log what was removed
                if original_text != cleaned:
                    logger.debug(f"stripped meta: -{len(original_text) - len(cleaned)}")
                
                return cleaned
            
            # Clean both thinking and response content (pass user message for echo detection)
            thinking_content = strip_meta_commentary(thinking_content, user_message)
            response_content = strip_meta_commentary(response_content, user_message)
            
            logger.debug(f"post-clean: think={len(thinking_content) or 0} resp={len(response_content) or 0}")
            
            # validate we have content
            if not response_content and not thinking_content:
                if full_response.strip():
                    response_content = clean_response_text(full_response)
                    logger.warning(f"Extraction failed but full_response exists - using clean_response_text: {len(response_content)} chars")
            
            # Emit close chunks BEFORE message_received (cleanup happens first)
            self._emit_chunk("response", "", delta=False, close=True)
            
            # Clean thinking content (remove bracket markers from small models)
            cleaned_thinking = clean_thinking_text(thinking_content) if thinking_content else ""
            
            # Create assistant message
            assistant_msg_data = {
                "role": "assistant",
                "content": response_content,
                "thinking": cleaned_thinking,
                "timestamp": time.time(),
                "uuid": self._current_message_uuid,
                "elapsed_ms": getattr(self, '_generation_elapsed_ms', None)
            }
            
            # Add to history
            self.conversation_history.append(assistant_msg_data)
            
            # Emit message_received AFTER close chunks (triggers add_message after cleanup)
            self.message_received.emit(assistant_msg_data)
            
        except Exception as e:
            # ERROR PATH: emit close chunks to cleanup UI
            logger.error(f"Error during generation: {e}")
            self._emit_chunk("thinking", "", delta=False, close=True)
            self._emit_chunk("response", "", delta=False, close=True)
            error_msg = f"Error generating thinking response: {str(e)}"
            self.error_occurred.emit(error_msg)
            import traceback
            traceback.print_exc()
        finally:
            self.is_generating = False
            self._skip_requested = False
            self._stop_requested = False
            self._current_message_uuid = None
            self._original_turn_uuid = None
            
    def _generate_standard_response_internal(self, messages: List[Dict], context: str, worker=None):
        """Generate standard response without thinking mode (QThread-safe)"""
        try:
            # Generate UUID at start for correlation
            self._current_message_uuid = str(uuid.uuid4())
            logger.debug(f"std stream uuid={self._current_message_uuid}")
            
            # Reset streaming state
            self.current_response = ""
            self._skip_requested = False  # Reset at start
            
            # Reset thinking-mode buffers to prevent tag contamination
            self._raw_accumulated_buffer = ""
            self._emitted_thinking = ""
            self._pending_tag_fragment = ""
            
            # Get the user's prompt
            user_message = messages[-1]["content"] if messages else ""
            
            # Apply context if provided
            enhanced_prompt = user_message
            if context:
                enhanced_prompt = f"{context}\n\n{user_message}"
            
            # Format messages for standard mode
            formatted_messages = messages.copy()
            if formatted_messages:
                formatted_messages[-1] = {"role": "user", "content": enhanced_prompt}
            
            # Check if this is a tiny model (270M or smaller) - use minimal system prompt
            from .prompt_patterns import get_model_capabilities
            model_path = self.model_service.current_model_path
            capabilities = get_model_capabilities(model_path) if model_path else {}
            is_tiny_model = "270m" in (model_path or "").lower() or "135m" in (model_path or "").lower()
            
            if is_tiny_model:
                # Tiny models (270M) can't follow complex instructions - use NO system prompt
                # Just let them respond naturally to the user's question
                logger.info("Tiny model detected - using no system prompt")
                system_prompt = ""
            else:
                system_prompt = """You are a helpful and knowledgeable AI assistant.

When answering questions:
- Provide complete, detailed explanations
- Include relevant facts, examples, and context
- Explain concepts step-by-step when helpful
- Give thorough, informative responses

Never give one-word or overly brief answers. Always explain fully and help the user understand the topic."""
            
            formatted_messages = format_chat_messages_standard(
                formatted_messages,
                system_prompt=system_prompt
            )
            
            # Emit response started
            self.response_started.emit()
            
            # Generate with streaming
            full_response = self.model_service.generate_chat_response(
                messages=formatted_messages,
                stream_callback=self._handle_standard_stream
            )
            
            # Clean response (clean_response_text already strips reasoning tags by default)
            cleaned_response = clean_response_text(full_response)
            logger.debug(f"resp: {len(cleaned_response)}")
            
            # Emit close chunk BEFORE message_received
            self._emit_chunk("response", "", delta=False, close=True)
            
            # Create assistant message
            assistant_msg_data = {
                "role": "assistant", 
                "content": cleaned_response,
                "timestamp": time.time(),
                "uuid": self._current_message_uuid,
                "elapsed_ms": getattr(self, '_generation_elapsed_ms', None)
            }
            
            # Add to history
            self.conversation_history.append(assistant_msg_data)
            
            # Emit message_received AFTER close chunk
            self.message_received.emit(assistant_msg_data)
            
        except Exception as e:
            # ERROR PATH: emit close chunk to cleanup UI
            logger.error(f"Error during generation: {e}")
            self._emit_chunk("response", "", delta=False, close=True)
            error_msg = f"Error generating standard response: {str(e)}"
            self.error_occurred.emit(error_msg)
        finally:
            self.is_generating = False
            self._skip_requested = False
            self._stop_requested = False
            self._current_message_uuid = None
    
    def _generate_concise_response(self, messages: List[Dict], context: str):
        """Generate concise answer without reasoning (after skip)."""
        try:
            # Generate NEW UUID for concise answer
            self._current_message_uuid = str(uuid.uuid4())
            logger.debug(f"concise stream uuid={self._current_message_uuid} orig={self._original_turn_uuid}")
            
            # Reset buffers for concise response
            self.current_response = ""
            self._skip_requested = False  # Clear skip flag for new generation
            
            # Get user prompt
            user_message = messages[-1]["content"] if messages else ""
            
            # Apply context if provided
            enhanced_prompt = user_message
            if context:
                enhanced_prompt = f"{context}\n\n{user_message}"
            
            # Format messages for STANDARD mode (no thinking tags)
            formatted_messages = messages.copy()
            if formatted_messages:
                formatted_messages[-1] = {"role": "user", "content": enhanced_prompt}
            
            formatted_messages = format_chat_messages_standard(
                formatted_messages,
                system_prompt="You are a helpful AI assistant. Provide a concise, direct answer."
            )
            
            # Emit response started (optional - UI already knows we're generating)
            self.response_started.emit()
            
            # Generate with standard streaming (no thinking)
            full_response = self.model_service.generate_chat_response(
                messages=formatted_messages,
                stream_callback=self._handle_standard_stream  # Uses _emit_chunk for response
            )
            
            # Clean response
            response_content = clean_response_text(full_response)
            
            # Emit close chunk for response
            self._emit_chunk("response", "", delta=False, close=True)
            
            # Emit message_received with NO thinking (empty string)
            assistant_msg_data = {
                "role": "assistant",
                "content": response_content,
                "thinking": "",  # Empty - this is concise mode
                "timestamp": time.time(),
                "uuid": self._current_message_uuid,
                "skipped_from": self._original_turn_uuid,  # Track skip lineage for telemetry
                "elapsed_ms": getattr(self, '_generation_elapsed_ms', None)
            }
            
            self.conversation_history.append(assistant_msg_data)
            self.message_received.emit(assistant_msg_data)
            
        except Exception as e:
            logger.error(f"Error during concise generation: {e}")
            self._emit_chunk("response", "", delta=False, close=True)
            self.error_occurred.emit(f"Error generating concise response: {str(e)}")
        finally:
            self.is_generating = False
            self._skip_requested = False
            self._stop_requested = False
            self._current_message_uuid = None
            self._original_turn_uuid = None
            
    def _handle_thinking_stream(self, chunk: str, metadata: Optional[dict] = None):
        """Handle streaming chunks for thinking mode."""
        # check skip flag first
        if self._skip_requested:
            return  # Silently drop chunks after skip to prevent repopulating deleted widgets
        
        # Check stop flag - ignore late chunks after stop
        if self._stop_requested:
            return  # Silently drop chunks after stop to prevent repopulating deleted widgets
        
        if not chunk:
            return
        
        # Optional: Log metadata for debugging (0.3.x feature)
        if metadata and metadata.get('finish_reason'):
            logger.debug(f"stream done: {metadata['finish_reason']}")
            
        # CRITICAL FIX: Prepend any pending tag fragment from previous chunk
        chunk = self._pending_tag_fragment + chunk
        self._pending_tag_fragment = ""
        
        # Check if chunk ends with a potential incomplete tag
        # Pattern: '<' followed by optional letters/underscore/slash
        match = re.search(r'<[a-zA-Z_/]*$', chunk)
        if match:
            # Hold back the incomplete tag fragment
            self._pending_tag_fragment = match.group(0)
            chunk = chunk[:match.start()]
            logger.debug(f"tag frag: {self._pending_tag_fragment!r}")
        
        if not chunk:
            # Nothing to emit after holding back fragment
            return
            
        # Accumulate raw chunk (with tags intact for proper parsing)
        self._raw_accumulated_buffer = getattr(self, '_raw_accumulated_buffer', '') + chunk
        accumulated = self._raw_accumulated_buffer
        
        # Format-aware tag stripping
        def strip_tags(text):
            from .dual_mode_utils import strip_harmony_control_tokens
            # Strip Harmony control tokens
            cleaned = strip_harmony_control_tokens(text)
            # Strip XML tags
            cleaned = re.sub(r'<\s*/?\s*(?:thinking|think|final_answer)(?:\b[^>]*)?>',
                            '', cleaned, flags=re.IGNORECASE)
            # Strip Apriel markers
            cleaned = re.sub(r'\[(?:BEGIN|END) FINAL RESPONSE\]', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'<\s*/?\s*final\s*>', '', cleaned, flags=re.IGNORECASE)
            return cleaned  # Don't strip whitespace - preserve spaces between words!
        
        # Track what we've already emitted (cleaned versions)
        self._emitted_thinking = getattr(self, '_emitted_thinking', '')
        self._emitted_response = getattr(self, '_emitted_response', '')
        
        # HARMONY STREAMING BRANCH: Monotonic buffer with length-based delta tracking
        if getattr(self, '_uses_harmony', False):
            from .dual_mode_utils import extract_harmony_channels, HARMONY_HEADER_RE, HARMONY_END_RE
            
            # Prepend carryover from previous chunk (for header fragments at boundaries)
            accumulated_with_carry = getattr(self, '_harmony_carry', '') + chunk
            
            # Parse channels from full buffer (scanner-based extraction)
            thinking_content, response_content = extract_harmony_channels(accumulated_with_carry)
            
            # Update carryover: keep from last header start (MONOTONIC buffer growth)
            last_header_match = None
            for match in HARMONY_HEADER_RE.finditer(accumulated_with_carry):
                last_header_match = match
            
            if last_header_match:
                # Keep from last header; cap to ~32KB to bound memory
                carry_start = last_header_match.start()
                if len(accumulated_with_carry) - carry_start > 32768:
                    carry_start = len(accumulated_with_carry) - 32768
                self._harmony_carry = accumulated_with_carry[carry_start:]
            else:
                # No header seen yet: keep a small tail to catch split headers
                self._harmony_carry = accumulated_with_carry[-1024:] if len(accumulated_with_carry) > 1024 else accumulated_with_carry
            
            # Detect stop tokens
            stop_match = HARMONY_END_RE.search(accumulated_with_carry)
            
            # Clean the content
            clean_thinking = strip_tags(thinking_content)
            clean_response = strip_tags(response_content)
            
            # Transition logic: has final content?
            has_final_content = bool(clean_response.strip())
            
            if has_final_content:
                # Emit thinking delta (finalize thinking) using length-based tracking
                if len(clean_thinking) > getattr(self, '_h_thinking_len', 0):
                    delta = clean_thinking[self._h_thinking_len:]
                    if delta:
                        self._emit_chunk("thinking", delta, delta=True, close=False)
                        self._h_thinking_len = len(clean_thinking)
                        self.current_thinking = clean_thinking
                
                # Close thinking bubble on first final content
                if not self._response_start_time:
                    self._response_start_time = time.time()
                    thinking_duration = self._response_start_time - self._thinking_start_time
                    logger.debug(f"harmony think done: {thinking_duration:.2f}s")
                    self._emit_chunk("thinking", "", delta=False, close=True)
                
                # Emit response delta using length-based tracking
                if len(clean_response) > getattr(self, '_h_final_len', 0):
                    delta = clean_response[self._h_final_len:]
                    if delta:
                        self._emit_chunk("response", delta, delta=True, close=False)
                        self._h_final_len = len(clean_response)
                        self.current_response = clean_response
            else:
                # Still in analysis channel - emit thinking deltas
                if len(clean_thinking) > getattr(self, '_h_thinking_len', 0):
                    delta = clean_thinking[self._h_thinking_len:]
                    if delta:
                        self._emit_chunk("thinking", delta, delta=True, close=False)
                        self._h_thinking_len = len(clean_thinking)
                        self.current_thinking = clean_thinking
            
            # Detect completion via stop tokens
            if stop_match:
                logger.debug(f"harmony stop @{stop_match.start()}")
            
            return  # Skip XML branch for Harmony models
        
        # GRANITE TOGGLE STREAMING BRANCH: <think_on>/<think_off> format
        if getattr(self, '_reasoning_format', '') == 'granite_toggle':
            from .dual_mode_utils import detect_granite_toggle_format, extract_granite_thinking
            
            # Check for <think_on> and <think_off> markers
            has_think_on = '<think_on>' in accumulated
            has_think_off = '<think_off>' in accumulated
            
            if has_think_on and has_think_off:
                # Both markers present - extract thinking and response
                thinking_content, response_content = extract_granite_thinking(accumulated)
                
                # Clean the content (strip Granite-specific markers)
                clean_thinking = re.sub(r'<think_on>|<think_off>', '', thinking_content, flags=re.IGNORECASE).strip()
                clean_response = re.sub(r'<think_on>|<think_off>', '', response_content, flags=re.IGNORECASE).strip()
                
                # Emit thinking delta
                if clean_thinking and len(clean_thinking) > len(self._emitted_thinking):
                    delta = clean_thinking[len(self._emitted_thinking):]
                    if delta:
                        self._emit_chunk("thinking", delta, delta=True, close=False)
                        self._emitted_thinking = clean_thinking
                        self.current_thinking = clean_thinking
                
                # Close thinking and emit response on first <think_off>
                if not self._response_start_time:
                    self._response_start_time = time.time()
                    thinking_duration = self._response_start_time - self._thinking_start_time
                    logger.debug(f"granite think done: {thinking_duration:.2f}s")
                    self._emit_chunk("thinking", "", delta=False, close=True)
                
                # Emit response delta
                if clean_response and len(clean_response) > len(self._emitted_response):
                    delta = clean_response[len(self._emitted_response):]
                    if delta:
                        self._emit_chunk("response", delta, delta=True, close=False)
                        self._emitted_response = clean_response
                        self.current_response = clean_response
                        
            elif has_think_on:
                # Still in thinking phase - extract and emit thinking content
                think_on_match = re.search(r'<think_on>(.*)', accumulated, re.DOTALL)
                if think_on_match:
                    clean_thinking = think_on_match.group(1).strip()
                    if clean_thinking and len(clean_thinking) > len(self._emitted_thinking):
                        delta = clean_thinking[len(self._emitted_thinking):]
                        if delta:
                            self._emit_chunk("thinking", delta, delta=True, close=False)
                            self._emitted_thinking = clean_thinking
                            self.current_thinking = clean_thinking
            else:
                # FALLBACK: Granite output without markers - treat as direct response
                # This handles Granite 4.0 which doesn't use thinking tokens by default
                # Strip any XML-style tags that the model may output from our template
                clean_response = accumulated.strip()
                # Remove thinking/final_answer tags for clean display (Granite-specific)
                clean_response = re.sub(r'</?thinking>', '', clean_response, flags=re.IGNORECASE)
                clean_response = re.sub(r'</?final_answer>', '', clean_response, flags=re.IGNORECASE)
                clean_response = clean_response.strip()
                
                if clean_response and len(clean_response) > len(self._emitted_response):
                    # Close thinking on first response chunk (if not already closed)
                    if not self._response_start_time:
                        self._response_start_time = time.time()
                        self._emit_chunk("thinking", "", delta=False, close=True)
                    
                    delta = clean_response[len(self._emitted_response):]
                    if delta:
                        self._emit_chunk("response", delta, delta=True, close=False)
                        self._emitted_response = clean_response
                        self.current_response = clean_response
            
            return  # Skip XML branch for Granite models
        
        # SMALL MODEL SIMULATED THINKING BRANCH: "Let me think..." / "Answer:" format
        # Handles SmolLM2 (135M) and Gemma-3-small (270M)
        if getattr(self, '_reasoning_format', '') in ('smollm_simulated', 'gemma_simulated'):
            from .dual_mode_utils import detect_smollm_simulated_format, extract_smollm_simulated
            
            # Small models use simple text markers, not XML tags
            # Check for "Answer:" marker to determine if we're past thinking phase
            has_answer_marker = any(marker in accumulated.lower() for marker in [
                'answer:', 'my answer:', 'my response:', 'so,', 'therefore,'
            ])
            
            if has_answer_marker:
                # Both thinking and response phases present
                thinking_content, response_content = extract_smollm_simulated(accumulated)
                
                # Emit thinking delta
                if thinking_content and len(thinking_content) > len(self._emitted_thinking):
                    delta = thinking_content[len(self._emitted_thinking):]
                    if delta:
                        self._emit_chunk("thinking", delta, delta=True, close=False)
                        self._emitted_thinking = thinking_content
                        self.current_thinking = thinking_content
                
                # Close thinking and emit response on first answer marker
                if not self._response_start_time:
                    self._response_start_time = time.time()
                    thinking_duration = self._response_start_time - self._thinking_start_time
                    logger.debug(f"small model think done: {thinking_duration:.2f}s")
                    self._emit_chunk("thinking", "", delta=False, close=True)
                
                # Emit response delta
                if response_content and len(response_content) > len(self._emitted_response):
                    delta = response_content[len(self._emitted_response):]
                    if delta:
                        self._emit_chunk("response", delta, delta=True, close=False)
                        self._emitted_response = response_content
                        self.current_response = response_content
            else:
                # Still in "thinking" phase - emit as thinking
                # For SmolLM2, treat everything before "Answer:" as thinking
                clean_text = accumulated.strip()
                if clean_text and len(clean_text) > len(self._emitted_thinking):
                    delta = clean_text[len(self._emitted_thinking):]
                    if delta:
                        self._emit_chunk("thinking", delta, delta=True, close=False)
                        self._emitted_thinking = clean_text
                        self.current_thinking = clean_text
            
            return  # Skip XML branch for SmolLM2 models
        
        # Check if we have complete sections (including Apriel markers)
        has_thinking_close = "</thinking>" in accumulated or "</think>" in accumulated.lower()
        has_final_answer_open = "<final_answer>" in accumulated
        has_final_answer_close = "</final_answer>" in accumulated
        
        # Check for Apriel markers if using Apriel format
        has_apriel_final = False
        if getattr(self, '_final_markers', []):
            for marker in self._final_markers:
                if marker in accumulated:
                    has_apriel_final = True
                    break
        
        # Check for Qwen3 closing-only pattern (orphaned </think> without opening)
        has_qwen3_closing = False
        if getattr(self, '_closing_only_think', False):
            if '</think>' in accumulated.lower() and '<think>' not in accumulated.lower():
                has_qwen3_closing = True
                has_thinking_close = True
        
        if (has_thinking_close and has_final_answer_close) or (has_thinking_close and has_apriel_final) or has_qwen3_closing:
            # We have BOTH complete sections - parse them
            thinking_content, response_content = extract_thinking_and_response(accumulated)
            
            # Clean the content
            clean_thinking = strip_tags(thinking_content)
            clean_response = strip_tags(response_content)
            
            # Emit thinking delta (only new content since last emit)
            if clean_thinking and clean_thinking != self._emitted_thinking:
                thinking_delta = clean_thinking[len(self._emitted_thinking):]
                if thinking_delta:
                    self._emit_chunk("thinking", thinking_delta, delta=True, close=False)
                    self._emitted_thinking = clean_thinking
                    self.current_thinking = clean_thinking  # Store CLEANED version for final extraction
            
            # Emit response delta (only new content since last emit)
            if clean_response and clean_response != self._emitted_response:
                response_delta = clean_response[len(self._emitted_response):]
                if response_delta:
                    logger.debug(f"resp delta: {response_delta[:50]!r}")
                    self._emit_chunk("response", response_delta, delta=True, close=False)
                    self._emitted_response = clean_response
                    self.current_response = clean_response
                    
        elif has_thinking_close:
            # Thinking is done, now streaming final_answer
            # Mark the transition time (for adaptive UI timing)
            if not self._response_start_time:
                self._response_start_time = time.time()
                thinking_duration = self._response_start_time - self._thinking_start_time
                logger.debug(f"think done: {thinking_duration:.2f}s")
                
                # Emit thinking close signal to trigger skeleton transition in UI
                self._emit_chunk("thinking", "", delta=False, close=True)
                logger.debug("think close -> skeleton")
            
            # Extract thinking first
            thinking_match = re.search(r'<thinking>(.*?)</thinking>', accumulated, re.DOTALL | re.IGNORECASE)
            if thinking_match:
                thinking_content = thinking_match.group(1)
                clean_thinking = strip_tags(thinking_content)
                
                # Emit thinking delta
                if clean_thinking and clean_thinking != self._emitted_thinking:
                    thinking_delta = clean_thinking[len(self._emitted_thinking):]
                    if thinking_delta:
                        self._emit_chunk("thinking", thinking_delta, delta=True, close=False)
                        self._emitted_thinking = clean_thinking
                        self.current_thinking = clean_thinking  # Store CLEANED version
                
                # Get response content (everything after </thinking>)
                thinking_end = thinking_match.end()
                response_content = accumulated[thinking_end:]
                clean_response = strip_tags(response_content)
                
                # Emit response delta
                if clean_response and clean_response != self._emitted_response:
                    response_delta = clean_response[len(self._emitted_response):]
                    if response_delta:
                        logger.debug(f"resp delta: {response_delta[:50]!r}")
                        self._emit_chunk("response", response_delta, delta=True, close=False)
                        self._emitted_response = clean_response
                        self.current_response = clean_response  # Store CLEANED version
        else:
            # Still in thinking phase
            clean_text = strip_tags(accumulated)
            
            # Emit thinking delta
            if clean_text and clean_text != self._emitted_thinking:
                thinking_delta = clean_text[len(self._emitted_thinking):]
                if thinking_delta:
                    self._emit_chunk("thinking", thinking_delta, delta=True, close=False)
                    self._emitted_thinking = clean_text
                    self.current_thinking = clean_text  # Store CLEANED version
                
    def _handle_standard_stream(self, chunk: str, metadata: Optional[dict] = None):
        """Handle streaming chunks for standard mode."""
        # Check skip flag (in case user skips during concise generation too)
        if self._skip_requested:
            return
        
        # Check stop flag
        if self._stop_requested:
            return
        
        if chunk:
            self._emit_chunk("response", chunk, delta=True, close=False)
            self.current_response += chunk
    
    # stop_generation() defined earlier
    # Removed duplicate definition that was shadowing the original
        
    def set_max_history_length(self, length: int):
        """Set maximum conversation history length"""
        self.max_history_length = max(1, length)
        
        # Trim history if needed
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]
            logger.debug(f"history trimmed to {self.max_history_length}")
            
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get conversation statistics"""
        total_messages = len(self.conversation_history)
        user_messages = sum(1 for msg in self.conversation_history if msg["role"] == "user")
        assistant_messages = sum(1 for msg in self.conversation_history if msg["role"] == "assistant")
        thinking_messages = sum(1 for msg in self.conversation_history if msg.get("thinking"))
        
        return {
            "total_messages": total_messages,
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "thinking_messages": thinking_messages,
            "max_history_length": self.max_history_length
        }
        
    def export_conversation(self) -> Dict[str, Any]:
        """Export conversation for saving"""
        return {
            "timestamp": time.time(),
            "history": self.conversation_history.copy(),
            "settings": {
                "max_history_length": self.max_history_length
            }
        }
        
    def import_conversation(self, conversation_data: Dict[str, Any]):
        """Import conversation from saved data"""
        try:
            self.conversation_history = conversation_data.get("history", [])
            settings = conversation_data.get("settings", {})
            
            self.max_history_length = settings.get("max_history_length", 50)
            
            logger.info(f"Conversation imported: {len(self.conversation_history)} messages")
            
        except Exception as e:
            error_msg = f"Error importing conversation: {str(e)}"
            self.error_occurred.emit(error_msg)
            logger.error(error_msg)
            
    def _on_model_loaded(self, model_name: str, model_path: str):
        """Handle model loaded event"""
        logger.info(f"Conversation service: Model loaded - {model_name}")
        
    def _on_model_error(self, error_message: str):
        """Handle model error event"""
        logger.error(f"Conversation service: Model error - {error_message}")
        if self.is_generating:
            self.is_generating = False
            self.error_occurred.emit(f"Model error during generation: {error_message}")

