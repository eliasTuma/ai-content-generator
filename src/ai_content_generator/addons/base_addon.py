"""Base addon interface and context."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime


@dataclass
class AddonContext:
    """
    Context data passed through addon pipeline.
    
    This context is shared across all addons and can be used to pass
    data between pre-request, post-request, and error handlers.
    
    Attributes:
        request_id: Unique identifier for the request
        prompt: The prompt being sent
        model: Model being used
        provider: Provider name
        metadata: Additional metadata
        start_time: When the request started
        end_time: When the request completed
        error: Any error that occurred
        response: Response from the provider
        custom: Custom data that addons can use
    """
    request_id: str
    prompt: str
    model: str
    provider: str
    metadata: dict[str, Any] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[Exception] = None
    response: Optional[dict[str, Any]] = None
    custom: dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Get request duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


class BaseAddon(ABC):
    """
    Abstract base class for addons.
    
    Addons can hook into the request lifecycle to add functionality like
    caching, retries, validation, etc.
    
    Lifecycle hooks:
    1. pre_request: Called before making the API request
    2. post_request: Called after successful API request
    3. on_error: Called when an error occurs
    
    Example:
        ```python
        class MyAddon(BaseAddon):
            def __init__(self):
                super().__init__()
            
            def get_name(self) -> str:
                return "My Addon"
            
            def get_description(self) -> str:
                return "Does something useful"
            
            def is_enabled(self) -> bool:
                return True
            
            async def pre_request(self, prompt: str, context: AddonContext) -> Optional[str]:
                # Modify prompt or return cached response
                return None
            
            async def post_request(self, response: dict, context: AddonContext) -> dict:
                # Process or validate response
                return response
            
            async def on_error(self, error: Exception, context: AddonContext) -> bool:
                # Handle error, return True to retry
                return False
        ```
    """
    
    def __init__(self):
        """Initialize the addon."""
        self._enabled = True
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Get the name of this addon.
        
        Returns:
            Addon name
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """
        Get a description of what this addon does.
        
        Returns:
            Addon description
        """
        pass
    
    def is_enabled(self) -> bool:
        """
        Check if this addon is enabled.
        
        Returns:
            True if addon is enabled
        """
        return self._enabled
    
    def enable(self) -> None:
        """Enable this addon."""
        self._enabled = True
    
    def disable(self) -> None:
        """Disable this addon."""
        self._enabled = False
    
    async def pre_request(
        self,
        prompt: str,
        context: AddonContext
    ) -> Optional[str]:
        """
        Hook called before making the API request.
        
        This can be used to:
        - Modify the prompt
        - Check cache and return cached response
        - Validate the request
        - Add metadata to context
        
        Args:
            prompt: The prompt being sent
            context: Addon context
        
        Returns:
            - None: Continue with normal request
            - str: Skip request and use this as the response content
        """
        return None
    
    async def post_request(
        self,
        response: dict[str, Any],
        context: AddonContext
    ) -> dict[str, Any]:
        """
        Hook called after successful API request.
        
        This can be used to:
        - Validate the response
        - Cache the response
        - Transform the response
        - Log the response
        
        Args:
            response: Response from the provider
            context: Addon context
        
        Returns:
            Modified or original response
        """
        return response
    
    async def on_error(
        self,
        error: Exception,
        context: AddonContext
    ) -> bool:
        """
        Hook called when an error occurs.
        
        This can be used to:
        - Log the error
        - Implement retry logic
        - Transform the error
        - Provide fallback behavior
        
        Args:
            error: The exception that occurred
            context: Addon context
        
        Returns:
            - True: Request should be retried
            - False: Error should be propagated
        """
        return False

