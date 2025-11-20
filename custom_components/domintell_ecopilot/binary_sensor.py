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
from homeassistant.const import EntityCategory

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
    EcoPilotBinarySensorEntityDescription(
        key="p1_data",
        translation_key="p1_data",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        has_fn=(
            lambda data: data.system is not None and data.system.p1_data is not None
        ),
        value_fn=lambda data: data.system.p1_data,
    ),
    EcoPilotBinarySensorEntityDescription(
        key="mcu_status",
        translation_key="mcu_status",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        has_fn=(
            lambda data: data.system is not None and data.system.mcu_status is not None
        ),
        value_fn=lambda data: data.system.mcu_status,
    ),
    EcoPilotBinarySensorEntityDescription(
        key="temperature_probe",
        translation_key="temperature_probe",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        has_fn=(
            lambda data: data.system is not None
            and data.system.temperature_probe is not None
        ),
        value_fn=lambda data: data.system.temperature_probe,
    ),
    EcoPilotBinarySensorEntityDescription(
        key="bad_load",
        translation_key="bad_load",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        has_fn=(
            lambda data: data.system is not None and data.system.bad_load is not None
        ),
        value_fn=lambda data: data.system.bad_load,
    ),
    EcoPilotBinarySensorEntityDescription(
        key="overheat",
        translation_key="overheat",
        device_class=BinarySensorDeviceClass.HEAT,
        entity_category=EntityCategory.DIAGNOSTIC,
        has_fn=(
            lambda data: data.system is not None and data.system.overheat is not None
        ),
        value_fn=lambda data: data.system.overheat,
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
