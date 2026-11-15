import json
from pathlib import Path

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.quests import Unlock
from src.schemas.astronaut import (
    EvidenceLevelEnum,
    ScienceContextCard,
    ScienceContextResponse,
)

router = APIRouter(prefix="/science-context", tags=["Science Context"])

# Load cards from JSON at module startup
_CARDS_PATH = Path(__file__).resolve().parents[2] / "data" / "science_cards.json"

with open(_CARDS_PATH, "r", encoding="utf-8") as _f:
    _RAW_CARDS: list[dict] = json.load(_f)

# Map quest IDs to science card IDs for unlock triggers
QUEST_TO_CARD: dict[str, str] = {
    "quest-resistive": "sc-fluid-shift",
    "quest-aerobic": "sc-sleep",
    "quest-circadian-light": "sc-circadian-light",
    "quest-hydration": "sc-radiation",
    "quest-rest-routine": "sc-latent-virus",
}

# Tregs unlocks after any 3 quests logged (special condition)
TREGS_CARD_ID = "sc-tregs"


@router.get(
    "",
    response_model=ScienceContextResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Scientific Context Cards",
    description="Returns science context cards with unlock state driven by quest logging.",
)
async def get_science_context(session: AsyncSession = Depends(get_db)) -> ScienceContextResponse:
    """Returns science context cards loaded from JSON with DB-driven unlock state."""
    # Get all unlocked card keys for the team
    stmt = select(Unlock.unlock_key).where(
        Unlock.crew_id == "team",
        Unlock.unlock_key.like("sc-%"),
    )
    res = await session.execute(stmt)
    unlocked_keys = set(res.scalars().all())

    cards = []
    for raw in _RAW_CARDS:
        cards.append(
            ScienceContextCard(
                id=raw["id"],
                title=raw["title"],
                plain_summary=raw["plain_summary"],
                why_it_matters=raw["why_it_matters"],
                evidence_level=EvidenceLevelEnum(raw["evidence_level"]),
                sources=raw["sources"],
                linked_signals=raw["linked_signals"],
                unlocked=raw["id"] in unlocked_keys,
            )
        )
    return ScienceContextResponse(cards=cards)
