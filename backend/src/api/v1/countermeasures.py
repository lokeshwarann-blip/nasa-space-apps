from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List

router = APIRouter(prefix="/countermeasures", tags=["Countermeasure Lab (What-If)"])

class SimulationRequest(BaseModel):
    sleep_hours: float = Field(default=7.5, ge=4.0, le=10.0, description="Scheduled sleep duration in hours")
    resistance_exercise_minutes: float = Field(default=45.0, ge=0.0, le=90.0, description="ARED resistance minutes/day")
    aerobic_exercise_minutes: float = Field(default=30.0, ge=0.0, le=60.0, description="T2 Treadmill / Cycle minutes/day")
    hydration_liters: float = Field(default=2.8, ge=1.5, le=4.0, description="Electrolyte fluid intake in liters/day")

class ForecastPoint(BaseModel):
    sol: str
    projected_hr: float
    forecast_low: float
    forecast_high: float
    baseline_low: float = 58.0
    baseline_high: float = 82.0

class BodyMeters(BaseModel):
    cardiac_stability_pct: float
    bone_retention_pct: float
    cognitive_vigilance_pct: float
    immune_resilience_pct: float

class SimulationResponse(BaseModel):
    simulation_label: str = "Illustrative effect sizes based on NASA bed-rest and ISS analogs"
    readiness_score: int
    readiness_delta: int
    forecast_cone: List[ForecastPoint]
    body_meters: BodyMeters
    evidence_badge: str = "illustrative"
    operational_advice: str

DEFAULT_BASELINE = {
    "sleep_hours": 6.2,
    "resistance_exercise_minutes": 35.0,
    "aerobic_exercise_minutes": 20.0,
    "hydration_liters": 2.4,
}

@router.get("/baseline")
def get_current_baseline():
    """Returns the current Sol 41 astronaut baseline settings for countermeasure what-if simulation."""
    return DEFAULT_BASELINE

@router.post("/simulate", response_model=SimulationResponse)
def simulate_countermeasures(req: SimulationRequest):
    """
    Computes real-time what-if physiological forecast cone and body system resilience meters.
    Labeled with 'illustrative effect sizes'.
    """
    # Baseline comparison deltas
    delta_sleep = req.sleep_hours - DEFAULT_BASELINE["sleep_hours"]
    delta_resist = req.resistance_exercise_minutes - DEFAULT_BASELINE["resistance_exercise_minutes"]
    delta_aero = req.aerobic_exercise_minutes - DEFAULT_BASELINE["aerobic_exercise_minutes"]
    delta_fluid = req.hydration_liters - DEFAULT_BASELINE["hydration_liters"]

    # Compute Readiness score (0-100)
    base_readiness = 78
    readiness_mod = (delta_sleep * 4.2) + (delta_resist * 0.18) + (delta_aero * 0.22) + (delta_fluid * 3.5)
    projected_readiness = int(max(40, min(99, round(base_readiness + readiness_mod))))
    delta_score = projected_readiness - base_readiness

    # Compute body resilience meters (0 - 100%)
    cardiac_pct = round(max(50.0, min(98.0, 75.0 + (delta_aero * 0.35) + (delta_fluid * 4.0))), 1)
    bone_pct = round(max(45.0, min(99.0, 72.0 + (delta_resist * 0.45))), 1)
    vigilance_pct = round(max(40.0, min(98.0, 70.0 + (delta_sleep * 6.5))), 1)
    immune_pct = round(max(50.0, min(95.0, 68.0 + (delta_sleep * 3.0) + (delta_fluid * 3.0) + (delta_resist * 0.1))), 1)

    # Generate 7-Sol forecast cone (Sol 41 through Sol 47)
    base_hr = 68.0
    cone: List[ForecastPoint] = []
    
    # As exercise and sleep increase, resting heart rate stabilizes toward optimal 64-66 bpm
    target_hr = 68.0 - (delta_aero * 0.08) - (delta_sleep * 0.8)
    target_hr = max(60.0, min(76.0, target_hr))

    for i in range(7):
        sol_num = 41 + i
        t = i / 6.0
        hr_val = round(base_hr + (target_hr - base_hr) * t, 1)
        # Cone widens slightly into future sols (uncertainty bounds)
        cone_spread = 2.5 + (i * 0.6) - (min(req.sleep_hours, 8.0) * 0.2)
        f_low = round(max(54.0, hr_val - cone_spread), 1)
        f_high = round(min(88.0, hr_val + cone_spread), 1)

        cone.append(
            ForecastPoint(
                sol=f"Sol {sol_num}",
                projected_hr=hr_val,
                forecast_low=f_low,
                forecast_high=f_high,
                baseline_low=58.0,
                baseline_high=82.0,
            )
        )

    advice = (
        "Projected stability favorable under proposed schedule. "
        "Maintain progressive ARED resistance load to mitigate lower-limb trabecular bone demineralization."
        if projected_readiness >= 80
        else "Projected sleep debt or aerobic volume reduction may elevate cardiovascular drift during next suited EVA. "
        "Review with flight surgeon before finalizing changes."
    )

    return SimulationResponse(
        simulation_label="Illustrative effect sizes based on NASA bed-rest and ISS analogs",
        readiness_score=projected_readiness,
        readiness_delta=delta_score,
        forecast_cone=cone,
        body_meters=BodyMeters(
            cardiac_stability_pct=cardiac_pct,
            bone_retention_pct=bone_pct,
            cognitive_vigilance_pct=vigilance_pct,
            immune_resilience_pct=immune_pct,
        ),
        evidence_badge="illustrative",
        operational_advice=advice,
    )
