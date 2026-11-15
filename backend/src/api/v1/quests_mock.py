import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.quests import Quest as QuestModel, QuestProgress, XPEvent, TeamStreak, Unlock
from src.schemas.astronaut import (
    EvidenceLevelEnum,
    Quest,
    QuestLogRequest,
    QuestLogResponse,
    QuestsResponse,
    TeamStreakResponse,
)

router = APIRouter(prefix="/quests", tags=["Quests & XP"])

DEFAULT_SEEDED_QUESTS = [
    {
        "id": "quest-resistive",
        "title": "Resistive Exercise Session",
        "target": 45.0,
        "unit": "minutes",
        "period": "daily",
        "rationale": "Maintains musculoskeletal integrity and mitigates bone mineral density loss trends in microgravity.",
        "source": "NASA Human Research Program (HRP-47065)",
        "evidence_level": "established",
    },
    {
        "id": "quest-aerobic",
        "title": "Aerobic Conditioning",
        "target": 30.0,
        "unit": "minutes",
        "period": "daily",
        "rationale": "Sustains VO2 peak and cardiovascular regulation under cephalad fluid shift context.",
        "source": "NASA HRP Cardiovascular Standards",
        "evidence_level": "established",
    },
    {
        "id": "quest-circadian-light",
        "title": "Circadian Light Regulation",
        "target": 30.0,
        "unit": "minutes",
        "period": "daily",
        "rationale": "Synchronizes suprachiasmatic nucleus circadian timing through calibrated blue-enriched spectrum exposure.",
        "source": "NASA Behavioral Health and Performance Division",
        "evidence_level": "established",
    },
    {
        "id": "quest-hydration",
        "title": "Hydration Optimization Protocol",
        "target": 2.5,
        "unit": "liters",
        "period": "daily",
        "rationale": "Supports intravascular volume regulation counteracting microgravity fluid shift trends.",
        "source": "NASA Space Physiology Guidelines",
        "evidence_level": "established",
    },
    {
        "id": "quest-rest-routine",
        "title": "Cabin Decompression Wind-down Routine",
        "target": 1.0,
        "unit": "session",
        "period": "daily",
        "rationale": "Promotes cognitive decompression before sleep window without clinical intervention.",
        "source": None,
        "evidence_level": "illustrative",
    },
]


async def _ensure_seeded_quests(session: AsyncSession) -> list[QuestModel]:
    stmt = select(QuestModel).order_by(QuestModel.id)
    res = await session.execute(stmt)
    quests = list(res.scalars().all())
    if not quests:
        now = datetime.now(timezone.utc)
        for q_data in DEFAULT_SEEDED_QUESTS:
            q = QuestModel(
                id=q_data["id"],
                title=q_data["title"],
                target=q_data["target"],
                unit=q_data["unit"],
                period=q_data["period"],
                rationale=q_data["rationale"],
                source=q_data["source"],
                evidence_level=q_data["evidence_level"],
                created_at=now,
                updated_at=now,
            )
            session.add(q)
        await session.commit()
        res = await session.execute(stmt)
        quests = list(res.scalars().all())
    return quests


def calculate_streak_update(
    current_streak: int,
    longest_streak: int,
    freeze_days_remaining: int,
    last_activity_date: datetime | None,
    new_activity_date: datetime,
) -> tuple[int, int, int]:
    """Calculates updated team streak values preserving 2 freeze days."""
    if not last_activity_date:
        return 1, max(longest_streak, 1), freeze_days_remaining

    diff_days = (new_activity_date.date() - last_activity_date.date()).days
    if diff_days <= 0:
        return current_streak, longest_streak, freeze_days_remaining
    elif diff_days == 1:
        new_curr = current_streak + 1
        return new_curr, max(longest_streak, new_curr), freeze_days_remaining
    else:
        missed = diff_days - 1
        if missed <= freeze_days_remaining:
            new_curr = current_streak + 1
            new_freeze = freeze_days_remaining - missed
            return new_curr, max(longest_streak, new_curr), new_freeze
        else:
            return 1, longest_streak, 2


async def _update_team_streak(session: AsyncSession, event_time: datetime) -> TeamStreak:
    stmt = select(TeamStreak).where(TeamStreak.streak_type == "team")
    res = await session.execute(stmt)
    streak = res.scalar_one_or_none()

    if not streak:
        streak = TeamStreak(
            id=uuid.uuid4(),
            streak_type="team",
            current_streak=1,
            longest_streak=1,
            freeze_days_remaining=2,
            last_activity_date=event_time,
        )
        session.add(streak)
        return streak

    c, l, f = calculate_streak_update(
        streak.current_streak,
        streak.longest_streak,
        streak.freeze_days_remaining,
        streak.last_activity_date,
        event_time,
    )
    streak.current_streak = c
    streak.longest_streak = l
    streak.freeze_days_remaining = f
    streak.last_activity_date = event_time
    return streak


@router.get(
    "/streak",
    response_model=TeamStreakResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Shared Team Routine Streak",
    description="Returns active collective crew streak and remaining freeze day protections with no individual rankings.",
)
async def get_team_streak(session: AsyncSession = Depends(get_db)) -> TeamStreakResponse:
    """Returns collective crew streak status."""
    stmt = select(TeamStreak).where(TeamStreak.streak_type == "team")
    res = await session.execute(stmt)
    streak = res.scalar_one_or_none()
    if not streak:
        return TeamStreakResponse(
            current_streak=0,
            longest_streak=0,
            freeze_days_remaining=2,
            last_activity_date=None,
        )
    return TeamStreakResponse(
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        freeze_days_remaining=streak.freeze_days_remaining,
        last_activity_date=streak.last_activity_date.isoformat() if streak.last_activity_date else None,
    )


