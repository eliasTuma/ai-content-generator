"""OpenAI provider implementation."""

import asyncio
from typing import Any, Optional

import tiktoken
from openai import AsyncOpenAI, APIError, RateLimitError as OpenAIRateLimitError, APIConnectionError

from ..core.provider import BaseProvider
from ..core.exceptions import (
    ProviderError,
    RateLimitError,
    ConnectionError,
    ModelNotFoundError,
    TokenLimitError,
)


# Model pricing data (per 1M tokens in USD)
MODEL_PRICING = {
    # GPT-5 models
    "gpt-5": {
        "input": 1.25,
        "output": 10.0,
        "context_window": 400000,
        "description": "Flagship model for coding, agents, and complex tasks",
        "notes": "Text + vision; supports reasoning controls",
    },
    "gpt-5-mini": {
        "input": 0.25,
        "output": 2.0,
        "context_window": 400000,
        "description": "Faster, cheaper GPT-5 for well-defined tasks",
        "notes": "Great price/latency tradeoff",
    },
    "gpt-5-nano": {
        "input": 0.05,
        "output": 0.4,
        "context_window": 400000,
        "description": "Smallest and cheapest GPT-5; ideal for summarization/classification",
        "notes": "High-throughput tasks; low latency",
    },
    "gpt-5-pro": {
        "input": 15.0,
        "output": 120.0,
        "context_window": 400000,
        "description": "The smartest and most precise model",
        "notes": "Reasoning model with extended capabilities",
    },
    "gpt-5-chat-latest": {
        "input": 1.25,
        "output": 10.0,
        "context_window": 128000,
        "description": "Continuously updated chat-tuned GPT-5",
        "notes": "Use when you want the newest chat behavior",
    },
    # GPT-4.1 models
    "gpt-4.1": {
        "context_window": 1047576,
        "description": "High-accuracy GPT-4 family model with very long context",
        "notes": "Text + image; 1M-token context",
    },
    "gpt-4.1-mini": {
        "context_window": 200000,
        "description": "Cost-efficient GPT-4.1 family model",
        "notes": "Good default for budget workloads",
    },
    # GPT-4o models
    "gpt-4o": {
        "context_window": 128000,
        "description": "Multimodal GPT-4o optimized for quality + speed",
        "notes": "Text + vision",
    },
    "gpt-4o-mini": {
        "context_window": 128000,
        "description": "Fast, affordable small multimodal model",
        "notes": "Great for focused tasks",
    },
    # o-series reasoning models
    "o4-mini": {
        "description": "Fast, cost-efficient reasoning model (pre-GPT-5 series)",
        "notes": "Superseded by GPT-5 mini for many cases",
    },
    "o3": {
        "description": "High-end reasoning model for complex multi-step problems",
        "notes": "Strong tool use and planning",
    },
    "o3-mini": {
        "description": "Cheaper o-series reasoning model",
        "notes": "Good cost/perf for reasoning",
    },
    # Specialized models
    "gpt-image-1": {
        "description": "Image generation model",
        "notes": "Text + image inputs; image outputs",
    },
    "gpt-audio-mini": {
        "description": "Audio understanding/generation tasks",
        "notes": "Audio-specialized model",
    },
    # Open-weight models
    "gpt-oss-120b": {
        "description": "Open-weight, deploy-anywhere model (OpenAI OSS family)",
        "notes": "For local or specialized use-cases",
    },
    "gpt-oss-20b": {
        "description": "Medium open-weight model for low-latency or local use",
        "notes": "Smaller, faster OSS variant",
    },
}


