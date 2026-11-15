"""Unit tests for immune-stress operational context evaluation.

Tests cover:
- Normal, watch, and act level classifications.
- Exact boundary conditions for all four signals (sleep, HRV, stress, cumulative dose).
- Multi-signal compounding scenarios.
- Threshold configuration override validation (verifying thresholds live in config, not hard-coded).
- Purity and non-diagnostic wording compliance ("context, not diagnosis").
"""
import pytest
from src.core.config import ImmuneStressThresholds
from src.modules.clinical.immune_stress import (
    ImmuneStressContext,
    compute_immune_stress_context,
    evaluate_immune_stress_context,
)


class TestImmuneStressContext:
    """Unit test suite for pure immune-stress context function."""

    @pytest.fixture
    def default_thresholds(self) -> ImmuneStressThresholds:
        return ImmuneStressThresholds(
            sleep_act=5.0,
            sleep_watch=6.5,
            hrv_act=25.0,
            hrv_watch=40.0,
            stress_watch=3.0,
            stress_act=4.5,
            dose_watch=50.0,
            dose_act=100.0,
        )

    # 1. Normal Level Tests
    def test_all_nominal_returns_normal(self, default_thresholds):
        """All signals within healthy operational range evaluate to NORMAL."""
        res = compute_immune_stress_context(
            sleep=8.0,
            hrv=55.0,
            stress_self_report=1.5,
            cumulative_dose=10.0,
            thresholds=default_thresholds,
        )
        assert res.status == "normal"
        assert res["status"] == "normal"
        assert res.contributing_signals == []
        assert res.note == "context, not diagnosis"
        assert res.signal_details == {
            "sleep": "normal",
            "hrv": "normal",
            "stress_self_report": "normal",
            "cumulative_dose": "normal",
        }

    # 2. Watch Level Tests for Each Signal
    def test_sleep_watch_level(self, default_thresholds):
        """Sleep in watch range (5.0 < sleep <= 6.5) triggers WATCH with sleep contributing."""
        res = compute_immune_stress_context(
            sleep=6.0,
            hrv=55.0,
            stress_self_report=1.5,
            cumulative_dose=10.0,
            thresholds=default_thresholds,
        )
        assert res.status == "watch"
        assert res.contributing_signals == ["sleep"]
        assert res.note == "context, not diagnosis"

    def test_hrv_watch_level(self, default_thresholds):
        """HRV in watch range (25.0 < hrv <= 40.0) triggers WATCH with hrv contributing."""
        res = compute_immune_stress_context(
            sleep=7.5,
            hrv=35.0,
            stress_self_report=1.5,
            cumulative_dose=10.0,
            thresholds=default_thresholds,
        )
        assert res.status == "watch"
        assert res.contributing_signals == ["hrv"]

    def test_stress_watch_level(self, default_thresholds):
        """Stress self-report in watch range (3.0 <= stress < 4.5) triggers WATCH."""
        res = compute_immune_stress_context(
            sleep=7.5,
            hrv=55.0,
            stress_self_report=3.5,
            cumulative_dose=10.0,
            thresholds=default_thresholds,
        )
        assert res.status == "watch"
        assert res.contributing_signals == ["stress_self_report"]

    def test_dose_watch_level(self, default_thresholds):
        """Cumulative radiation dose in watch range (50.0 <= dose < 100.0) triggers WATCH."""
        res = compute_immune_stress_context(
            sleep=7.5,
            hrv=55.0,
            stress_self_report=1.5,
            cumulative_dose=75.0,
            thresholds=default_thresholds,
        )
        assert res.status == "watch"
        assert res.contributing_signals == ["cumulative_dose"]

    # 3. Act Level Tests for Each Signal
    def test_sleep_act_level(self, default_thresholds):
        """Sleep <= 5.0 hours triggers ACT with sleep contributing."""
        res = compute_immune_stress_context(
            sleep=4.5,
            hrv=55.0,
            stress_self_report=1.5,
            cumulative_dose=10.0,
            thresholds=default_thresholds,
        )
        assert res.status == "act"
        assert "sleep" in res.contributing_signals

    def test_hrv_act_level(self, default_thresholds):
        """HRV <= 25.0 ms triggers ACT with hrv contributing."""
        res = compute_immune_stress_context(
            sleep=7.5,
            hrv=20.0,
            stress_self_report=1.5,
            cumulative_dose=10.0,
            thresholds=default_thresholds,
        )
        assert res.status == "act"
        assert "hrv" in res.contributing_signals

    def test_stress_act_level(self, default_thresholds):
        """Stress >= 4.5 triggers ACT with stress_self_report contributing."""
        res = compute_immune_stress_context(
            sleep=7.5,
            hrv=55.0,
            stress_self_report=4.8,
            cumulative_dose=10.0,
            thresholds=default_thresholds,
        )
        assert res.status == "act"
        assert "stress_self_report" in res.contributing_signals

    def test_dose_act_level(self, default_thresholds):
        """Cumulative dose >= 100.0 mSv triggers ACT with cumulative_dose contributing."""
        res = compute_immune_stress_context(
            sleep=7.5,
            hrv=55.0,
            stress_self_report=1.5,
            cumulative_dose=120.0,
            thresholds=default_thresholds,
        )
        assert res.status == "act"
        assert "cumulative_dose" in res.contributing_signals

    # 4. Exact Boundary Condition Tests
    def test_sleep_boundary_conditions(self, default_thresholds):
        """Tests exact boundary thresholds for sleep."""
        # Exactly at sleep_watch (6.5) -> WATCH
        res_watch_exact = compute_immune_stress_context(
            sleep=6.5, hrv=55.0, stress_self_report=1.5, cumulative_dose=10.0, thresholds=default_thresholds
        )
        assert res_watch_exact.status == "watch"
        assert "sleep" in res_watch_exact.contributing_signals

        # Just above sleep_watch (6.51) -> NORMAL
        res_normal = compute_immune_stress_context(
            sleep=6.51, hrv=55.0, stress_self_report=1.5, cumulative_dose=10.0, thresholds=default_thresholds
        )
        assert res_normal.status == "normal"

        # Exactly at sleep_act (5.0) -> ACT
        res_act_exact = compute_immune_stress_context(
            sleep=5.0, hrv=55.0, stress_self_report=1.5, cumulative_dose=10.0, thresholds=default_thresholds
        )
        assert res_act_exact.status == "act"
        assert "sleep" in res_act_exact.contributing_signals

        # Just above sleep_act (5.01) -> WATCH
        res_watch_above = compute_immune_stress_context(
            sleep=5.01, hrv=55.0, stress_self_report=1.5, cumulative_dose=10.0, thresholds=default_thresholds
        )
        assert res_watch_above.status == "watch"

    def test_hrv_boundary_conditions(self, default_thresholds):
        """Tests exact boundary thresholds for HRV."""
        # Exactly at hrv_watch (40.0) -> WATCH
        res_watch = compute_immune_stress_context(
            sleep=7.5, hrv=40.0, stress_self_report=1.5, cumulative_dose=10.0, thresholds=default_thresholds
        )
        assert res_watch.status == "watch"

        # Just above hrv_watch (40.1) -> NORMAL
        res_normal = compute_immune_stress_context(
            sleep=7.5, hrv=40.1, stress_self_report=1.5, cumulative_dose=10.0, thresholds=default_thresholds
        )
        assert res_normal.status == "normal"

        # Exactly at hrv_act (25.0) -> ACT
        res_act = compute_immune_stress_context(
            sleep=7.5, hrv=25.0, stress_self_report=1.5, cumulative_dose=10.0, thresholds=default_thresholds
        )
        assert res_act.status == "act"

        # Just above hrv_act (25.1) -> WATCH
        res_watch_above = compute_immune_stress_context(
            sleep=7.5, hrv=25.1, stress_self_report=1.5, cumulative_dose=10.0, thresholds=default_thresholds
        )
        assert res_watch_above.status == "watch"

    def test_stress_boundary_conditions(self, default_thresholds):
        """Tests exact boundary thresholds for stress self-report."""
        # Exactly at stress_watch (3.0) -> WATCH
        res_watch = compute_immune_stress_context(
            sleep=7.5, hrv=55.0, stress_self_report=3.0, cumulative_dose=10.0, thresholds=default_thresholds
        )
        assert res_watch.status == "watch"

        # Just below stress_watch (2.99) -> NORMAL
        res_normal = compute_immune_stress_context(
            sleep=7.5, hrv=55.0, stress_self_report=2.99, cumulative_dose=10.0, thresholds=default_thresholds
        )
        assert res_normal.status == "normal"

        # Exactly at stress_act (4.5) -> ACT
        res_act = compute_immune_stress_context(
            sleep=7.5, hrv=55.0, stress_self_report=4.5, cumulative_dose=10.0, thresholds=default_thresholds
        )
        assert res_act.status == "act"

        # Just below stress_act (4.49) -> WATCH
        res_watch_below = compute_immune_stress_context(
            sleep=7.5, hrv=55.0, stress_self_report=4.49, cumulative_dose=10.0, thresholds=default_thresholds
        )
        assert res_watch_below.status == "watch"

    def test_dose_boundary_conditions(self, default_thresholds):
        """Tests exact boundary thresholds for cumulative radiation dose."""
        # Exactly at dose_watch (50.0) -> WATCH
        res_watch = compute_immune_stress_context(
            sleep=7.5, hrv=55.0, stress_self_report=1.5, cumulative_dose=50.0, thresholds=default_thresholds
        )
        assert res_watch.status == "watch"

        # Just below dose_watch (49.9) -> NORMAL
        res_normal = compute_immune_stress_context(
            sleep=7.5, hrv=55.0, stress_self_report=1.5, cumulative_dose=49.9, thresholds=default_thresholds
        )
        assert res_normal.status == "normal"

        # Exactly at dose_act (100.0) -> ACT
        res_act = compute_immune_stress_context(
            sleep=7.5, hrv=55.0, stress_self_report=1.5, cumulative_dose=100.0, thresholds=default_thresholds
        )
        assert res_act.status == "act"

        # Just below dose_act (99.9) -> WATCH
        res_watch_below = compute_immune_stress_context(
            sleep=7.5, hrv=55.0, stress_self_report=1.5, cumulative_dose=99.9, thresholds=default_thresholds
        )
        assert res_watch_below.status == "watch"

    # 5. Multi-Signal Compounding
    def test_multiple_watch_signals(self, default_thresholds):
        """Multiple watch-level signals list all contributing signals."""
        res = compute_immune_stress_context(
            sleep=5.8,
            hrv=32.0,
            stress_self_report=3.8,
            cumulative_dose=65.0,
            thresholds=default_thresholds,
        )
        assert res.status == "watch"
        assert set(res.contributing_signals) == {"sleep", "hrv", "stress_self_report", "cumulative_dose"}

    def test_mixed_act_and_watch_signals(self, default_thresholds):
        """ACT signals take precedence for overall status while all non-normal signals are reported."""
        res = compute_immune_stress_context(
            sleep=4.2,  # act
            hrv=35.0,  # watch
            stress_self_report=2.0,  # normal
            cumulative_dose=110.0,  # act
            thresholds=default_thresholds,
        )
        assert res.status == "act"
        assert "sleep" in res.contributing_signals
        assert "cumulative_dose" in res.contributing_signals
        assert "hrv" in res.contributing_signals
        assert "stress_self_report" not in res.contributing_signals

    # 6. Thresholds Live in Config (Not Hardcoded)
    def test_custom_thresholds_override(self):
        """Verifies thresholds can be customized via config and are not hard-coded."""
        custom = ImmuneStressThresholds(
            sleep_act=4.0,
            sleep_watch=5.0,
            hrv_act=15.0,
            hrv_watch=30.0,
            stress_watch=4.0,
            stress_act=4.8,
            dose_watch=80.0,
            dose_act=150.0,
        )
        # sleep=5.5 would be WATCH under default (6.5), but is NORMAL under custom (5.0)
        res = compute_immune_stress_context(
            sleep=5.5,
            hrv=35.0,
            stress_self_report=3.5,
            cumulative_dose=70.0,
            thresholds=custom,
        )
        assert res.status == "normal"
        assert res.contributing_signals == []

    # 7. Function Purity and Aliasing
    def test_pure_function_deterministic(self, default_thresholds):
        """Repeated invocations with identical parameters yield identical results with zero side effects."""
        res1 = compute_immune_stress_context(6.0, 35.0, 3.2, 55.0, default_thresholds)
        res2 = compute_immune_stress_context(6.0, 35.0, 3.2, 55.0, default_thresholds)
        res3 = evaluate_immune_stress_context(6.0, 35.0, 3.2, 55.0, default_thresholds)

        assert res1.model_dump() == res2.model_dump() == res3.model_dump()
        assert res1.note == "context, not diagnosis"
