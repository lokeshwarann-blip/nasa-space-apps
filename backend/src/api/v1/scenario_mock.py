from datetime import datetime, timezone
from fastapi import APIRouter, status
from src.schemas.astronaut import (
    ScenarioRequest,
    ScenarioResponse,
    ScenarioType,
)

router = APIRouter(prefix="/scenario", tags=["Scenario"])

SCENARIO_CONFIGS = {
    ScenarioType.COORDINATED_DRIFT: (
        "Coordinated multi-signal physiological drift simulation active. Monitoring cross-system trend shifts.",
        {"drift_rate_sd_per_day": 0.25, "affected_signals": ["heart_rate", "spo2", "sleep_duration", "body_temperature"]},
    ),
    ScenarioType.SENSOR_FAULT: (
        "Sensor fault simulation active. Injected telemetry flatline and signal corruption.",
        {"dropout_rate": 0.20, "faulty_sensors": ["heart_rate", "pulse_oximeter"]},
    ),
    ScenarioType.COMMS_BLACKOUT: (
        "Communications blackout scenario active. Autonomous decision support mode engaged.",
        {"expected_duration_hours": 48.0, "uplink_available": False},
    ),
    ScenarioType.DUST_STORM: (
        "Surface dust storm scenario active. Solar irradiance attenuation and elevated environmental stress active.",
        {"solar_array_efficiency": 0.45, "ambient_dust_index": 3.8},
    ),
    ScenarioType.RESET: (
        "Simulation reset to nominal baseline conditions. All synthetic perturbations cleared.",
        {},
    ),
}

_active_scenario: ScenarioType = ScenarioType.RESET


def get_active_scenario() -> ScenarioType:
    """Returns the currently active simulation scenario."""
    return _active_scenario


def set_active_scenario_state(scenario: ScenarioType) -> None:
    """Updates the currently active simulation scenario."""
    global _active_scenario
    _active_scenario = scenario


@router.get(
    "",
    response_model=ScenarioResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Active Simulation Scenario",
    description="Returns the currently active simulation scenario and parameters.",
)
async def get_scenario() -> ScenarioResponse:
    """Returns active simulation scenario status."""
    message, params = SCENARIO_CONFIGS[_active_scenario]
    return ScenarioResponse(
        active_scenario=_active_scenario,
        message=message,
        started_at=datetime.now(timezone.utc).isoformat(),
        parameters=params,
    )


@router.post(
    "",
    response_model=ScenarioResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate Simulation Scenario",
    description="Switches the simulation environment to a test scenario (coordinated_drift, sensor_fault, comms_blackout, dust_storm, or reset).",
)
async def set_scenario(payload: ScenarioRequest) -> ScenarioResponse:
    """Switches or resets active simulation scenarios."""
    set_active_scenario_state(payload.type)
    message, params = SCENARIO_CONFIGS[payload.type]
    return ScenarioResponse(
        active_scenario=payload.type,
        message=message,
        started_at=datetime.now(timezone.utc).isoformat(),
        parameters=params,
    )
