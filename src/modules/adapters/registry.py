from typing import Any
from src.modules.adapters.base import DeviceAdapterInterface


class DeviceAdapterRegistry:
    """Registry maintaining approved external device integration adapters.
    
    SAFETY & INTEGRATION POLICY:
    Initialized empty by default. No hardware integration is claimed as functional
    until actual supported provider hardware has been connected and tested.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, DeviceAdapterInterface] = {}

    def register(self, adapter: DeviceAdapterInterface) -> None:
        """Registers a device provider adapter."""
        self._adapters[adapter.provider_id.upper()] = adapter

    def unregister(self, provider_id: str) -> None:
        """Removes a provider adapter."""
        self._adapters.pop(provider_id.upper(), None)

    def clear(self) -> None:
        """Clears all adapters (used for test isolation)."""
        self._adapters.clear()

    def get(self, provider_id: str) -> DeviceAdapterInterface | None:
        """Retrieves adapter for a provider ID."""
        return self._adapters.get(provider_id.upper())

    def list_adapters(self) -> list[dict[str, Any]]:
        """Lists registered adapters with metadata and connection status."""
        return [
            {
                "provider_id": adapter.provider_id,
                "version": adapter.version,
                "is_connected": getattr(adapter, "is_connected", False),
                "supported_measurement_types": getattr(adapter, "supported_measurement_types", []),
            }
            for adapter in self._adapters.values()
        ]


# Global singleton registry (initialized EMPTY per contract)
device_adapter_registry = DeviceAdapterRegistry()

