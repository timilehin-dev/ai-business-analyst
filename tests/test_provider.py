"""
Tests for the model provider layer: litellm prefixing and credential plumbing.
"""
from agent.models.provider import ModelRouter, prefix_model_name


class TestPrefixModelName:
    def test_ollama_local(self):
        assert prefix_model_name("qwen2.5:7b", "ollama-local") == "ollama/qwen2.5:7b"

    def test_ollama_cloud(self):
        # Ollama Cloud exposes an OpenAI-compatible API at https://ollama.com/v1,
        # so it must route through litellm's openai provider (chat/completions),
        # NOT the native ollama provider (which would hit /v1/api/generate).
        assert prefix_model_name("qwen2.5:7b", "ollama-cloud") == "openai/qwen2.5:7b"

    def test_openai(self):
        assert prefix_model_name("gpt-4o", "openai") == "openai/gpt-4o"

    def test_anthropic(self):
        assert prefix_model_name("claude-sonnet-4", "anthropic") == "anthropic/claude-sonnet-4"

    def test_custom_endpoint(self):
        assert prefix_model_name("my-model", "custom") == "openai/my-model"

    def test_already_prefixed(self):
        assert prefix_model_name("ollama/llama3.1:8b", "ollama-local") == "ollama/llama3.1:8b"
        assert prefix_model_name("openai/gpt-4o", "openai") == "openai/gpt-4o"

    def test_unknown_provider_unchanged(self):
        assert prefix_model_name("some-model", "weird") == "some-model"


class TestModelRouterCredentials:
    def test_api_key_and_base_url_reach_providers(self):
        router = ModelRouter(
            {"reasoning": "ollama/qwen2.5:7b", "sql": "ollama/qwen2.5-coder:7b"},
            api_key="sk-test-123",
            api_base="http://host.docker.internal:11434",
        )
        for task_type in ("reasoning", "sql"):
            provider = router.get_provider(task_type)
            assert provider.api_key == "sk-test-123"
            assert provider.api_base == "http://host.docker.internal:11434"

    def test_no_credentials_defaults_to_none(self):
        router = ModelRouter({"reasoning": "ollama/llama3.1:8b"})
        provider = router.get_provider("reasoning")
        assert provider.api_key is None
        assert provider.api_base is None