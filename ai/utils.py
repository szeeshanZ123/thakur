"""
Helper utilities for AI and LLM response handling.
"""

import json
import re
from typing import Any, Dict, Optional


def extract_json_from_response(text: str) -> Optional[Dict[str, Any]]:
    """
    Safely extract and parse a JSON object from raw LLM text response.
    Handles responses wrapped in markdown codeblocks (```json ... ```) or plain JSON.
    """
    if not text:
        return None

    # Check for markdown code blocks
    json_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if json_block_match:
        content = json_block_match.group(1).strip()
    else:
        # Look for the outer-most JSON curly brackets or array brackets
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            content = text[first_brace:last_brace + 1]
        else:
            content = text.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def estimate_tokens(text: str) -> int:
    """
    Rough heuristic token estimation (~4 chars per token for English).
    Useful for hackathon rate-limiting checks before making API calls.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def clean_text(text: str) -> str:
    """
    Basic text cleaner: strips trailing/leading whitespaces and normalizes line breaks.
    """
    if not text:
        return ""
    return re.sub(r"\r\n|\r", "\n", text).strip()
