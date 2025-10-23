"""Base entity for the Domintell EcoPilot integration."""

from __future__ import annotations

from homeassistant.const import ATTR_CONNECTIONS, ATTR_IDENTIFIERS
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EcoPilotDeviceUpdateCoordinator


class EcoPilotEntity(CoordinatorEntity[EcoPilotDeviceUpdateCoordinator]):
    """Defines a Domintell EcoPilot entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EcoPilotDeviceUpdateCoordinator) -> None:
        """Initialize the Domintell EcoPilot entity."""
        super().__init__(coordinator)
        device_name = coordinator.data.device.model_name
        if coordinator.data.device.product_model not in [
            "ecoP1",
            "ecoDrive-P1",
            "ecoDrive-LK",
        ]:
            device_name = f"{device_name} ({coordinator.data.device.serial_number})"

        self._attr_device_info = DeviceInfo(
            name=device_name,
            model_id=coordinator.data.device.product_model,
            model=coordinator.data.device.model_name,
            serial_number=coordinator.data.device.serial_number,
            hw_version=coordinator.data.device.hardware_version,
            sw_version=coordinator.data.device.firmware_version,
            manufacturer="Domintell",
        )

        if (mac_address := coordinator.data.device.mac_address) is not None:
            self._attr_device_info[ATTR_CONNECTIONS] = {
                (CONNECTION_NETWORK_MAC, mac_address)
            }

        device_identifier = f"{coordinator.data.device.product_model}_{coordinator.data.device.serial_number}"
        self._attr_device_info[ATTR_IDENTIFIERS] = {(DOMAIN, device_identifier)}
