"""Creates EcoPilot Number entities."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Final, Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
    UnitOfPower,
    UnitOfLength,
    UnitOfVolume,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .ecopilot_api.models import CombinedModels as DeviceResponseEntry
from .ecopilot_api import DomintellEcopilotV1
from .coordinator import EcoPilotConfigEntry, EcoPilotDeviceUpdateCoordinator
from .entity import EcoPilotEntity
from .helpers import ecopilot_exception_handler


@dataclass(frozen=True, kw_only=True)
class EcoPilotNumberEntityDescription(NumberEntityDescription):
    """Class describing EcoPilot number entities."""

    available_fn: Callable[[DeviceResponseEntry], bool]
    enabled_fn: Callable[[DeviceResponseEntry], bool] = lambda x: True
    has_fn: Callable[[DeviceResponseEntry], bool]
    value_fn: Callable[[DeviceResponseEntry], StateType]
    set_fn: Callable[[DomintellEcopilotV1, int], Awaitable[Any]]


NUMBERS: Final[tuple[EcoPilotNumberEntityDescription, ...]] = (
    EcoPilotNumberEntityDescription(
        key="overload_protection",
        translation_key="overload_protection",
        native_unit_of_measurement=UnitOfPower.WATT,
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=3500,
        native_step=100,
        mode="box",
        available_fn=lambda data: data.config is not None,
        has_fn=lambda api: api.config is not None
        and api.config.overload_protection is not None,
        value_fn=lambda api: api.config.overload_protection,
        set_fn=lambda api, value: api.config(overload_protection=int(value)),
    ),
    EcoPilotNumberEntityDescription(
        key="pwm_state",
        translation_key="pwm_state",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        available_fn=lambda data: data.state is not None and data.config.mode == 0,
        has_fn=lambda api: api.state is not None and api.state.pwm_state is not None,
        value_fn=lambda api: api.state.pwm_state,
        set_fn=lambda api, value: api.state(pwm_state=int(value)),
    ),
    EcoPilotNumberEntityDescription(
        key="max_temperature",
        translation_key="max_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=80,
        native_step=1,
        mode="box",
        device_class=NumberDeviceClass.TEMPERATURE,
        available_fn=lambda api: api.config is not None,
        has_fn=lambda api: api.config is not None
        and api.config.max_temperature is not None,
        value_fn=lambda api: api.config.max_temperature,
        set_fn=lambda api, value: api.config(max_temperature=value),
    ),
    EcoPilotNumberEntityDescription(
        key="max_peak_power",
        translation_key="max_peak_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        entity_category=EntityCategory.CONFIG,
        native_min_value=100,
        native_max_value=4000,
        native_step=100,
        mode="box",
        device_class=NumberDeviceClass.POWER,
        available_fn=lambda api: api.config is not None,
        has_fn=lambda api: api.config is not None
        and api.config.max_peak_power is not None,
        value_fn=lambda api: api.config.max_peak_power,
        set_fn=lambda api, value: api.config(max_peak_power=value),
    ),
    EcoPilotNumberEntityDescription(
        key="max_pwm_power",
        translation_key="max_pwm_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        entity_category=EntityCategory.CONFIG,
        native_min_value=100,
        native_max_value=3000,
        native_step=100,
        mode="box",
        device_class=NumberDeviceClass.POWER,
        available_fn=lambda api: api.config is not None,
        has_fn=lambda api: api.config is not None
        and api.config.max_pwm_power is not None,
        value_fn=lambda api: api.config.max_pwm_power,
        set_fn=lambda api, value: api.config(max_pwm_power=value),
    ),
    EcoPilotNumberEntityDescription(
        key="threshold_power",
        translation_key="threshold_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=300,
        native_step=100,
        mode="box",
        device_class=NumberDeviceClass.POWER,
        available_fn=lambda api: api.config is not None and api.config.mode != 0,
        has_fn=lambda api: api.config is not None
        and api.config.threshold_power is not None,
        value_fn=lambda api: api.config.threshold_power,
        set_fn=lambda api, value: api.config(threshold_power=value),
    ),
    EcoPilotNumberEntityDescription(
        key="current_heating_oil_volume",
        translation_key="current_heating_oil_volume",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=NumberDeviceClass.VOLUME,
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=5000,
        native_step=100,
        mode="box",
        available_fn=lambda data: data.state is not None,
        has_fn=lambda api: api.state is not None
        and api.state.current_heating_oil_volume is not None,
        value_fn=lambda api: api.state.current_heating_oil_volume,
        set_fn=lambda api, value: api.state(current_heating_oil_volume=value),
    ),
    EcoPilotNumberEntityDescription(
        key="heating_oil_energy_density",
        translation_key="heating_oil_energy_density",
        native_unit_of_measurement="kWh/L",
        entity_category=EntityCategory.CONFIG,
        native_min_value=8,
        native_max_value=15,
        native_step=0.5,
        mode="box",
        available_fn=lambda data: data.config is not None,
        has_fn=lambda api: api.config is not None
        and api.config.heating_oil_energy_density is not None,
        value_fn=lambda api: api.config.heating_oil_energy_density,
        set_fn=lambda api, value: api.config(heating_oil_energy_density=value),
    ),
    EcoPilotNumberEntityDescription(
        key="heating_oil_consumption_rate",
        translation_key="heating_oil_consumption_rate",
        native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_HOUR,
        device_class=NumberDeviceClass.VOLUME_FLOW_RATE,
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=10,
        native_step=0.5,
        mode="box",
        available_fn=lambda data: data.config is not None,
        has_fn=lambda api: api.config is not None
        and api.config.heating_oil_consumption_rate is not None,
        value_fn=lambda api: api.config.heating_oil_consumption_rate,
        set_fn=lambda api, value: api.config(heating_oil_consumption_rate=value),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcoPilotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Initialize numbers."""

    # Initialize default numbers
    entities: list = [
        EcoPilotNumberEntity(entry.runtime_data, description)
        for description in NUMBERS
        if description.has_fn(entry.runtime_data.data)
    ]

    async_add_entities(entities)


class EcoPilotNumberEntity(EcoPilotEntity, NumberEntity):
    """Representation of number."""

    entity_description: EcoPilotNumberEntityDescription

    def __init__(
        self,
        coordinator: EcoPilotDeviceUpdateCoordinator,
        description: EcoPilotNumberEntityDescription,
    ) -> None:
        """Initialize the control number."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.unique_id}_{description.key}"
        if not description.enabled_fn(self.coordinator.data):
            self._attr_entity_registry_enabled_default = False

    @ecopilot_exception_handler
    async def async_set_native_value(self, value: float) -> None:
        """Set a new value."""

        await self.entity_description.set_fn(self.coordinator.api, value)
        await self.coordinator.async_refresh()

    @property
    def available(self) -> bool:
        """Return availability."""
        return super().available and self.entity_description.available_fn(
            self.coordinator.data
        )

    @property
    def native_value(self) -> StateType | None:
        """Return the number value."""
        return self.entity_description.value_fn(self.coordinator.data)
