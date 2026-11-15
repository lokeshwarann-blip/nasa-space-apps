from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

DISCLAIMER: str = "Simulated data, decision support, not a medical device."


class StatusEnum(str, Enum):
    NORMAL = "normal"
    WATCH = "watch"
    ACT = "act"
    CALL_GROUND = "call_ground"


class StatusIconEnum(str, Enum):
    CIRCLE_CHECK = "circle-check"
    TRIANGLE = "triangle"
    DIAMOND = "diamond"
    OCTAGON = "octagon"


class EvidenceLevelEnum(str, Enum):
    ESTABLISHED = "established"
    EMERGING = "emerging"
    ILLUSTRATIVE = "illustrative"


# Backward-compatible type aliases
Status = StatusEnum
StatusIcon = StatusIconEnum
EvidenceLevel = EvidenceLevelEnum


class BaseDisclaimedModel(BaseModel):
    """Base response model enforcing simulation decision-support disclaimer."""
    disclaimer: str = Field(
        default=DISCLAIMER,
        description="Simulated data, decision support, not a medical device.",
    )


# Backward-compatible alias for existing imports
Disclaimed = BaseDisclaimedModel


class SeriesPoint(BaseModel):
    t: str = Field(..., description="ISO 8601 timestamp of historical measurement")
    value: float = Field(..., description="Observed measurement value")


class ForecastPoint(BaseModel):
    t: str = Field(..., description="ISO 8601 timestamp of forecast horizon")
    low: float = Field(..., description="Lower prediction interval bound")
    high: float = Field(..., description="Upper prediction interval bound")


class BodySystem(BaseModel):
    name: Literal["heart", "lungs", "sleep_brain", "muscles_bones", "immune"] = Field(
        ..., description="Body system identifier"
    )
    status: StatusEnum = Field(..., description="System status indicator")
    status_icon: StatusIconEnum = Field(..., description="Status icon representation")
    value: float = Field(..., description="Current physiological telemetry value")
    unit: str = Field(..., description="Physical measurement unit")
    baseline_low: float = Field(..., description="Individual baseline lower bound")
    baseline_high: float = Field(..., description="Individual baseline upper bound")
    trend: str = Field(..., description="Physiological trend observation")
    evidence_level: EvidenceLevelEnum = Field(..., description="Strength of supporting operational evidence")
    series: list[SeriesPoint] = Field(default_factory=list, description="Historical trend observations")
    forecast: list[ForecastPoint] = Field(default_factory=list, description="Forward predictive uncertainty envelope")


