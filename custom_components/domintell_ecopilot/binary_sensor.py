"""Creates EcoPilot binary sensor entities."""

from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers import entity_registry as er
import homeassistant.helpers.config_validation as cv
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN
from .coordinator import (
    EcoPilotConfigEntry,
    EcoPilotDeviceUpdateCoordinator,
)
from .entity import EcoPilotEntity
from .ecopilot_api.models import CombinedModels


@dataclass(frozen=True, kw_only=True)
class EcoPilotBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Class describing EcoPilot binary sensor entities."""

    has_fn: Callable[[CombinedModels], bool]
    value_fn: Callable[[CombinedModels], bool]


BINARY_SENSORS: Final[tuple[EcoPilotBinarySensorEntityDescription, ...]] = (
    EcoPilotBinarySensorEntityDescription(
        key="burner_state",
        translation_key="burner_state",
        has_fn=lambda data: data.measurement.burner_state is not None,
        value_fn=lambda data: data.measurement.burner_state,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcoPilotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Initialize binary sensors."""

    entities: list = [
        EcoPilotBinarySensorEntity(entry.runtime_data, description)
        for description in BINARY_SENSORS
        if description.has_fn(entry.runtime_data.data)
    ]

    async_add_entities(entities)


class EcoPilotBinarySensorEntity(EcoPilotEntity, BinarySensorEntity):
    """Representation of a EcoPilot Sensor."""

    entity_description: EcoPilotBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: EcoPilotDeviceUpdateCoordinator,
        description: EcoPilotBinarySensorEntityDescription,
    ) -> None:
        """Initialize Binary Sensor Domain."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.unique_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        """Return the binary sensor state."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Return availability."""
        return super().available and self.is_on is not None
