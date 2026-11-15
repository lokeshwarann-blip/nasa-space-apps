from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/settings", tags=["User Preferences & Accessibility Settings"])

class SettingsModel(BaseModel):
    gamification_enabled: bool = True
    sound_enabled: bool = True
    reduced_motion: bool = False
    high_contrast: bool = False
    text_size: str = "standard"
    units_system: str = "metric"
    last_synced: Optional[str] = "Sol 41 14:35 UTC"

SETTINGS_STATE = SettingsModel()

@router.get("", response_model=SettingsModel)
def get_user_settings():
    return SETTINGS_STATE

@router.post("", response_model=SettingsModel)
def update_user_settings(payload: SettingsModel):
    global SETTINGS_STATE
    SETTINGS_STATE = payload
    return SETTINGS_STATE
