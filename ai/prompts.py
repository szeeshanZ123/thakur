"""
AI Prompt templates and builders for Hackathon tasks.
"""

from typing import Optional, Dict, Any


DEFAULT_SYSTEM_PROMPT = """You are an intelligent, high-performance AI assistant built for an AI/ML hackathon project.
Provide concise, accurate, and structured responses. Where applicable, format responses clearly with markdown or JSON."""


def format_hackathon_prompt(
    task_description: str,
    user_input: str,
    context: Optional[str] = None,
    output_format: str = "text"
) -> str:
    """
    Format a standard hackathon task prompt.
    """
    prompt_parts = [
        f"### Task: {task_description}",
        f"### Input:\n{user_input}"
    ]

    if context:
        prompt_parts.append(f"### Context / Reference Data:\n{context}")

    if output_format.lower() == "json":
        prompt_parts.append(
            "### Format Requirement:\n"
            "Return ONLY a valid JSON object matching the problem requirements. "
            "Do not include markdown backticks or explanations outside the JSON."
        )
    else:
        prompt_parts.append("### Format Requirement:\nProvide a clear, structured response.")

    return "\n\n".join(prompt_parts)


def build_analysis_prompt(data_summary: str, question: str) -> str:
    """
    Prompt template for analyzing tabular data summaries or text datasets.
    """
    return (
        f"### Data Summary:\n{data_summary}\n\n"
        f"### Question / Analysis Goal:\n{question}\n\n"
        "### Instructions:\n"
        "1. Highlight key patterns, anomalies, and insights.\n"
        "2. Provide actionable recommendations based on the findings."
    )
