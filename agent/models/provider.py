"""
Model Provider Layer - Unified interface for all LLM providers.
Supports Ollama (local/cloud), OpenAI, Anthropic, and any OpenAI-compatible endpoint.
"""
from typing import List, Dict, Any, Optional, Protocol
from litellm import completion, embedding
import asyncio


class ModelProvider(Protocol):
    """Protocol defining the interface for all model providers."""
    
    async def complete(
        self, 
        messages: List[Dict[str, str]], 
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        **kwargs
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
    
    def __init__(self, model_name: str, api_key: Optional[str] = None, api_base: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key
        self.api_base = api_base
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        Generate completion using LiteLLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions for function calling
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        loop = asyncio.get_event_loop()
        
        def sync_completion():
            try:
                response = completion(
                    model=self.model_name,
                    messages=messages,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    api_key=self.api_key,
                    api_base=self.api_base,
                    **kwargs
                )
                
                # Extract content from response
                if hasattr(response, 'choices') and len(response.choices) > 0:
                    return response.choices[0].message.content or ""
                return ""
                
            except Exception as e:
                raise Exception(f"Model completion failed: {str(e)}")
        
        return await loop.run_in_executor(None, sync_completion)
    
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of strings to embed
            
        Returns:
            List of embedding vectors
        """
        loop = asyncio.get_event_loop()
        
        def sync_embedding():
            try:
                # Use the configured embedding model
                response = embedding(
                    model=self.model_name.replace('completion', 'embedding') 
                        if 'completion' in self.model_name else self.model_name,
                    input=texts,
                    api_key=self.api_key,
                    api_base=self.api_base
                )
                
                # Extract embeddings from response
                if hasattr(response, 'data'):
                    return [item['embedding'] for item in response.data]
                return []
                
            except Exception as e:
                print(f"Embedding failed: {e}")
                # Return zero vectors as fallback
                return [[0.0] * 768 for _ in texts]
        
        return await loop.run_in_executor(None, sync_embedding)


def prefix_model_name(model_name: str, provider: str) -> str:
    """
    Add the litellm provider prefix if missing.
    e.g. 'qwen2.5:7b' + 'ollama-local' -> 'ollama/qwen2.5:7b'.
    LiteLLM requires the prefix to route to the right provider.
    """
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
    ):
        """
        Initialize router with model configuration.

        Args:
            config: Dict mapping task types to model names
                   e.g., {'reasoning': 'claude-sonnet-4', 'sql': 'ollama/qwen2.5'}
            api_key: Provider API key (None for local Ollama)
            api_base: Custom base URL (e.g. http://localhost:11434)
        """
        self.providers = {}
        for task_type, model_name in config.items():
            self.providers[task_type] = LiteLLMProvider(
                model_name, api_key=api_key, api_base=api_base
            )
    
    def get_provider(self, task_type: str = 'reasoning') -> LiteLLMProvider:
        """Get provider for specific task type."""
        if task_type not in self.providers:
            # Fallback to reasoning model
            return self.providers.get('reasoning', list(self.providers.values())[0])
        return self.providers[task_type]
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        task_type: str = 'reasoning',
        **kwargs
    ) -> str:
        """Route completion request to appropriate model."""
        provider = self.get_provider(task_type)
        return await provider.complete(messages, **kwargs)
    
    async def embed(self, texts: List[str], task_type: str = 'embedding') -> List[List[float]]:
        """Route embedding request to appropriate model."""
        provider = self.get_provider(task_type)
        return await provider.embed(texts)


def create_model_router_from_config(config_dict: Dict[str, str]) -> ModelRouter:
    """Factory function to create model router from configuration."""
    return ModelRouter(config_dict)
