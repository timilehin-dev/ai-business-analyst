"""
Model Provider Layer - Unified interface for all LLM providers.
Supports Ollama (local/cloud), OpenAI, Anthropic, and any OpenAI-compatible endpoint.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Protocol

from litellm import completion, embedding

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_EMBEDDING_DIM = 768


class ModelUnavailableError(RuntimeError):
    """Raised when a model call fails and no fallback succeeds."""


class ModelProvider(Protocol):
    """Protocol defining the interface for all model providers."""

    async def complete(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Generate completion for given messages."""
        ...

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        ...


class LiteLLMProvider:
    """
    Universal model provider using LiteLLM.
    Supports 20+ providers with one interface.
    """

    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.model_name = model_name
        self.api_key = api_key
        self.api_base = api_base
        self.timeout = timeout

    async def complete(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> str:
        """
        Generate completion using LiteLLM.

        Raises:
            ModelUnavailableError: the endpoint failed or timed out. Callers
                decide whether to fall back; failing loudly beats returning
                an empty string that silently corrupts an analysis.
        """

        def sync_completion() -> str:
            response = completion(
                model=self.model_name,
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=self.api_key,
                api_base=self.api_base,
                timeout=self.timeout,
                **kwargs,
            )
            choices = getattr(response, "choices", None)
            if choices:
                return choices[0].message.content or ""
            return ""

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(sync_completion), timeout=self.timeout + 10
            )
        except asyncio.TimeoutError as e:
            raise ModelUnavailableError(
                f"Model '{self.model_name}' timed out after {self.timeout}s"
            ) from e
        except Exception as e:
            raise ModelUnavailableError(
                f"Model '{self.model_name}' failed: {e}"
            ) from e

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Returns zero vectors on failure so callers relying on embeddings
        degrade rather than crash; retrieval elsewhere is lexical and does
        not depend on this.
        """

        def sync_embedding() -> List[List[float]]:
            response = embedding(
                model=self.model_name,
                input=texts,
                api_key=self.api_key,
                api_base=self.api_base,
                timeout=self.timeout,
            )
            data = getattr(response, "data", None)
            if data:
                return [item["embedding"] for item in data]
            return []

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(sync_embedding), timeout=self.timeout + 10
            )
        except Exception as e:
            logger.warning("Embedding failed for %s: %s", self.model_name, e)
            return [[0.0] * DEFAULT_EMBEDDING_DIM for _ in texts]


def prefix_model_name(model_name: str, provider: str) -> str:
    """
    Add the litellm provider prefix if missing.
    e.g. 'qwen2.5:7b' + 'ollama-local' -> 'ollama/qwen2.5:7b'.
    LiteLLM requires the prefix to route to the right provider.
    """
    if not model_name:
        return model_name
    if "/" in model_name:
        return model_name
    prefixes = {
        "ollama-local": "ollama",  # native /api/chat + /api/generate endpoints
        # Ollama Cloud exposes an OpenAI-compatible API at https://ollama.com/v1,
        # so it must route through litellm's openai provider (chat/completions),
        # NOT the native ollama provider (which would hit /v1/api/generate).
        "ollama-cloud": "openai",
        "openai": "openai",
        "anthropic": "anthropic",
        "custom": "openai",  # custom OpenAI-compatible endpoints
    }
    prefix = prefixes.get(provider)
    return f"{prefix}/{model_name}" if prefix else model_name


class ModelRouter:
    """
    Routes tasks to appropriate models based on configuration.
    Implements task-based model selection for cost/privacy optimization.
    """

    def __init__(
        self,
        config: Dict[str, str],
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ):
        """
        Initialize router with model configuration.

        Args:
            config: Dict mapping task types to model names
                   e.g., {'reasoning': 'claude-sonnet-4', 'sql': 'ollama/qwen2.5'}
            api_key: Provider API key (None for local Ollama)
            api_base: Custom base URL (e.g. http://localhost:11434)
            timeout: Per-request timeout in seconds
        """
        if not config:
            raise ValueError("ModelRouter requires at least one task -> model mapping")

        self.providers: Dict[str, LiteLLMProvider] = {
            task_type: LiteLLMProvider(
                model_name, api_key=api_key, api_base=api_base, timeout=timeout
            )
            for task_type, model_name in config.items()
            if model_name
        }
        if not self.providers:
            raise ValueError("ModelRouter requires at least one non-empty model name")

    def get_provider(self, task_type: str = "reasoning") -> LiteLLMProvider:
        """Get provider for a task, falling back to reasoning then any configured model."""
        provider = self.providers.get(task_type)
        if provider is not None:
            return provider
        provider = self.providers.get("reasoning")
        if provider is not None:
            return provider
        return next(iter(self.providers.values()))

    async def complete(
        self,
        messages: List[Dict[str, str]],
        task_type: str = "reasoning",
        **kwargs,
    ) -> str:
        """
        Route a completion to the task's model, retrying once on the
        configured fallback model when the primary is unreachable.
        """
        provider = self.get_provider(task_type)
        try:
            return await provider.complete(messages, **kwargs)
        except ModelUnavailableError as primary_error:
            fallback = self.providers.get("fallback")
            if fallback is None or fallback is provider:
                raise
            logger.warning(
                "Model '%s' unavailable (%s); retrying on fallback '%s'",
                provider.model_name,
                primary_error,
                fallback.model_name,
            )
            return await fallback.complete(messages, **kwargs)

    async def embed(
        self, texts: List[str], task_type: str = "embedding"
    ) -> List[List[float]]:
        """Route embedding request to appropriate model."""
        provider = self.get_provider(task_type)
        return await provider.embed(texts)


def create_model_router_from_config(config_dict: Dict[str, str]) -> ModelRouter:
    """Factory function to create model router from configuration."""
    return ModelRouter(config_dict)
