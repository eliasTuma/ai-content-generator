"""Unit tests for provider implementations."""

import pytest
from ai_content_generator.providers import (
    OpenAIProvider,
    AnthropicProvider,
    get_provider,
    list_providers,
    register_provider,
)
from ai_content_generator.core.provider import BaseProvider
from ai_content_generator.core.exceptions import ProviderError, ModelNotFoundError


class TestProviderRegistry:
    """Tests for provider registry functions."""

    def test_list_providers(self):
        """Test listing available providers."""
        providers = list_providers()
        assert "openai" in providers
        assert "anthropic" in providers
        assert len(providers) >= 2

    def test_get_provider_openai(self):
        """Test getting OpenAI provider."""
        provider = get_provider("openai", api_key="test-key")
        assert isinstance(provider, OpenAIProvider)
        assert provider.provider_name == "openai"

    def test_get_provider_anthropic(self):
        """Test getting Anthropic provider."""
        provider = get_provider("anthropic", api_key="test-key")
        assert isinstance(provider, AnthropicProvider)
        assert provider.provider_name == "anthropic"

    def test_get_provider_case_insensitive(self):
        """Test provider name is case-insensitive."""
        provider1 = get_provider("OpenAI", api_key="test-key")
        provider2 = get_provider("OPENAI", api_key="test-key")
        assert isinstance(provider1, OpenAIProvider)
        assert isinstance(provider2, OpenAIProvider)

    def test_get_provider_not_found(self):
        """Test error when provider not found."""
        with pytest.raises(ProviderError) as exc_info:
            get_provider("nonexistent", api_key="test-key")
        assert "not found" in str(exc_info.value).lower()

    def test_get_provider_missing_api_key(self):
        """Test error when API key is missing."""
        with pytest.raises(ProviderError) as exc_info:
            get_provider("openai")
        assert "api key" in str(exc_info.value).lower()

    def test_register_custom_provider(self):
        """Test registering a custom provider."""
        class CustomProvider(BaseProvider):
            @property
            def provider_name(self) -> str:
                return "custom"

            @property
            def supported_models(self) -> list[str]:
                return ["model-1"]

            async def validate_connection(self) -> bool:
                return True

            async def list_models(self):
                return []

            async def get_model_info(self, model_name: str):
                return {}

            async def chat(self, messages, model, **kwargs):
                return {}

            async def count_tokens(self, text: str, model: str) -> int:
                return 0

            async def estimate_cost(self, prompt: str, model: str, max_tokens=None):
                return {}

            def calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
                return 0.0

        register_provider("custom", CustomProvider)
        provider = get_provider("custom", api_key="test-key")
        assert isinstance(provider, CustomProvider)


class TestOpenAIProvider:
    """Tests for OpenAI provider."""

    def test_initialization(self):
        """Test provider initialization."""
        provider = OpenAIProvider(api_key="test-key", timeout=30, max_retries=5)
        assert provider.api_key == "test-key"
        assert provider.timeout == 30
        assert provider.max_retries == 5
        assert provider.provider_name == "openai"

    def test_supported_models(self):
        """Test supported models list."""
        provider = OpenAIProvider(api_key="test-key")
        models = provider.supported_models
        # GPT-5 models
        assert "gpt-5" in models
        assert "gpt-5-mini" in models
        assert "gpt-5-nano" in models
        assert "gpt-5-pro" in models
        # GPT-4.1 models
        assert "gpt-4.1" in models
        assert "gpt-4.1-mini" in models
        assert "gpt-4.1-nano" in models
        # GPT-4o models
        assert "gpt-4o" in models
        assert "gpt-4o-mini" in models
        # o-series models
        assert "o1" in models
        assert "o1-mini" in models
        assert "o3" in models
        assert "o4-mini" in models

    @pytest.mark.asyncio
    async def test_list_models(self):
        """Test listing models with metadata."""
        provider = OpenAIProvider(api_key="test-key")
        models = await provider.list_models()

        assert len(models) > 0
        for model in models:
            assert "name" in model
            assert "context_window" in model
            assert "input_price_per_1m" in model
            assert "output_price_per_1m" in model
            assert "capabilities" in model

    @pytest.mark.asyncio
    async def test_get_model_info(self):
        """Test getting model information."""
        provider = OpenAIProvider(api_key="test-key")
        info = await provider.get_model_info("gpt-4o-mini")

        assert info["name"] == "gpt-4o-mini"
        assert info["context_window"] == 128000
        assert info["input_price_per_1m"] == 0.15
        assert info["output_price_per_1m"] == 0.6

    @pytest.mark.asyncio
    async def test_get_model_info_not_found(self):
        """Test error when model not found."""
        provider = OpenAIProvider(api_key="test-key")
        with pytest.raises(ModelNotFoundError):
            await provider.get_model_info("nonexistent-model")

    @pytest.mark.asyncio
    async def test_count_tokens(self):
        """Test token counting."""
        provider = OpenAIProvider(api_key="test-key")
        text = "Hello, world!"
        tokens = await provider.count_tokens(text, "gpt-4")
        assert tokens > 0
        assert isinstance(tokens, int)

    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        """Test cost estimation."""
        provider = OpenAIProvider(api_key="test-key")
        estimate = await provider.estimate_cost(
            prompt="Hello, world!",
            model="gpt-4o-mini",
            max_tokens=100
        )

        assert "input_cost" in estimate
        assert "output_cost" in estimate
        assert "total_cost" in estimate
        assert "input_tokens" in estimate
        assert estimate["total_cost"] > 0

    def test_calculate_cost(self):
        """Test cost calculation."""
        provider = OpenAIProvider(api_key="test-key")
        cost = provider.calculate_cost(
            input_tokens=1000,
            output_tokens=500,
            model="gpt-4o-mini"
        )
        # gpt-4o-mini: $0.15/1M input, $0.6/1M output
        # Expected: (1000/1M * 0.15) + (500/1M * 0.6) = 0.00015 + 0.0003 = 0.00045
        expected = (1000 / 1_000_000 * 0.15) + (500 / 1_000_000 * 0.6)
        assert abs(cost - expected) < 0.000001

    def test_calculate_cost_unknown_model(self):
        """Test cost calculation for unknown model returns 0."""
        provider = OpenAIProvider(api_key="test-key")
        cost = provider.calculate_cost(
            input_tokens=1000,
            output_tokens=500,
            model="unknown-model"
        )
        assert cost == 0.0


