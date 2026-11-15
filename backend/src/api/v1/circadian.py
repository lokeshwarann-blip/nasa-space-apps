from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/circadian", tags=["Sol Clock & Circadian Dial"])

class CircadianDialResponse(BaseModel):
    habitat_time_str: str = "Sol 41 14:25"
    habitat_hour: float = 14.42
    body_clock_hour: float = 16.15
    phase_offset_hours: float = 1.73
    realignment_sols: int = 2
    personal_tau: float = 24.2
    baseline_note: str = "Your intrinsic circadian period: 24.2h (NASA analog baseline)"
    suggested_light_window: str = "07:00 – 09:30 (480nm Blue-Enriched LED, 450 lux)"
    suggested_sleep_window: str = "23:00 – 07:00 (Dark / Melatonin Window)"
    dim_light_melatonin_onset: str = "21:30"
    status_level: str = "watch"
    status_label: str = "Phase Shift Context"
    clinical_note: str = "1.7h circadian phase delay detected relative to habitat operational clock. Scheduled narrow-band 480nm morning illumination advised to phase-advance suprachiasmatic nucleus."

@router.get("/dial", response_model=CircadianDialResponse)
def get_circadian_dial_status():
    return CircadianDialResponse()
