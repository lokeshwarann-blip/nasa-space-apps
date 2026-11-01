"""Sensor and external health-device integration module."""
from src.modules.adapters.base import (
    CanonicalMeasurementDTO,
    DeviceAdapterInterface,
    DevicePayloadEnvelope,
)
from src.modules.adapters.registry import (
    DeviceAdapterRegistry,
    device_adapter_registry,
)
from src.modules.adapters.service import DeviceIngestionService

__all__ = [
    "CanonicalMeasurementDTO",
    "DeviceAdapterInterface",
    "DevicePayloadEnvelope",
    "DeviceAdapterRegistry",
    "device_adapter_registry",
    "DeviceIngestionService",
]

