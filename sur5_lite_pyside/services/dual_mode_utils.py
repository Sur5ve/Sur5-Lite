#!/usr/bin/env python3
"""
Dual Mode Utilities for Thinking Models
Handles models that support both thinking/reasoning and standard response modes
"""

import re
from typing import Dict, Any, Tuple, Optional

from utils.logger import create_module_logger
logger = create_module_logger(__name__)


# Harmony control token patterns (compiled for performance)
# Allow optional assistant|user|system role after <|start|> for robustness
HARMONY_HEADER_RE = re.compile(
    r'<\|start\|>\s*(?:assistant|user|system)?\s*<\|channel\|>\s*([a-z0-9_:-]+)\s*<\|message\|>',
    re.IGNORECASE
)
HARMONY_END_RE = re.compile(r'<\|end\|>|<\|return\|>', re.IGNORECASE)
HARMONY_HEADER_LINE_RE = re.compile(
    r'<\|start\|>\s*(?:assistant|user|system)?\s*<\|channel\|>\s*[a-z0-9_:-]+\s*<\|message\|>',
    re.IGNORECASE
)


def detect_harmony_format(text: str) -> bool:
    """Detect OpenAI Harmony channel format"""
    return bool(HARMONY_HEADER_RE.search(text)) or '<|channel|>' in text or '<|start|>' in text


def detect_apertus_format(text: str) -> bool:
    """Detect Apertus multi-layer format"""
    # Check for structured JSON-like format with thinking/response layers
    return bool(re.search(r'"thinking":\s*"', text)) or bool(re.search(r'"response":\s*"', text))


def detect_apriel_markers(text: str) -> bool:
    """Detect Apriel explicit markers"""
    return '[BEGIN FINAL RESPONSE]' in text or '[END FINAL RESPONSE]' in text or '<final>' in text.lower()


def detect_qwen3_closing_only(text: str) -> bool:
    """Check for orphaned </think> without opening tag (Qwen3 closing-only pattern)"""
    has_closing = '</think>' in text.lower()
    has_opening = '<think>' in text.lower()
    return has_closing and not has_opening


def strip_harmony_control_tokens(text: str) -> str:
    """Remove Harmony control tokens via two-pass cleanup."""
    # Pass 1: Remove entire header lines first
    cleaned = HARMONY_HEADER_LINE_RE.sub("", text)
    
    # Pass 2: Remove residual individual control tokens
    cleaned = re.sub(r'<\|start\|>', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'<\|end\|>', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'<\|message\|>', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'<\|channel\|>', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'<\|return\|>', '', cleaned, flags=re.IGNORECASE)
    
    return cleaned


def extract_harmony_channels(text: str, thinking_channel: str = "analysis", final_channel: str = "final") -> Tuple[str, str]:
    """Extract thinking and final content from Harmony channels."""
    # Find all channel headers with positions
    spans = list(HARMONY_HEADER_RE.finditer(text))
    if not spans:
        return "", ""
    
    # Find stop position (<|end|> or <|return|>)
    stop_match = HARMONY_END_RE.search(text)
    end_at = stop_match.start() if stop_match else len(text)
    
    # Build channel_to_content dict by extracting content between headers
    channel_to_content = {}
    for i, match in enumerate(spans):
        channel_name = match.group(1).lower()
        start = match.end()
        stop = spans[i + 1].start() if i + 1 < len(spans) else end_at
        
        # Prevent negative spans
        if stop < start:
            stop = start
        
        # Concatenate content for repeated channel names
        channel_to_content.setdefault(channel_name, "")
        channel_to_content[channel_name] += text[start:stop]
    
    # Extract thinking and final content
    thinking = channel_to_content.get(thinking_channel, "")
    final = channel_to_content.get(final_channel, "")
    
    return thinking, final