class TestAnthropicProvider:
    """Tests for Anthropic provider."""

    def test_initialization(self):
        """Test provider initialization."""
        provider = AnthropicProvider(api_key="test-key", timeout=30, max_retries=5)
        assert provider.api_key == "test-key"
        assert provider.timeout == 30
        assert provider.max_retries == 5
        assert provider.provider_name == "anthropic"

    def test_supported_models(self):
        """Test supported models list."""
        provider = AnthropicProvider(api_key="test-key")
        models = provider.supported_models
        assert "claude-sonnet-4-20250514" in models
        assert "claude-opus-4-20250514" in models
        assert "claude-haiku-4-20250514" in models
        # Only Claude 4.x models
        assert len(models) == 5

    @pytest.mark.asyncio
    async def test_list_models(self):
        """Test listing models with metadata."""
        provider = AnthropicProvider(api_key="test-key")
        models = await provider.list_models()

        assert len(models) > 0
        for model in models:
            assert "name" in model
            assert "context_window" in model
            assert "input_price_per_1m" in model
            assert "output_price_per_1m" in model
            assert "capabilities" in model

    @pytest.mark.asyncio
    async def test_get_model_info(self):
        """Test getting model information."""
        provider = AnthropicProvider(api_key="test-key")
        # Test with Claude 4.5 Haiku
        info = await provider.get_model_info("claude-haiku-4-20250514")

        assert info["name"] == "claude-haiku-4-20250514"
        assert info["context_window"] == 200000
        assert info["input_price_per_1m"] == 1.0
        assert info["output_price_per_1m"] == 5.0

    @pytest.mark.asyncio
    async def test_get_model_info_not_found(self):
        """Test error when model not found."""
        provider = AnthropicProvider(api_key="test-key")
        with pytest.raises(ModelNotFoundError):
            await provider.get_model_info("nonexistent-model")

    def test_calculate_cost(self):
        """Test cost calculation."""
        provider = AnthropicProvider(api_key="test-key")
        cost = provider.calculate_cost(
            input_tokens=1000,
            output_tokens=500,
            model="claude-haiku-4-20250514"
        )
        # claude-haiku-4.5: $1.0/1M input, $5.0/1M output
        # Expected: (1000/1M * 1.0) + (500/1M * 5.0) = 0.001 + 0.0025 = 0.0035
        expected = (1000 / 1_000_000 * 1.0) + (500 / 1_000_000 * 5.0)
        assert abs(cost - expected) < 0.000001

    def test_calculate_cost_unknown_model(self):
        """Test cost calculation for unknown model returns 0."""
        provider = AnthropicProvider(api_key="test-key")
        cost = provider.calculate_cost(
            input_tokens=1000,
            output_tokens=500,
            model="unknown-model"
        )
        assert cost == 0.0

