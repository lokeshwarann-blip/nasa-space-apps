from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter(prefix="/scenario", tags=["Scenario Panel (Demo Mode)"])

class ScenarioRequest(BaseModel):
    scenario_id: str

class ScenarioResponse(BaseModel):
    scenario_id: str
    name: str
    description: str
    alert_level: str
    alert_title: str
    alert_reason: str
    alert_next_step: str
    sensor_quality: str
    network_link_status: str
    telemetry_hr: float
    telemetry_spo2: float
    telemetry_temp: float
    message: str

SCENARIOS: Dict[str, dict] = {
    "nominal": {
        "scenario_id": "nominal",
        "name": "Nominal Baseline Flight",
        "description": "All environmental scrubbers and crew vital telemetry within personalized normal baseline bands.",
        "alert_level": "normal",
        "alert_title": "All Systems Nominal",
        "alert_reason": "No adverse environmental or physiological anomalies detected.",
        "alert_next_step": "Maintain routine Sol 41 operational schedule.",
        "sensor_quality": "good",
        "network_link_status": "online",
        "telemetry_hr": 68.0,
        "telemetry_spo2": 98.2,
        "telemetry_temp": 36.8,
        "message": "Nominal flight baseline restored.",
    },
    "dust_storm": {
        "scenario_id": "dust_storm",
        "name": "Martian Dust Storm (Atmospheric Opacity)",
        "description": "High tau optical depth event reducing solar array output by 65%. Habitat life-support power-save protocol active.",
        "alert_level": "watch",
        "alert_title": "Dust Storm Advisory",
        "alert_reason": "Low solar irradiance and atmospheric dust accumulation. Non-critical EVA postponed.",
        "alert_next_step": "Verify habitat HEPA filter seals, switch to low-draw interior illumination, and postpone orbital EVA.",
        "sensor_quality": "good",
        "network_link_status": "online",
        "telemetry_hr": 74.0,
        "telemetry_spo2": 97.5,
        "telemetry_temp": 36.9,
        "message": "Dust storm environmental profile broadcasted.",
    },
    "comms_blackout": {
        "scenario_id": "comms_blackout",
        "name": "Deep Space Comms Blackout (Solar Conjunction)",
        "description": "Telemetry link to terrestrial ground station blocked by solar conjunction. Autonomous edge decision support engaged.",
        "alert_level": "watch",
        "alert_title": "Deep Space Comms Link Offline",
        "alert_reason": "Solar radio interference interrupting terrestrial relay. All data cached in local habitat memory.",
        "alert_next_step": "Operate under autonomous flight protocol. Local data-quality gates remain active.",
        "sensor_quality": "good",
        "network_link_status": "blackout",
        "telemetry_hr": 70.0,
        "telemetry_spo2": 98.0,
        "telemetry_temp": 36.8,
        "message": "Comms blackout simulation active: local cache enabled.",
    },
    "sensor_fault": {
        "scenario_id": "sensor_fault",
        "name": "Sensor Fault & Optical SNR Dropout",
        "description": "Pulse oximeter optical sensor artifact / photoplethysmogram saturation.",
        "alert_level": "watch",
        "alert_title": "Sensor Issue Detected (Hardware)",
        "alert_reason": "Sensor photodiode contact loss on Left Ring Finger. Not a cardiovascular health event.",
        "alert_next_step": "Clean optical sensor lens, reseat biometric finger clip, or use manual pulse check. Note: this is a sensor problem, not a health alert.",
        "sensor_quality": "sensor issue",
        "network_link_status": "online",
        "telemetry_hr": 68.0,
        "telemetry_spo2": 98.2,
        "telemetry_temp": 36.8,
        "message": "Sensor fault simulation: flagged as hardware issue, not health alert.",
    },
    "coordinated_drift": {
        "scenario_id": "coordinated_drift",
        "name": "Coordinated Physiological Drift (Post-EVA Strain)",
        "description": "Mild elevation in resting HR (+14 bpm) and core body temperature (+0.8°C) following 6-hour orbital hatch egress.",
        "alert_level": "act",
        "alert_title": "Cardiovascular & Thermal Drift",
        "alert_reason": "Post-EVA fluid loss and metabolic heat accumulation exceeding personal baseline upper limits.",
        "alert_next_step": "Initiate 1.5L chilled electrolyte rehydration, active liquid cooling garment (LCG) cycle, and notify flight surgeon.",
        "sensor_quality": "good",
        "network_link_status": "online",
        "telemetry_hr": 88.5,
        "telemetry_spo2": 96.8,
        "telemetry_temp": 37.6,
        "message": "Coordinated drift scenario loaded across all vital telemetry indicators.",
    },
}

CURRENT_SCENARIO = {"id": "nominal"}

@router.get("/current", response_model=ScenarioResponse)
def get_current_scenario():
    sc_id = CURRENT_SCENARIO["id"]
    return ScenarioResponse(**SCENARIOS.get(sc_id, SCENARIOS["nominal"]))

@router.post("", response_model=ScenarioResponse)
def trigger_scenario(req: ScenarioRequest):
    if req.scenario_id in SCENARIOS:
        CURRENT_SCENARIO["id"] = req.scenario_id
        return ScenarioResponse(**SCENARIOS[req.scenario_id])
    return ScenarioResponse(**SCENARIOS["nominal"])