def extract_apriel_format(text: str) -> Tuple[str, str]:
    """Parse Apriel [BEGIN/END FINAL RESPONSE] markers."""
    thinking_content = ""
    response_content = ""
    
    # Primary: Look for [BEGIN FINAL RESPONSE]...[END FINAL RESPONSE] markers
    final_pattern = r'\[BEGIN FINAL RESPONSE\](.*?)\[END FINAL RESPONSE\]'
    final_match = re.search(final_pattern, text, re.DOTALL | re.IGNORECASE)
    
    if final_match:
        response_content = final_match.group(1).strip()
        # Everything before the marker is thinking
        thinking_content = text[:final_match.start()].strip()
        # Remove any <think> tags from thinking
        thinking_content = re.sub(r'<\s*/?think\s*>', '', thinking_content, flags=re.IGNORECASE)
        return thinking_content, response_content
    
    # Secondary: Check for <final>...</final> tags
    final_tag_pattern = r'<final>(.*?)</final>'
    final_tag_match = re.search(final_tag_pattern, text, re.DOTALL | re.IGNORECASE)
    
    if final_tag_match:
        response_content = final_tag_match.group(1).strip()
        # Everything before the tag is thinking
        thinking_content = text[:final_tag_match.start()].strip()
        # Remove any <think> tags from thinking
        thinking_content = re.sub(r'<\s*/?think\s*>', '', thinking_content, flags=re.IGNORECASE)
        return thinking_content, response_content
    
    return "", ""


def detect_granite_toggle_format(text: str) -> bool:
    """Detect Granite's <think_on>/<think_off> toggle format"""
    return "<think_on>" in text or "<think_off>" in text


def detect_smollm_simulated_format(text: str) -> bool:
    """Detect SmolLM2's simulated thinking format (Let me think... / Answer:)"""
    text_lower = text.lower()
    has_thinking_marker = any(marker in text_lower for marker in [
        "let me think", "thinking:", "first,", "i'll think", "let's think"
    ])
    has_answer_marker = any(marker in text_lower for marker in [
        "answer:", "my answer:", "so,", "therefore,", "in conclusion,"
    ])
    return has_thinking_marker or has_answer_marker


def extract_smollm_simulated(text: str) -> Tuple[str, str]:
    """Extract thinking/response from SmolLM2 simulated format."""
    thinking_content = ""
    response_content = ""
    
    # Primary pattern: "Answer:" separator
    answer_patterns = [
        r'(?:^|\n)\s*Answer:\s*',
        r'(?:^|\n)\s*My answer:\s*',
        r'(?:^|\n)\s*My response:\s*',
    ]
    
    for pattern in answer_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            thinking_content = text[:match.start()].strip()
            response_content = text[match.end():].strip()
            return thinking_content, response_content
    
    # Secondary pattern: Paragraph break after thinking markers
    thinking_markers = [
        r'^Let me think[^.]*\.\s*',
        r'^Thinking:\s*[^.]*\.\s*',
        r'^First,\s*[^.]*\.\s*',
    ]
    
    for pattern in thinking_markers:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            # Find next paragraph break
            remaining = text[match.end():]
            para_break = remaining.find('\n\n')
            if para_break != -1:
                thinking_content = text[:match.end() + para_break].strip()
                response_content = remaining[para_break:].strip()
                return thinking_content, response_content
            else:
                # No paragraph break - use sentence-based split
                sentences = text.split('. ')
                if len(sentences) >= 2:
                    # First 1-2 sentences as thinking
                    split_point = min(2, len(sentences) - 1)
                    thinking_content = '. '.join(sentences[:split_point]) + '.'
                    response_content = '. '.join(sentences[split_point:])
                    return thinking_content, response_content
    
    # Fallback: If text starts with thinking marker, try splitting by "So," or "Therefore,"
    conclusion_patterns = [
        r'\n\s*So,\s*',
        r'\n\s*Therefore,\s*',
        r'\n\s*Thus,\s*',
        r'\n\s*In conclusion,\s*',
    ]
    
    for pattern in conclusion_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            thinking_content = text[:match.start()].strip()
            response_content = text[match.start():].strip()
            return thinking_content, response_content
    
    # Last resort: Use first paragraph as thinking if multiple paragraphs exist
    paragraphs = text.strip().split('\n\n')
    if len(paragraphs) >= 2:
        thinking_content = paragraphs[0].strip()
        response_content = '\n\n'.join(paragraphs[1:]).strip()
        return thinking_content, response_content
    
    # If nothing else works, treat entire text as response
    return "", text.strip()


