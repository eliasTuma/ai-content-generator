"""Base provider interface for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseProvider(ABC):
    """
    Abstract base class for LLM providers.

    All provider implementations must inherit from this class and implement
    the required abstract methods.
    """

    def __init__(
        self,
        api_key: str,
        timeout: int = 60,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the provider.

        Args:
            api_key: API key for the provider
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            **kwargs: Additional provider-specific configuration
        """
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.extra_config = kwargs
        self._is_connected = False

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Get the name of the provider.

        Returns:
            Provider name (e.g., "openai", "anthropic")
        """
        pass

    @property
    @abstractmethod
    def supported_models(self) -> list[str]:
        """
        Get list of supported model names.

        Returns:
            List of model identifiers supported by this provider
        """
        pass

    @property
    def is_connected(self) -> bool:
        """
        Check if provider connection has been validated.

        Returns:
            True if connection has been validated, False otherwise
        """
        return self._is_connected

    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        Validate the connection to the provider.

        This method should test if the API key is valid and the provider
        is reachable. It should not raise exceptions but return False on failure.

        Returns:
            True if connection is valid, False otherwise

        Example:
            ```python
            provider = OpenAIProvider(api_key="sk-...")
            is_valid = await provider.validate_connection()
            if is_valid:
                print("Connection successful!")
            ```
        """
        pass

    @abstractmethod
    async def list_models(self) -> list[dict[str, Any]]:
        """
        Get list of available models with their metadata.

        Returns:
            List of dictionaries containing model information:
            - name: Model identifier
            - context_window: Maximum context window size
            - input_price_per_1m: Price per 1M input tokens in USD
            - output_price_per_1m: Price per 1M output tokens in USD
            - capabilities: List of model capabilities

        Example:
            ```python
            models = await provider.list_models()
            for model in models:
                print(f"{model['name']}: ${model['input_price_per_1m']}/1M tokens")
            ```
        """
        pass

    @abstractmethod
    async def get_model_info(self, model_name: str) -> dict[str, Any]:
        """
        Get detailed information about a specific model.

        Args:
            model_name: Name of the model

        Returns:
            Dictionary containing model information:
            - name: Model identifier
            - context_window: Maximum context window size
            - input_price_per_1m: Price per 1M input tokens in USD
            - output_price_per_1m: Price per 1M output tokens in USD
            - capabilities: List of model capabilities
            - description: Model description

        Raises:
            ModelNotFoundError: If model is not found

        Example:
            ```python
            info = await provider.get_model_info("gpt-4")
            print(f"Context window: {info['context_window']}")
            ```
        """
        pass

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Send a chat completion request to the provider.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model identifier to use
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            Dictionary containing:
            - content: Generated text response
            - model: Model used
            - input_tokens: Number of input tokens
            - output_tokens: Number of output tokens
            - finish_reason: Reason for completion
            - raw_response: Original provider response

        Raises:
            ProviderError: If the request fails
            RateLimitError: If rate limit is exceeded
            TokenLimitError: If token limit is exceeded
            ModelNotFoundError: If model is not found

        Example:
            ```python
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"}
            ]
            response = await provider.chat(messages, model="gpt-4")
            print(response["content"])
            ```
        """
        pass

    @abstractmethod
    async def count_tokens(self, text: str, model: str) -> int:
        """
        Count the number of tokens in a text for a specific model.

        Args:
            text: Text to count tokens for
            model: Model identifier (tokenization may vary by model)

        Returns:
            Number of tokens

        Example:
            ```python
            text = "Hello, world!"
            tokens = await provider.count_tokens(text, "gpt-4")
            print(f"Token count: {tokens}")
            ```
        """
        pass

    @abstractmethod
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
            Dictionary containing:
            - input_cost: Estimated input cost in USD
            - output_cost: Estimated output cost in USD (if max_tokens provided)
            - total_cost: Total estimated cost in USD
            - input_tokens: Estimated input token count

        Example:
            ```python
            estimate = await provider.estimate_cost(
                prompt="Write a story",
                model="gpt-4",
                max_tokens=1000
            )
            print(f"Estimated cost: ${estimate['total_cost']:.4f}")
            ```
        """
        pass

    @abstractmethod
    def calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """
        Calculate the actual cost of a completed request.

        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated
            model: Model identifier

        Returns:
            Total cost in USD

        Example:
            ```python
            cost = provider.calculate_cost(
                input_tokens=100,
                output_tokens=200,
                model="gpt-4"
            )
            print(f"Cost: ${cost:.4f}")
            ```
        """
        pass

    async def __aenter__(self) -> "BaseProvider":
        """Async context manager entry."""
        await self.validate_connection()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        # Cleanup if needed
        pass

    def __repr__(self) -> str:
        """String representation of the provider."""
        return f"{self.__class__.__name__}(provider={self.provider_name})"

