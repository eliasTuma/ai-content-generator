"""Anthropic provider implementation."""

from typing import Any, Optional

from anthropic import AsyncAnthropic, APIError, RateLimitError as AnthropicRateLimitError, APIConnectionError

from ..core.provider import BaseProvider
from ..core.exceptions import (
    ProviderError,
    RateLimitError,
    ConnectionError,
    ModelNotFoundError,
)


# Model pricing data (per 1M tokens in USD) - as of Jan 2025
# Source: https://docs.claude.com/en/docs/about-claude/pricing
MODEL_PRICING = {
    # Claude 4.x models
    "claude-opus-4-20250514": {
        "input": 15.0,
        "output": 75.0,
        "context_window": 200000,
        "description": "Claude Opus 4.1 - most powerful model for complex tasks",
    },
    "claude-opus-4-20250124": {
        "input": 15.0,
        "output": 75.0,
        "context_window": 200000,
        "description": "Claude Opus 4 - powerful model for complex tasks",
    },
    "claude-sonnet-4-20250514": {
        "input": 3.0,
        "output": 15.0,
        "context_window": 200000,
        "description": "Claude Sonnet 4.5 - latest intelligent model",
    },
    "claude-sonnet-4-20250124": {
        "input": 3.0,
        "output": 15.0,
        "context_window": 200000,
        "description": "Claude Sonnet 4 - intelligent model",
    },
    "claude-haiku-4-20250514": {
        "input": 1.0,
        "output": 5.0,
        "context_window": 200000,
        "description": "Claude Haiku 4.5 - fast and efficient model",
    },
}


