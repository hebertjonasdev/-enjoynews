"""LLM Client - supports Ollama (local/remote) and Hugging Face Inference API."""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .prompts import SYSTEM_PROMPT, VIDEO_SCRIPT_SYSTEM_PROMPT, build_user_prompt, build_video_script_prompt, validate_summary_json
from .models import PipelineConfig, RawArticle, Summary


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict[str, int] | None = None


class LLMClient(ABC):
    """Abstract LLM client."""

    @abstractmethod
    async def generate(self, system: str, user: str, temperature: float = 0.2, max_tokens: int = 1500) -> LLMResponse:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass

    async def summarize_article(self, article: RawArticle, config: PipelineConfig) -> Summary | None:
        """Summarize a single article."""
        user_prompt = build_user_prompt(
            article_text=article.raw_text or "",
            source_name=article.source_name,
            published_at=article.published_at.isoformat(),
            url=str(article.url),
            category_hint=article.category_hint.value if article.category_hint else None,
            source_tags=article.tags,
        )

        response = await self.generate(SYSTEM_PROMPT, user_prompt, temperature=0.2, max_tokens=1500)
        parsed = validate_summary_json(response.content)
        if not parsed:
            return None

        return Summary(
            headline=parsed["headline"],
            kicker=parsed["kicker"],
            lead=parsed["lead"],
            body=parsed["body"],
            context=parsed["context"],
            tags=parsed.get("tags", []),
            importance=parsed.get("importance", 3),
            confidence=parsed.get("confidence", 0.8),
            model_used=response.model,
        )

    async def generate_video_script(self, date: str, summaries: list[dict]) -> str | None:
        """Generate daily video script."""
        user_prompt = build_video_script_prompt(date, summaries)
        response = await self.generate(VIDEO_SCRIPT_SYSTEM_PROMPT, user_prompt, temperature=0.3, max_tokens=500)
        return response.content.strip() if response.content else None


class OllamaClient(LLMClient):
    """Ollama client (local or remote)."""

    def __init__(self, host: str, model: str = "llama3.1:8b", timeout: int = 120):
        self.host = host.rstrip("/")
        self.model = model
        self.client = httpx.AsyncClient(timeout=timeout)

    @retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(3))
    async def generate(self, system: str, user: str, temperature: float = 0.2, max_tokens: int = 1500) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
            },
        }
        resp = await self.client.post(f"{self.host}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()

        content = data.get("message", {}).get("content", "")
        return LLMResponse(content=content, model=self.model, usage=data.get("usage"))

    async def health_check(self) -> bool:
        try:
            resp = await self.client.get(f"{self.host}/api/tags")
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self):
        await self.client.aclose()


class HuggingFaceClient(LLMClient):
    """Hugging Face Inference API client (free tier)."""

    def __init__(self, api_token: str, model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct", timeout: int = 120):
        self.api_token = api_token
        self.model = model
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_token}"},
        )
        self.api_url = f"https://api-inference.huggingface.co/models/{model}"

    @retry(wait=wait_exponential(multiplier=1, min=5, max=60), stop=stop_after_attempt(3))
    async def generate(self, system: str, user: str, temperature: float = 0.2, max_tokens: int = 1500) -> LLMResponse:
        # HF Inference API uses chat template
        prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{system}<|eot_id|><|start_header_id|>user<|end_header_id|>\n{user}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "top_p": 0.9,
                "return_full_text": False,
            },
        }
        resp = await self.client.post(self.api_url, json=payload)
        resp.raise_for_status()
        data = resp.json()

        # HF returns list of dicts
        content = ""
        if isinstance(data, list) and data:
            content = data[0].get("generated_text", "")
        elif isinstance(data, dict):
            content = data.get("generated_text", "")

        return LLMResponse(content=content, model=self.model)

    async def health_check(self) -> bool:
        try:
            resp = await self.client.get(f"https://huggingface.co/api/models/{self.model}")
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self):
        await self.client.aclose()


def create_llm_client(config: PipelineConfig) -> LLMClient:
    """Factory to create appropriate LLM client based on config."""
    if config.hf_api_token:
        return HuggingFaceClient(config.hf_api_token, config.hf_model)
    return OllamaClient(config.ollama_host, config.ollama_model)