def extract_granite_thinking(text: str) -> Tuple[str, str]:
    """Extract thinking/response from Granite <think_on>/<think_off> format."""
    thinking_content = ""
    response_content = ""
    
    # Pattern: <think_on>...content...<think_off>...response...
    pattern = r'<think_on>(.*?)<think_off>(.*)'
    match = re.search(pattern, text, re.DOTALL)
    
    if match:
        thinking_content = match.group(1).strip()
        response_content = match.group(2).strip()
    else:
        # Check for partial format: only <think_on> present (still thinking)
        if "<think_on>" in text and "<think_off>" not in text:
            # Still in thinking phase
            think_on_match = re.search(r'<think_on>(.*)', text, re.DOTALL)
            if think_on_match:
                thinking_content = think_on_match.group(1).strip()
        elif "<think_off>" in text:
            # Has think_off but no think_on - treat everything before as thinking
            think_off_match = re.search(r'(.*?)<think_off>(.*)', text, re.DOTALL)
            if think_off_match:
                thinking_content = think_off_match.group(1).strip()
                response_content = think_off_match.group(2).strip()
        else:
            # No thinking tags, treat entire text as response
            response_content = text.strip()
    
    return thinking_content, response_content


def extract_thinking_and_response(text: str) -> Tuple[str, str]:
    """Extract thinking and response from model output (multi-format support)."""
    thinking_content = ""
    response_content = ""
    
    logger.debug(f"extract: {len(text)} chars")
    
    # PRIORITY 0: Harmony channels (GPT-OSS)
    if detect_harmony_format(text):
        thinking_content, response_content = extract_harmony_channels(text)
        if thinking_content or response_content:
            logger.debug(f"harmony: think={len(thinking_content)} resp={len(response_content)}")
            return thinking_content, response_content
    
    # PRIORITY 1: Apertus multi-layer format
    if detect_apertus_format(text):
        # For now, treat as JSON-like; in future could use apertus-format lib
        try:
            import json
            data = json.loads(text)
            thinking_content = data.get('thinking', '')
            response_content = data.get('response', '')
            if thinking_content or response_content:
                logger.debug(f"apertus: think={len(thinking_content)} resp={len(response_content)}")
                return thinking_content, response_content
        except Exception:
            pass
    
    # PRIORITY 2: Apriel explicit markers
    if detect_apriel_markers(text):
        thinking_content, response_content = extract_apriel_format(text)
        if thinking_content or response_content:
            logger.debug(f"apriel: think={len(thinking_content)} resp={len(response_content)}")
            return thinking_content, response_content
    
    # PRIORITY 2.5: Granite toggle format (<think_on>/<think_off>)
    if detect_granite_toggle_format(text):
        thinking_content, response_content = extract_granite_thinking(text)
        if thinking_content or response_content:
            logger.debug(f"granite: think={len(thinking_content)} resp={len(response_content)}")
            return thinking_content, response_content
    
    # PRIORITY 2.6: SmolLM2 simulated thinking format (Let me think... / Answer:)
    if detect_smollm_simulated_format(text):
        thinking_content, response_content = extract_smollm_simulated(text)
        if thinking_content or response_content:
            logger.debug(f"smollm: think={len(thinking_content)} resp={len(response_content)}")
            return thinking_content, response_content
    
    # PRIORITY 3: Look for explicit <final_answer> tags (structured prompting)
    final_answer_pattern = r'<final_answer>(.*?)</final_answer>'
    final_answer_match = re.search(final_answer_pattern, text, re.DOTALL | re.IGNORECASE)
    
    if final_answer_match:
        response_content = final_answer_match.group(1).strip()
        logger.debug(f"<final_answer>: {len(response_content)}")
    
    # PRIORITY 4: Look for <thinking> tags
    thinking_pattern = r'<thinking>(.*?)</thinking>'
    thinking_match = re.search(thinking_pattern, text, re.DOTALL | re.IGNORECASE)
    
    if thinking_match:
        thinking_content = thinking_match.group(1).strip()
        logger.debug(f"<thinking>: {len(thinking_content)}")
        
        # If we didn't find <final_answer>, fall back to content after </thinking>
        if not response_content:
            end_pos = thinking_match.end()
            response_content = text[end_pos:].strip()
            # Remove any XML-like tags
            response_content = re.sub(r'^<[^>]+>', '', response_content).strip()
            response_content = re.sub(r'<[^>]+>$', '', response_content).strip()
            logger.debug(f"post </thinking>: {len(response_content)}")
    
    # PRIORITY 5: Try <think> tags with Qwen3 closing-only fallback
    if not thinking_content:
        think_pattern = r'<think>(.*?)</think>'
        think_match = re.search(think_pattern, text, re.DOTALL | re.IGNORECASE)
        
        if think_match:
            thinking_content = think_match.group(1).strip()
            logger.debug(f"<think>: {len(thinking_content)}")
            
            if not response_content:
                end_pos = think_match.end()
                response_content = text[end_pos:].strip()
                response_content = re.sub(r'^<[^>]+>', '', response_content).strip()
                response_content = re.sub(r'<[^>]+>$', '', response_content).strip()
                logger.debug(f"post </think>: {len(response_content)}")
        elif detect_qwen3_closing_only(text):
            # Qwen3 closing-only: </think> without opening <think>
            closing_match = re.search(r'</think>', text, re.IGNORECASE)
            if closing_match:
                thinking_content = text[:closing_match.start()].strip()
                response_content = text[closing_match.end():].strip()
                logger.debug(f"qwen3 </think>: {len(thinking_content)}")
    
    # PRIORITY 6: Keyword-based separation (if no tags found)
    if not thinking_content and not response_content:
        separation_keywords = [
            r'\n\n(?:In summary|Final answer|Therefore|The answer is|To conclude)',
            r'\n\n(?:So|Thus|Hence)',
            r'\n(?:Answer:|My answer:|My response:)',
            r'\n\n(?:Based on|Given that|Considering)',
            r'(?:^|\n)(?:So,|Therefore,|Thus,)\s+(?=[A-Z])',
        ]
        
        for keyword_pattern in separation_keywords:
            match = re.search(keyword_pattern, text, re.IGNORECASE)
            if match:
                thinking_content = text[:match.start()].strip()
                response_content = text[match.start():].strip()
                logger.debug(f"keyword match: think={len(thinking_content)} resp={len(response_content)}")
                break
    
    # PRIORITY 7: Last resort - treat everything as response
    if not thinking_content and not response_content:
        response_content = text.strip()
        logger.debug(f"no pattern, full text as resp: {len(response_content)}")
    
    return thinking_content, response_content


