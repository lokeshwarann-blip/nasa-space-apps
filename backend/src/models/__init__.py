"""Database models package exporting all SQLAlchemy declarative entities."""

from src.models.base import Base, TimestampMixin
from src.models.crew import CrewMember
from src.models.mission import Mission, MissionMembership
from src.models.telemetry import HealthMeasurement
from src.models.wellness import WellnessCheckIn, SymptomCheckIn
from src.models.clinical import GuidanceSource, GuidanceDocument, GuidanceReviewRecord, ClinicalRule, Assessment
from src.models.audit import AuditEvent
from src.models.user import User
from src.models.tasks import TaskDefinition, TaskInstance, TaskAuditRecord
from src.models.alerts import AlertInstance, AlertAuditRecord
from src.models.sync import SyncEventRecord
from src.models.quests import Quest, QuestProgress, XPEvent, TeamStreak, Unlock

__all__ = [
    "Base",
    "TimestampMixin",
    "CrewMember",
    "Mission",
    "MissionMembership",
    "HealthMeasurement",
    "WellnessCheckIn",
    "SymptomCheckIn",
    "GuidanceSource",
    "GuidanceDocument",
    "GuidanceReviewRecord",
    "ClinicalRule",
    "Assessment",
    "AuditEvent",
    "User",
    "TaskDefinition",
    "TaskInstance",
    "TaskAuditRecord",
    "AlertInstance",
    "AlertAuditRecord",
    "SyncEventRecord",
]
