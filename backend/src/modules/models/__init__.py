"""Future analytical model interface module."""
from src.modules.models.base import (
    MANDATORY_MODEL_LIMITATIONS,
    AnalysisProviderInterface,
    AnalysisRequest,
    AnalysisResultDTO,
)
from src.modules.models.service import AnalysisService

__all__ = [
    "MANDATORY_MODEL_LIMITATIONS",
    "AnalysisProviderInterface",
    "AnalysisRequest",
    "AnalysisResultDTO",
    "AnalysisService",
]