def create_thinking_prompt(user_message: str, system_prompt: str = "", context: str = "") -> str:
    """Create prompt for thinking mode output."""
    prompt_parts = []
    
    if system_prompt:
        prompt_parts.append(f"System: {system_prompt}")
    
    if context:
        prompt_parts.append(f"Context: {context}")
    
    # Add thinking instruction with EXPLICIT final_answer tags
    thinking_instruction = """
Please think through your response step by step, then provide your final answer.

You MUST use this exact format:
<thinking>
Your step-by-step reasoning here...
</thinking>

<final_answer>
Your complete answer to the user's question here.
</final_answer>

IMPORTANT: Always include BOTH the <thinking> section AND the <final_answer> section in your response.
"""
    
    prompt_parts.append(thinking_instruction)
    prompt_parts.append(f"User: {user_message}")
    prompt_parts.append("Assistant:")
    
    return "\n\n".join(prompt_parts)


def create_standard_prompt(user_message: str, system_prompt: str = "", context: str = "") -> str:
    """Create standard prompt without thinking mode."""
    prompt_parts = []
    
    if system_prompt:
        prompt_parts.append(f"System: {system_prompt}")
    
    if context:
        prompt_parts.append(f"Context: {context}")
    
    prompt_parts.append(f"User: {user_message}")
    prompt_parts.append("Assistant:")
    
    return "\n\n".join(prompt_parts)


