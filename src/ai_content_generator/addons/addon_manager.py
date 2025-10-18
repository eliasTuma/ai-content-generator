"""Addon manager for orchestrating addon execution."""

from typing import Any, Optional

from .base_addon import BaseAddon, AddonContext


class AddonManager:
    """
    Manager for orchestrating addon execution.
    
    Manages the addon lifecycle and executes hooks in the correct order.
    
    Example:
        ```python
        from ai_content_generator.addons import (
            AddonManager,
            CacheAddon,
            RetryAddon,
            DryRunAddon
        )
        
        manager = AddonManager()
        
        # Add addons (order matters!)
        manager.add_addon(DryRunAddon())  # First - intercepts early
        manager.add_addon(CacheAddon())   # Second - checks cache
        manager.add_addon(RetryAddon())   # Third - handles retries
        
        # Execute pre-request hooks
        context = AddonContext(
            request_id="req-123",
            prompt="Hello",
            model="gpt-5-nano",
            provider="openai"
        )
        
        cached_response = await manager.execute_pre_request("Hello", context)
        
        if not cached_response:
            # Make actual API call
            response = await provider.chat(...)
            
            # Execute post-request hooks
            response = await manager.execute_post_request(response, context)
        ```
    """
    
    def __init__(self):
        """Initialize addon manager."""
        self._addons: list[BaseAddon] = []
    
    def add_addon(self, addon: BaseAddon) -> None:
        """
        Register an addon.
        
        Addons are executed in the order they are added.
        
        Args:
            addon: Addon instance to register
        """
        self._addons.append(addon)
    
    def remove_addon(self, name: str) -> bool:
        """
        Unregister an addon by name.
        
        Args:
            name: Name of the addon to remove
        
        Returns:
            True if addon was found and removed
        """
        for i, addon in enumerate(self._addons):
            if addon.get_name() == name:
                self._addons.pop(i)
                return True
        return False
    
    def get_addons(self) -> list[BaseAddon]:
        """
        Get list of registered addons.
        
        Returns:
            List of addon instances
        """
        return self._addons.copy()
    
    def get_addon(self, name: str) -> Optional[BaseAddon]:
        """
        Get an addon by name.
        
        Args:
            name: Name of the addon
        
        Returns:
            Addon instance or None if not found
        """
        for addon in self._addons:
            if addon.get_name() == name:
                return addon
        return None
    
    def clear_addons(self) -> None:
        """Remove all registered addons."""
        self._addons.clear()
    
    async def execute_pre_request(
        self,
        prompt: str,
        context: AddonContext
    ) -> Optional[str]:
        """
        Execute all pre-request hooks.
        
        Addons are executed in order. If any addon returns a response,
        execution stops and that response is returned (short-circuit).
        
        Args:
            prompt: The prompt being sent
            context: Addon context
        
        Returns:
            - None: Continue with normal request
            - str: Skip request and use this as response content
        """
        for addon in self._addons:
            # Skip disabled addons
            if not addon.is_enabled():
                continue
            
            try:
                result = await addon.pre_request(prompt, context)
                
                # If addon returns a response, short-circuit
                if result is not None:
                    return result
            
            except Exception as e:
                # Log addon error but continue with other addons
                import sys
                print(
                    f"ERROR in addon '{addon.get_name()}' pre_request: {str(e)}",
                    file=sys.stderr
                )
                # Store error in context for debugging
                if "addon_errors" not in context.custom:
                    context.custom["addon_errors"] = []
                context.custom["addon_errors"].append({
                    "addon": addon.get_name(),
                    "hook": "pre_request",
                    "error": str(e),
                })
        
        return None
    
    async def execute_post_request(
        self,
        response: dict[str, Any],
        context: AddonContext
    ) -> dict[str, Any]:
        """
        Execute all post-request hooks.
        
        Addons are executed in order. Each addon can modify the response.
        
        Args:
            response: Response from the provider
            context: Addon context
        
        Returns:
            Modified or original response
        """
        current_response = response
        
        for addon in self._addons:
            # Skip disabled addons
            if not addon.is_enabled():
                continue
            
            try:
                current_response = await addon.post_request(current_response, context)
            
            except Exception as e:
                # Log addon error but continue with other addons
                import sys
                print(
                    f"ERROR in addon '{addon.get_name()}' post_request: {str(e)}",
                    file=sys.stderr
                )
                # Store error in context for debugging
                if "addon_errors" not in context.custom:
                    context.custom["addon_errors"] = []
                context.custom["addon_errors"].append({
                    "addon": addon.get_name(),
                    "hook": "post_request",
                    "error": str(e),
                })
        
        return current_response
    
    async def execute_on_error(
        self,
        error: Exception,
        context: AddonContext
    ) -> bool:
        """
        Execute all error hooks.
        
        Addons are executed in order. If any addon returns True,
        the request should be retried.
        
        Args:
            error: The exception that occurred
            context: Addon context
        
        Returns:
            True if request should be retried
        """
        should_retry = False
        
        for addon in self._addons:
            # Skip disabled addons
            if not addon.is_enabled():
                continue
            
            try:
                if await addon.on_error(error, context):
                    should_retry = True
            
            except Exception as e:
                # Log addon error but continue with other addons
                import sys
                print(
                    f"ERROR in addon '{addon.get_name()}' on_error: {str(e)}",
                    file=sys.stderr
                )
                # Store error in context for debugging
                if "addon_errors" not in context.custom:
                    context.custom["addon_errors"] = []
                context.custom["addon_errors"].append({
                    "addon": addon.get_name(),
                    "hook": "on_error",
                    "error": str(e),
                })
        
        return should_retry

