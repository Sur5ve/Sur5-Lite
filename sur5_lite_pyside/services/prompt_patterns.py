#!/usr/bin/env python3
"""
Prompt Patterns and Model Templates
Model-specific prompt templates and capability detection for dual-mode models.
Extracted from dual_mode_utils.py for better modularity.
"""

import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL CAPABILITIES - Defines what each model type supports
# ═══════════════════════════════════════════════════════════════════════════════

MODEL_CAPABILITIES = {
    "gpt-oss": {
        "has_reasoning": True,
        "supports_thinking": True,
        "format": "harmony",
        "uses_harmony": True,
        "harmony_channels": {"reasoning": "analysis", "final": "final"},
        "control_tokens": ["<|start|>", "<|end|>", "<|message|>", "<|channel|>", "<|return|>"],
        "optimal_temperature": 0.7,
        "max_context": 32768
    },
    "qwen3": {
        "has_reasoning": True,
        "supports_thinking": True,
        "format": "xml_tags",
        "uses_harmony": False,
        "closing_only_think": True,
        "thinking_tokens": ["<think>", "<thinking>"],
        "response_tokens": ["</think>", "</thinking>"],
        "optimal_temperature": 0.6,
        "max_context": 40960
    },
    "jamba-reasoning": {
        "has_reasoning": True,
        "supports_thinking": True,
        "format": "xml_tags",
        "uses_harmony": False,
        "thinking_tokens": ["<think>"],
        "response_tokens": ["</think>"],
        "optimal_temperature": 0.7,
        "max_context": 16384
    },
    "apriel-thinker": {
        "has_reasoning": True,
        "supports_thinking": True,
        "format": "apriel_markers",
        "uses_harmony": False,
        "thinking_tokens": ["<think>", "[BEGIN FINAL RESPONSE]"],
        "response_tokens": ["</think>", "[END FINAL RESPONSE]"],
        "final_markers": ["[BEGIN FINAL RESPONSE]", "[END FINAL RESPONSE]", "<final>", "</final>"],
        "optimal_temperature": 0.7,
        "max_context": 8192
    },
    "apertus": {
        "has_reasoning": True,
        "supports_thinking": True,
        "format": "apertus",
        "uses_harmony": False,
        "optimal_temperature": 0.7,
        "max_context": 8192,
        "note": "Multi-layer format; fallback to plain text if unsupported"
    },
    "granite-hybrid": {
        # FIX: Granite 4.0 Hybrid uses standard XML <thinking> tags, not <think_on>/<think_off>
        "has_reasoning": True,
        "supports_thinking": True,
        "format": "xml_tags",
        "uses_harmony": False,
        "thinking_tokens": ["<thinking>"],
        "response_tokens": ["</thinking>"],
        "control_tokens": ["<|start_of_role|>", "<|end_of_role|>", "<|end_of_text|>"],
        "optimal_temperature": 0.7,
        "max_context": 32768,
        "repetition_penalty": 1.15,
        "stop_sequences": ["<|end_of_text|>"],
        "note": "Granite Hybrid (-H-) models use standard XML <thinking> tags"
    },
    "granite-dense": {
        "has_reasoning": False,
        "supports_thinking": False,
        "format": "standard",
        "uses_harmony": False,
        "optimal_temperature": 0.7,
        "max_context": 8192,
        "repetition_penalty": 1.15,
        "stop_sequences": ["<|end_of_text|>"],
        "note": "Granite Dense models (non-Hybrid) do NOT support thinking mode"
    },
    "gemma-3": {
        "has_reasoning": False,
        "supports_thinking": False,
        "format": "standard",
        "optimal_temperature": 1.0,
        "max_context": 32768,
        "note": "Gemma 3 large models (1B+), instruction-tuned",
        "thinking_tokens": [],
        "response_tokens": [],
        "control_tokens": ["<start_of_turn>", "<end_of_turn>"],
        "stop_sequences": ["<end_of_turn>", "<eos>"]
    },
    "gemma-3-small": {
        "has_reasoning": False,
        "supports_thinking": False,
        "format": "standard",
        "uses_harmony": False,
        "control_tokens": ["<start_of_turn>", "<end_of_turn>"],
        "optimal_temperature": 1.0,
        "max_context": 32768,
        "stop_sequences": ["<end_of_turn>", "<eos>"],
        "note": "Gemma 3 270M model - too small for thinking, uses standard response"
    },
    "llama-3.1": {
        "has_reasoning": True,
        "supports_thinking": True,
        "format": "xml_tags",
        "optimal_temperature": 0.8,
        "max_context": 32768,
        "thinking_tokens": ["**Thinking Process:**", "**Analysis:**"],
        "response_tokens": ["**Response:**", "**Final Answer:**"]
    },
    "smollm": {
        "has_reasoning": False,
        "supports_thinking": False,
        "format": "standard",
        "uses_harmony": False,
        "control_tokens": ["<|im_start|>", "<|im_end|>"],
        "optimal_temperature": 0.6,
        "max_context": 2048,
        "stop_sequences": ["<|im_end|>", "<|endoftext|>", "<|im_start|>user"],
        "note": "Small 135M model - too small for thinking, uses standard response"
    },
    "smollm2": {
        "has_reasoning": False,
        "supports_thinking": False,
        "format": "standard",
        "uses_harmony": False,
        "control_tokens": ["<|im_start|>", "<|im_end|>"],
        "optimal_temperature": 0.6,
        "max_context": 2048,
        "stop_sequences": ["<|im_end|>", "<|endoftext|>", "<|im_start|>user"],
        "note": "SmolLM2 135M-1.7B models - too small for thinking, uses standard response"
    }
}