def format_chat_messages_thinking(messages: list, system_prompt: str = "", model_capabilities: Optional[Dict[str, Any]] = None) -> list:
    """Format messages for thinking mode (format-aware)."""
    formatted_messages = []
    
    # Determine format type from capabilities
    uses_harmony = model_capabilities and model_capabilities.get("uses_harmony", False)
    simulated_thinking = model_capabilities and model_capabilities.get("simulated_thinking", False)
    model_format = model_capabilities.get("format", "xml_tags") if model_capabilities else "xml_tags"
    
    # Format-appropriate system message
    if uses_harmony:
        # Harmony format: use analysis/final channels, NO XML tags
        thinking_system = system_prompt + """

When responding, provide thorough analysis using Harmony channels:

- Use the 'analysis' channel for your step-by-step reasoning and detailed thinking
- Use the 'final' channel for your complete answer to the user

Provide comprehensive analysis exploring multiple perspectives, then deliver a thorough final response with examples and clear explanations. Quality and depth matter - aim for detailed, substantive content."""
    elif simulated_thinking or model_format == "smollm_simulated" or model_format == "gemma_simulated":
        # Small model simulated thinking: MINIMAL prompt for 135M-270M models
        # Don't add complex instructions - model is too small to follow them reliably
        # Just use a simple system prompt and let it respond naturally
        thinking_system = "You are a helpful assistant. Answer clearly and directly."
    else:
        # XML tag format: use <thinking> and <final_answer> tags
        thinking_system = system_prompt + """

When responding, please provide DETAILED and COMPREHENSIVE answers:

Step 1: Think deeply and thoroughly about the question
- Analyze multiple aspects and perspectives
- Consider context, examples, and relevant details
- Explore the topic comprehensively (aim for 150+ words in thinking)

Step 2: Provide a thorough, detailed final answer
- Include specific examples and explanations
- Add relevant background information and context
- Use clear structure (paragraphs, lists) for readability
- Aim for completeness (target 200-400+ words in final answer)

You MUST use this exact format:
<thinking>
[Your extensive step-by-step reasoning with detailed analysis. Explore the topic comprehensively, consider multiple angles, and think through relevant examples and context. Be thorough and detailed here.]
</thinking>

<final_answer>
[Your comprehensive, detailed final answer with multiple paragraphs, specific examples, scientific details where applicable, and thorough explanations. Elaborate fully on all key points. Make this substantive and informative.]
</final_answer>

IMPORTANT: Always include BOTH the <thinking> section AND the <final_answer> section in your response. Remember: Quality and depth matter more than brevity. Provide rich, detailed content that truly helps the user understand the topic thoroughly."""
    
    formatted_messages.append({
        "role": "system",
        "content": thinking_system
    })
    
    # Add conversation messages
    formatted_messages.extend(messages)
    
    return formatted_messages


