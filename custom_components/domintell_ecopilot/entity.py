"""Base entity for the Domintell EcoPilot integration."""

from __future__ import annotations

from homeassistant.const import ATTR_CONNECTIONS, ATTR_IDENTIFIERS, ATTR_SERIAL_NUMBER
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
            name=device_name,  # TODO donner un nom ici va inclure dans le nom de l'entité également
            # default_name=device_name, #TODO
            model_id=coordinator.data.device.product_model,
            model=coordinator.data.device.model_name,
            serial_number=coordinator.data.device.serial_number,
            hw_version=coordinator.data.device.hardware_version,
            sw_version=coordinator.data.device.firmware_version,
            manufacturer="Domintell",
        )

        if (serial_number := coordinator.data.device.serial_number) is not None:
            self._attr_device_info[ATTR_CONNECTIONS] = {
                (CONNECTION_NETWORK_MAC, serial_number)
            }
            self._attr_device_info[ATTR_IDENTIFIERS] = {(DOMAIN, serial_number)}