class Readiness(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Readiness index from 0 to 100")
    status: StatusEnum = Field(..., description="Overall mission readiness status")
    status_icon: StatusIconEnum = Field(..., description="Readiness status icon")
    confidence: Literal["high", "medium", "low"] = Field(..., description="Measurement confidence level")
    updated_at: str = Field(..., description="ISO 8601 timestamp of latest readiness update")


class CrewStatus(BaseDisclaimedModel):
    crew_id: str = Field(..., description="Unique crew member identifier")
    readiness: Readiness = Field(..., description="Composite readiness assessment")
    body_systems: list[BodySystem] = Field(..., description="Status breakdown across core body systems")
    data_quality: Literal["good", "sensor_issue"] = Field(..., description="Telemetry data acquisition quality")


# Quests Schemas
class Quest(BaseModel):
    id: str = Field(..., description="Unique quest identifier")
    title: str = Field(..., description="Quest title")
    target: float = Field(..., description="Quantitative objective target")
    unit: str = Field(..., description="Unit of measurement for the target")
    period: str = Field(..., description="Frequency or timeframe (e.g. daily, weekly)")
    rationale: str = Field(..., description="Operational physiological rationale")
    source: str = Field(..., description="Scientific or operational citation source")
    evidence_level: EvidenceLevelEnum = Field(..., description="Evidence level")


class QuestsResponse(BaseDisclaimedModel):
    quests: list[Quest] = Field(..., description="Active operational quests")


class QuestLogRequest(BaseModel):
    event_id: str = Field(..., description="Identifier of the completed event or activity")


class QuestLogResponse(BaseDisclaimedModel):
    quest_id: str = Field(..., description="Identifier of the logged quest")
    event_id: str = Field(..., description="Linked activity event identifier")
    xp_gained: int = Field(..., description="Experience points gained")
    progress: float = Field(..., description="Current quest completion progress (0.0 to 1.0)")
    unlocked: list[str] = Field(default_factory=list, description="List of unlocked badges or operational perks")


class TeamStreakResponse(BaseDisclaimedModel):
    current_streak: int = Field(..., description="Active collective crew routine streak in days")
    longest_streak: int = Field(..., description="Longest historical team streak achieved")
    freeze_days_remaining: int = Field(..., description="Available freeze days to protect streak")
    last_activity_date: Optional[str] = Field(default=None, description="ISO timestamp of latest team routine")


# Science Context Schemas
class ScienceContextCard(BaseModel):
    id: str = Field(..., description="Unique scientific context card identifier")
    title: str = Field(..., description="Card title")
    plain_summary: str = Field(..., description="Plain language explanation of physiological mechanism")
    why_it_matters: str = Field(..., description="Operational importance for crew health and mission performance")
    evidence_level: EvidenceLevelEnum = Field(..., description="Scientific evidence classification")
    sources: list[str] = Field(..., description="Peer-reviewed research and mission operational sources")
    linked_signals: list[str] = Field(..., description="Associated physiological and environmental telemetry signals")
    unlocked: bool = Field(default=False, description="Whether this card has been unlocked via quest logging")


class ScienceContextResponse(BaseDisclaimedModel):
    cards: list[ScienceContextCard] = Field(..., description="Educational and decision-support science context cards")


# Immune-Stress Context Schemas
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
        return getattr(self, item)


# Pulse Measurements Schemas
class PulseMeasurementRequest(BaseModel):
    hr: float = Field(..., ge=20.0, le=250.0, description="Heart rate in beats per minute")
    hrv: Optional[float] = Field(default=None, ge=0.0, le=500.0, description="Heart rate variability (RMSSD) in ms")
    signal_quality: str = Field(..., description="Telemetry signal quality (good, fair, poor)")
    source: str = Field(..., description="Sensor acquisition hardware or method")


class PulseMeasurementResponse(BaseDisclaimedModel):
    status: Literal["accepted", "rejected"] = Field(..., description="Ingestion acceptance status")
    message: str = Field(..., description="Processing and context status message")
    recorded_at: str = Field(..., description="ISO 8601 ingestion timestamp")
    measurement_id: Optional[str] = Field(default=None, description="Generated telemetry record identifier")


# Scenario Schemas
class ScenarioType(str, Enum):
    COORDINATED_DRIFT = "coordinated_drift"
    SENSOR_FAULT = "sensor_fault"
    COMMS_BLACKOUT = "comms_blackout"
    DUST_STORM = "dust_storm"
    RESET = "reset"


class ScenarioRequest(BaseModel):
    type: ScenarioType = Field(..., description="Simulation scenario type to activate or reset")


class ScenarioResponse(BaseDisclaimedModel):
    active_scenario: ScenarioType = Field(..., description="Currently active scenario type")
    message: str = Field(..., description="Scenario activation details and operational context")
    started_at: str = Field(..., description="ISO 8601 scenario initiation timestamp")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Active scenario simulation parameters")


# Circadian Schemas
class EnvironmentProfile(BaseModel):
    light_lux: float = Field(..., description="Ambient illuminance in lux")
    color_temperature_k: int = Field(..., description="Correlated color temperature in Kelvin")
    blue_wavelength_attenuation: bool = Field(..., description="Whether blue spectrum attenuation is engaged")
    temperature_c: float = Field(..., description="Cabin ambient temperature in degrees Celsius")
    scheduled_dark_hours: float = Field(..., description="Scheduled sleep dark window duration in hours")


class CircadianResponse(BaseDisclaimedModel):
    crew_id: str = Field(..., description="Crew member identifier")
    phase_offset_hours: float = Field(..., description="Estimated circadian phase shift in hours relative to schedule")
    suggested_shift: float = Field(..., description="Recommended daily adjustment shift in hours")
    days_to_realign: int = Field(..., description="Estimated days required to achieve circadian alignment")
    model: str = Field(..., description="Circadian mathematical model identification")
    assumptions: list[str] = Field(..., description="Model baseline assumptions and operational caveats")
    environment_profile: EnvironmentProfile = Field(..., description="Current cabin environmental lighting and thermal profile")
