"""Creates EcoPilot switch entities."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback


from .ecopilot_api import DomintellEcopilotV1
from .ecopilot_api.models import CombinedModels as DeviceResponseEntry
from .coordinator import (
    EcoPilotConfigEntry,
    EcoPilotDeviceUpdateCoordinator,
)
from .entity import EcoPilotEntity
from .helpers import ecopilot_exception_handler


@dataclass(frozen=True, kw_only=True)
class EcoPilotSwitchEntityDescription(SwitchEntityDescription):
    """Class describing EcoPilot switch entities."""

    available_fn: Callable[[DeviceResponseEntry], bool]
    create_fn: Callable[[DeviceResponseEntry], bool]
    is_on_fn: Callable[[DeviceResponseEntry], bool | None]
    set_fn: Callable[[DomintellEcopilotV1, bool], Awaitable[Any]]


SWITCHES = [
    EcoPilotSwitchEntityDescription(
        key="power_on",
        name=None,
        translation_key="power_on",
        device_class=SwitchDeviceClass.OUTLET,
        create_fn=lambda x: x.device.supports_state() and x.state.power_on is not None,
        available_fn=lambda x: x.state is not None and not x.config.switch_lock,
        is_on_fn=lambda x: x.state.power_on if x.state else None,
        set_fn=lambda api, active: api.state(power_on=active),
    ),
    EcoPilotSwitchEntityDescription(
        key="switch_lock",
        translation_key="switch_lock",
        entity_category=EntityCategory.CONFIG,
        create_fn=lambda x: x.device.supports_config()
        and x.config.switch_lock is not None,
        available_fn=lambda x: x.config is not None,
        is_on_fn=lambda x: x.config.switch_lock if x.config else None,
        set_fn=lambda api, active: api.config(switch_lock=active),
    ),
    EcoPilotSwitchEntityDescription(
        key="restore_state",
        translation_key="restore_state",
        entity_category=EntityCategory.CONFIG,
        create_fn=lambda x: x.device.supports_config()
        and x.config.restore_state is not None,
        available_fn=lambda x: x.config is not None,
        is_on_fn=lambda x: x.config.restore_state if x.config else None,
        set_fn=lambda api, active: api.config(restore_state=active),
    ),
    EcoPilotSwitchEntityDescription(
        key="relay1",
        translation_key="relay1",
        create_fn=lambda x: x.device.supports_state()
        and x.state.relay1_state is not None,
        available_fn=lambda x: x.state is not None and x.config.mode == 0,
        is_on_fn=lambda x: x.state.relay1_state if x.state else None,
        set_fn=lambda api, active: api.state(relay1_state=active),
    ),
    EcoPilotSwitchEntityDescription(
        key="relay2",
        translation_key="relay2",
        create_fn=lambda x: x.device.supports_state()
        and x.state.relay2_state is not None,
        available_fn=lambda x: x.state is not None and x.config.mode == 0,
        is_on_fn=lambda x: x.state.relay2_state if x.state else None,
        set_fn=lambda api, active: api.state(relay2_state=active),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcoPilotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up switches."""
    async_add_entities(
        EcoPilotSwitchEntity(entry.runtime_data, description)
        for description in SWITCHES
        if description.create_fn(entry.runtime_data.data)
    )


class EcoPilotSwitchEntity(EcoPilotEntity, SwitchEntity):
    """Representation of a Domintell EcoPilot switch."""

    entity_description: EcoPilotSwitchEntityDescription

    def __init__(
        self,
        coordinator: EcoPilotDeviceUpdateCoordinator,
        description: EcoPilotSwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.unique_id}_{description.key}"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self.entity_description.available_fn(
            self.coordinator.data
        )

    @property
    def is_on(self) -> bool | None:
        """Return state of the switch."""
        return self.entity_description.is_on_fn(self.coordinator.data)

    @ecopilot_exception_handler
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.entity_description.set_fn(self.coordinator.api, True)
        await self.coordinator.async_refresh()

    @ecopilot_exception_handler
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.entity_description.set_fn(self.coordinator.api, False)
        await self.coordinator.async_refresh()
