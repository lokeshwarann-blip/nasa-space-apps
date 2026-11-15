from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Dict, Any

router = APIRouter(prefix="/immune", tags=["Immune Shield"])

class StressorItem(BaseModel):
    id: str
    name: str
    value: str
    impact_pct: int
    icon: str
    mechanism: str

class ImmuneShieldResponse(BaseModel):
    shield_score: int = 74
    baseline_low: int = 70
    baseline_high: int = 95
    status_level: str = "watch"
    status_label: str = "Moderate Stress Context"
    disclaimer_label: str = "Immune stress context: not a diagnosis"
    stressors: List[StressorItem]
    countermeasure_notes: List[str]
    last_synced: str = "Sol 41 14:30 UTC"

@router.get("/shield", response_model=ImmuneShieldResponse)
def get_immune_shield():
    return ImmuneShieldResponse(
        shield_score=74,
        baseline_low=70,
        baseline_high=95,
        status_level="watch",
        status_label="Moderate Stress Context",
        disclaimer_label="Immune stress context: not a diagnosis",
        stressors=[
            StressorItem(
                id="sleep_debt",
                name="Cumulative Sleep Debt",
                value="1.8 hrs deficit",
                impact_pct=14,
                icon="moon",
                mechanism="Elevates FOXP3+ regulatory T-cells (Tregs) and down-regulates interleukin cascades.",
            ),
            StressorItem(
                id="mission_stress",
                name="Mission & Isolation Stress",
                value="Elevated cortisol rhythm",
                impact_pct=8,
                icon="pulse",
                mechanism="Subclinical latent EBV/CMV viral reactivation pressure under chronic cortisol elevation.",
            ),
            StressorItem(
                id="radiation_dose",
                name="Cosmic Radiation Exposure",
                value="0.42 mSv acute transit",
                impact_pct=4,
                icon="shield",
                mechanism="High-Z energetic particle tracks inducing DNA clustered break response.",
            ),
            StressorItem(
                id="fluid_shift",
                name="Cephalad Fluid Shift",
                value="Active rostral shift",
                impact_pct=5,
                icon="drop",
                mechanism="Venous engorgement altering central lymphatic drainage and interstitial filtration.",
            ),
        ],
        countermeasure_notes=[
            "Target 8.0h consolidated restorative sleep Sol 42 to restore T-cell proliferation.",
            "Maintain 2.8L electrolyte hydration to buffer plasma volume under microgravity fluid shift.",
            "Check with flight surgeon before taking supplementary medications.",
        ],
    )