def format_chat_messages_standard(messages: list, system_prompt: str = "") -> list:
    """Format messages for standard mode."""
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
    """Check if text contains reasoning format markers."""
    # Check for Harmony format (GPT-OSS)
    if detect_harmony_format(text):
        return True
    
    # Check for Apriel markers
    if detect_apriel_markers(text):
        return True
    
    # Check for Apertus format
    if detect_apertus_format(text):
        return True
    
    # Check for Granite toggle format (<think_on>/<think_off>)
    if detect_granite_toggle_format(text):
        return True
    
    # Check for SmolLM2 simulated format (Let me think... / Answer:)
    if detect_smollm_simulated_format(text):
        return True
    
    # Check for XML tag patterns (Qwen3, Llama, default)
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
    """Remove reasoning format artifacts from response text."""
    # Step 0a: Strip Harmony control tokens (headers and individual tokens)
    cleaned = strip_harmony_control_tokens(text)
    
    # Step 0b: Remove Apriel text markers
    cleaned = re.sub(r'\[BEGIN FINAL RESPONSE\]', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\[END FINAL RESPONSE\]', '', cleaned, flags=re.IGNORECASE)
    
    # Step 0c: Remove Apriel XML tags
    cleaned = re.sub(r'<\s*/?\s*final\s*>', '', cleaned, flags=re.IGNORECASE)
    
    # Step 0d: Remove Granite toggle markers
    cleaned = re.sub(r'<think_on>|<think_off>', '', cleaned, flags=re.IGNORECASE)
    
    # Step 0e: Remove bracket markers from small models (Granite 350M, Gemma 270M, etc.)
    # These models often output structured markers like [Thinking], [Perspective analysis], etc.
    bracket_markers = [
        r'\[Thinking\]',
        r'\[Perspective analysis\]',
        r'\[Examples and background\]',
        r'\[Scientific background and context\]',
        r'\[In conclusion,?\]',
        r'\[final_answer\]',
        r'\[Response\]',
        r'\[Answer\]',
        r'\[Summary\]',
        r'\[Analysis\]',
        r'\[Conclusion\]',
        r'\[Background\]',
        r'\[Context\]',
        r'\[Overview\]',
        r'\[Details\]',
        r'\[Explanation\]',
    ]
    for pattern in bracket_markers:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Step 1: Remove thinking blocks with content
    cleaned = re.sub(
        r"<\s*(?:thinking|think)\b[^>]*>.*?</\s*(?:thinking|think)\s*>",
        "",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    
    # Step 2: Remove all wrapper tags (keep content): response, final_answer, answer, result
    cleaned = re.sub(
        r"<\s*/?(?:response|final_answer|answer|result)\s*>",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    
    # Step 3: Remove any orphaned tags
    cleaned = re.sub(
        r"<\s*/?\s*(?:thinking|think|response|final_answer|answer|result)\b[^>]*>?",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    
    # Step 4: Remove common prefixes (including variations)
    prefixes_to_remove = [
        "Your final response:",
        "Final response:",
        "Final answer:",
        "Your response:",
        "Your answer:",
        "Assistant:",
        "Response:",
        "Answer:",
        "Reply:",
    ]
    
    cleaned = cleaned.strip()
    
    # Try each prefix (case-insensitive)
    for prefix in prefixes_to_remove:
        if cleaned.lower().startswith(prefix.lower()):
            cleaned = cleaned[len(prefix):].strip()
            break  # Only remove one prefix
    
    # Step 5: Remove extra whitespace
    cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned)
    cleaned = cleaned.strip()
    
    return cleaned


def clean_thinking_text(text: str) -> str:
    """Remove bracket markers and formatting artifacts from thinking text."""
    if not text:
        return ""
    
    cleaned = text
    
    # Remove bracket markers that small models often output
    bracket_markers = [
        r'\[Thinking\]',
        r'\[Perspective analysis\]',
        r'\[Examples and background\]',
        r'\[Scientific background and context\]',
        r'\[In conclusion,?\]',
        r'\[final_answer\]',
        r'\[Response\]',
        r'\[Answer\]',
        r'\[Summary\]',
        r'\[Analysis\]',
        r'\[Conclusion\]',
        r'\[Background\]',
        r'\[Context\]',
        r'\[Overview\]',
        r'\[Details\]',
        r'\[Explanation\]',
    ]
    for pattern in bracket_markers:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Remove thinking XML tags
    cleaned = re.sub(r'<\s*/?(?:thinking|think)\s*>', '', cleaned, flags=re.IGNORECASE)
    
    # Remove extra whitespace
    cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned)
    cleaned = cleaned.strip()
    
    return cleaned


def get_default_stop_sequences(model_capabilities: Optional[Dict[str, Any]] = None, model_path: str = None) -> list:
    """Get stop sequences for dual-mode models (capability-aware)."""
    import os
    
    # Base stop sequences
    stop_sequences = [
        "</thinking>",
        "<|im_end|>",
        "<|endoftext|>",
        "\n\nUser:",
        "\n\nHuman:",
        "\n\nSystem:",
    ]
    
    # Add Harmony stop tokens if model uses Harmony format
    if model_capabilities and model_capabilities.get("uses_harmony"):
        stop_sequences.extend(["<|end|>", "<|return|>"])
    
    # Add Granite-specific stop tokens (only for Hybrid models with toggle format)
    if model_capabilities and model_capabilities.get("format") == "granite_toggle":
        stop_sequences.extend(["<|end_of_text|>", "<think_off>", "<|end_of_role|>"])
    elif model_path:
        model_name = os.path.basename(model_path).lower()
        # Only Granite Hybrid models use toggle tokens
        if "granite" in model_name and ("-h-" in model_name or "_h_" in model_name):
            stop_sequences.extend(["<|end_of_text|>", "<think_off>", "<|end_of_role|>"])
        elif "granite" in model_name:
            # Granite Dense - just the end token
            stop_sequences.append("<|end_of_text|>")
    
    # Add Qwen-specific stop tokens
    if model_path:
        model_name = os.path.basename(model_path).lower()
        if "qwen" in model_name:
            stop_sequences.extend(["<|im_end|>", "</think>"])
        # Add SmolLM2-specific stop tokens (ChatML format)
        elif "smollm2" in model_name or "smollm" in model_name or "smol" in model_name:
            # SmolLM2 uses ChatML format with <|im_start|> and <|im_end|>
            stop_sequences.extend([
                "<|im_end|>", 
                "<|endoftext|>",
                "<|im_start|>user",  # Prevent model from generating user turns
                "<|im_start|>system",  # Prevent model from generating system turns
            ])
        # Add Gemma-3 stop tokens
        elif "gemma-3" in model_name or "gemma3" in model_name:
            stop_sequences.extend([
                "<end_of_turn>",
                "<eos>",
                "<start_of_turn>user",  # Prevent model from generating user turns
            ])
    
    return stop_sequences


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
# TEMPLATE SYSTEM - Imported from prompt_patterns.py
# ═══════════════════════════════════════════════════════════════════════════════

# Import template functions from the extracted module
from .prompt_patterns import (
    get_prompt_template,
    apply_prompt_template,
    is_template_enabled,
    is_dual_mode_model,
    get_dual_mode_preference,
    get_model_capabilities,
    should_show_thinking_toggle,
)

# Export main functions
__all__ = [
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
    # Harmony format
    "HARMONY_HEADER_RE",
    "HARMONY_END_RE",
    "extract_harmony_channels",
    "strip_harmony_control_tokens",
    # Granite format
    "detect_granite_toggle_format",
    "extract_granite_thinking",
    # SmolLM2 simulated format
    "detect_smollm_simulated_format",
    "extract_smollm_simulated",
    # Template system functions
    "get_prompt_template",
    "apply_prompt_template", 
    "is_template_enabled",
    "is_dual_mode_model",
    "get_dual_mode_preference",
    "get_model_capabilities",
    "should_show_thinking_toggle"
]
