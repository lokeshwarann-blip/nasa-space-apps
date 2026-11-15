from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/team", tags=["Team Streak & Shared Mission Goals"])

class TeamStreakResponse(BaseModel):
    team_streak_sols: int = 13
    freeze_days_total: int = 2
    freeze_days_remaining: int = 1
    shared_goal_name: str = "Expedition 72 Weekly Aerobic & Bone Countermeasure Target"
    shared_goal_current_hours: float = 30.8
    shared_goal_target_hours: float = 35.0
    shared_goal_pct: float = 88.0
    rings_closed: int = 6
    rings_total: int = 7
    active_freeze_applied: bool = False
    carried_over_tasks: int = 1
    status_level: str = "normal"
    status_label: str = "Collective Goal On Track"
    policy_note: str = "NASA behavioral policy: Collective progress monitoring only. Zero individual leaderboards, shame states, or rank sorting."

@router.get("/streak", response_model=TeamStreakResponse)
def get_team_streak():
    return TeamStreakResponse()
