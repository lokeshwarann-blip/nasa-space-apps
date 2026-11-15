from fastapi import APIRouter, status
from src.schemas.astronaut import (
    CircadianResponse,
    EnvironmentProfile,
)

router = APIRouter(prefix="/circadian", tags=["Circadian Alignment Mock"])


@router.get(
    "/{id}",
    response_model=CircadianResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Circadian Phase Alignment Analysis",
    description="Returns estimated circadian phase offset, realignment recommendations, model assumptions, and environmental profiles.",
)
async def get_circadian_status(id: str) -> CircadianResponse:
    """Mock endpoint returning circadian rhythm analysis and lighting recommendations."""
    return CircadianResponse(
        crew_id=id,
        phase_offset_hours=-2.25,
        suggested_shift=1.5,
        days_to_realign=3,
        model="Kronauer-Forger Limit-Cycle Circadian Oscillator v3.2",
        assumptions=[
            "Assumes strict adherence to scheduled 8.0h dark cabin lighting window",
            "Core body temperature nadir estimated at 04:30 mission elapsed time",
            "Blue-spectrum attenuation active during pre-sleep operational protocol",
            "Check with flight surgeon for individualized schedule adjustments",
        ],
        environment_profile=EnvironmentProfile(
            light_lux=450.0,
            color_temperature_k=4500,
            blue_wavelength_attenuation=True,
            temperature_c=21.0,
            scheduled_dark_hours=8.0,
        ),
    )
