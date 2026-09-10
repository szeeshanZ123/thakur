"""
Modular LLM Client wrapper for Hackathons.
Supports external APIs (OpenAI, Gemini, custom endpoints) with instant fallback/mock mode.
"""

import os
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from ai.prompts import DEFAULT_SYSTEM_PROMPT

load_dotenv()


class LLMClient:
    def __init__(
        self,
        provider: str = "auto",
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.openai_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.gemini_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
        self.provider = provider.lower()

        if self.provider == "auto":
            if self.openai_key:
                self.provider = "openai"
            elif self.gemini_key:
                self.provider = "gemini"
            else:
                self.provider = "mock"

    def generate(
        self,
        prompt: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Generate a text response from the configured LLM provider.
        Returns a dict: {"success": bool, "content": str, "provider": str, "model": str, "error": Optional[str]}
        """
        if self.provider == "mock":
            return self._mock_generate(prompt)

        if self.provider == "openai":
            return self._openai_generate(prompt, system_prompt, temperature, max_tokens)

        if self.provider == "gemini":
            return self._gemini_generate(prompt, system_prompt, temperature, max_tokens)

        return self._mock_generate(prompt)

    def _mock_generate(self, prompt: str) -> Dict[str, Any]:
        """Fallback mock generator for hackathon scaffolding and testing."""
        return {
            "success": True,
            "content": (
                f"[AI Starter Mock Response]\n\n"
                f"Received Prompt: \"{prompt[:120]}{'...' if len(prompt) > 120 else ''}\"\n\n"
                f"• Analysis: The problem input has been processed successfully.\n"
                f"• Recommendation: Configure OPENAI_API_KEY or GEMINI_API_KEY in .env to connect live LLM APIs."
            ),
            "provider": "mock",
            "model": "starter-mock-v1",
            "error": None
        }

    def _openai_generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        if not self.openai_key:
            return self._mock_generate(prompt)

        try:
            headers = {
                "Authorization": f"Bearer {self.openai_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model if self.model != "mock-model" else "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return {
                    "success": True,
                    "content": content,
                    "provider": "openai",
                    "model": payload["model"],
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "content": "",
                    "provider": "openai",
                    "model": payload["model"],
                    "error": f"OpenAI API Error {resp.status_code}: {resp.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "content": "",
                "provider": "openai",
                "model": self.model,
                "error": str(e)
            }

    def _gemini_generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        if not self.gemini_key:
            return self._mock_generate(prompt)

        try:
            model_name = self.model if self.model != "mock-model" else "gemini-1.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.gemini_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"System Instructions: {system_prompt}\n\nUser Request: {prompt}"}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens
                }
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                content = data["candidates"][0]["content"]["parts"][0]["text"]
                return {
                    "success": True,
                    "content": content,
                    "provider": "gemini",
                    "model": model_name,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "content": "",
                    "provider": "gemini",
                    "model": model_name,
                    "error": f"Gemini API Error {resp.status_code}: {resp.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "content": "",
                "provider": "gemini",
                "model": self.model,
                "error": str(e)
            }


# Singleton instance for quick usage
llm_client = LLMClient()