# Default capabilities for unknown models
DEFAULT_CAPABILITIES = {
    "has_reasoning": False,
    "supports_thinking": False,
    "optimal_temperature": 0.7,
    "max_context": 8192,
    "thinking_tokens": ["<reasoning>"],
    "response_tokens": ["</reasoning>"]
}


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT TEMPLATES - Model-specific prompt patterns
# ═══════════════════════════════════════════════════════════════════════════════

PROMPT_TEMPLATES = {
    "gpt-oss": {
        "thinking": """You are an advanced AI assistant with deep reasoning capabilities. Structure your response using Harmony channels:
- Use the 'analysis' channel for step-by-step reasoning
- Use the 'final' channel for your complete answer to the user

Provide thorough analysis before your final response.

Question: {user_prompt}""",
        "standard": "You are a helpful AI assistant. Please provide a clear and concise response.\n\n{user_prompt}"
    },
    "qwen3": {
        "thinking": """You are a helpful AI assistant. When answering, follow this structure:

<thinking>
[Your step-by-step reasoning process here]
</thinking>

<final_answer>
[Your complete answer here]
</final_answer>

Question: {user_prompt}""",
        "standard": "You are a helpful AI assistant. Please provide a direct and helpful response.\n\n{user_prompt}"
    },
    "jamba-reasoning": {
        "thinking": """You are an advanced reasoning assistant. Structure your response as:

<think>
[Your step-by-step reasoning process here]
</think>

[Your complete answer here]

Question: {user_prompt}""",
        "standard": "You are a helpful AI assistant. Please provide a clear response.\n\n{user_prompt}"
    },
    "apriel-thinker": {
        "thinking": """You are a thoughtful AI assistant. Show your reasoning process, then provide your final answer:

<think>
[Your reasoning process]
</think>

[BEGIN FINAL RESPONSE]
[Your complete answer]
[END FINAL RESPONSE]

Question: {user_prompt}""",
        "standard": "You are a helpful AI assistant. Please provide a clear response.\n\n{user_prompt}"
    },
    "gemma-3": {
        "thinking": "You are Gemma, a helpful AI assistant created by Google DeepMind.\n\n{user_prompt}",
        "standard": "You are Gemma, a helpful AI assistant created by Google DeepMind.\n\n{user_prompt}"
    },
    "gemma-3-small": {
        "thinking": "{user_prompt}",
        "standard": "{user_prompt}"
    },
    "granite-hybrid": {
        # FIX: Granite Hybrid uses XML <thinking> tags like other models
        "thinking": """{user_prompt}

Please think through this step-by-step in a <thinking> block, then provide your answer:
<thinking>""",
        "standard": "{user_prompt}"
    },
    "granite-dense": {
        "thinking": "{user_prompt}",
        "standard": "{user_prompt}"
    },
    "llama-3.1": {
        "thinking": """You are a helpful AI assistant based on Llama 3.1. Please respond using this format:

<thinking>
[Your analytical reasoning process]
</thinking>

<final_answer>
[Your clear, complete answer]
</final_answer>

Question: {user_prompt}""",
        "standard": "You are a helpful AI assistant based on Llama 3.1. Please provide a helpful and accurate response.\n\n{user_prompt}"
    },
    "smollm": {
        "thinking": """You are a helpful assistant. When answering:
1. First, briefly explain your reasoning (1-2 sentences starting with "Let me think...")
2. Then, give your answer (starting with "Answer:")

{user_prompt}""",
        "standard": "You are a helpful AI assistant. Answer concisely.\n\n{user_prompt}"
    },
    "smollm2": {
        "thinking": """You are a helpful assistant. When answering:
1. First, briefly explain your reasoning (1-2 sentences starting with "Let me think...")
2. Then, give your answer (starting with "Answer:")

{user_prompt}""",
        "standard": "You are a helpful AI assistant. Answer concisely.\n\n{user_prompt}"
    },
    "default": {
        "thinking": """You are a helpful AI assistant. Please structure your response as:

<thinking>
[Your step-by-step reasoning]
</thinking>

<final_answer>
[Your complete answer]
</final_answer>

Question: {user_prompt}""",
        "standard": "You are a helpful AI assistant.\n\n{user_prompt}"
    }
}

