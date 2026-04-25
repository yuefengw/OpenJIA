"""LLM backend adapters for OpenJIA role agents."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
from typing import Any, Protocol

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()


class LLMBackend(Protocol):
    """Minimal backend contract used by role agents."""

    def generate_json(self, *, instructions: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate structured JSON matching a schema."""


class LLMConfigurationError(RuntimeError):
    """Raised when an LLM backend is requested but not configured."""


@dataclass
class OpenAIResponsesBackend:
    """OpenAI Responses API backend."""

    model: str = "gpt-4.1"
    api_key_env: str = "OPENAI_API_KEY"

    def generate_json(self, *, instructions: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate JSON through the OpenAI Responses API."""
        if not os.getenv(self.api_key_env):
            raise LLMConfigurationError(
                f"{self.api_key_env} is not set; cannot use OpenAI LLM backend."
            )

        try:
            from openai import OpenAI
        except ImportError as error:
            raise LLMConfigurationError(
                "The 'openai' package is not installed. Install with `pip install -e .[llm]`."
            ) from error

        client = OpenAI()
        try:
            response = client.responses.create(
                model=self.model,
                instructions=instructions,
                input=prompt,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": schema.get("title", "openjia_schema"),
                        "schema": schema,
                        "strict": False,
                    }
                },
            )
        except Exception as error:
            raise LLMConfigurationError(f"OpenAI request failed: {error}") from error
        return _parse_response_json(response)


@dataclass
class OpenAICompatibleChatBackend:
    """OpenAI-compatible Chat Completions backend."""

    model: str
    base_url: str
    api_key_env: str = "OPENAI_API_KEY"
    provider_name: str = "openai-compatible"
    use_response_format: bool = False

    def generate_json(self, *, instructions: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate JSON through an OpenAI-compatible chat completions endpoint."""
        if not os.getenv(self.api_key_env):
            raise LLMConfigurationError(
                f"{self.api_key_env} is not set; cannot use {self.provider_name} backend."
            )

        try:
            from openai import OpenAI
        except ImportError as error:
            raise LLMConfigurationError(
                "The 'openai' package is not installed. Install with `pip install -e .[llm]`."
            ) from error

        client = OpenAI(api_key=os.getenv(self.api_key_env), base_url=self.base_url)
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": _json_prompt(prompt, schema)},
            ],
        }
        if self.use_response_format:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = client.chat.completions.create(**kwargs)
        except Exception as error:
            raise LLMConfigurationError(
                f"{self.provider_name} request failed: {error}"
            ) from error
        content = response.choices[0].message.content
        if not content:
            raise ValueError(f"{self.provider_name} response did not contain content.")
        return _loads_json_from_text(content)


def make_llm_backend(name: str | None, model: str | None = None) -> LLMBackend | None:
    """Create an LLM backend by name."""
    backend = (name or os.getenv("OPENJIA_LLM_BACKEND") or "deterministic").lower()
    selected_model = model or os.getenv("OPENJIA_LLM_MODEL")

    if backend in {"", "deterministic", "none"}:
        return None
    if backend == "openai":
        return OpenAIResponsesBackend(model=selected_model or "gpt-4.1")
    if backend == "minimax":
        return OpenAICompatibleChatBackend(
            model=selected_model or "MiniMax-M2.7",
            base_url=os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/v1"),
            api_key_env="MINIMAX_API_KEY",
            provider_name="minimax",
            use_response_format=False,
        )
    if backend in {"openai-compatible", "compatible"}:
        base_url = os.getenv("OPENAI_COMPATIBLE_BASE_URL")
        if not base_url:
            raise LLMConfigurationError(
                "OPENAI_COMPATIBLE_BASE_URL is not set for openai-compatible backend."
            )
        return OpenAICompatibleChatBackend(
            model=selected_model or "gpt-4.1",
            base_url=base_url,
            api_key_env=os.getenv("OPENAI_COMPATIBLE_API_KEY_ENV", "OPENAI_API_KEY"),
            use_response_format=False,
        )
    raise LLMConfigurationError(f"Unsupported LLM backend: {backend}")


def _parse_response_json(response: Any) -> dict[str, Any]:
    """Extract JSON from an OpenAI response object."""
    text = getattr(response, "output_text", None)
    if not text:
        chunks: list[str] = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                if getattr(content, "type", None) == "output_text":
                    chunks.append(getattr(content, "text", ""))
        text = "\n".join(chunks)

    if not text:
        raise ValueError("LLM response did not contain output text.")

    return _loads_json_from_text(text)


def _json_prompt(prompt: str, schema: dict[str, Any]) -> str:
    """Create a JSON-only prompt for chat-completions compatible providers."""
    return "\n\n".join([
        prompt,
        "Return one valid JSON object only. Do not wrap it in markdown.",
        "The JSON object must conform to this JSON Schema:",
        json.dumps(schema, ensure_ascii=False),
    ])


def _loads_json_from_text(text: str) -> dict[str, Any]:
    """Load a JSON object from model text, tolerating reasoning wrappers."""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    last_object: dict[str, Any] | None = None
    for index, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            last_object = parsed

    if last_object is None:
        raise ValueError("LLM response did not contain a JSON object.")
    return last_object
