"""Dry run addon for testing without making actual API calls."""

from typing import Any, Optional

from .base_addon import BaseAddon, AddonContext


class DryRunAddon(BaseAddon):
    """
    Addon for dry run mode - simulates API calls without actually making them.
    
    Features:
    - Intercepts requests before they're sent
    - Returns mock responses
    - Estimates tokens and costs
    - Logs what would have been sent
    - Useful for testing and cost estimation
    
    Example:
        ```python
        dry_run = DryRunAddon(
            mock_response="This is a mock response",
            estimate_tokens=True,
            log_requests=True
        )
        
        # Use in session
        session.add_addon(dry_run)
        
        # All requests will be intercepted and not sent to API
        response = await session.chat("Hello")
        # Returns mock response
        
        # Check what would have been sent
        logs = dry_run.get_request_log()
        ```
    """
    
    def __init__(
        self,
        mock_response: Optional[str] = None,
        estimate_tokens: bool = True,
        log_requests: bool = True,
        mock_input_tokens: int = 10,
        mock_output_tokens: int = 50,
    ):
        """
        Initialize dry run addon.
        
        Args:
            mock_response: Mock response content (None for auto-generated)
            estimate_tokens: Whether to estimate token counts
            log_requests: Whether to log intercepted requests
            mock_input_tokens: Default input token count for estimation
            mock_output_tokens: Default output token count for estimation
        """
        super().__init__()
        self.mock_response = mock_response
        self.estimate_tokens = estimate_tokens
        self.log_requests = log_requests
        self.mock_input_tokens = mock_input_tokens
        self.mock_output_tokens = mock_output_tokens
        self._request_log: list[dict[str, Any]] = []
    
    def get_name(self) -> str:
        """Get addon name."""
        return "Dry Run Addon"
    
    def get_description(self) -> str:
        """Get addon description."""
        return "Simulates API calls without actually making them"
    
    def _estimate_token_count(self, text: str) -> int:
        """
        Rough estimation of token count.
        
        Args:
            text: Text to estimate
        
        Returns:
            Estimated token count
        """
        # Rough estimation: 1 token ≈ 4 characters
        return len(text) // 4
    
    def _generate_mock_response(self, prompt: str, context: AddonContext) -> str:
        """
        Generate mock response content.
        
        Args:
            prompt: The prompt
            context: Addon context
        
        Returns:
            Mock response content
        """
        if self.mock_response:
            return self.mock_response
        
        # Auto-generate mock response
        return (
            f"[DRY RUN] Mock response for prompt: '{prompt[:50]}...' "
            f"using model '{context.model}' on provider '{context.provider}'"
        )
    
    async def pre_request(
        self,
        prompt: str,
        context: AddonContext
    ) -> Optional[str]:
        """
        Intercept request and return mock response.
        
        Args:
            prompt: The prompt
            context: Addon context
        
        Returns:
            Mock response content
        """
        # Log the request if enabled
        if self.log_requests:
            log_entry = {
                "request_id": context.request_id,
                "prompt": prompt,
                "model": context.model,
                "provider": context.provider,
                "metadata": context.metadata,
            }
            self._request_log.append(log_entry)
        
        # Estimate tokens if enabled
        if self.estimate_tokens:
            input_tokens = self._estimate_token_count(prompt)
            context.custom["estimated_input_tokens"] = input_tokens
            context.custom["estimated_output_tokens"] = self.mock_output_tokens
        else:
            context.custom["estimated_input_tokens"] = self.mock_input_tokens
            context.custom["estimated_output_tokens"] = self.mock_output_tokens
        
        # Mark as dry run
        context.custom["dry_run"] = True
        
        # Generate and return mock response
        mock_content = self._generate_mock_response(prompt, context)
        return mock_content
    
    async def post_request(
        self,
        response: dict[str, Any],
        context: AddonContext
    ) -> dict[str, Any]:
        """
        This won't be called in dry run mode since pre_request returns a response.
        
        Args:
            response: Response (won't be used)
            context: Addon context
        
        Returns:
            Original response
        """
        return response
    
    def get_request_log(self) -> list[dict[str, Any]]:
        """
        Get log of intercepted requests.
        
        Returns:
            List of logged requests
        """
        return self._request_log.copy()
    
    def clear_log(self) -> None:
        """Clear the request log."""
        self._request_log.clear()
    
    def get_stats(self) -> dict:
        """
        Get dry run statistics.
        
        Returns:
            Dictionary with stats
        """
        return {
            "total_intercepted": len(self._request_log),
            "log_enabled": self.log_requests,
            "estimate_tokens": self.estimate_tokens,
        }

