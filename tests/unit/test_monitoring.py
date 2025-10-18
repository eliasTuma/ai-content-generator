"""Tests for monitoring components."""

import pytest
from ai_content_generator.monitoring import (
    TokenMonitor,
    CostTracker,
    AlertManager,
    Alert,
)
from ai_content_generator.core.exceptions import BudgetExceededError


class TestTokenMonitor:
    """Tests for TokenMonitor."""
    
    def test_record_usage(self):
        """Test recording token usage."""
        monitor = TokenMonitor()
        
        usage = monitor.record_usage(
            input_tokens=100,
            output_tokens=50,
            model="gpt-5-nano",
            request_id="req-123"
        )
        
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.total_tokens == 150
        assert usage.model == "gpt-5-nano"
    
    def test_get_total_tokens(self):
        """Test getting total tokens."""
        monitor = TokenMonitor()
        
        monitor.record_usage(100, 50, "gpt-5-nano")
        monitor.record_usage(200, 100, "gpt-5-mini")
        
        assert monitor.get_total_tokens() == 450
        assert monitor.get_total_input_tokens() == 300
        assert monitor.get_total_output_tokens() == 150
    
    def test_get_usage_breakdown(self):
        """Test getting usage breakdown by model."""
        monitor = TokenMonitor()
        
        monitor.record_usage(100, 50, "gpt-5-nano")
        monitor.record_usage(200, 100, "gpt-5-nano")
        monitor.record_usage(150, 75, "gpt-5-mini")
        
        breakdown = monitor.get_usage_breakdown()
        
        assert "gpt-5-nano" in breakdown
        assert breakdown["gpt-5-nano"]["total"] == 450
        assert breakdown["gpt-5-mini"]["total"] == 225
    
    def test_reset(self):
        """Test resetting monitor."""
        monitor = TokenMonitor()
        
        monitor.record_usage(100, 50, "gpt-5-nano")
        monitor.reset()
        
        assert monitor.get_total_tokens() == 0


class TestCostTracker:
    """Tests for CostTracker."""
    
    def test_record_cost(self):
        """Test recording cost."""
        tracker = CostTracker(budget_usd=10.0)
        
        record = tracker.record_cost(
            cost_usd=0.5,
            request_id="req-123",
            model="gpt-5-nano",
            input_tokens=100,
            output_tokens=50
        )
        
        assert record.cost_usd == 0.5
        assert record.model == "gpt-5-nano"
    
    def test_get_total_cost(self):
        """Test getting total cost."""
        tracker = CostTracker(budget_usd=10.0)
        
        tracker.record_cost(0.5, "req-1", "gpt-5-nano", 100, 50)
        tracker.record_cost(1.0, "req-2", "gpt-5-mini", 200, 100)
        
        assert tracker.get_total_cost() == 1.5
    
    def test_get_remaining_budget(self):
        """Test getting remaining budget."""
        tracker = CostTracker(budget_usd=10.0)
        
        tracker.record_cost(3.0, "req-1", "gpt-5-nano", 100, 50)
        
        assert tracker.get_remaining_budget() == 7.0
    
    def test_check_budget_available(self):
        """Test checking budget availability."""
        tracker = CostTracker(budget_usd=10.0)
        
        tracker.record_cost(8.0, "req-1", "gpt-5-nano", 100, 50)
        
        assert tracker.check_budget_available(1.0) is True
        assert tracker.check_budget_available(3.0) is False
    
    def test_budget_exceeded_error(self):
        """Test budget exceeded error."""
        tracker = CostTracker(budget_usd=1.0)
        
        with pytest.raises(BudgetExceededError):
            tracker.record_cost(1.5, "req-1", "gpt-5-nano", 100, 50)
    
    def test_unlimited_budget(self):
        """Test unlimited budget (None)."""
        tracker = CostTracker(budget_usd=None)
        
        tracker.record_cost(1000.0, "req-1", "gpt-5-nano", 100, 50)
        
        assert tracker.check_budget_available(1000.0) is True


class TestAlertManager:
    """Tests for AlertManager."""
    
    def test_add_alert(self):
        """Test adding alert."""
        manager = AlertManager()
        
        def callback(current, budget):
            pass
        
        alert = manager.add_alert(0.5, callback)
        
        assert alert.threshold == 0.5
        assert alert.triggered is False
    
    def test_check_alerts(self):
        """Test checking and triggering alerts."""
        manager = AlertManager()
        triggered_alerts = []
        
        def callback(current, budget):
            triggered_alerts.append((current, budget))
        
        manager.add_alert(0.5, callback)
        manager.add_alert(0.8, callback)
        
        # Below threshold
        manager.check_alerts(3.0, 10.0)
        assert len(triggered_alerts) == 0
        
        # Trigger 50% alert
        manager.check_alerts(5.0, 10.0)
        assert len(triggered_alerts) == 1
        
        # Trigger 80% alert
        manager.check_alerts(8.0, 10.0)
        assert len(triggered_alerts) == 2
    
    def test_alert_only_triggers_once(self):
        """Test that alerts only trigger once."""
        manager = AlertManager()
        trigger_count = [0]
        
        def callback(current, budget):
            trigger_count[0] += 1
        
        manager.add_alert(0.5, callback)
        
        manager.check_alerts(5.0, 10.0)
        manager.check_alerts(6.0, 10.0)
        manager.check_alerts(7.0, 10.0)
        
        assert trigger_count[0] == 1
    
    def test_reset_alerts(self):
        """Test resetting alerts."""
        manager = AlertManager()
        
        def callback(current, budget):
            pass
        
        manager.add_alert(0.5, callback)
        manager.check_alerts(5.0, 10.0)
        
        manager.reset_alerts()
        
        triggered = manager.get_triggered_alerts()
        assert len(triggered) == 0