# Models that support dual-mode operation
DUAL_MODE_MODELS = ["gpt-oss", "qwen3", "llama", "jamba-reasoning", "apriel", "apertus", "granite-hybrid", "smollm", "smollm2", "gemma-3-small"]


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _detect_model_type(model_path: str) -> str:
    """
    Detect the model type from the model path.
    
    Args:
        model_path: Full path to the model file
        
    Returns:
        Model type key (e.g., "gpt-oss", "qwen3", "default")
    """
    model_name = os.path.basename(model_path).lower()
    
    if "gpt-oss" in model_name:
        return "gpt-oss"
    elif "qwen3" in model_name:
        return "qwen3"
    elif "jamba" in model_name and "reasoning" in model_name:
        return "jamba-reasoning"
    elif "apriel" in model_name and "thinker" in model_name:
        return "apriel-thinker"
    elif "apertus" in model_name:
        return "apertus"
    elif "granite" in model_name:
        # Differentiate between Granite Hybrid (-H- or -h-) and Granite Dense
        if "-h-" in model_name or "_h_" in model_name or "-hybrid" in model_name:
            return "granite-hybrid"
        else:
            return "granite-dense"
    elif "gemma-3" in model_name or "gemma3" in model_name:
        # Check for small Gemma-3 models (270M) that need simulated thinking
        if "270m" in model_name:
            return "gemma-3-small"
        return "gemma-3"
    elif "llama" in model_name and ("3.1" in model_name or "3_1" in model_name):
        return "llama-3.1"
    elif "smollm2" in model_name:
        return "smollm2"
    elif "smollm" in model_name or "smol" in model_name:
        return "smollm"
    else:
        return "default"


def get_prompt_template(model_path: str, thinking_mode: bool) -> str:
    """
    Get the appropriate prompt template for a dual-mode model.
    
    Args:
        model_path: Full path to the model file
        thinking_mode: True for thinking mode, False for standard mode
        
    Returns:
        Prompt template string with {user_prompt} placeholder
    """
    try:
        model_type = _detect_model_type(model_path)
        templates = PROMPT_TEMPLATES.get(model_type, PROMPT_TEMPLATES["default"])
        mode_key = "thinking" if thinking_mode else "standard"
        return templates.get(mode_key, templates.get("standard", ""))
    except Exception as e:
        logger.warning(f"Could not get template for {model_path}: {e}")
        return ""


def apply_prompt_template(user_prompt: str, template: str) -> str:
    """
    Apply a prompt template to a user's input.
    
    Args:
        user_prompt: The original user prompt
        template: Template string with {user_prompt} placeholder
        
    Returns:
        Formatted prompt, or original prompt if template application fails
    """
    try:
        if not template or "{user_prompt}" not in template:
            return user_prompt
        return template.format(user_prompt=user_prompt)
    except Exception as e:
        logger.warning(f"Error applying template: {e}")
        return user_prompt


def is_template_enabled(model_path: str) -> bool:
    """
    Check if prompt templating is enabled for a model.
    
    Args:
        model_path: Full path to the model file
        
    Returns:
        True if templating is enabled
    """
    try:
        model_name = os.path.basename(model_path).lower()
        return any(model_type in model_name for model_type in DUAL_MODE_MODELS)
    except Exception:
        return False


def is_dual_mode_model(model_path: str) -> bool:
    """
    Check if a model supports dual-mode operation (thinking + standard).
    
    Args:
        model_path: Full path to the model file
        
    Returns:
        True if model supports dual-mode
    """
    try:
        # FIX: Use _detect_model_type() which correctly parses filenames
        # instead of simple substring matching against DUAL_MODE_MODELS
        model_type = _detect_model_type(model_path)
        return model_type in DUAL_MODE_MODELS
    except Exception:
        return False


def get_model_capabilities(model_path: str) -> Dict[str, Any]:
    """
    Get capabilities and optimal settings for a specific model.
    
    Args:
        model_path: Full path to the model file
        
    Returns:
        Dictionary of model capabilities
    """
    try:
        model_type = _detect_model_type(model_path)
        model_name = os.path.basename(model_path).lower()
        
        # Get base capabilities
        capabilities = MODEL_CAPABILITIES.get(model_type, DEFAULT_CAPABILITIES).copy()
        
        # Apply model-specific adjustments
        if model_type == "gemma-3":
            if "12b" in model_name:
                capabilities["max_context"] = 32768
            elif "4b" in model_name:
                capabilities["max_context"] = 16384
                
        return capabilities
        
    except Exception as e:
        logger.warning(f"Error getting capabilities: {e}")
        return DEFAULT_CAPABILITIES.copy()


def should_show_thinking_toggle(model_path: str) -> bool:
    """
    Determine if the thinking mode toggle should be shown for this model.
    
    Args:
        model_path: Full path to the model file
        
    Returns:
        True if thinking toggle should be shown
    """
    return is_dual_mode_model(model_path)


def get_dual_mode_preference(key: str, default=None):
    """
    Get a dual-mode preference setting.
    
    Args:
        key: Preference key to look up
        default: Default value if not found
        
    Returns:
        Preference value or default
    """
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


# Export all functions
__all__ = [
    "get_prompt_template",
    "apply_prompt_template",
    "is_template_enabled",
    "is_dual_mode_model",
    "get_model_capabilities",
    "should_show_thinking_toggle",
    "get_dual_mode_preference",
    "MODEL_CAPABILITIES",
    "PROMPT_TEMPLATES",
    "DUAL_MODE_MODELS",
]