@router.get(
    "",
    response_model=QuestsResponse,
    status_code=status.HTTP_200_OK,
    summary="List Active Operational Quests",
    description="Returns active astronaut wellness and operational quests from the database.",
)
async def list_quests(session: AsyncSession = Depends(get_db)) -> QuestsResponse:
    """Lists seeded quests with plain language rationales and evidence classifications."""
    db_quests = await _ensure_seeded_quests(session)
    return QuestsResponse(
        quests=[
            Quest(
                id=q.id,
                title=q.title,
                target=q.target,
                unit=q.unit,
                period=q.period,
                rationale=q.rationale,
                source=q.source or "NASA Exploration Operational Guidance",
                evidence_level=EvidenceLevelEnum(q.evidence_level),
            )
            for q in db_quests
        ]
    )


@router.post(
    "/{id}/log",
    response_model=QuestLogResponse,
    status_code=status.HTTP_200_OK,
    summary="Log Quest Activity",
    description="Idempotently logs completion of a quest activity by client event_id, awarding XP and updating streaks.",
)
async def log_quest(id: str, payload: QuestLogRequest, session: AsyncSession = Depends(get_db)) -> QuestLogResponse:
    """Logs quest completion. Idempotent on client event_id (no double XP on replay)."""
    # Verify quest exists
    stmt_q = select(QuestModel).where(QuestModel.id == id)
    res_q = await session.execute(stmt_q)
    quest = res_q.scalar_one_or_none()
    if not quest:
        await _ensure_seeded_quests(session)
        res_q = await session.execute(stmt_q)
        quest = res_q.scalar_one_or_none()
        if not quest:
            raise HTTPException(status_code=404, detail="Quest not found")

    # Check for existing event_id (Idempotency)
    stmt_xp = select(XPEvent).where(XPEvent.event_id == payload.event_id)
    res_xp = await session.execute(stmt_xp)
    existing_xp = res_xp.scalar_one_or_none()

    if existing_xp:
        # Idempotent replay: return recorded state with 0 additional XP gained
        stmt_u = select(Unlock.unlock_key).where(Unlock.crew_id == existing_xp.crew_id)
        res_u = await session.execute(stmt_u)
        unlocked_keys = list(res_u.scalars().all())
        return QuestLogResponse(
            quest_id=id,
            event_id=payload.event_id,
            xp_gained=existing_xp.xp_gained,
            progress=1.0,
            unlocked=unlocked_keys,
        )

    # First-time event logging
    now = datetime.now(timezone.utc)
    xp_to_award = 50

    xp_event = XPEvent(
        id=uuid.uuid4(),
        event_id=payload.event_id,
        quest_id=id,
        crew_id="team",
        xp_gained=xp_to_award,
        created_at=now,
    )
    session.add(xp_event)

    # Update or insert quest progress
    stmt_prog = select(QuestProgress).where(
        QuestProgress.quest_id == id, QuestProgress.crew_id == "team"
    )
    res_prog = await session.execute(stmt_prog)
    prog = res_prog.scalar_one_or_none()
    if not prog:
        prog = QuestProgress(
            id=uuid.uuid4(),
            quest_id=id,
            crew_id="team",
            progress=1.0,
            completed=True,
            completed_at=now,
        )
        session.add(prog)
    else:
        prog.progress = 1.0
        prog.completed = True
        prog.completed_at = now

    # Update team streak
    await _update_team_streak(session, now)

    # Check and trigger unlock conditions
    new_unlocks = []
    # Trigger 1: First logged quest -> badge_circadian_alignment
    stmt_chk1 = select(Unlock).where(Unlock.crew_id == "team", Unlock.unlock_key == "badge_circadian_alignment")
    if not (await session.execute(stmt_chk1)).scalar_one_or_none():
        u1 = Unlock(id=uuid.uuid4(), crew_id="team", unlock_key="badge_circadian_alignment", unlocked_at=now)
        session.add(u1)
        new_unlocks.append("badge_circadian_alignment")

    # Trigger 2: If 3 or more total XP events logged -> bonus_rest_window
    stmt_cnt = select(XPEvent)
    all_events = (await session.execute(stmt_cnt)).scalars().all()
    if len(all_events) >= 3:
        stmt_chk2 = select(Unlock).where(Unlock.crew_id == "team", Unlock.unlock_key == "bonus_rest_window")
        if not (await session.execute(stmt_chk2)).scalar_one_or_none():
            u2 = Unlock(id=uuid.uuid4(), crew_id="team", unlock_key="bonus_rest_window", unlocked_at=now)
            session.add(u2)
            new_unlocks.append("bonus_rest_window")

    await session.commit()

    # Retrieve all current unlocks for response
    stmt_all_u = select(Unlock.unlock_key).where(Unlock.crew_id == "team")
    all_unlocked = list((await session.execute(stmt_all_u)).scalars().all())

    return QuestLogResponse(
        quest_id=id,
        event_id=payload.event_id,
        xp_gained=xp_to_award,
        progress=1.0,
        unlocked=all_unlocked,
    )
