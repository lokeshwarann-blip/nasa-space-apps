from fastapi import APIRouter, status
from src.schemas.astronaut import (
    BodySystem,
    CrewStatus,
    EvidenceLevelEnum,
    ForecastPoint,
    Readiness,
    SeriesPoint,
    StatusEnum,
    StatusIconEnum,
)

router = APIRouter(prefix="/crew", tags=["Crew Status Mock"])


@router.get(
    "/{id}/status",
    response_model=CrewStatus,
    status_code=status.HTTP_200_OK,
    summary="Get Crew Readiness Status",
    description="Returns physiological readiness score, multi-system telemetry status, and forecast envelopes.",
)
async def get_crew_status(id: str) -> CrewStatus:
    """Mock endpoint returning simulated crew member status and multi-system trends."""
    return CrewStatus(
        crew_id=id,
        readiness=Readiness(
            score=88,
            status=StatusEnum.NORMAL,
            status_icon=StatusIconEnum.CIRCLE_CHECK,
            confidence="high",
            updated_at="2026-11-15T20:00:00Z",
        ),
        body_systems=[
            BodySystem(
                name="heart",
                status=StatusEnum.NORMAL,
                status_icon=StatusIconEnum.CIRCLE_CHECK,
                value=68.0,
                unit="bpm",
                baseline_low=55.0,
                baseline_high=85.0,
                trend="stable resting rhythm within baseline range",
                evidence_level=EvidenceLevelEnum.ESTABLISHED,
                series=[
                    SeriesPoint(t="2026-11-15T08:00:00Z", value=65.0),
                    SeriesPoint(t="2026-11-15T12:00:00Z", value=71.0),
                    SeriesPoint(t="2026-11-15T16:00:00Z", value=67.0),
                    SeriesPoint(t="2026-11-15T20:00:00Z", value=68.0),
                ],
                forecast=[
                    ForecastPoint(t="2026-11-16T00:00:00Z", low=58.0, high=76.0),
                    ForecastPoint(t="2026-11-16T04:00:00Z", low=54.0, high=70.0),
                ],
            ),
            BodySystem(
                name="lungs",
                status=StatusEnum.NORMAL,
                status_icon=StatusIconEnum.CIRCLE_CHECK,
                value=98.2,
                unit="%",
                baseline_low=95.0,
                baseline_high=100.0,
                trend="optimal oxygen saturation context",
                evidence_level=EvidenceLevelEnum.ESTABLISHED,
                series=[
                    SeriesPoint(t="2026-11-15T08:00:00Z", value=98.0),
                    SeriesPoint(t="2026-11-15T12:00:00Z", value=98.5),
                    SeriesPoint(t="2026-11-15T16:00:00Z", value=98.1),
                    SeriesPoint(t="2026-11-15T20:00:00Z", value=98.2),
                ],
                forecast=[
                    ForecastPoint(t="2026-11-16T00:00:00Z", low=96.0, high=99.5),
                    ForecastPoint(t="2026-11-16T04:00:00Z", low=95.5, high=99.0),
                ],
            ),
            BodySystem(
                name="sleep_brain",
                status=StatusEnum.NORMAL,
                status_icon=StatusIconEnum.CIRCLE_CHECK,
                value=7.4,
                unit="hours",
                baseline_low=7.0,
                baseline_high=9.0,
                trend="restorative sleep trend maintained",
                evidence_level=EvidenceLevelEnum.ESTABLISHED,
                series=[
                    SeriesPoint(t="2026-11-12T06:00:00Z", value=7.1),
                    SeriesPoint(t="2026-11-13T06:00:00Z", value=7.6),
                    SeriesPoint(t="2026-11-14T06:00:00Z", value=7.3),
                    SeriesPoint(t="2026-11-15T06:00:00Z", value=7.4),
                ],
                forecast=[
                    ForecastPoint(t="2026-11-16T06:00:00Z", low=6.8, high=8.2),
                ],
            ),
            BodySystem(
                name="muscles_bones",
                status=StatusEnum.NORMAL,
                status_icon=StatusIconEnum.CIRCLE_CHECK,
                value=102.5,
                unit="% baseline force",
                baseline_low=90.0,
                baseline_high=110.0,
                trend="countermeasure workload adherence on target",
                evidence_level=EvidenceLevelEnum.ESTABLISHED,
                series=[
                    SeriesPoint(t="2026-11-12T18:00:00Z", value=100.0),
                    SeriesPoint(t="2026-11-13T18:00:00Z", value=101.5),
                    SeriesPoint(t="2026-11-14T18:00:00Z", value=103.0),
                    SeriesPoint(t="2026-11-15T18:00:00Z", value=102.5),
                ],
                forecast=[
                    ForecastPoint(t="2026-11-16T18:00:00Z", low=98.0, high=105.0),
                ],
            ),
            BodySystem(
                name="immune",
                status=StatusEnum.WATCH,
                status_icon=StatusIconEnum.TRIANGLE,
                value=1.05,
                unit="ratio",
                baseline_low=0.85,
                baseline_high=1.25,
                trend="emerging modulation observed; check with flight surgeon",
                evidence_level=EvidenceLevelEnum.EMERGING,
                series=[
                    SeriesPoint(t="2026-11-01T12:00:00Z", value=0.92),
                    SeriesPoint(t="2026-11-05T12:00:00Z", value=0.97),
                    SeriesPoint(t="2026-11-10T12:00:00Z", value=1.01),
                    SeriesPoint(t="2026-11-15T12:00:00Z", value=1.05),
                ],
                forecast=[
                    ForecastPoint(t="2026-11-20T12:00:00Z", low=0.95, high=1.18),
                ],
            ),
        ],
        data_quality="good",
    )
