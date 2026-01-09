#!/usr/bin/env python3
"""
Sur5ve Services Module - Core business logic services for AI and conversation management

Sur5ve LLC - Services Module (Protected)
Copyright (c) 2024-2026 Sur5ve LLC
Licensed under MIT License
https://sur5ve.com

This module is protected by Sur5ve brand integrity verification.
"""

# Core service classes
from .model_service import ModelService
from .conversation_service import ConversationService

# Backend systems
from .model_engine import (
    ModelEngine, get_engine, is_model_loaded,
    load_model_simple, generate_simple, get_thinking_preference,
    RAM_CONFIGS, load_settings, save_settings, get_current_settings
)
from .dual_mode_utils import (
    extract_thinking_and_response, create_thinking_prompt,
    create_standard_prompt, format_chat_messages_thinking,
    format_chat_messages_standard, is_thinking_response,
    clean_response_text, clean_thinking_text, get_default_stop_sequences, DualModeConfig,
    # Template system functions
    get_prompt_template, apply_prompt_template, is_template_enabled,
    is_dual_mode_model, get_dual_mode_preference, get_model_capabilities,
    should_show_thinking_toggle
)

__all__ = [
    # Service classes
    "ModelService", 
    "ConversationService",
    
    # Model engine
    "ModelEngine",
    "get_engine", 
    "is_model_loaded",
    "load_model_simple",
    "generate_simple",
    "get_thinking_preference",
    "RAM_CONFIGS",
    "load_settings",
    "save_settings", 
    "get_current_settings",
    
    # Dual mode utilities
    "extract_thinking_and_response",
    "create_thinking_prompt",
    "create_standard_prompt",
    "format_chat_messages_thinking",
    "format_chat_messages_standard", 
    "is_thinking_response",
    "clean_response_text",
    "clean_thinking_text",
    "get_default_stop_sequences",
    "DualModeConfig",
    
    # Template system
    "get_prompt_template",
    "apply_prompt_template", 
    "is_template_enabled",
    "is_dual_mode_model",
    "get_dual_mode_preference",
    "get_model_capabilities",
    "should_show_thinking_toggle"
]