class AnthropicProvider(BaseProvider):
    """
    Anthropic provider implementation.

    Supports Claude 4.x models (Opus 4.1, Opus 4, Sonnet 4.5, Sonnet 4, Haiku 4.5).

    Example:
        ```python
        provider = AnthropicProvider(api_key="sk-ant-...")
        is_valid = await provider.validate_connection()

        messages = [
            {"role": "user", "content": "Hello!"}
        ]
        response = await provider.chat(messages, model="claude-sonnet-4-20250514")
        print(response["content"])
        ```
    """

    def __init__(
        self,
        api_key: str,
        timeout: int = 60,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> None:
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            **kwargs: Additional Anthropic client configuration
        """
        super().__init__(api_key, timeout, max_retries, **kwargs)
        self.client = AsyncAnthropic(
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )

    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "anthropic"

    @property
    def supported_models(self) -> list[str]:
        """Get list of supported model names."""
        return list(MODEL_PRICING.keys())

    @staticmethod
    def get_available_models() -> list[dict[str, Any]]:
        """
        Get all available models without needing to instantiate the provider.
        
        Returns:
            List of dictionaries with model information (name, description, pricing, etc.)
            
        Example:
            ```python
            # No provider instance needed
            models = AnthropicProvider.get_available_models()
            for model in models:
                print(f"{model['name']}: {model['description']}")
            ```
        """
        models = []
        for model_name, pricing in MODEL_PRICING.items():
            models.append({
                "name": model_name,
                "context_window": pricing["context_window"],
                "input_price_per_1m": pricing["input"],
                "output_price_per_1m": pricing["output"],
                "capabilities": ["chat", "vision"],
                "description": pricing["description"],
            })
        return models

    @staticmethod
    def get_model_names() -> list[str]:
        """
        Get just the model names without needing to instantiate the provider.
        
        Returns:
            List of model name strings
            
        Example:
            ```python
            models = AnthropicProvider.get_model_names()
            print(models)  # ['claude-opus-4-20250514', ...]
            ```
        """
        return list(MODEL_PRICING.keys())

    async def validate_connection(self) -> bool:
        """
        Validate the connection to Anthropic.

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Make a minimal request to test the connection
            # Anthropic doesn't have a models.list endpoint, so we'll make a small message request
            await self.client.messages.create(
                model="claude-haiku-4-20250514",  # Use cheapest Claude 4 model for validation
                max_tokens=1,
                messages=[{"role": "user", "content": "Hi"}],
            )
            self._is_connected = True
            return True
        except Exception:
            self._is_connected = False
            return False

    async def list_models(self) -> list[dict[str, Any]]:
        """
        Get list of available models with their metadata.

        Returns:
            List of dictionaries containing model information
        """
        models = []
        for model_name, pricing in MODEL_PRICING.items():
            models.append({
                "name": model_name,
                "context_window": pricing["context_window"],
                "input_price_per_1m": pricing["input"],
                "output_price_per_1m": pricing["output"],
                "capabilities": ["chat", "vision"],
                "description": pricing["description"],
            })
        return models

    async def get_model_info(self, model_name: str) -> dict[str, Any]:
        """
        Get detailed information about a specific model.

        Args:
            model_name: Name of the model

        Returns:
            Dictionary containing model information

        Raises:
            ModelNotFoundError: If model is not found
        """
        if model_name not in MODEL_PRICING:
            raise ModelNotFoundError(
                model=model_name,
                provider=self.provider_name,
                context={"available_models": self.supported_models},
            )

        pricing = MODEL_PRICING[model_name]
        return {
            "name": model_name,
            "context_window": pricing["context_window"],
            "input_price_per_1m": pricing["input"],
            "output_price_per_1m": pricing["output"],
            "capabilities": ["chat", "vision"],
            "description": pricing["description"],
        }

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Send a chat completion request to Anthropic.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model identifier to use
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate (required for Anthropic)
            **kwargs: Additional Anthropic parameters

        Returns:
            Dictionary containing response data

        Raises:
            ProviderError: If the request fails
            RateLimitError: If rate limit is exceeded
            ModelNotFoundError: If model is not found
        """
        if model not in MODEL_PRICING:
            raise ModelNotFoundError(
                model=model,
                provider=self.provider_name,
                context={"available_models": self.supported_models},
            )

        # Default max_tokens if not provided (Anthropic requires this)
        if max_tokens is None:
            max_tokens = 4096

        # Extract system message if present
        system_message = None
        filtered_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                filtered_messages.append(msg)

        try:
            # Build request parameters
            request_params: dict[str, Any] = {
                "model": model,
                "messages": filtered_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs,
            }

            # Add system message if present
            if system_message:
                request_params["system"] = system_message

            response = await self.client.messages.create(**request_params)

            # Extract response data
            content = ""
            if response.content:
                # Anthropic returns a list of content blocks
                content = "".join(
                    block.text for block in response.content if hasattr(block, "text")
                )

            # Get token usage
            input_tokens = response.usage.input_tokens if response.usage else 0
            output_tokens = response.usage.output_tokens if response.usage else 0

            return {
                "content": content,
                "model": response.model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "finish_reason": response.stop_reason,
                "raw_response": response.model_dump(),
            }

        except AnthropicRateLimitError as e:
            raise RateLimitError(
                message="Anthropic rate limit exceeded",
                provider=self.provider_name,
                context={"error": str(e)},
            )
        except APIConnectionError as e:
            raise ConnectionError(
                message="Failed to connect to Anthropic",
                provider=self.provider_name,
                context={"error": str(e)},
            )
        except APIError as e:
            raise ProviderError(
                message=f"Anthropic API error: {str(e)}",
                provider=self.provider_name,
                context={"error": str(e), "status_code": getattr(e, "status_code", None)},
            )
        except Exception as e:
            raise ProviderError(
                message=f"Unexpected error: {str(e)}",
                provider=self.provider_name,
                context={"error": str(e), "error_type": type(e).__name__},
            )

    async def count_tokens(self, text: str, model: str) -> int:
        """
        Count the number of tokens in a text for a specific model.

        Args:
            text: Text to count tokens for
            model: Model identifier

        Returns:
            Number of tokens

        Note:
            Anthropic uses the `count_tokens` API method for accurate token counting.
        """
        try:
            # Use Anthropic's token counting API
            result = await self.client.messages.count_tokens(
                model=model,
                messages=[{"role": "user", "content": text}],
            )
            # Subtract 3 tokens for the message wrapper overhead
            return max(0, result.input_tokens - 3)
        except Exception:
            # Fallback: rough estimation (1 token ≈ 4 characters)
            return len(text) // 4

    async def estimate_cost(
        self, prompt: str, model: str, max_tokens: Optional[int] = None
    ) -> dict[str, float]:
        """
        Estimate the cost of a request before making it.

        Args:
            prompt: Input prompt text
            model: Model identifier
            max_tokens: Expected maximum output tokens

        Returns:
            Dictionary containing cost estimates
        """
        if model not in MODEL_PRICING:
            raise ModelNotFoundError(
                model=model,
                provider=self.provider_name,
                context={"available_models": self.supported_models},
            )

        pricing = MODEL_PRICING[model]
        input_tokens = await self.count_tokens(prompt, model)

        # Calculate input cost
        input_cost = (input_tokens / 1_000_000) * pricing["input"]

        # Calculate output cost if max_tokens provided
        output_cost = 0.0
        if max_tokens:
            output_cost = (max_tokens / 1_000_000) * pricing["output"]

        return {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": input_cost + output_cost,
            "input_tokens": input_tokens,
        }

    def calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """
        Calculate the actual cost of a completed request.

        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated
            model: Model identifier

        Returns:
            Total cost in USD
        """
        if model not in MODEL_PRICING:
            # Return 0 for unknown models rather than raising
            return 0.0

        pricing = MODEL_PRICING[model]
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit - cleanup resources."""
        await self.client.close()

