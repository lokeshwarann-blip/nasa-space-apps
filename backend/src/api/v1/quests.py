from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/quests", tags=["Quests & Missions"])

class QuestLogRequest(BaseModel):
    amount: Optional[float] = Field(default=None, description="Amount completed to add or finalize")

class QuestLogResponse(BaseModel):
    quest_id: str
    status: str
    xp_gained: int
    current_value: float
    target_value: float
    unit: str = "units"
    ring_closed: bool
    unlocked_codex_id: Optional[str] = None
    unlocked_title: Optional[str] = None
    team_streak: int
    message: str

class QuestItem(BaseModel):
    id: str
    title: str = "Quest"
    category: str
    target_text: str
    current_value: float
    target_value: float
    unit: str
    consequence: str
    xp: int
    evidence: str
    is_carried_over: bool = False
    is_completed: bool = False

class WeeklySummary(BaseModel):
    rings_closed: int
    rings_total: int
    team_streak_sols: int
    freeze_days_remaining: int
    shared_goal_pct: int

# In-memory flight state for the current Sol
QUEST_STATE = {
    "ared_exercise": {
        "id": "ared_exercise",
        "title": "ARED Resistance Training",
        "category": "Musculoskeletal",
        "target_text": "2.0 / 2.5 h this week",
        "current_value": 2.0,
        "target_value": 2.5,
        "unit": "hours",
        "consequence": "Protects L3–L5 trabecular bone density and reduces 1% monthly calcium loss in zero-G.",
        "xp": 50,
        "evidence": "established",
        "is_carried_over": False,
        "is_completed": False,
        "unlock_on_complete": {
            "id": "codex_bone_remodeling",
            "title": "Microgravity Bone Remodeling Dynamics",
        },
    },
    "hydration_target": {
        "id": "hydration_target",
        "title": "Electrolyte Hydration Intake",
        "category": "Vascular",
        "target_text": "2.8 / 3.0 L today",
        "current_value": 2.8,
        "target_value": 3.0,
        "unit": "liters",
        "consequence": "Maintains plasma volume and prevents renal stone formation under cephalad fluid shift.",
        "xp": 30,
        "evidence": "established",
        "is_carried_over": False,
        "is_completed": False,
        "unlock_on_complete": {
            "id": "codex_fluid_shift",
            "title": "Cephalad Fluid Shift & Kidney Filtration",
        },
    },
    "cognitive_vigilance": {
        "id": "cognitive_vigilance",
        "title": "PVT Cognitive Reaction Test",
        "category": "Neuro",
        "target_text": "Carries over from Sol 40",
        "current_value": 0.5,
        "target_value": 1.0,
        "unit": "session",
        "consequence": "Verifies high-speed psychomotor vigilance (PVT) reaction time before suited orbital EVA.",
        "xp": 40,
        "evidence": "emerging",
        "is_carried_over": True,
        "is_completed": False,
        "unlock_on_complete": {
            "id": "codex_circadian_alertness",
            "title": "Circadian Photobiology & Reaction Time",
        },
    },
}

WEEKLY_METRICS = {
    "rings_closed": 5,
    "rings_total": 7,
    "team_streak_sols": 12,
    "freeze_days_remaining": 1,
    "shared_goal_pct": 82,
}

@router.get("", response_model=List[QuestItem])
async def list_quests():
    """Returns active quests for Sol 41."""
    return list(QUEST_STATE.values())

@router.get("/summary", response_model=WeeklySummary)
async def get_weekly_summary():
    """Returns weekly rings closed and shared team streak (no individual rankings)."""
    return WEEKLY_METRICS

@router.post("/{quest_id}/log", response_model=QuestLogResponse)
async def log_quest(quest_id: str, payload: QuestLogRequest = QuestLogRequest()):
    """
    Idempotently logs quest progress and awards XP / codex unlocks.
    Handles duplicate logs safely without double counting.
    """
    if quest_id not in QUEST_STATE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quest '{quest_id}' not found in active mission schedule.",
        )

    quest = QUEST_STATE[quest_id]

    # Idempotent check: if already completed, return cached completion without double XP
    if quest["is_completed"]:
        return QuestLogResponse(
            quest_id=quest_id,
            status="already_completed",
            xp_gained=0,
            current_value=quest["current_value"],
            target_value=quest["target_value"],
            unit=quest["unit"],
            ring_closed=True,
            team_streak=WEEKLY_METRICS["team_streak_sols"],
            message=f"'{quest['title']}' is already completed for this cycle. Goal carries over upon cycle reset.",
        )

    # Increment or complete
    add_val = payload.amount if payload.amount is not None else (quest["target_value"] - quest["current_value"])
    quest["current_value"] = min(quest["target_value"], quest["current_value"] + add_val)
    
    is_now_closed = quest["current_value"] >= quest["target_value"]
    xp_award = quest["xp"] if is_now_closed else int(quest["xp"] * 0.5)
    
    unlocked_id = None
    unlocked_title = None

    if is_now_closed:
        quest["is_completed"] = True
        WEEKLY_METRICS["rings_closed"] = min(WEEKLY_METRICS["rings_total"], WEEKLY_METRICS["rings_closed"] + 1)
        WEEKLY_METRICS["team_streak_sols"] += 1
        WEEKLY_METRICS["shared_goal_pct"] = min(100, WEEKLY_METRICS["shared_goal_pct"] + 6)
        
        unlock_info = quest.get("unlock_on_complete")
        if unlock_info:
            unlocked_id = unlock_info["id"]
            unlocked_title = unlock_info["title"]

    return QuestLogResponse(
        quest_id=quest_id,
        status="completed" if is_now_closed else "in_progress",
        xp_gained=xp_award,
        current_value=quest["current_value"],
        target_value=quest["target_value"],
        unit=quest["unit"],
        ring_closed=is_now_closed,
        unlocked_codex_id=unlocked_id,
        unlocked_title=unlocked_title,
        team_streak=WEEKLY_METRICS["team_streak_sols"],
        message=f"Mission logged: {quest['title']}. +{xp_award} XP awarded!" + (f" Unlocked Codex: {unlocked_title}" if unlocked_title else ""),
    )
