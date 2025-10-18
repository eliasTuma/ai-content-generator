"""Custom exceptions for AI Content Generator."""

from typing import Any, Optional


class AIContentGeneratorError(Exception):
    """Base exception for all AI Content Generator errors."""

    def __init__(self, message: str, context: Optional[dict[str, Any]] = None) -> None:
        """
        Initialize the exception.

        Args:
            message: Error message
            context: Additional context information about the error
        """
        self.message = message
        self.context = context or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} (Context: {context_str})"
        return self.message


class ConfigurationError(AIContentGeneratorError):
    """Raised when there's an issue with configuration."""

    def __init__(
        self, message: str = "Configuration error occurred", context: Optional[dict[str, Any]] = None
    ) -> None:
        """Initialize configuration error."""
        super().__init__(message, context)


class ValidationError(AIContentGeneratorError):
    """Raised when validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        errors: Optional[list[str]] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Initialize validation error.

        Args:
            message: Error message
            errors: List of validation errors
            context: Additional context
        """
        self.errors = errors or []
        super().__init__(message, context)

    def __str__(self) -> str:
        """Return string representation including validation errors."""
        base_str = super().__str__()
        if self.errors:
            errors_str = "\n  - ".join(self.errors)
            return f"{base_str}\nValidation errors:\n  - {errors_str}"
        return base_str


class ProviderError(AIContentGeneratorError):
    """Raised when there's an issue with a provider."""

    def __init__(
        self,
        message: str = "Provider error occurred",
        provider: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Initialize provider error.

        Args:
            message: Error message
            provider: Name of the provider that caused the error
            context: Additional context
        """
        self.provider = provider
        if context is None:
            context = {}
        if provider:
            context["provider"] = provider
        super().__init__(message, context)


class BudgetExceededError(AIContentGeneratorError):
    """Raised when budget limit is exceeded."""

    def __init__(
        self,
        budget: float,
        cost: float,
        message: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Initialize budget exceeded error.

        Args:
            budget: Budget limit in USD
            cost: Current or projected cost in USD
            message: Optional custom message
            context: Additional context
        """
        self.budget = budget
        self.cost = cost
        if message is None:
            message = f"Budget exceeded: ${cost:.4f} exceeds limit of ${budget:.4f}"
        if context is None:
            context = {}
        context.update({"budget": budget, "cost": cost, "exceeded_by": cost - budget})
        super().__init__(message, context)


class APIKeyMissingError(ConfigurationError):
    """Raised when an API key is missing."""

    def __init__(
        self, provider: str, message: Optional[str] = None, context: Optional[dict[str, Any]] = None
    ) -> None:
        """
        Initialize API key missing error.

        Args:
            provider: Name of the provider missing the API key
            message: Optional custom message
            context: Additional context
        """
        self.provider = provider
        if message is None:
            message = (
                f"API key for provider '{provider}' is missing. "
                f"Please set it in your configuration or environment variables."
            )
        if context is None:
            context = {}
        context["provider"] = provider
        super().__init__(message, context)


class ConnectionError(ProviderError):
    """Raised when there's a connection issue with a provider."""

    def __init__(
        self,
        message: str = "Failed to connect to provider",
        provider: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize connection error."""
        super().__init__(message, provider, context)


class RateLimitError(ProviderError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        provider: Optional[str] = None,
        retry_after: Optional[float] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Initialize rate limit error.

        Args:
            message: Error message
            provider: Name of the provider
            retry_after: Seconds to wait before retrying
            context: Additional context
        """
        self.retry_after = retry_after
        if context is None:
            context = {}
        if retry_after is not None:
            context["retry_after"] = retry_after
            message = f"{message} (retry after {retry_after}s)"
        super().__init__(message, provider, context)


class ModelNotFoundError(ProviderError):
    """Raised when a specified model is not found or not available."""

    def __init__(
        self,
        model: str,
        provider: Optional[str] = None,
        message: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Initialize model not found error.

        Args:
            model: Name of the model that wasn't found
            provider: Name of the provider
            message: Optional custom message
            context: Additional context
        """
        self.model = model
        if message is None:
            provider_str = f" for provider '{provider}'" if provider else ""
            message = f"Model '{model}' not found{provider_str}"
        if context is None:
            context = {}
        context["model"] = model
        super().__init__(message, provider, context)


class TokenLimitError(ProviderError):
    """Raised when token limit is exceeded."""

    def __init__(
        self,
        tokens: int,
        limit: int,
        message: Optional[str] = None,
        provider: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Initialize token limit error.

        Args:
            tokens: Number of tokens in the request
            limit: Token limit for the model
            message: Optional custom message
            provider: Name of the provider
            context: Additional context
        """
        self.tokens = tokens
        self.limit = limit
        if message is None:
            message = f"Token limit exceeded: {tokens} tokens exceeds limit of {limit}"
        if context is None:
            context = {}
        context.update({"tokens": tokens, "limit": limit, "exceeded_by": tokens - limit})
        super().__init__(message, provider, context)


class AddonError(AIContentGeneratorError):
    """Raised when an addon encounters an error."""

    def __init__(
        self,
        addon_name: str,
        message: str = "Addon error occurred",
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Initialize addon error.

        Args:
            addon_name: Name of the addon that caused the error
            message: Error message
            context: Additional context
        """
        self.addon_name = addon_name
        if context is None:
            context = {}
        context["addon"] = addon_name
        super().__init__(message, context)

