"""Session manager for LLM interactions with budget tracking."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional
from uuid import uuid4

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

        # Session state
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._is_active = False
        self._request_count = 0
        self._addons: list[Any] = []  # Will be properly typed when addon system is implemented

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

        # Build messages
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        # Estimate cost and check budget
        if not self.dry_run:
            estimate = await self.provider.estimate_cost(prompt, self.model, max_tokens)
            estimated_cost = estimate["total_cost"]

            # Check budget
            try:
                self.cost_tracker.check_budget_available(estimated_cost)
            except BudgetExceededError:
                raise

        # Dry run mode
        if self.dry_run:
            input_tokens = await self.provider.count_tokens(prompt, self.model)
            output_tokens = max_tokens or 100  # Estimate
            cost = self.provider.calculate_cost(input_tokens, output_tokens, self.model)

            # Record metrics
            self.token_monitor.record_usage(input_tokens, output_tokens, self.model, request_id)
            self.cost_tracker.record_cost(cost, self.model, input_tokens, output_tokens, request_id)
            self._request_count += 1

            return {
                "content": "[DRY RUN] Response would be generated here",
                "model": self.model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost,
                "request_id": request_id,
                "dry_run": True,
            }

        # Execute pre-request addons
        # TODO: Implement addon pipeline when addon system is ready

        # Make the actual request
        response = await self.provider.chat(
            messages=messages,
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        # Extract metrics
        input_tokens = response["input_tokens"]
        output_tokens = response["output_tokens"]
        cost = self.provider.calculate_cost(input_tokens, output_tokens, self.model)

        # Record metrics
        self.token_monitor.record_usage(input_tokens, output_tokens, self.model, request_id)
        self.cost_tracker.record_cost(cost, self.model, input_tokens, output_tokens, request_id)
        self._request_count += 1

        # Check alerts
        if self.cost_tracker.budget_usd is not None:
            self.alert_manager.check_alerts(self.cost_usd, self.cost_tracker.budget_usd)

        # Execute post-request addons
        # TODO: Implement addon pipeline when addon system is ready

        # Build response
        return {
            "content": response["content"],
            "model": response["model"],
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost,
            "request_id": request_id,
            "finish_reason": response.get("finish_reason"),
        }

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

    def add_addon(self, addon: Any) -> None:
        """
        Add an addon to the session.

        Args:
            addon: Addon instance

        Note:
            Full addon system will be implemented in a future phase.
        """
        self._addons.append(addon)

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

