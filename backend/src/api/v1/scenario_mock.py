from datetime import datetime, timezone
from fastapi import APIRouter, status
from src.schemas.astronaut import (
    ScenarioRequest,
    ScenarioResponse,
    ScenarioType,
)

router = APIRouter(prefix="/scenario", tags=["Scenario Mock"])

SCENARIO_CONFIGS = {
    ScenarioType.COORDINATED_DRIFT: (
        "Coordinated multi-signal physiological drift simulation active. Monitoring cross-system trend shifts.",
        {"drift_rate_sd_per_day": 0.25, "affected_signals": ["heart_rate", "spo2", "sleep_duration"]},
    ),
    ScenarioType.SENSOR_FAULT: (
        "Sensor fault simulation active. Injected intermittent telemetry dropouts and signal flatlines.",
        {"dropout_rate": 0.20, "faulty_sensors": ["pulse_oximeter"]},
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


@router.post(
    "",
    response_model=ScenarioResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate Simulation Scenario",
    description="Switches the simulation environment to a test scenario (coordinated_drift, sensor_fault, comms_blackout, dust_storm, or reset).",
)
async def set_scenario(payload: ScenarioRequest) -> ScenarioResponse:
    """Mock endpoint switching or resetting active simulation scenarios."""
    message, params = SCENARIO_CONFIGS[payload.type]
    return ScenarioResponse(
        active_scenario=payload.type,
        message=message,
        started_at=datetime.now(timezone.utc).isoformat(),
        parameters=params,
    )
