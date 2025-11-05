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

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""

        data = self.coordinator.data.device

        device_name = data.model_name
        if data.product_model not in ["ecoP1"]:
            device_name = f"{device_name} ({data.serial_number})"

        info = DeviceInfo(
            name=device_name,
            model_id=data.product_model,
            model=data.model_name,
            serial_number=data.serial_number,
            hw_version=data.hardware_version,
            sw_version=data.firmware_version,
            manufacturer="Domintell",
        )

        if (mac_address := data.mac_address) is not None:
            info[ATTR_CONNECTIONS] = {(CONNECTION_NETWORK_MAC, mac_address)}

        device_identifier = f"{data.product_model}_{data.serial_number}"
        info[ATTR_IDENTIFIERS] = {(DOMAIN, device_identifier)}

        return info

    def _handle_coordinator_update(self) -> None:
        """
        Handles coordinator update notifications.
        This method is called by the parent class CoordinatorEntity.
        """
        self.schedule_update_ha_state()