class OpenAIProvider(BaseProvider):
    """
    OpenAI provider implementation.

    Supports GPT-5, GPT-4.1, GPT-4o, o-series (o1, o3, o4), and specialized models.

    Example:
        ```python
        provider = OpenAIProvider(api_key="sk-...")
        is_valid = await provider.validate_connection()

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ]
        response = await provider.chat(messages, model="gpt-5-nano")
        print(response["content"])
        ```
    """

    def __init__(
        self,
        api_key: str,
        timeout: int = 180,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> None:
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            timeout: Request timeout in seconds (default 180s for long generations)
            max_retries: Maximum number of retry attempts
            **kwargs: Additional OpenAI client configuration
        """
        super().__init__(api_key, timeout, max_retries, **kwargs)
        self.client = AsyncOpenAI(
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )
        self._tokenizer_cache: dict[str, Any] = {}

    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "openai"

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
            models = OpenAIProvider.get_available_models()
            for model in models:
                print(f"{model['name']}: {model['description']}")
            ```
        """
        models = []
        for model_name, pricing in MODEL_PRICING.items():
            model_info = {
                "name": model_name,
                "description": pricing["description"],
                "capabilities": ["chat", "completion"],
            }
            if "context_window" in pricing:
                model_info["context_window"] = pricing["context_window"]
            if "input" in pricing:
                model_info["input_price_per_1m"] = pricing["input"]
            if "output" in pricing:
                model_info["output_price_per_1m"] = pricing["output"]
            if "notes" in pricing:
                model_info["notes"] = pricing["notes"]
            models.append(model_info)
        return models

    @staticmethod
    def get_model_names() -> list[str]:
        """
        Get just the model names without needing to instantiate the provider.
        
        Returns:
            List of model name strings
            
        Example:
            ```python
            models = OpenAIProvider.get_model_names()
            print(models)  # ['gpt-5', 'gpt-5-mini', ...]
            ```
        """
        return list(MODEL_PRICING.keys())

    async def validate_connection(self) -> bool:
        """
        Validate the connection to OpenAI.

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Make a minimal request to test the connection
            models = await self.client.models.list()
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
            model_info = {
                "name": model_name,
                "description": pricing["description"],
                "capabilities": ["chat", "completion"],
            }
            if "context_window" in pricing:
                model_info["context_window"] = pricing["context_window"]
            if "input" in pricing:
                model_info["input_price_per_1m"] = pricing["input"]
            if "output" in pricing:
                model_info["output_price_per_1m"] = pricing["output"]
            if "notes" in pricing:
                model_info["notes"] = pricing["notes"]
            models.append(model_info)
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
        model_info = {
            "name": model_name,
            "description": pricing["description"],
            "capabilities": ["chat", "completion"],
        }
        if "context_window" in pricing:
            model_info["context_window"] = pricing["context_window"]
        if "input" in pricing:
            model_info["input_price_per_1m"] = pricing["input"]
        if "output" in pricing:
            model_info["output_price_per_1m"] = pricing["output"]
        if "notes" in pricing:
            model_info["notes"] = pricing["notes"]
        return model_info

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Send a chat completion request to OpenAI.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model identifier to use
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional OpenAI parameters

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

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            # Extract response data
            choice = response.choices[0]
            content = choice.message.content or ""
            finish_reason = choice.finish_reason

            # Get token usage
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

            return {
                "content": content,
                "model": response.model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "finish_reason": finish_reason,
                "raw_response": response.model_dump(),
            }

        except OpenAIRateLimitError as e:
            raise RateLimitError(
                message="OpenAI rate limit exceeded",
                provider=self.provider_name,
                context={"error": str(e)},
            )
        except APIConnectionError as e:
            raise ConnectionError(
                message="Failed to connect to OpenAI",
                provider=self.provider_name,
                context={"error": str(e)},
            )
        except APIError as e:
            raise ProviderError(
                message=f"OpenAI API error: {str(e)}",
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
            model: Model identifier (tokenization may vary by model)

        Returns:
            Number of tokens
        """
        try:
            # Get or create tokenizer for this model
            if model not in self._tokenizer_cache:
                try:
                    encoding = tiktoken.encoding_for_model(model)
                except KeyError:
                    # Fallback to cl100k_base encoding for unknown models
                    encoding = tiktoken.get_encoding("cl100k_base")
                self._tokenizer_cache[model] = encoding
            else:
                encoding = self._tokenizer_cache[model]

            # Count tokens
            tokens = encoding.encode(text)
            return len(tokens)

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

