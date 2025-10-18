"""Cost tracking and budget management."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ai_content_generator.core.exceptions import BudgetExceededError


@dataclass
class CostRecord:
    """Record of cost for a single request."""

    request_id: str
    model: str
    cost_usd: float
    input_tokens: int
    output_tokens: int
    timestamp: datetime = field(default_factory=datetime.now)


class CostTracker:
    """
    Track costs and enforce budget limits.

    Monitors spending across requests, enforces budget limits,
    and provides cost breakdowns and projections.
    """

    def __init__(self, budget_usd: Optional[float] = None) -> None:
        """
        Initialize the cost tracker.

        Args:
            budget_usd: Budget limit in USD (None for unlimited)

        Example:
            ```python
            tracker = CostTracker(budget_usd=10.0)
            ```
        """
        self._budget_usd = budget_usd
        self._total_cost = 0.0
        self._cost_records: list[CostRecord] = []
        self._cost_by_model: dict[str, float] = {}

    @property
    def budget_usd(self) -> Optional[float]:
        """Get the budget limit."""
        return self._budget_usd

    @budget_usd.setter
    def budget_usd(self, value: Optional[float]) -> None:
        """Set the budget limit."""
        if value is not None and value < 0:
            raise ValueError("Budget must be non-negative")
        self._budget_usd = value

    def record_cost(
        self,
        cost: float,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        request_id: Optional[str] = None,
    ) -> CostRecord:
        """
        Record cost for a request.

        Args:
            cost: Cost in USD
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            request_id: Optional request identifier

        Returns:
            CostRecord

        Example:
            ```python
            tracker = CostTracker(budget_usd=10.0)
            record = tracker.record_cost(
                cost=0.05,
                model="gpt-4",
                input_tokens=100,
                output_tokens=200
            )
            ```
        """
        if request_id is None:
            request_id = f"req_{len(self._cost_records) + 1}"

        record = CostRecord(
            request_id=request_id,
            model=model,
            cost_usd=cost,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        self._cost_records.append(record)
        self._total_cost += cost

        # Track by model
        if model not in self._cost_by_model:
            self._cost_by_model[model] = 0.0
        self._cost_by_model[model] += cost

        return record

    def get_total_cost(self) -> float:
        """
        Get total cost across all requests.

        Returns:
            Total cost in USD
        """
        return self._total_cost

    def get_remaining_budget(self) -> Optional[float]:
        """
        Get remaining budget.

        Returns:
            Remaining budget in USD, or None if no budget is set

        Example:
            ```python
            remaining = tracker.get_remaining_budget()
            if remaining is not None:
                print(f"Remaining: ${remaining:.4f}")
            ```
        """
        if self._budget_usd is None:
            return None
        return max(0.0, self._budget_usd - self._total_cost)

    def get_budget_usage_percentage(self) -> Optional[float]:
        """
        Get budget usage as a percentage.

        Returns:
            Percentage of budget used (0.0 to 1.0), or None if no budget is set
        """
        if self._budget_usd is None or self._budget_usd == 0:
            return None
        return min(1.0, self._total_cost / self._budget_usd)

    def check_budget_available(self, estimated_cost: float) -> bool:
        """
        Check if there's enough budget for an estimated cost.

        Args:
            estimated_cost: Estimated cost in USD

        Returns:
            True if budget allows the cost, False otherwise
            (always True if no budget is set)

        Raises:
            BudgetExceededError: If budget would be exceeded

        Example:
            ```python
            if tracker.check_budget_available(0.05):
                # Proceed with request
                pass
            ```
        """
        if self._budget_usd is None:
            return True

        projected_cost = self._total_cost + estimated_cost

        if projected_cost > self._budget_usd:
            raise BudgetExceededError(
                budget=self._budget_usd,
                cost=projected_cost,
                context={
                    "current_cost": self._total_cost,
                    "estimated_cost": estimated_cost,
                },
            )

        return True

    def get_cost_breakdown(self) -> dict[str, any]:
        """
        Get detailed breakdown of costs.

        Returns:
            Dictionary containing:
            - total_cost: Total cost in USD
            - budget: Budget limit (or None)
            - remaining_budget: Remaining budget (or None)
            - budget_usage_percentage: Percentage used (or None)
            - request_count: Number of requests
            - by_model: Cost breakdown by model
            - average_per_request: Average cost per request
            - records: List of all cost records

        Example:
            ```python
            breakdown = tracker.get_cost_breakdown()
            print(f"Total cost: ${breakdown['total_cost']:.4f}")
            print(f"By model: {breakdown['by_model']}")
            ```
        """
        request_count = len(self._cost_records)
        avg_per_request = self._total_cost / request_count if request_count > 0 else 0

        return {
            "total_cost": self._total_cost,
            "budget": self._budget_usd,
            "remaining_budget": self.get_remaining_budget(),
            "budget_usage_percentage": self.get_budget_usage_percentage(),
            "request_count": request_count,
            "by_model": dict(self._cost_by_model),
            "average_per_request": avg_per_request,
            "records": [
                {
                    "request_id": record.request_id,
                    "model": record.model,
                    "cost_usd": record.cost_usd,
                    "input_tokens": record.input_tokens,
                    "output_tokens": record.output_tokens,
                    "timestamp": record.timestamp.isoformat(),
                }
                for record in self._cost_records
            ],
        }

    def get_statistics(self) -> dict[str, float]:
        """
        Get statistical summary of costs.

        Returns:
            Dictionary containing min, max, mean, and median costs
        """
        if not self._cost_records:
            return {
                "min": 0.0,
                "max": 0.0,
                "mean": 0.0,
                "median": 0.0,
            }

        costs = [record.cost_usd for record in self._cost_records]
        costs_sorted = sorted(costs)

        n = len(costs)
        median = (
            costs_sorted[n // 2]
            if n % 2 == 1
            else (costs_sorted[n // 2 - 1] + costs_sorted[n // 2]) / 2
        )

        return {
            "min": min(costs),
            "max": max(costs),
            "mean": sum(costs) / n,
            "median": median,
        }

    def reset(self) -> None:
        """
        Reset all cost tracking (but keep budget).

        Clears all cost records and resets total cost to zero.
        The budget limit is preserved.
        """
        self._cost_records.clear()
        self._total_cost = 0.0
        self._cost_by_model.clear()

    def __repr__(self) -> str:
        """String representation of the tracker."""
        budget_str = f"${self._budget_usd:.2f}" if self._budget_usd else "unlimited"
        return (
            f"CostTracker(total_cost=${self._total_cost:.4f}, "
            f"budget={budget_str}, requests={len(self._cost_records)})"
        )

