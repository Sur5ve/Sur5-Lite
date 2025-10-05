#!/usr/bin/env python3
"""
Dual Mode Utilities for Thinking Models
Handles models that support both thinking/reasoning and standard response modes
"""

import re
from typing import Dict, Any, Tuple, Optional


def extract_thinking_and_response(text: str) -> Tuple[str, str]:
    """
    Extract thinking process and final response from model output.
    
    Args:
        text: Raw model output containing thinking tags
        
    Returns:
        Tuple of (thinking_content, response_content)
    """
    thinking_content = ""
    response_content = ""
    
    # Try multiple thinking tag patterns
    patterns = [
        r"<thinking>(.*?)</thinking>(.*?)$",
        r"<think>(.*?)</think>(.*?)$", 
        r"\*\*Thinking:\*\*(.*?)\*\*Response:\*\*(.*?)$",
        r"# Thinking(.*?)# Response(.*?)$",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            thinking_content = match.group(1).strip()
            response_content = match.group(2).strip()
            break
    
    # If no thinking tags found, treat entire text as response
    if not thinking_content and not response_content:
        response_content = text.strip()
    
    return thinking_content, response_content


def create_thinking_prompt(user_message: str, system_prompt: str = "", context: str = "") -> str:
    """
    Create a prompt that encourages thinking mode output.
    
    Args:
        user_message: The user's input message
        system_prompt: Optional system prompt
        context: Optional RAG context
        
    Returns:
        Formatted prompt for thinking mode
    """
    prompt_parts = []
    
    if system_prompt:
        prompt_parts.append(f"System: {system_prompt}")
    
    if context:
        prompt_parts.append(f"Context: {context}")
    
    # Add thinking instruction
    thinking_instruction = """
Please think through your response step by step. Use <thinking> tags to show your reasoning process, then provide your final response.

Format:
<thinking>
Your step-by-step reasoning here...
</thinking>

Your final response here.
"""
    
    prompt_parts.append(thinking_instruction)
    prompt_parts.append(f"User: {user_message}")
    prompt_parts.append("Assistant:")
    
    return "\n\n".join(prompt_parts)


def create_standard_prompt(user_message: str, system_prompt: str = "", context: str = "") -> str:
    """
    Create a standard prompt without thinking mode.
    
    Args:
        user_message: The user's input message
        system_prompt: Optional system prompt
        context: Optional RAG context
        
    Returns:
        Formatted prompt for standard mode
    """
    prompt_parts = []
    
    if system_prompt:
        prompt_parts.append(f"System: {system_prompt}")
    
    if context:
        prompt_parts.append(f"Context: {context}")
    
    prompt_parts.append(f"User: {user_message}")
    prompt_parts.append("Assistant:")
    
    return "\n\n".join(prompt_parts)


def format_chat_messages_thinking(messages: list, system_prompt: str = "") -> list:
    """
    Format messages for thinking mode with chat format.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content'
        system_prompt: Optional system prompt
        
    Returns:
        Formatted messages list with thinking instructions
    """
    formatted_messages = []
    
    # Add system message with thinking instructions
    thinking_system = system_prompt + """

When responding, please think through your answer step by step. Use <thinking> tags to show your reasoning process, then provide your final response.

Format your response as:
<thinking>
Your step-by-step reasoning here...
</thinking>

Your final response here."""
    
    formatted_messages.append({
        "role": "system",
        "content": thinking_system
    })
    
    # Add conversation messages
    formatted_messages.extend(messages)
    
    return formatted_messages


def format_chat_messages_standard(messages: list, system_prompt: str = "") -> list:
    """
    Format messages for standard mode with chat format.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content'
        system_prompt: Optional system prompt
        
    Returns:
        Formatted messages list without thinking instructions
    """
    formatted_messages = []
    
    if system_prompt:
        formatted_messages.append({
            "role": "system", 
            "content": system_prompt
        })
    
    # Add conversation messages
    formatted_messages.extend(messages)
    
    return formatted_messages


def is_thinking_response(text: str) -> bool:
    """
    Check if text contains thinking tags.
    
    Args:
        text: Text to check
        
    Returns:
        True if thinking tags are found
    """
    thinking_patterns = [
        r"<thinking>.*?</thinking>",
        r"<think>.*?</think>",
        r"\*\*Thinking:\*\*.*?\*\*Response:\*\*",
        r"# Thinking.*?# Response",
    ]
    
    for pattern in thinking_patterns:
        if re.search(pattern, text, re.DOTALL | re.IGNORECASE):
            return True
    
    return False


def clean_response_text(text: str) -> str:
    """
    Clean response text by removing common artifacts.
    
    Args:
        text: Raw response text
        
    Returns:
        Cleaned response text
    """
    # Remove common prefixes
    prefixes_to_remove = [
        "Assistant:",
        "Response:",
        "Answer:",
        "Reply:",
    ]
    
    cleaned = text.strip()
    
    for prefix in prefixes_to_remove:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
    
    # Remove extra whitespace
    cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
    cleaned = cleaned.strip()
    
    return cleaned


def get_default_stop_sequences() -> list:
    """
    Get default stop sequences for dual-mode models.
    
    Returns:
        List of stop sequences
    """
    return [
        "</thinking>",
        "<|im_end|>",
        "<|endoftext|>",
        "\n\nUser:",
        "\n\nHuman:",
        "\n\nSystem:",
    ]


class DualModeConfig:
    """Configuration class for dual-mode model settings"""
    
    def __init__(
        self,
        thinking_enabled: bool = True,
        show_thinking: bool = True,
        thinking_temperature: float = 0.7,
        response_temperature: float = 0.7,
        max_thinking_tokens: int = 1000,
        max_response_tokens: int = 2000
    ):
        self.thinking_enabled = thinking_enabled
        self.show_thinking = show_thinking
        self.thinking_temperature = thinking_temperature
        self.response_temperature = response_temperature
        self.max_thinking_tokens = max_thinking_tokens
        self.max_response_tokens = max_response_tokens
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "thinking_enabled": self.thinking_enabled,
            "show_thinking": self.show_thinking,
            "thinking_temperature": self.thinking_temperature,
            "response_temperature": self.response_temperature,
            "max_thinking_tokens": self.max_thinking_tokens,
            "max_response_tokens": self.max_response_tokens,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DualModeConfig':
        """Create config from dictionary"""
        return cls(
            thinking_enabled=data.get("thinking_enabled", True),
            show_thinking=data.get("show_thinking", True),
            thinking_temperature=data.get("thinking_temperature", 0.7),
            response_temperature=data.get("response_temperature", 0.7),
            max_thinking_tokens=data.get("max_thinking_tokens", 1000),
            max_response_tokens=data.get("max_response_tokens", 2000),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 TEMPLATE SYSTEM - Complete Implementation
# ═══════════════════════════════════════════════════════════════════════════════

def get_prompt_template(model_path: str, thinking_mode: bool) -> str:
    """
    Get the appropriate prompt template for a dual-mode model
    
    Args:
        model_path: Full path to the model file
        thinking_mode: True for thinking mode, False for standard mode
        
    Returns:
        str: Prompt template string with {user_prompt} placeholder, or empty string if not available
    """
    try:
        import os
        model_name = os.path.basename(model_path).lower()
        
        # GPT-OSS models - Advanced reasoning capabilities
        if "gpt-oss" in model_name:
            if thinking_mode:
                return """You are an advanced AI assistant with deep reasoning capabilities. Think through this step by step before providing your final answer.

<thinking>
Let me analyze this request carefully and think through the best approach...
</thinking>

{user_prompt}"""
            else:
                return "You are a helpful AI assistant. Please provide a clear and concise response.\n\n{user_prompt}"
                
        # Qwen3 models - Thinking-enabled models
        elif "qwen3" in model_name:
            if thinking_mode:
                return """You are a helpful AI assistant that thinks step by step. Show your reasoning process.

<think>
Let me think about this step by step...
</think>

{user_prompt}"""
            else:
                return "You are a helpful AI assistant. Please provide a direct and helpful response.\n\n{user_prompt}"
                
        # Gemma-3 models - Google's instruction-tuned models  
        elif "gemma-3" in model_name or "gemma3" in model_name:
            if thinking_mode:
                return """You are Gemma, a helpful AI assistant. Think carefully before responding.

Let me think about this step by step:

{user_prompt}"""
            else:
                return "You are Gemma, a helpful AI assistant created by Google DeepMind.\n\n{user_prompt}"
                
        # Llama-3.1 models - Meta's latest models
        elif "llama" in model_name and ("3.1" in model_name or "3_1" in model_name):
            if thinking_mode:
                return """You are a helpful AI assistant based on Llama 3.1. Think through this systematically.

**Thinking Process:**
Let me approach this step by step...

**Question:** {user_prompt}

**Analysis:**"""
            else:
                return "You are a helpful AI assistant based on Llama 3.1. Please provide a helpful and accurate response.\n\n{user_prompt}"
        
        # Default template for other models
        else:
            if thinking_mode:
                return """You are a helpful AI assistant. Think step by step before responding.

<reasoning>
Let me consider this carefully...
</reasoning>

{user_prompt}"""
            else:
                return "You are a helpful AI assistant.\n\n{user_prompt}"
                
    except Exception as e:
        print(f"⚠️ Could not get prompt template for {model_path}: {e}")
        return ""

def apply_prompt_template(user_prompt: str, template: str) -> str:
    """
    Apply a prompt template to a user's input
    
    Args:
        user_prompt: The original user prompt
        template: Template string with {user_prompt} placeholder
        
    Returns:
        str: Formatted prompt, or original prompt if template application fails
    """
    try:
        if not template or "{user_prompt}" not in template:
            return user_prompt
            
        # Apply the template
        formatted_prompt = template.format(user_prompt=user_prompt)
        return formatted_prompt
        
    except Exception as e:
        print(f"⚠️ Error applying prompt template: {e}")
        return user_prompt  # Fallback to original prompt

def is_template_enabled(model_path: str) -> bool:
    """
    Check if prompt templating is enabled for a dual-mode model
    
    Args:
        model_path: Full path to the model file
        
    Returns:
        bool: True if templating is enabled, False otherwise
    """
    try:
        import os
        model_name = os.path.basename(model_path).lower()
        
        # Enable templates for supported models
        supported_models = ["gpt-oss", "qwen3", "gemma-3", "gemma3", "llama"]
        return any(model_type in model_name for model_type in supported_models)
        
    except Exception:
        return False

def is_dual_mode_model(model_path: str) -> bool:
    """Check if a model supports dual-mode operation (thinking + standard)"""
    try:
        import os
        model_name = os.path.basename(model_path).lower()
        
        # Models with dual-mode capabilities
        dual_mode_models = ["gpt-oss", "qwen3", "gemma-3", "gemma3", "llama"]
        return any(model_type in model_name for model_type in dual_mode_models)
        
    except Exception:
        return False

def get_dual_mode_preference(key: str, default=None):
    """Get a dual-mode preference setting"""
    try:
        from .model_engine import get_current_settings
        settings = get_current_settings()
        dual_prefs = settings.get("dual_mode_preferences", {
            "enable_prompt_templating": True,
            "template_debug_mode": False,
            "remember_last_mode": True,
            "default_thinking_mode": True,
            "model_specific": {}
        })
        return dual_prefs.get(key, default)
    except Exception:
        return default

def get_model_capabilities(model_path: str) -> Dict[str, Any]:
    """Get capabilities and optimal settings for a specific model"""
    try:
        import os
        model_name = os.path.basename(model_path).lower()
        
        # GPT-OSS models
        if "gpt-oss" in model_name:
            return {
                "has_reasoning": True,
                "supports_thinking": True,
                "optimal_temperature": 0.7,
                "max_context": 32768,
                "thinking_tokens": ["<thinking>", "<reasoning>"],
                "response_tokens": ["</thinking>", "</reasoning>"]
            }
            
        # Qwen3 models  
        elif "qwen3" in model_name:
            return {
                "has_reasoning": True,
                "supports_thinking": True,
                "optimal_temperature": 0.6,
                "max_context": 40960,
                "thinking_tokens": ["<think>", "<thinking>"],
                "response_tokens": ["</think>", "</thinking>"]
            }
            
        # Gemma-3 models
        elif "gemma-3" in model_name or "gemma3" in model_name:
            context_size = 8192
            if "12b" in model_name:
                context_size = 32768
            elif "4b" in model_name:
                context_size = 16384
                
            return {
                "has_reasoning": True,
                "supports_thinking": True,
                "optimal_temperature": 0.7,
                "max_context": context_size,
                "thinking_tokens": ["**Thinking Process:**", "**Analysis:**"],
                "response_tokens": ["**Response:**", "**Answer:**"]
            }
            
        # Llama-3.1 models
        elif "llama" in model_name and ("3.1" in model_name or "3_1" in model_name):
            context_size = 32768
            if "8b" in model_name:
                context_size = 32768
                
            return {
                "has_reasoning": True, 
                "supports_thinking": True,
                "optimal_temperature": 0.8,
                "max_context": context_size,
                "thinking_tokens": ["**Thinking Process:**", "**Analysis:**"],
                "response_tokens": ["**Response:**", "**Final Answer:**"]
            }
            
        # Default capabilities
        else:
            return {
                "has_reasoning": False,
                "supports_thinking": False,
                "optimal_temperature": 0.7,
                "max_context": 8192,
                "thinking_tokens": ["<reasoning>"],
                "response_tokens": ["</reasoning>"]
            }
            
    except Exception as e:
        print(f"⚠️ Error getting model capabilities: {e}")
        return {
            "has_reasoning": False,
            "supports_thinking": False,
            "optimal_temperature": 0.7,
            "max_context": 8192,
            "thinking_tokens": [],
            "response_tokens": []
        }

def should_show_thinking_toggle(model_path: str) -> bool:
    """Determine if the thinking mode toggle should be shown for this model"""
    return is_dual_mode_model(model_path)

# Export main functions
__all__ = [
    "extract_thinking_and_response",
    "create_thinking_prompt", 
    "create_standard_prompt",
    "format_chat_messages_thinking",
    "format_chat_messages_standard",
    "is_thinking_response",
    "clean_response_text",
    "get_default_stop_sequences",
    "DualModeConfig",
    # Template system functions
    "get_prompt_template",
    "apply_prompt_template", 
    "is_template_enabled",
    "is_dual_mode_model",
    "get_dual_mode_preference",
    "get_model_capabilities",
    "should_show_thinking_toggle"
]
