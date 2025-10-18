"""Retry addon for handling transient failures."""

import asyncio
from typing import Optional, Type

from .base_addon import BaseAddon, AddonContext
from ..core.exceptions import RateLimitError, ConnectionError, ProviderError


class RetryAddon(BaseAddon):
    """
    Addon for retrying failed requests with exponential backoff.
    
    Features:
    - Configurable max retries
    - Exponential backoff with jitter
    - Selective retry based on error type
    - Retry statistics
    
    Example:
        ```python
        retry = RetryAddon(
            max_retries=3,
            initial_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            retry_on_errors=[RateLimitError, ConnectionError]
        )
        
        # Use in session
        session.add_addon(retry)
        
        # Check stats
        stats = retry.get_stats()
        print(f"Total retries: {stats['total_retries']}")
        ```
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retry_on_errors: Optional[list[Type[Exception]]] = None,
    ):
        """
        Initialize retry addon.
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            retry_on_errors: List of exception types to retry on (None for all)
        """
        super().__init__()
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retry_on_errors = retry_on_errors or [
            RateLimitError,
            ConnectionError,
            ProviderError,
        ]
        self._total_retries = 0
        self._successful_retries = 0
        self._failed_retries = 0
    
    def get_name(self) -> str:
        """Get addon name."""
        return "Retry Addon"
    
    def get_description(self) -> str:
        """Get addon description."""
        return f"Retries failed requests (max: {self.max_retries}, backoff: exponential)"
    
    def _should_retry(self, error: Exception) -> bool:
        """
        Check if error should trigger a retry.
        
        Args:
            error: The exception that occurred
        
        Returns:
            True if should retry
        """
        return any(isinstance(error, error_type) for error_type in self.retry_on_errors)
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for retry attempt using exponential backoff.
        
        Args:
            attempt: Retry attempt number (0-based)
        
        Returns:
            Delay in seconds
        """
        # Exponential backoff: initial_delay * (base ^ attempt)
        delay = self.initial_delay * (self.exponential_base ** attempt)
        
        # Cap at max_delay
        delay = min(delay, self.max_delay)
        
        # Add jitter (±20%) to prevent thundering herd
        import random
        jitter = delay * 0.2 * (random.random() * 2 - 1)
        delay += jitter
        
        return max(0, delay)
    
    async def on_error(
        self,
        error: Exception,
        context: AddonContext
    ) -> bool:
        """
        Handle error and determine if retry should occur.
        
        Args:
            error: The exception that occurred
            context: Addon context
        
        Returns:
            True if request should be retried
        """
        # Check if we should retry this error type
        if not self._should_retry(error):
            return False
        
        # Get current retry count from context
        retry_count = context.custom.get("retry_count", 0)
        
        # Check if we've exceeded max retries
        if retry_count >= self.max_retries:
            self._failed_retries += 1
            return False
        
        # Calculate delay
        delay = self._calculate_delay(retry_count)
        
        # Store retry info in context
        context.custom["retry_count"] = retry_count + 1
        context.custom["retry_delay"] = delay
        context.custom["retry_reason"] = type(error).__name__
        
        # Wait before retry
        await asyncio.sleep(delay)
        
        # Track retry
        self._total_retries += 1
        
        # Indicate that retry should occur
        return True
    
    async def post_request(
        self,
        response: dict,
        context: AddonContext
    ) -> dict:
        """
        Track successful retry.
        
        Args:
            response: Response from provider
            context: Addon context
        
        Returns:
            Original response
        """
        # If this was a retry that succeeded, track it
        if context.custom.get("retry_count", 0) > 0:
            self._successful_retries += 1
        
        return response
    
    def get_stats(self) -> dict:
        """
        Get retry statistics.
        
        Returns:
            Dictionary with retry stats
        """
        return {
            "total_retries": self._total_retries,
            "successful_retries": self._successful_retries,
            "failed_retries": self._failed_retries,
            "max_retries": self.max_retries,
        }
    
    def reset_stats(self) -> None:
        """Reset retry statistics."""
        self._total_retries = 0
        self._successful_retries = 0
        self._failed_retries = 0

