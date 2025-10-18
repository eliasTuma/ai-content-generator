"""Budget alert system for monitoring spending thresholds."""

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional


@dataclass
class Alert:
    """
    Budget alert configuration.

    Represents a threshold at which an alert should be triggered.
    """

    threshold: float  # Alert threshold (0.0 to 1.0, representing percentage)
    callback: Callable[[float, float], None]  # Callback function(current_cost, budget)
    triggered: bool = False
    trigger_time: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Validate threshold value."""
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError(f"Threshold must be between 0.0 and 1.0, got {self.threshold}")


class AlertManager:
    """
    Manage budget alerts and trigger callbacks.

    Monitors budget usage and triggers alerts when thresholds are reached.
    """

    def __init__(self) -> None:
        """Initialize the alert manager."""
        self._alerts: list[Alert] = []

    def add_alert(
        self, threshold: float, callback: Callable[[float, float], None]
    ) -> Alert:
        """
        Register a new alert.

        Args:
            threshold: Budget usage threshold (0.0 to 1.0)
                      e.g., 0.5 = 50%, 0.75 = 75%
            callback: Function to call when threshold is reached.
                     Receives (current_cost, budget) as arguments.

        Returns:
            The created Alert object

        Raises:
            ValueError: If threshold is not between 0.0 and 1.0

        Example:
            ```python
            def on_alert(cost, budget):
                print(f"Alert! Used ${cost:.2f} of ${budget:.2f}")

            manager = AlertManager()
            manager.add_alert(threshold=0.5, callback=on_alert)
            ```
        """
        alert = Alert(threshold=threshold, callback=callback)
        self._alerts.append(alert)
        # Sort alerts by threshold for efficient checking
        self._alerts.sort(key=lambda a: a.threshold)
        return alert

    def check_alerts(self, current_cost: float, budget: float) -> list[Alert]:
        """
        Check if any alerts should be triggered.

        Args:
            current_cost: Current spending in USD
            budget: Total budget in USD

        Returns:
            List of alerts that were triggered

        Example:
            ```python
            triggered = manager.check_alerts(
                current_cost=5.0,
                budget=10.0
            )
            print(f"{len(triggered)} alerts triggered")
            ```
        """
        if budget <= 0:
            return []

        usage_percentage = current_cost / budget
        triggered_alerts: list[Alert] = []

        for alert in self._alerts:
            # Only trigger if not already triggered and threshold is reached
            if not alert.triggered and usage_percentage >= alert.threshold:
                alert.triggered = True
                alert.trigger_time = datetime.now()
                triggered_alerts.append(alert)

                # Call the callback
                try:
                    alert.callback(current_cost, budget)
                except Exception as e:
                    # Log error but don't fail the check
                    print(f"Error in alert callback: {e}")

        return triggered_alerts

    def reset_alerts(self) -> None:
        """
        Reset all alerts to untriggered state.

        Useful when starting a new session or resetting budget tracking.
        """
        for alert in self._alerts:
            alert.triggered = False
            alert.trigger_time = None

    def remove_alert(self, alert: Alert) -> bool:
        """
        Remove an alert from the manager.

        Args:
            alert: Alert object to remove

        Returns:
            True if alert was removed, False if not found
        """
        try:
            self._alerts.remove(alert)
            return True
        except ValueError:
            return False

    def clear_alerts(self) -> None:
        """Remove all alerts."""
        self._alerts.clear()

    def get_triggered_alerts(self) -> list[Alert]:
        """
        Get list of alerts that have been triggered.

        Returns:
            List of triggered Alert objects
        """
        return [alert for alert in self._alerts if alert.triggered]

    def get_pending_alerts(self) -> list[Alert]:
        """
        Get list of alerts that haven't been triggered yet.

        Returns:
            List of pending Alert objects
        """
        return [alert for alert in self._alerts if not alert.triggered]

    def get_all_alerts(self) -> list[Alert]:
        """
        Get all registered alerts.

        Returns:
            List of all Alert objects
        """
        return list(self._alerts)

    def __len__(self) -> int:
        """Get number of registered alerts."""
        return len(self._alerts)

    def __repr__(self) -> str:
        """String representation of the alert manager."""
        triggered = len(self.get_triggered_alerts())
        total = len(self._alerts)
        return f"AlertManager(alerts={total}, triggered={triggered})"

