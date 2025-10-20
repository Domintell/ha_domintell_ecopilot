"""Creates EcoPilot select entities."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .ecopilot_api import DomintellEcopilotV1
from .ecopilot_api.models import CombinedModels as DeviceResponseEntry
from .coordinator import EcoPilotConfigEntry, EcoPilotDeviceUpdateCoordinator
from .entity import EcoPilotEntity
from .helpers import ecopilot_exception_handler


@dataclass(frozen=True, kw_only=True)
class EcoPilotSelectEntityDescription(SelectEntityDescription):
    """Class describing EcoPilot select entities."""

    available_fn: Callable[[DeviceResponseEntry], bool]
    create_fn: Callable[[DeviceResponseEntry], bool]
    current_fn: Callable[[DeviceResponseEntry], str | None]
    set_fn: Callable[[DomintellEcopilotV1, str], Awaitable[Any]]


DESCRIPTIONS = [
    EcoPilotSelectEntityDescription(
        key="mode",
        translation_key="mode",
        entity_category=EntityCategory.CONFIG,
        options=["0", "1", "2", "3", "4"],
        available_fn=lambda x: x.config is not None and x.config.mode is not None,
        create_fn=lambda x: x.config.mode is not None,
        current_fn=lambda x: str(x.config.mode) if hasattr(x.config, "mode") else None,
        set_fn=lambda api, mode: api.config(mode=mode),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcoPilotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up EcoPilot select based on a config entry."""
    async_add_entities(
        EcoPilotSelectEntity(
            coordinator=entry.runtime_data,
            description=description,
        )
        for description in DESCRIPTIONS
        if description.create_fn(entry.runtime_data.data)
    )


class EcoPilotSelectEntity(EcoPilotEntity, SelectEntity):
    """Defines a EcoPilot select entity."""

    entity_description: EcoPilotSelectEntityDescription

    def __init__(
        self,
        coordinator: EcoPilotDeviceUpdateCoordinator,
        description: EcoPilotSelectEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{coordinator.config_entry.unique_id}_{description.key}"

    @ecopilot_exception_handler
    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.entity_description.set_fn(self.coordinator.api, int(option))
        await self.coordinator.async_request_refresh()

    @property
    def available(self) -> bool:
        """Return availability."""
        return super().available and self.entity_description.available_fn(
            self.coordinator.data
        )

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        return self.entity_description.current_fn(self.coordinator.data)
