"""Token monitoring and tracking."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class TokenUsage:
    """Record of token usage for a single request."""

    request_id: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def tokens(self) -> int:
        """Get total tokens (alias for total_tokens)."""
        return self.total_tokens


class TokenMonitor:
    """
    Monitor and track token usage across requests.

    Tracks input, output, and total tokens per request and provides
    statistics and breakdowns.
    """

    def __init__(self) -> None:
        """Initialize the token monitor."""
        self._usage_records: list[TokenUsage] = []
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._total_tokens = 0
        self._tokens_by_model: dict[str, dict[str, int]] = {}

    def record_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str,
        request_id: Optional[str] = None,
    ) -> TokenUsage:
        """
        Record token usage for a request.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model identifier
            request_id: Optional request identifier

        Returns:
            TokenUsage record

        Example:
            ```python
            monitor = TokenMonitor()
            usage = monitor.record_usage(
                input_tokens=100,
                output_tokens=200,
                model="gpt-4"
            )
            ```
        """
        if request_id is None:
            request_id = f"req_{len(self._usage_records) + 1}"

        total = input_tokens + output_tokens

        usage = TokenUsage(
            request_id=request_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total,
        )

        self._usage_records.append(usage)
        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens
        self._total_tokens += total

        # Track by model
        if model not in self._tokens_by_model:
            self._tokens_by_model[model] = {
                "input": 0,
                "output": 0,
                "total": 0,
            }

        self._tokens_by_model[model]["input"] += input_tokens
        self._tokens_by_model[model]["output"] += output_tokens
        self._tokens_by_model[model]["total"] += total

        return usage

    def get_total_tokens(self) -> int:
        """
        Get total tokens used across all requests.

        Returns:
            Total token count
        """
        return self._total_tokens

    def get_total_input_tokens(self) -> int:
        """
        Get total input tokens used.

        Returns:
            Total input token count
        """
        return self._total_input_tokens

    def get_total_output_tokens(self) -> int:
        """
        Get total output tokens used.

        Returns:
            Total output token count
        """
        return self._total_output_tokens

    def get_usage_breakdown(self) -> dict[str, any]:
        """
        Get detailed breakdown of token usage.

        Returns:
            Dictionary containing:
            - total_tokens: Total tokens across all requests
            - total_input_tokens: Total input tokens
            - total_output_tokens: Total output tokens
            - request_count: Number of requests
            - by_model: Token breakdown by model
            - average_per_request: Average tokens per request
            - records: List of all usage records

        Example:
            ```python
            breakdown = monitor.get_usage_breakdown()
            print(f"Total tokens: {breakdown['total_tokens']}")
            print(f"Average per request: {breakdown['average_per_request']}")
            ```
        """
        request_count = len(self._usage_records)
        avg_per_request = self._total_tokens / request_count if request_count > 0 else 0

        return {
            "total_tokens": self._total_tokens,
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
            "request_count": request_count,
            "by_model": dict(self._tokens_by_model),
            "average_per_request": avg_per_request,
            "records": [
                {
                    "request_id": record.request_id,
                    "model": record.model,
                    "input_tokens": record.input_tokens,
                    "output_tokens": record.output_tokens,
                    "total_tokens": record.total_tokens,
                    "timestamp": record.timestamp.isoformat(),
                }
                for record in self._usage_records
            ],
        }

    def get_statistics(self) -> dict[str, float]:
        """
        Get statistical summary of token usage.

        Returns:
            Dictionary containing min, max, mean, and median token counts

        Example:
            ```python
            stats = monitor.get_statistics()
            print(f"Average tokens: {stats['mean']:.2f}")
            print(f"Max tokens: {stats['max']}")
            ```
        """
        if not self._usage_records:
            return {
                "min": 0,
                "max": 0,
                "mean": 0,
                "median": 0,
            }

        token_counts = [record.total_tokens for record in self._usage_records]
        token_counts_sorted = sorted(token_counts)

        n = len(token_counts)
        median = (
            token_counts_sorted[n // 2]
            if n % 2 == 1
            else (token_counts_sorted[n // 2 - 1] + token_counts_sorted[n // 2]) / 2
        )

        return {
            "min": min(token_counts),
            "max": max(token_counts),
            "mean": sum(token_counts) / n,
            "median": median,
        }

    def reset(self) -> None:
        """
        Reset all token tracking.

        Clears all usage records and resets counters to zero.
        """
        self._usage_records.clear()
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._total_tokens = 0
        self._tokens_by_model.clear()

    def __repr__(self) -> str:
        """String representation of the monitor."""
        return (
            f"TokenMonitor(total_tokens={self._total_tokens}, "
            f"requests={len(self._usage_records)})"
        )

