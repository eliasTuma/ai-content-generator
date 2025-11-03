"""Session manager for LLM interactions with budget tracking."""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional
from uuid import uuid4

from ai_content_generator.addons import AddonManager, AddonContext
from ai_content_generator.addons.base_addon import BaseAddon
from ai_content_generator.core.exceptions import BudgetExceededError
from ai_content_generator.core.provider import BaseProvider
from ai_content_generator.monitoring.alerts import AlertManager
from ai_content_generator.monitoring.cost_tracker import CostTracker
from ai_content_generator.monitoring.token_monitor import TokenMonitor


class LLMSession:
    """
    Manage an LLM session with budget tracking and monitoring.

    Provides a context manager interface for safe resource management,
    tracks costs and tokens, enforces budget limits, and supports addons.
    """

    def __init__(
        self,
        provider: BaseProvider,
        model: str,
        budget_usd: Optional[float] = None,
        dry_run: bool = False,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Initialize an LLM session.

        Args:
            provider: LLM provider instance
            model: Model identifier to use
            budget_usd: Budget limit in USD (None for unlimited)
            dry_run: If True, simulate requests without calling the API
            metadata: Optional metadata to attach to the session

        Example:
            ```python
            from ai_content_generator.providers import OpenAIProvider

            provider = OpenAIProvider(api_key="sk-...")
            async with LLMSession(provider, "gpt-4", budget_usd=10.0) as session:
                response = await session.chat("Hello, world!")
                print(response["content"])
            ```
        """
        self.session_id = str(uuid4())
        self.provider = provider
        self.model = model
        self.dry_run = dry_run
        self.metadata = metadata or {}

        # Monitoring components
        self.token_monitor = TokenMonitor()
        self.cost_tracker = CostTracker(budget_usd=budget_usd)
        self.alert_manager = AlertManager()

        # Addon system
        self.addon_manager = AddonManager()

        # Session state
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._is_active = False
        self._request_count = 0
        
        # Addon execution logging
        self._log_addon_execution: bool = True
        self._addon_execution_log: list[dict[str, Any]] = []

    @property
    def cost_usd(self) -> float:
        """Get total cost in USD."""
        return self.cost_tracker.get_total_cost()

    @property
    def tokens_used(self) -> int:
        """Get total tokens used."""
        return self.token_monitor.get_total_tokens()

    @property
    def budget_remaining(self) -> Optional[float]:
        """Get remaining budget in USD."""
        return self.cost_tracker.get_remaining_budget()

    @property
    def request_count(self) -> int:
        """Get number of requests made."""
        return self._request_count

    @property
    def is_active(self) -> bool:
        """Check if session is currently active."""
        return self._is_active

    @property
    def duration(self) -> Optional[float]:
        """Get session duration in seconds."""
        if self._start_time is None:
            return None
        end = self._end_time or datetime.now()
        return (end - self._start_time).total_seconds()

    async def start(self) -> None:
        """
        Start the session.

        Validates provider connection and initializes session state.
        """
        if self._is_active:
            return

        # Validate provider connection
        if not self.provider.is_connected:
            await self.provider.validate_connection()

        self._start_time = datetime.now()
        self._is_active = True

    async def end(self) -> None:
        """
        End the session.

        Finalizes session state and cleanup.
        """
        if not self._is_active:
            return

        self._end_time = datetime.now()
        self._is_active = False

    def _log_addon(
        self,
        hook: str,
        addon_name: str,
        execution_time_ms: float,
        success: bool,
        error: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> None:
        """Log addon execution for monitoring and debugging."""
        if not self._log_addon_execution:
            return
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "hook": hook,
            "addon": addon_name,
            "execution_time_ms": execution_time_ms,
            "success": success,
            "request_id": request_id,
        }
        if error:
            log_entry["error"] = error
        
        self._addon_execution_log.append(log_entry)
        
        # Also print for immediate visibility
        status = "✓" if success else "✗"
        error_msg = f" - ERROR: {error}" if error else ""
        print(
            f"[ADDON] {status} {addon_name}.{hook} ({execution_time_ms:.2f}ms){error_msg}",
            file=sys.stderr if error else sys.stdout
        )

    def _is_final_response(self, addon_response: str, context: AddonContext, original_prompt: str) -> bool:
        """
        Determine if addon_response is a final response (cache/dry-run) or modified prompt.
        
        Logic:
        - If context indicates cache_hit or dry_run -> final response
        - If response is significantly different length/content from prompt -> likely final response
        - If original prompt stored in context and response != original -> modified prompt
        - Otherwise assume modified prompt if response is similar length to prompt
        """
        # Check explicit flags first
        if context.custom.get("cache_hit") or context.custom.get("dry_run"):
            return True
        
        # If original prompt is stored and response matches it, it's modified
        original_in_context = context.custom.get("whitespace_minimizer_original")
        if original_in_context:
            # If response equals original, it wasn't modified (shouldn't happen)
            # If response doesn't equal original, check similarity
            if addon_response == original_in_context:
                return False  # Unchanged
            
            # For modified prompt, length should be close
            len_diff_ratio = abs(len(addon_response) - len(original_in_context)) / max(len(original_in_context), 1)
            if len_diff_ratio < 0.3:  # Less than 30% difference = likely modified prompt
                return False
        
        # Check if response looks like a generated response vs prompt
        # Generated responses are usually longer, have newlines, more complete sentences
        len_ratio = len(addon_response) / max(len(original_prompt), 1)
        has_many_newlines = addon_response.count("\n") > 2
        
        # If significantly longer with many newlines, likely a response
        if len_ratio > 2.0 and has_many_newlines:
            return True
        
        # If similar length to original prompt, likely modified prompt
        if 0.7 <= len_ratio <= 1.3:
            return False
        
        # Default: assume modified prompt for safety
        return False

    async def _handle_addon_error(
        self,
        error: Exception,
        context: AddonContext,
    ) -> bool:
        """
        Handle error through addon pipeline.
        
        Returns True if request should be retried.
        """
        context.error = error
        context.end_time = datetime.now()
        
        start_time = datetime.now()
        should_retry = await self.addon_manager.execute_on_error(error, context)
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        if self._log_addon_execution:
            addon_name = "error_handlers"
            self._log_addon(
                hook="on_error",
                addon_name=addon_name,
                execution_time_ms=execution_time,
                success=True,
                request_id=context.request_id,
            )
        
        return should_retry

    def _build_response_dict(
        self,
        content: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        request_id: str,
        **extra_fields: Any,
    ) -> dict[str, Any]:
        """Build standardized response dictionary."""
        return {
            "content": content,
            "model": self.model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost,
            "request_id": request_id,
            **extra_fields,
        }

    def _record_metrics(
        self,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        request_id: str,
    ) -> None:
        """Record metrics for a request."""
        self.token_monitor.record_usage(input_tokens, output_tokens, self.model, request_id)
        self.cost_tracker.record_cost(cost, self.model, input_tokens, output_tokens, request_id)
        self._request_count += 1
        
        if self.cost_tracker.budget_usd is not None:
            self.alert_manager.check_alerts(self.cost_usd, self.cost_tracker.budget_usd)

    async def _execute_addon_pre_request(
        self,
        text: str,
        context: AddonContext,
        text_type: str = "prompt",
    ) -> tuple[Optional[str], bool]:
        """
        Execute pre-request addons on text.
        
        Returns:
            Tuple of (modified_text_or_response, is_final_response)
            - If is_final_response=True, the text is a final response (cache/dry-run)
            - If is_final_response=False and result not None, text was modified
            - If result is None, text unchanged
        """
        has_addons = len(self.addon_manager.get_addons()) > 0
        if not has_addons:
            return None, False
        
        original_text = text
        start_time = datetime.now()
        
        try:
            result = await self.addon_manager.execute_pre_request(text, context)
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log addon execution
            if self._log_addon_execution and result is not None:
                addon_names = [a.get_name() for a in self.addon_manager.get_addons()]
                for name in addon_names:
                    self._log_addon(
                        hook="pre_request",
                        addon_name=name,
                        execution_time_ms=execution_time / len(addon_names) if addon_names else execution_time,
                        success=True,
                        request_id=context.request_id,
                    )
            
            if result is not None:
                is_final = self._is_final_response(result, context, original_text)
                return result, is_final
            
            return None, False
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            if self._log_addon_execution:
                addon_names = [a.get_name() for a in self.addon_manager.get_addons()]
                for name in addon_names:
                    self._log_addon(
                        hook="pre_request",
                        addon_name=name,
                        execution_time_ms=execution_time,
                        success=False,
                        error=str(e),
                        request_id=context.request_id,
                    )
            raise

    async def _execute_addon_post_request(
        self,
        response_dict: dict[str, Any],
        context: AddonContext,
    ) -> dict[str, Any]:
        """Execute post-request addons."""
        has_addons = len(self.addon_manager.get_addons()) > 0
        if not has_addons:
            return response_dict
        
        context.response = response_dict
        start_time = datetime.now()
        
        try:
            result = await self.addon_manager.execute_post_request(response_dict, context)
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log addon execution
            if self._log_addon_execution:
                addon_names = [a.get_name() for a in self.addon_manager.get_addons()]
                for name in addon_names:
                    self._log_addon(
                        hook="post_request",
                        addon_name=name,
                        execution_time_ms=execution_time / len(addon_names) if addon_names else execution_time,
                        success=True,
                        request_id=context.request_id,
                    )
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            if self._log_addon_execution:
                addon_names = [a.get_name() for a in self.addon_manager.get_addons()]
                for name in addon_names:
                    self._log_addon(
                        hook="post_request",
                        addon_name=name,
                        execution_time_ms=execution_time,
                        success=False,
                        error=str(e),
                        request_id=context.request_id,
                    )
            # Return original response on error, don't raise
            return response_dict

    async def chat(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_message: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Send a chat request to the LLM.

        Args:
            prompt: User prompt/message
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            system_message: Optional system message
            **kwargs: Additional provider-specific parameters

        Returns:
            Dictionary containing:
            - content: Generated text response
            - model: Model used
            - input_tokens: Number of input tokens
            - output_tokens: Number of output tokens
            - cost_usd: Cost of this request
            - request_id: Unique request identifier

        Raises:
            BudgetExceededError: If budget would be exceeded
            ProviderError: If the request fails

        Example:
            ```python
            response = await session.chat(
                prompt="Write a haiku about Python",
                temperature=0.8,
                max_tokens=100
            )
            print(response["content"])
            print(f"Cost: ${response['cost_usd']:.4f}")
            ```
        """
        if not self._is_active:
            await self.start()

        request_id = f"{self.session_id}_{self._request_count + 1}"
        request_start_time = datetime.now()
        
        # Check if we have addons - early exit optimization
        has_addons = len(self.addon_manager.get_addons()) > 0
        
        # Create addon context
        addon_context = AddonContext(
            request_id=request_id,
            prompt=prompt,
            model=self.model,
            provider=self.provider.provider_name,
            metadata={**self.metadata, **kwargs},
            start_time=request_start_time,
        )

        # Execute pre-request addons for user prompt
        try:
            addon_result, is_final_response = await self._execute_addon_pre_request(
                prompt, addon_context
            )
            
            if addon_result is not None:
                if is_final_response:
                    # This is a final response (cache/dry-run) - handle and return
                    original_prompt = addon_context.custom.get("whitespace_minimizer_original", prompt)
                    input_tokens = await self.provider.count_tokens(original_prompt, self.model)
                    # Use accurate token counting instead of estimate
                    output_tokens = await self.provider.count_tokens(addon_result, self.model)
                    cost = self.provider.calculate_cost(input_tokens, output_tokens, self.model)

                    self._record_metrics(input_tokens, output_tokens, cost, request_id)

                    response_dict = self._build_response_dict(
                        content=addon_result,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cost=cost,
                        request_id=request_id,
                    )
                    
                    addon_context.end_time = datetime.now()
                    response_dict = await self._execute_addon_post_request(response_dict, addon_context)
                    return response_dict
                else:
                    # Modified prompt - use it for API call
                    prompt = addon_result

        except Exception as e:
            if has_addons:
                # Log error through addon pipeline
                await self._handle_addon_error(e, addon_context)
            raise

        # Apply addons to system message if provided
        if system_message and has_addons:
            sys_context = AddonContext(
                request_id=f"{request_id}_sys",
                prompt=system_message,
                model=self.model,
                provider=self.provider.provider_name,
                metadata={**addon_context.metadata, "message_type": "system"},
                start_time=request_start_time,
            )
            sys_result, sys_is_final = await self._execute_addon_pre_request(system_message, sys_context)
            if sys_result is not None and not sys_is_final:
                system_message = sys_result

        # Handle dry-run mode (after addons can intercept)
        if self.dry_run or addon_context.custom.get("dry_run"):
            input_tokens = await self.provider.count_tokens(prompt, self.model)
            output_tokens = max_tokens or 100  # Estimate
            cost = self.provider.calculate_cost(input_tokens, output_tokens, self.model)

            self._record_metrics(input_tokens, output_tokens, cost, request_id)

            response_dict = self._build_response_dict(
                content="[DRY RUN] Response would be generated here",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                request_id=request_id,
                dry_run=True,
            )
            
            addon_context.end_time = datetime.now()
            response_dict = await self._execute_addon_post_request(response_dict, addon_context)
            return response_dict

        # Build messages with potentially modified prompt and system message
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        # Estimate cost and check budget (use modified prompt)
        estimate = await self.provider.estimate_cost(prompt, self.model, max_tokens)
        estimated_cost = estimate["total_cost"]

        # Check budget
        try:
            self.cost_tracker.check_budget_available(estimated_cost)
        except BudgetExceededError as e:
            if has_addons:
                await self._handle_addon_error(e, addon_context)
            raise

        # Make the actual request with retry support
        max_retries = 3
        retry_count = addon_context.custom.get("retry_count", 0)
        
        for attempt in range(max_retries):
            try:
                response = await self.provider.chat(
                    messages=messages,
                    model=self.model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
                break  # Success, exit retry loop
                
            except Exception as e:
                if has_addons:
                    should_retry = await self._handle_addon_error(e, addon_context)
                    if should_retry and attempt < max_retries - 1:
                        retry_count += 1
                        addon_context.custom["retry_count"] = retry_count
                        # Exponential backoff
                        await asyncio.sleep(2 ** retry_count)
                        continue
                # Max retries reached or no retry requested
                raise

        # Extract metrics
        input_tokens = response["input_tokens"]
        output_tokens = response["output_tokens"]
        cost = self.provider.calculate_cost(input_tokens, output_tokens, self.model)

        # Record metrics
        self._record_metrics(input_tokens, output_tokens, cost, request_id)

        # Build response dict
        response_dict = self._build_response_dict(
            content=response["content"],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            request_id=request_id,
            finish_reason=response.get("finish_reason"),
        )

        # Execute post-request addons
        addon_context.end_time = datetime.now()
        response_dict = await self._execute_addon_post_request(response_dict, addon_context)

        return response_dict

    async def batch_generate(
        self,
        prompts: list[str],
        check_budget_per_item: bool = True,
        max_concurrent: int = 5,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        Generate responses for multiple prompts in batch.

        Args:
            prompts: List of prompts to process
            check_budget_per_item: If True, check budget before each item
            max_concurrent: Maximum number of concurrent requests
            **kwargs: Additional parameters passed to chat()

        Returns:
            List of response dictionaries

        Example:
            ```python
            prompts = [
                "Write a haiku about Python",
                "Write a haiku about JavaScript",
                "Write a haiku about Rust"
            ]
            responses = await session.batch_generate(prompts)
            for response in responses:
                print(response["content"])
            ```
        """
        if not self._is_active:
            await self.start()

        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_prompt(prompt: str) -> dict[str, Any]:
            async with semaphore:
                return await self.chat(prompt, **kwargs)

        # Process all prompts concurrently (with semaphore limiting concurrency)
        results = await asyncio.gather(*[process_prompt(p) for p in prompts], return_exceptions=True)

        # Convert exceptions to error dictionaries
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {
                        "error": str(result),
                        "prompt_index": i,
                        "success": False,
                    }
                )
            else:
                result["success"] = True
                processed_results.append(result)

        return processed_results

    def set_alert(self, threshold: float, callback: Callable[[float, float], None]) -> None:
        """
        Set a budget alert.

        Args:
            threshold: Budget usage threshold (0.0 to 1.0)
            callback: Function to call when threshold is reached

        Example:
            ```python
            def on_budget_alert(cost, budget):
                print(f"Warning: Used ${cost:.2f} of ${budget:.2f}")

            session.set_alert(0.75, on_budget_alert)
            ```
        """
        self.alert_manager.add_alert(threshold, callback)

    def add_addon(self, addon: BaseAddon) -> None:
        """
        Add an addon to the session.

        Args:
            addon: Addon instance
        """
        self.addon_manager.add_addon(addon)
    
    def get_addon_execution_log(self) -> list[dict[str, Any]]:
        """
        Get the addon execution log for debugging and monitoring.
        
        Returns:
            List of addon execution log entries
        """
        return self._addon_execution_log.copy()
    
    def clear_addon_execution_log(self) -> None:
        """Clear the addon execution log."""
        self._addon_execution_log.clear()
    
    def enable_addon_logging(self) -> None:
        """Enable addon execution logging."""
        self._log_addon_execution = True
    
    def disable_addon_logging(self) -> None:
        """Disable addon execution logging."""
        self._log_addon_execution = False
    
    def get_addon_execution_stats(self) -> dict[str, Any]:
        """
        Get statistics about addon execution.
        
        Returns:
            Dictionary with execution statistics
        """
        if not self._addon_execution_log:
            return {
                "total_executions": 0,
                "successful": 0,
                "failed": 0,
                "average_time_ms": 0.0,
                "by_addon": {},
                "by_hook": {},
            }
        
        total = len(self._addon_execution_log)
        successful = sum(1 for entry in self._addon_execution_log if entry.get("success", False))
        failed = total - successful
        avg_time = sum(entry.get("execution_time_ms", 0) for entry in self._addon_execution_log) / total
        
        by_addon: dict[str, dict[str, Any]] = {}
        by_hook: dict[str, dict[str, Any]] = {}
        
        for entry in self._addon_execution_log:
            addon_name = entry.get("addon", "unknown")
            hook = entry.get("hook", "unknown")
            
            # Count by addon
            if addon_name not in by_addon:
                by_addon[addon_name] = {"total": 0, "successful": 0, "failed": 0, "total_time_ms": 0.0}
            by_addon[addon_name]["total"] += 1
            if entry.get("success"):
                by_addon[addon_name]["successful"] += 1
            else:
                by_addon[addon_name]["failed"] += 1
            by_addon[addon_name]["total_time_ms"] += entry.get("execution_time_ms", 0)
            
            # Count by hook
            if hook not in by_hook:
                by_hook[hook] = {"total": 0, "successful": 0, "failed": 0, "total_time_ms": 0.0}
            by_hook[hook]["total"] += 1
            if entry.get("success"):
                by_hook[hook]["successful"] += 1
            else:
                by_hook[hook]["failed"] += 1
            by_hook[hook]["total_time_ms"] += entry.get("execution_time_ms", 0)
        
        # Calculate averages
        for addon_stats in by_addon.values():
            if addon_stats["total"] > 0:
                addon_stats["avg_time_ms"] = addon_stats["total_time_ms"] / addon_stats["total"]
        
        for hook_stats in by_hook.values():
            if hook_stats["total"] > 0:
                hook_stats["avg_time_ms"] = hook_stats["total_time_ms"] / hook_stats["total"]
        
        return {
            "total_executions": total,
            "successful": successful,
            "failed": failed,
            "average_time_ms": avg_time,
            "by_addon": by_addon,
            "by_hook": by_hook,
        }

    def export_to_dict(self) -> dict[str, Any]:
        """
        Export session data as a dictionary.

        Returns:
            Dictionary containing all session data

        Example:
            ```python
            data = session.export_to_dict()
            print(f"Total cost: ${data['cost_usd']:.4f}")
            ```
        """
        return {
            "session_id": self.session_id,
            "provider": self.provider.provider_name,
            "model": self.model,
            "dry_run": self.dry_run,
            "metadata": self.metadata,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "end_time": self._end_time.isoformat() if self._end_time else None,
            "duration_seconds": self.duration,
            "is_active": self._is_active,
            "request_count": self._request_count,
            "cost_usd": self.cost_usd,
            "tokens_used": self.tokens_used,
            "budget_remaining": self.budget_remaining,
            "cost_breakdown": self.cost_tracker.get_cost_breakdown(),
            "token_breakdown": self.token_monitor.get_usage_breakdown(),
            "addon_execution_stats": self.get_addon_execution_stats() if self._log_addon_execution else None,
        }

    async def export_to_json(self, filepath: str | Path) -> None:
        """
        Export session data to a JSON file.

        Args:
            filepath: Path to save the JSON file

        Example:
            ```python
            await session.export_to_json("session_data.json")
            ```
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        data = self.export_to_dict()

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    async def __aenter__(self) -> "LLMSession":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.end()

    def __repr__(self) -> str:
        """String representation of the session."""
        return (
            f"LLMSession(id={self.session_id[:8]}..., "
            f"provider={self.provider.provider_name}, "
            f"model={self.model}, "
            f"cost=${self.cost_usd:.4f}, "
            f"requests={self._request_count})"
        )

