"""Immune-stress operational context evaluation.

Pure function calculating multi-signal immune-stress context from sleep duration,
heart rate variability (HRV), subjective stress self-reports, and cumulative radiation dose.
Thresholds are dynamically sourced from application configuration, not hard-coded.

Operational note: This provides decision-support physiological context, not clinical diagnosis.
"""
from typing import Any, Literal
from pydantic import BaseModel, Field

from src.core.config import ImmuneStressThresholds, get_settings


class ImmuneStressContext(BaseModel):
    """Operational context outcome for crew immune-stress evaluation."""
    status: Literal["normal", "watch", "act"] = Field(
        ..., description="Overall evaluated operational status: normal, watch, or act"
    )
    contributing_signals: list[str] = Field(
        default_factory=list,
        description="Telemetry signals contributing to elevated watch or act status"
    )
    note: str = Field(
        default="context, not diagnosis",
        description="Operational context reminder reinforcing non-diagnostic role"
    )
    signal_details: dict[str, Literal["normal", "watch", "act"]] = Field(
        default_factory=dict,
        description="Individual status classification for each evaluated telemetry signal"
    )

    def __getitem__(self, item: str) -> Any:
        """Allows dictionary-style subscript access (e.g. res['status'])."""
        return getattr(self, item)


def compute_immune_stress_context(
    sleep: float,
    hrv: float,
    stress_self_report: float,
    cumulative_dose: float,
    thresholds: ImmuneStressThresholds | None = None,
) -> ImmuneStressContext:
    """Pure function evaluating immune-stress context across four operational telemetry signals.

    Args:
        sleep: Sleep duration in hours for the monitoring window.
        hrv: Heart rate variability RMSSD in milliseconds.
        stress_self_report: Subjective stress assessment score on standard 1-5 scale.
        cumulative_dose: Cumulative absorbed radiation dose in mSv / mGy.
        thresholds: Configurable threshold boundaries. Defaults to config settings.

    Returns:
        ImmuneStressContext with status ('normal' | 'watch' | 'act'),
        contributing_signals list, and note 'context, not diagnosis'.
    """
    if thresholds is None:
        thresholds = get_settings().IMMUNE_STRESS_THRESHOLDS

    signal_levels: dict[str, Literal["normal", "watch", "act"]] = {}

    # 1. Sleep Duration (lower is worse)
    if sleep <= thresholds.sleep_act:
        signal_levels["sleep"] = "act"
    elif sleep <= thresholds.sleep_watch:
        signal_levels["sleep"] = "watch"
    else:
        signal_levels["sleep"] = "normal"

    # 2. HRV RMSSD (lower is worse)
    if hrv <= thresholds.hrv_act:
        signal_levels["hrv"] = "act"
    elif hrv <= thresholds.hrv_watch:
        signal_levels["hrv"] = "watch"
    else:
        signal_levels["hrv"] = "normal"

    # 3. Subjective Stress Self-Report (higher is worse)
    if stress_self_report >= thresholds.stress_act:
        signal_levels["stress_self_report"] = "act"
    elif stress_self_report >= thresholds.stress_watch:
        signal_levels["stress_self_report"] = "watch"
    else:
        signal_levels["stress_self_report"] = "normal"

    # 4. Cumulative Radiation Dose (higher is worse)
    if cumulative_dose >= thresholds.dose_act:
        signal_levels["cumulative_dose"] = "act"
    elif cumulative_dose >= thresholds.dose_watch:
        signal_levels["cumulative_dose"] = "watch"
    else:
        signal_levels["cumulative_dose"] = "normal"

    # Determine overall status and contributing signals
    act_signals = [sig for sig, lvl in signal_levels.items() if lvl == "act"]
    watch_signals = [sig for sig, lvl in signal_levels.items() if lvl == "watch"]

    if act_signals:
        overall_status: Literal["normal", "watch", "act"] = "act"
        # Include all signals that deviate from normal (act first, then watch)
        contributing = act_signals + watch_signals
    elif watch_signals:
        overall_status = "watch"
        contributing = watch_signals
    else:
        overall_status = "normal"
        contributing = []

    return ImmuneStressContext(
        status=overall_status,
        contributing_signals=contributing,
        note="context, not diagnosis",
        signal_details=signal_levels,
    )


# Alias for alternative naming convention
evaluate_immune_stress_context = compute_immune_stress_context
