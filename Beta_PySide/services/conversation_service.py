#!/usr/bin/env python3
"""
Conversation Service  
Orchestrates AI conversations with RAG integration and thinking mode support
"""

import time
import threading
from typing import List, Dict, Any, Optional

from PySide6.QtCore import QObject, Signal, QTimer

from .model_service import ModelService
from .document_service import DocumentService
from .dual_mode_utils import (
    extract_thinking_and_response, 
    create_thinking_prompt,
    create_standard_prompt,
    format_chat_messages_thinking,
    format_chat_messages_standard,
    is_thinking_response,
    clean_response_text,
    # Template system functions
    get_prompt_template,
    apply_prompt_template, 
    is_template_enabled,
    is_dual_mode_model,
    get_dual_mode_preference
)


class ConversationService(QObject):
    """Service for managing AI conversations"""
    
    # Signals
    message_received = Signal(dict)  # message_data
    thinking_started = Signal()
    thinking_chunk = Signal(str)  # thinking_content  
    streaming_chunk = Signal(str)  # response_chunk
    response_complete = Signal()
    error_occurred = Signal(str)  # error_message
    
    def __init__(self, model_service: ModelService, document_service: DocumentService, parent=None):
        super().__init__(parent)
        
        # Service dependencies
        self.model_service = model_service
        self.document_service = document_service
        
        # Conversation state
        self.conversation_history: List[Dict[str, Any]] = []
        self.current_thinking = ""
        self.current_response = ""
        self.is_generating = False
        
        # Settings
        self.max_history_length = 50
        self.use_rag = True
        self.rag_context_tokens = 1000
        
        # Connect to model service signals
        self.model_service.model_loaded.connect(self._on_model_loaded)
        self.model_service.model_error.connect(self._on_model_error)
        
        print("💬 Conversation Service initialized")
        
    def send_message(self, user_message: str, use_thinking: bool = None) -> bool:
        """Send a user message and generate AI response"""
        if self.is_generating:
            self.error_occurred.emit("Already generating response")
            return False
            
        # Allow sending even if model is not yet loaded. The first send will lazy-load
        # the model in the background thread inside ModelService.generate_chat_response().
            
        try:
            # Add user message to history
            user_msg_data = {
                "role": "user",
                "content": user_message,
                "timestamp": time.time(),
                "thinking": "",
                "metadata": {}
            }
            
            self.conversation_history.append(user_msg_data)
            self.message_received.emit(user_msg_data)
            
            # Determine thinking mode
            if use_thinking is None:
                use_thinking = self.model_service.get_thinking_mode()
                
            # Start generation in background thread
            generation_thread = threading.Thread(
                target=self._generate_response_thread,
                args=(user_message, use_thinking),
                daemon=True
            )
            generation_thread.start()
            
            return True
            
        except Exception as e:
            error_msg = f"Error sending message: {str(e)}"
            self.error_occurred.emit(error_msg)
            print(f"❌ {error_msg}")
            return False
            
    def _generate_response_thread(self, user_message: str, use_thinking: bool):
        """Generate AI response in background thread"""
        try:
            self.is_generating = True
            
            # Get RAG context if enabled
            context = ""
            if self.use_rag and self.document_service.is_rag_enabled():
                context = self.document_service.get_context_for_query(
                    user_message, 
                    self.rag_context_tokens
                )
                
            # Prepare conversation for model
            conversation_messages = []
            for msg in self.conversation_history[-10:]:  # Last 10 messages for context
                if msg["role"] in ["user", "assistant"]:
                    conversation_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                    
            # Generate response based on thinking mode
            if use_thinking:
                self._generate_thinking_response(conversation_messages, context)
            else:
                self._generate_standard_response(conversation_messages, context)
                
        except Exception as e:
            error_msg = f"Generation error: {str(e)}"
            self.error_occurred.emit(error_msg)
            print(f"❌ {error_msg}")
        finally:
            self.is_generating = False
            
    def _generate_thinking_response(self, messages: List[Dict], context: str):
        """Generate response with thinking mode"""
        try:
            # Emit thinking started
            self.thinking_started.emit()
            
            # Get the user's prompt (last message)
            user_message = messages[-1]["content"] if messages else ""
            model_path = self.model_service.current_model_path
            
            # Apply prompt templating for dual-mode models (CRITICAL STEP - like Tkinter line 13)
            enhanced_prompt = user_message
            if context:
                enhanced_prompt = f"{context}\n\n{user_message}"
            
            template_enabled_globally = get_dual_mode_preference("enable_prompt_templating", True)
            is_dual_mode = is_dual_mode_model(model_path) if model_path else False
            
            if is_dual_mode and template_enabled_globally and is_template_enabled(model_path):
                template = get_prompt_template(model_path, thinking_mode=True)
                if template:
                    # Apply template to the enhanced prompt (which may already include RAG context)
                    enhanced_prompt = apply_prompt_template(enhanced_prompt, template)
                    
                    # Show template debug info (like Tkinter)
                    debug_mode = get_dual_mode_preference("template_debug_mode", False)
                    if debug_mode:
                        print(f"🎯 Applied thinking template to prompt")
                        print(f"📝 Template preview: {template[:100]}..." if len(template) > 100 else f"📝 Template: {template}")
                    else:
                        print(f"🎯 Applied thinking template to prompt")
            
            # Format messages for thinking mode (use enhanced prompt)
            formatted_messages = messages.copy()
            if formatted_messages:
                formatted_messages[-1] = {"role": "user", "content": enhanced_prompt}
            
            formatted_messages = format_chat_messages_thinking(
                formatted_messages, 
                system_prompt=f"Context: {context}" if context else ""
            )
            
            # Reset current content
            self.current_thinking = ""
            self.current_response = ""
            
            # Model loading will happen automatically in generate_chat_response (like Tkinter)
            if not model_path:
                raise RuntimeError("No model path set")
            
            # Generate with streaming
            full_response = self.model_service.generate_chat_response(
                messages=formatted_messages,
                stream_callback=self._handle_thinking_stream
            )
            
            # Extract thinking and response
            thinking_content, response_content = extract_thinking_and_response(full_response)
            
            if not response_content:
                response_content = clean_response_text(full_response)
                
            # Add to conversation history
            assistant_msg_data = {
                "role": "assistant",
                "content": response_content,
                "timestamp": time.time(),
                "thinking": thinking_content,
                "metadata": {
                    "thinking_mode": True,
                    "context_used": bool(context)
                }
            }
            
            self.conversation_history.append(assistant_msg_data)
            self.message_received.emit(assistant_msg_data)
            self.response_complete.emit()
            
        except Exception as e:
            raise e
            
    def _generate_standard_response(self, messages: List[Dict], context: str):
        """Generate standard response without thinking"""
        try:
            # Get the user's prompt (last message)
            user_message = messages[-1]["content"] if messages else ""
            model_path = self.model_service.current_model_path
            
            # Apply prompt templating for dual-mode models (CRITICAL STEP - like Tkinter line 13)
            enhanced_prompt = user_message
            if context:
                enhanced_prompt = f"{context}\n\n{user_message}"
            
            template_enabled_globally = get_dual_mode_preference("enable_prompt_templating", True)
            is_dual_mode = is_dual_mode_model(model_path) if model_path else False
            
            if is_dual_mode and template_enabled_globally and is_template_enabled(model_path):
                template = get_prompt_template(model_path, thinking_mode=False)
                if template:
                    # Apply template to the enhanced prompt (which may already include RAG context)
                    enhanced_prompt = apply_prompt_template(enhanced_prompt, template)
                    
                    # Show template debug info (like Tkinter)
                    debug_mode = get_dual_mode_preference("template_debug_mode", False)
                    if debug_mode:
                        print(f"🎯 Applied standard template to prompt")
                        print(f"📝 Template preview: {template[:100]}..." if len(template) > 100 else f"📝 Template: {template}")
                    else:
                        print(f"🎯 Applied standard template to prompt")
            
            # Format messages for standard mode (use enhanced prompt)
            formatted_messages = messages.copy()
            if formatted_messages:
                formatted_messages[-1] = {"role": "user", "content": enhanced_prompt}
            
            formatted_messages = format_chat_messages_standard(
                formatted_messages,
                system_prompt=f"Context: {context}" if context else ""
            )
            
            # Reset current content
            self.current_response = ""
            
            # Model loading will happen automatically in generate_chat_response (like Tkinter)
            if not model_path:
                raise RuntimeError("No model path set")
            
            # Generate with streaming
            response = self.model_service.generate_chat_response(
                messages=formatted_messages,
                stream_callback=self._handle_standard_stream
            )
            
            response = clean_response_text(response)
            
            # Add to conversation history
            assistant_msg_data = {
                "role": "assistant", 
                "content": response,
                "timestamp": time.time(),
                "thinking": "",
                "metadata": {
                    "thinking_mode": False,
                    "context_used": bool(context)
                }
            }
            
            self.conversation_history.append(assistant_msg_data)
            self.message_received.emit(assistant_msg_data)
            self.response_complete.emit()
            
        except Exception as e:
            raise e
            
    def _handle_thinking_stream(self, chunk: str):
        """Handle streaming chunks for thinking mode"""
        if not chunk:
            return
            
        # Try to determine if we're in thinking or response phase
        accumulated = self.current_thinking + self.current_response + chunk
        
        if "<thinking>" in accumulated and "</thinking>" in accumulated:
            # We have complete thinking content
            thinking_content, response_content = extract_thinking_and_response(accumulated)
            
            # Emit thinking chunk if new
            if thinking_content and thinking_content != self.current_thinking:
                new_thinking = thinking_content[len(self.current_thinking):]
                if new_thinking:
                    self.thinking_chunk.emit(new_thinking)
                    self.current_thinking = thinking_content
                    
            # Emit response chunk if new  
            if response_content and response_content != self.current_response:
                new_response = response_content[len(self.current_response):]
                if new_response:
                    self.streaming_chunk.emit(new_response)
                    self.current_response = response_content
        else:
            # Still accumulating or in response phase
            if "</thinking>" in accumulated:
                # Finished thinking, now in response
                self.streaming_chunk.emit(chunk)
                self.current_response += chunk
            else:
                # Still thinking
                self.thinking_chunk.emit(chunk)
                self.current_thinking += chunk
                
    def _handle_standard_stream(self, chunk: str):
        """Handle streaming chunks for standard mode"""
        if chunk:
            self.streaming_chunk.emit(chunk)
            self.current_response += chunk
            
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history.clear()
        print("🗑️ Conversation history cleared")
        
    def get_history(self) -> List[Dict[str, Any]]:
        """Get conversation history"""
        return self.conversation_history.copy()
        
    def get_last_message(self) -> Optional[Dict[str, Any]]:
        """Get the last message in conversation"""
        return self.conversation_history[-1] if self.conversation_history else None
        
    def remove_last_message(self) -> bool:
        """Remove the last message from conversation"""
        if self.conversation_history:
            removed = self.conversation_history.pop()
            print(f"🗑️ Removed message: {removed['role']}")
            return True
        return False
        
    def set_rag_enabled(self, enabled: bool):
        """Enable or disable RAG for conversations"""
        self.use_rag = enabled
        print(f"🔄 RAG in conversations: {'enabled' if enabled else 'disabled'}")
        
    def is_rag_enabled(self) -> bool:
        """Check if RAG is enabled for conversations"""
        return self.use_rag
        
    def set_max_history_length(self, length: int):
        """Set maximum conversation history length"""
        self.max_history_length = max(1, length)
        
        # Trim history if needed
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]
            print(f"📝 Conversation history trimmed to {self.max_history_length} messages")
            
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
            "rag_enabled": self.use_rag,
            "max_history_length": self.max_history_length
        }
        
    def export_conversation(self) -> Dict[str, Any]:
        """Export conversation for saving"""
        return {
            "timestamp": time.time(),
            "history": self.conversation_history.copy(),
            "settings": {
                "rag_enabled": self.use_rag,
                "max_history_length": self.max_history_length,
                "rag_context_tokens": self.rag_context_tokens
            }
        }
        
    def import_conversation(self, conversation_data: Dict[str, Any]):
        """Import conversation from saved data"""
        try:
            self.conversation_history = conversation_data.get("history", [])
            settings = conversation_data.get("settings", {})
            
            self.use_rag = settings.get("rag_enabled", True)
            self.max_history_length = settings.get("max_history_length", 50)
            self.rag_context_tokens = settings.get("rag_context_tokens", 1000)
            
            print(f"📥 Conversation imported: {len(self.conversation_history)} messages")
            
        except Exception as e:
            error_msg = f"Error importing conversation: {str(e)}"
            self.error_occurred.emit(error_msg)
            print(f"❌ {error_msg}")
            
    def _on_model_loaded(self, model_name: str, model_path: str):
        """Handle model loaded event"""
        print(f"🤖 Conversation service: Model loaded - {model_name}")
        
    def _on_model_error(self, error_message: str):
        """Handle model error event"""
        print(f"❌ Conversation service: Model error - {error_message}")
        if self.is_generating:
            self.is_generating = False
            self.error_occurred.emit(f"Model error during generation: {error_message}")
