from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict

router = APIRouter(prefix="/environment", tags=["Environment Profile Switch"])

class EnvironmentProfile(BaseModel):
    id: str
    name: str
    icon: str
    gravity_g: float
    gravity_label: str
    radiation_context: str
    ambient_o2_kpa: float
    ambient_co2_mmhg: float
    diurnal_cycle: str
    baseline_hr_low: float
    baseline_hr_high: float
    countermeasure_focus: str
    description: str

PROFILES: Dict[str, dict] = {
    "mars_base": {
        "id": "mars_base",
        "name": "Mars Surface Habitat",
        "icon": "🔴",
        "gravity_g": 0.38,
        "gravity_label": "0.38 G (Martian Surface)",
        "radiation_context": "Partial regolith berm shielding (0.35 mSv/sol)",
        "ambient_o2_kpa": 21.3,
        "ambient_co2_mmhg": 3.8,
        "diurnal_cycle": "24h 39m 35s (Martian Sol)",
        "baseline_hr_low": 58.0,
        "baseline_high": 82.0,
        "countermeasure_focus": "Orthostatic tolerance under 0.38G & perchlorate dust scrubbing",
        "description": "Martian outpost habitat with subsurface regolith shielding and circadian tracking locked to the 24.65h Sol.",
    },
    "spacecraft": {
        "id": "spacecraft",
        "name": "Deep Space Transit Vehicle (Orion/Starship)",
        "icon": "🚀",
        "gravity_g": 0.0,
        "gravity_label": "Microgravity (0.0 G)",
        "radiation_context": "Deep space GCR / Solar Particle Storm Shelter (1.2 mSv/sol)",
        "ambient_o2_kpa": 23.5,
        "ambient_co2_mmhg": 4.5,
        "diurnal_cycle": "24.0h Artificial UTC lighting schedule",
        "baseline_hr_low": 56.0,
        "baseline_high": 80.0,
        "countermeasure_focus": "Intensive ARED resistance (2.5h/day) to prevent 1% monthly bone demineralization",
        "description": "Interplanetary transfer vehicle in transit between Earth and Mars. Maximum microgravity fluid shift context.",
    },
    "space_station": {
        "id": "space_station",
        "name": "Orbital Space Station (ISS / Gateway)",
        "icon": "🛰️",
        "gravity_g": 0.0,
        "gravity_label": "Microgravity (0.0 G)",
        "radiation_context": "Low Earth Orbit / Geomagnetic cusp transit (0.5 mSv/sol)",
        "ambient_o2_kpa": 21.0,
        "ambient_co2_mmhg": 3.2,
        "diurnal_cycle": "90-minute orbital sunrise/sunset anchored by 480nm LED interior lighting",
        "baseline_hr_low": 58.0,
        "baseline_high": 82.0,
        "countermeasure_focus": "T2 treadmill, Cycle Ergometer (CEVIS), and SANS optical coherence tomography",
        "description": "Permanent microgravity research outpost with daily tele-guidance from terrestrial flight surgeons.",
    },
    "rover": {
        "id": "rover",
        "name": "Pressurized Exploration Rover",
        "icon": "🚜",
        "gravity_g": 0.38,
        "gravity_label": "0.38 G (Martian Surface)",
        "radiation_context": "Mobile storm shelter water wall (0.45 mSv/sol)",
        "ambient_o2_kpa": 24.0,
        "ambient_co2_mmhg": 5.0,
        "diurnal_cycle": "24h 39m Sol diurnal cycle",
        "baseline_hr_low": 60.0,
        "baseline_high": 85.0,
        "countermeasure_focus": "Whole-body vibration dampening, suit egress ergonomics, and acute hydration",
        "description": "Mobile pressurized exploration module supporting multi-sol surface traverses beyond base perimeter.",
    },
    "lunar_base": {
        "id": "lunar_base",
        "name": "Lunar Surface Outpost (Artemis Base Camp)",
        "icon": "🌕",
        "gravity_g": 0.166,
        "gravity_label": "0.166 G (Lunar Surface)",
        "radiation_context": "Lava tube habitat / Sintered regolith shielding (0.28 mSv/sol)",
        "ambient_o2_kpa": 22.0,
        "ambient_co2_mmhg": 3.5,
        "diurnal_cycle": "14 Earth-day lunar day / 14 Earth-day night cycle (Artificial habitat chronobiology)",
        "baseline_hr_low": 57.0,
        "baseline_high": 81.0,
        "countermeasure_focus": "Partial-G muscle atrophy prevention and abrasive silica dust mitigation",
        "description": "Shackleton Crater south-pole habitat optimized for deep cryogenic shadows and long lunar darkness.",
    },
}

ACTIVE_PROFILE = {"id": "mars_base"}

class SwitchRequest(BaseModel):
    profile_id: str

class EnvironmentStatusResponse(BaseModel):
    active_profile: EnvironmentProfile
    all_profiles: List[EnvironmentProfile]
    message: str

@router.get("", response_model=EnvironmentStatusResponse)
def get_environment_profiles():
    active_id = ACTIVE_PROFILE["id"]
    active = PROFILES.get(active_id, PROFILES["mars_base"])
    return EnvironmentStatusResponse(
        active_profile=EnvironmentProfile(**active),
        all_profiles=[EnvironmentProfile(**p) for p in PROFILES.values()],
        message="Active flight environment retrieved.",
    )

@router.post("/switch", response_model=EnvironmentStatusResponse)
def switch_environment(req: SwitchRequest):
    if req.profile_id in PROFILES:
        ACTIVE_PROFILE["id"] = req.profile_id
    active_id = ACTIVE_PROFILE["id"]
    active = PROFILES[active_id]
    return EnvironmentStatusResponse(
        active_profile=EnvironmentProfile(**active),
        all_profiles=[EnvironmentProfile(**p) for p in PROFILES.values()],
        message=f"Environment context switched to {active['name']}.",
    )
