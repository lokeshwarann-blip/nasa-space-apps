from fastapi import APIRouter, status
from src.schemas.astronaut import (
    EvidenceLevelEnum,
    Quest,
    QuestLogRequest,
    QuestLogResponse,
    QuestsResponse,
)

router = APIRouter(prefix="/quests", tags=["Quests Mock"])


MOCK_QUESTS = [
    Quest(
        id="quest-resistive",
        title="Resistive Exercise Session",
        target=45.0,
        unit="minutes",
        period="daily",
        rationale="Maintains musculoskeletal integrity and mitigates bone mineral density loss trends in microgravity.",
        source="NASA Human Research Program (HRP-47065)",
        evidence_level=EvidenceLevelEnum.ESTABLISHED,
    ),
    Quest(
        id="quest-aerobic",
        title="Aerobic Conditioning",
        target=30.0,
        unit="minutes",
        period="daily",
        rationale="Sustains VO2 peak and cardiovascular regulation under cephalad fluid shift context.",
        source="NASA HRP Cardiovascular Standards",
        evidence_level=EvidenceLevelEnum.ESTABLISHED,
    ),
    Quest(
        id="quest-circadian-light",
        title="Circadian Light Regulation",
        target=30.0,
        unit="minutes",
        period="daily",
        rationale="Synchronizes suprachiasmatic nucleus circadian timing through calibrated blue-enriched spectrum exposure.",
        source="NASA Behavioral Health and Performance Division",
        evidence_level=EvidenceLevelEnum.ESTABLISHED,
    ),
    Quest(
        id="quest-hydration",
        title="Hydration Optimization Protocol",
        target=2.5,
        unit="liters",
        period="daily",
        rationale="Supports intravascular volume regulation counteracting microgravity fluid shift trends.",
        source="NASA Space Physiology Guidelines",
        evidence_level=EvidenceLevelEnum.ESTABLISHED,
    ),
    Quest(
        id="quest-sleep-hygiene",
        title="Rest & Immune Surveillance Window",
        target=8.0,
        unit="hours",
        period="daily",
        rationale="Restorative rest supports immune regulation and viral latency control; check with flight surgeon for individualized context.",
        source="NASA Exploration Medical Integrated Product Team",
        evidence_level=EvidenceLevelEnum.EMERGING,
    ),
]


@router.get(
    "",
    response_model=QuestsResponse,
    status_code=status.HTTP_200_OK,
    summary="List Active Operational Quests",
    description="Returns active daily and weekly astronaut health and operational wellness quests.",
)
async def list_quests() -> QuestsResponse:
    """Mock endpoint returning active astronaut quests."""
    return QuestsResponse(quests=MOCK_QUESTS)


@router.post(
    "/{id}/log",
    response_model=QuestLogResponse,
    status_code=status.HTTP_200_OK,
    summary="Log Quest Activity",
    description="Logs completion or progress for a specific operational quest.",
)
async def log_quest(id: str, payload: QuestLogRequest) -> QuestLogResponse:
    """Mock endpoint logging quest progress and returning rewards."""
    return QuestLogResponse(
        quest_id=id,
        event_id=payload.event_id,
        xp_gained=50,
        progress=1.0,
        unlocked=["badge_circadian_alignment", "bonus_rest_window"],
    )
