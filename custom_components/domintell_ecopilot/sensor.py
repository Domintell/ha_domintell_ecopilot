"""Creates EcoPilot sensor entities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final


from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    DEVICE_CLASS_UNITS,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    ATTR_VIA_DEVICE,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS,
    EntityCategory,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfReactivePower,
    UnitOfVolume,
    UnitOfVolumeFlowRate,
    UnitOfTemperature,
    UnitOfLength,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.util.dt import utcnow

from .const import DOMAIN, TANK_SHAPE_MAP, LOGGER
from .coordinator import (
    EcoPilotConfigEntry,
    EcoPilotDeviceUpdateCoordinator,
)
from .entity import EcoPilotEntity
from .ecopilot_api.models import CombinedModels, Device


@dataclass(frozen=True, kw_only=True)
class EcoPilotSensorEntityDescription(SensorEntityDescription):
    """Class describing EcoPilot sensor entities."""

    enabled_fn: Callable[[CombinedModels], bool] = lambda x: True
    has_fn: Callable[[CombinedModels], bool]
    value_fn: Callable[[CombinedModels], StateType | datetime]


@dataclass(frozen=True, kw_only=True)
class EcoPilotP1SensorEntityDescription(SensorEntityDescription):
    """Class describing P1 sensor entities."""

    suggested_device_class: SensorDeviceClass
    device_name: str


def to_percentage(value: float | None) -> float | None:
    """Convert 0..1 value to percentage when value is not None."""
    return value * 100 if value is not None else None


def time_to_datetime(value: int | None) -> datetime | None:
    """Convert seconds to datetime when value is not None."""
    return (
        utcnow().replace(microsecond=0) - timedelta(seconds=value)
        if value is not None
        else None
    )


P1_METER: Final[tuple[EcoPilotSensorEntityDescription, ...]] = (
    EcoPilotSensorEntityDescription(
        key="dsmr_version",
        translation_key="dsmr_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        has_fn=lambda data: data.dsmr_version is not None,
        value_fn=lambda data: data.dsmr_version,
    ),
    EcoPilotSensorEntityDescription(
        key="meter_model",
        translation_key="meter_model",
        entity_category=EntityCategory.DIAGNOSTIC,
        has_fn=lambda data: data.meter_model is not None,
        value_fn=lambda data: data.meter_model,
    ),
    EcoPilotSensorEntityDescription(
        key="unique_id",
        translation_key="unique_id",
        entity_category=EntityCategory.DIAGNOSTIC,
        has_fn=lambda data: data.unique_id is not None,
        value_fn=lambda data: data.unique_id,
    ),
    EcoPilotSensorEntityDescription(
        key="tariff_indicator",
        translation_key="tariff_indicator",
        has_fn=lambda data: data.tariff_indicator is not None,
        value_fn=(
            lambda data: (
                None if data.tariff_indicator is None else str(data.tariff_indicator)
            )
        ),
        device_class=SensorDeviceClass.ENUM,
        options=["1", "2", "3", "4"],
    ),
    EcoPilotSensorEntityDescription(
        key="energy_import",
        translation_key="energy_import",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: data.energy_import is not None,
        value_fn=lambda data: data.energy_import,
    ),
    EcoPilotSensorEntityDescription(
        key="energy_import_t1",
        translation_key="total_energy_import_tariff",
        translation_placeholders={"tariff": "1"},
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: (
            # SKT/SDM230/630 provides both total and tariff 1: duplicate.
            data.energy_import_t1 is not None
            and data.energy_import_t2 is not None
        ),
        value_fn=lambda data: data.energy_import_t1,
    ),
    EcoPilotSensorEntityDescription(
        key="energy_import_t2",
        translation_key="total_energy_import_tariff",
        translation_placeholders={"tariff": "2"},
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: data.energy_import_t2 is not None,
        value_fn=lambda data: data.energy_import_t2,
    ),
    EcoPilotSensorEntityDescription(
        key="energy_import_t3",
        translation_key="total_energy_import_tariff",
        translation_placeholders={"tariff": "3"},
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: data.energy_import_t3 is not None,
        value_fn=lambda data: data.energy_import_t3,
    ),
    EcoPilotSensorEntityDescription(
        key="energy_import_t4",
        translation_key="total_energy_import_tariff",
        translation_placeholders={"tariff": "4"},
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: data.energy_import_t4 is not None,
        value_fn=lambda data: data.energy_import_t4,
    ),
    EcoPilotSensorEntityDescription(
        key="energy_export",
        translation_key="energy_export",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: data.energy_export is not None,
        enabled_fn=lambda data: data.energy_export != 0,
        value_fn=lambda data: data.energy_export,
    ),
    EcoPilotSensorEntityDescription(
        key="energy_export_t1",
        translation_key="total_energy_export_tariff",
        translation_placeholders={"tariff": "1"},
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: (
            # SKT/SDM230/630 provides both total and tariff 1: duplicate.
            data.energy_export_t1 is not None
            and data.energy_export_t2 is not None
        ),
        enabled_fn=lambda data: data.energy_export_t1 != 0,
        value_fn=lambda data: data.energy_export_t1,
    ),
    EcoPilotSensorEntityDescription(
        key="energy_export_t2",
        translation_key="total_energy_export_tariff",
        translation_placeholders={"tariff": "2"},
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: data.energy_export_t2 is not None,
        enabled_fn=lambda data: data.energy_export_t2 != 0,
        value_fn=lambda data: data.energy_export_t2,
    ),
    EcoPilotSensorEntityDescription(
        key="energy_export_t3",
        translation_key="total_energy_export_tariff",
        translation_placeholders={"tariff": "3"},
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: data.energy_export_t3 is not None,
        enabled_fn=lambda data: data.energy_export_t3 != 0,
        value_fn=lambda data: data.energy_export_t3,
    ),
    EcoPilotSensorEntityDescription(
        key="energy_export_t4",
        translation_key="total_energy_export_tariff",
        translation_placeholders={"tariff": "4"},
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: data.energy_export_t4 is not None,
        enabled_fn=lambda data: data.energy_export_t4 != 0,
        value_fn=lambda data: data.energy_export_t4,
    ),
    EcoPilotSensorEntityDescription(
        key="power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        has_fn=lambda data: data.power is not None,
        value_fn=lambda data: data.power,
    ),
    EcoPilotSensorEntityDescription(
        key="power_l1",
        translation_key="power_phase",
        translation_placeholders={"phase": "1"},
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        has_fn=lambda data: data.power_l1 is not None,
        value_fn=lambda data: data.power_l1,
    ),
    EcoPilotSensorEntityDescription(
        key="power_l2",
        translation_key="power_phase",
        translation_placeholders={"phase": "2"},
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        has_fn=lambda data: data.power_l2 is not None,
        value_fn=lambda data: data.power_l2,
    ),
    EcoPilotSensorEntityDescription(
        key="power_l3",
        translation_key="power_phase",
        translation_placeholders={"phase": "3"},
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        has_fn=lambda data: data.power_l3 is not None,
        value_fn=lambda data: data.power_l3,
    ),
    EcoPilotSensorEntityDescription(
        key="voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.voltage is not None,
        value_fn=lambda data: data.voltage,
    ),
    EcoPilotSensorEntityDescription(
        key="voltage_l1",
        translation_key="voltage_phase",
        translation_placeholders={"phase": "1"},
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.voltage_l1 is not None,
        value_fn=lambda data: data.voltage_l1,
    ),
    EcoPilotSensorEntityDescription(
        key="voltage_l2",
        translation_key="voltage_phase",
        translation_placeholders={"phase": "2"},
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.voltage_l2 is not None,
        value_fn=lambda data: data.voltage_l2,
    ),
    EcoPilotSensorEntityDescription(
        key="voltage_l3",
        translation_key="voltage_phase",
        translation_placeholders={"phase": "3"},
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.voltage_l3 is not None,
        value_fn=lambda data: data.voltage_l3,
    ),
    EcoPilotSensorEntityDescription(
        key="current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.current is not None,
        value_fn=lambda data: data.current,
    ),
    EcoPilotSensorEntityDescription(
        key="current_l1",
        translation_key="current_phase",
        translation_placeholders={"phase": "1"},
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.current_l1 is not None,
        value_fn=lambda data: data.current_l1,
    ),
    EcoPilotSensorEntityDescription(
        key="current_l2",
        translation_key="current_phase",
        translation_placeholders={"phase": "2"},
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.current_l2 is not None,
        value_fn=lambda data: data.current_l2,
    ),
    EcoPilotSensorEntityDescription(
        key="current_l3",
        translation_key="current_phase",
        translation_placeholders={"phase": "3"},
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.current_l3 is not None,
        value_fn=lambda data: data.current_l3,
    ),
    EcoPilotSensorEntityDescription(
        key="voltage_sag_l1",
        translation_key="voltage_sag_phase",
        translation_placeholders={"phase": "1"},
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.voltage_sag_l1 is not None,
        value_fn=lambda data: data.voltage_sag_l1,
    ),
    EcoPilotSensorEntityDescription(
        key="voltage_sag_l2",
        translation_key="voltage_sag_phase",
        translation_placeholders={"phase": "2"},
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.voltage_sag_l2 is not None,
        value_fn=lambda data: data.voltage_sag_l2,
    ),
    EcoPilotSensorEntityDescription(
        key="voltage_sag_l3",
        translation_key="voltage_sag_phase",
        translation_placeholders={"phase": "3"},
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.voltage_sag_l3 is not None,
        value_fn=lambda data: data.voltage_sag_l3,
    ),
    EcoPilotSensorEntityDescription(
        key="voltage_swell_l1",
        translation_key="voltage_swell_phase",
        translation_placeholders={"phase": "1"},
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.voltage_swell_l1 is not None,
        value_fn=lambda data: data.voltage_swell_l1,
    ),
    EcoPilotSensorEntityDescription(
        key="voltage_swell_l2",
        translation_key="voltage_swell_phase",
        translation_placeholders={"phase": "2"},
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.voltage_swell_l2 is not None,
        value_fn=lambda data: data.voltage_swell_l2,
    ),
    EcoPilotSensorEntityDescription(
        key="voltage_swell_l3",
        translation_key="voltage_swell_phase",
        translation_placeholders={"phase": "3"},
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.voltage_swell_l3 is not None,
        value_fn=lambda data: data.voltage_swell_l3,
    ),
    EcoPilotSensorEntityDescription(
        key="any_power_fail_count",
        translation_key="any_power_fail_count",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.any_power_fail_count is not None,
        value_fn=lambda data: data.any_power_fail_count,
    ),
    EcoPilotSensorEntityDescription(
        key="long_power_fail_count",
        translation_key="long_power_fail_count",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.long_power_fail_count is not None,
        value_fn=lambda data: data.long_power_fail_count,
    ),
)


SENSORS: Final[tuple[EcoPilotSensorEntityDescription, ...]] = (
    EcoPilotSensorEntityDescription(
        key="wifi_ssid",
        translation_key="wifi_ssid",
        entity_category=EntityCategory.DIAGNOSTIC,
        has_fn=(
            lambda data: data.system is not None and data.system.wifi_ssid is not None
        ),
        value_fn=(
            lambda data: data.system.wifi_ssid if data.system is not None else None
        ),
    ),
    EcoPilotSensorEntityDescription(
        key="wifi_strength",
        translation_key="wifi_strength",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        has_fn=(
            lambda data: data.system is not None
            and data.system.wifi_strength is not None
        ),
        value_fn=(
            lambda data: (
                data.system.wifi_strength if data.system is not None else None
            )
        ),
    ),
    # EcoPilotSensorEntityDescription(
    #     key="wifi_rssi",
    #     translation_key="wifi_rssi",
    #     native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
    #     state_class=SensorStateClass.MEASUREMENT,
    #     entity_category=EntityCategory.DIAGNOSTIC,
    #     entity_registry_enabled_default=False,
    #     has_fn=(
    #         lambda data: data.system is not None
    #         and data.system.wifi_rssi_db is not None
    #     ),
    #     value_fn=(
    #         lambda data: data.system.wifi_rssi_db if data.system is not None else None
    #     ),
    # ),
    EcoPilotSensorEntityDescription(
        key="dsmr_version",
        translation_key="dsmr_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        has_fn=lambda data: data.measurement.dsmr_version is not None,
        value_fn=lambda data: data.measurement.dsmr_version,
    ),
    EcoPilotSensorEntityDescription(
        key="meter_model",
        translation_key="meter_model",
        entity_category=EntityCategory.DIAGNOSTIC,
        has_fn=lambda data: data.measurement.meter_model is not None,
        value_fn=lambda data: data.measurement.meter_model,
    ),
    EcoPilotSensorEntityDescription(
        key="unique_id",
        translation_key="unique_id",
        entity_category=EntityCategory.DIAGNOSTIC,
        has_fn=lambda data: data.measurement.unique_id is not None,
        value_fn=lambda data: data.measurement.unique_id,
    ),
    EcoPilotSensorEntityDescription(
        key="tariff_indicator",
        translation_key="tariff_indicator",
        has_fn=lambda data: data.measurement.tariff_indicator is not None,
        value_fn=(
            lambda data: (
                None
                if data.measurement.tariff_indicator is None
                else str(data.measurement.tariff_indicator)
            )
        ),
        device_class=SensorDeviceClass.ENUM,
        options=["1", "2", "3", "4"],
    ),
    EcoPilotSensorEntityDescription(
        key="energy",
        translation_key="energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: data.measurement.energy is not None,
        value_fn=lambda data: data.measurement.energy,
    ),
    EcoPilotSensorEntityDescription(
        key="energy_import",
        translation_key="energy_import",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: data.measurement.energy_import is not None,
        value_fn=lambda data: data.measurement.energy_import,
    ),
    EcoPilotSensorEntityDescription(
        key="energy_import_t1",
        translation_key="total_energy_import_tariff",
        translation_placeholders={"tariff": "1"},
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: (
            # SKT/SDM230/630 provides both total and tariff 1: duplicate.
            data.measurement.energy_import_t1 is not None
            and data.measurement.energy_import_t2 is not None
        ),
        value_fn=lambda data: data.measurement.energy_import_t1,
    ),
    EcoPilotSensorEntityDescription(
        key="energy_import_t2",
        translation_key="total_energy_import_tariff",
        translation_placeholders={"tariff": "2"},
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: data.measurement.energy_import_t2 is not None,
        value_fn=lambda data: data.measurement.energy_import_t2,
    ),
    EcoPilotSensorEntityDescription(
        key="energy_import_t3",
        translation_key="total_energy_import_tariff",
        translation_placeholders={"tariff": "3"},
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: data.measurement.energy_import_t3 is not None,
        value_fn=lambda data: data.measurement.energy_import_t3,
    ),
    EcoPilotSensorEntityDescription(
        key="energy_import_t4",
        translation_key="total_energy_import_tariff",
        translation_placeholders={"tariff": "4"},
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: data.measurement.energy_import_t4 is not None,
        value_fn=lambda data: data.measurement.energy_import_t4,
    ),
    EcoPilotSensorEntityDescription(
        key="energy_export",
        translation_key="energy_export",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: data.measurement.energy_export is not None,
        enabled_fn=lambda data: data.measurement.energy_export != 0,
        value_fn=lambda data: data.measurement.energy_export,
    ),
    EcoPilotSensorEntityDescription(
        key="energy_export_t1",
        translation_key="total_energy_export_tariff",
        translation_placeholders={"tariff": "1"},
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: (
            # SKT/SDM230/630 provides both total and tariff 1: duplicate.
            data.measurement.energy_export_t1 is not None
            and data.measurement.energy_export_t2 is not None
        ),
        enabled_fn=lambda data: data.measurement.energy_export_t1 != 0,
        value_fn=lambda data: data.measurement.energy_export_t1,
    ),
    EcoPilotSensorEntityDescription(
        key="energy_export_t2",
        translation_key="total_energy_export_tariff",
        translation_placeholders={"tariff": "2"},
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: data.measurement.energy_export_t2 is not None,
        enabled_fn=lambda data: data.measurement.energy_export_t2 != 0,
        value_fn=lambda data: data.measurement.energy_export_t2,
    ),
    EcoPilotSensorEntityDescription(
        key="energy_export_t3",
        translation_key="total_energy_export_tariff",
        translation_placeholders={"tariff": "3"},
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: data.measurement.energy_export_t3 is not None,
        enabled_fn=lambda data: data.measurement.energy_export_t3 != 0,
        value_fn=lambda data: data.measurement.energy_export_t3,
    ),
    EcoPilotSensorEntityDescription(
        key="energy_export_t4",
        translation_key="total_energy_export_tariff",
        translation_placeholders={"tariff": "4"},
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: data.measurement.energy_export_t4 is not None,
        enabled_fn=lambda data: data.measurement.energy_export_t4 != 0,
        value_fn=lambda data: data.measurement.energy_export_t4,
    ),
    EcoPilotSensorEntityDescription(
        key="power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        has_fn=lambda data: data.measurement.power is not None,
        value_fn=lambda data: data.measurement.power,
    ),
    EcoPilotSensorEntityDescription(
        key="power_l1",
        translation_key="power_phase",
        translation_placeholders={"phase": "1"},
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        has_fn=lambda data: data.measurement.power_l1 is not None,
        value_fn=lambda data: data.measurement.power_l1,
    ),
    EcoPilotSensorEntityDescription(
        key="power_l2",
        translation_key="power_phase",
        translation_placeholders={"phase": "2"},
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        has_fn=lambda data: data.measurement.power_l2 is not None,
        value_fn=lambda data: data.measurement.power_l2,
    ),
    EcoPilotSensorEntityDescription(
        key="power_l3",
        translation_key="power_phase",
        translation_placeholders={"phase": "3"},
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        has_fn=lambda data: data.measurement.power_l3 is not None,
        value_fn=lambda data: data.measurement.power_l3,
    ),
    EcoPilotSensorEntityDescription(
        key="voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.measurement.voltage is not None,
        value_fn=lambda data: data.measurement.voltage,
    ),
    EcoPilotSensorEntityDescription(
        key="voltage_l1",
        translation_key="voltage_phase",
        translation_placeholders={"phase": "1"},
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.measurement.voltage_l1 is not None,
        value_fn=lambda data: data.measurement.voltage_l1,
    ),
    EcoPilotSensorEntityDescription(
        key="voltage_l2",
        translation_key="voltage_phase",
        translation_placeholders={"phase": "2"},
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.measurement.voltage_l2 is not None,
        value_fn=lambda data: data.measurement.voltage_l2,
    ),
    EcoPilotSensorEntityDescription(
        key="voltage_l3",
        translation_key="voltage_phase",
        translation_placeholders={"phase": "3"},
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.measurement.voltage_l3 is not None,
        value_fn=lambda data: data.measurement.voltage_l3,
    ),
    EcoPilotSensorEntityDescription(
        key="current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.measurement.current is not None,
        value_fn=lambda data: data.measurement.current,
    ),
    EcoPilotSensorEntityDescription(
        key="current_l1",
        translation_key="current_phase",
        translation_placeholders={"phase": "1"},
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.measurement.current_l1 is not None,
        value_fn=lambda data: data.measurement.current_l1,
    ),
    EcoPilotSensorEntityDescription(
        key="current_l2",
        translation_key="current_phase",
        translation_placeholders={"phase": "2"},
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.measurement.current_l2 is not None,
        value_fn=lambda data: data.measurement.current_l2,
    ),
    EcoPilotSensorEntityDescription(
        key="current_l3",
        translation_key="current_phase",
        translation_placeholders={"phase": "3"},
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.measurement.current_l3 is not None,
        value_fn=lambda data: data.measurement.current_l3,
    ),
    EcoPilotSensorEntityDescription(
        key="frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.measurement.frequency is not None,
        value_fn=lambda data: data.measurement.frequency,
    ),
    EcoPilotSensorEntityDescription(
        key="voltage_sag_l1",
        translation_key="voltage_sag_phase",
        translation_placeholders={"phase": "1"},
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.measurement.voltage_sag_l1 is not None,
        value_fn=lambda data: data.measurement.voltage_sag_l1,
    ),
    EcoPilotSensorEntityDescription(
        key="voltage_sag_l2",
        translation_key="voltage_sag_phase",
        translation_placeholders={"phase": "2"},
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.measurement.voltage_sag_l2 is not None,
        value_fn=lambda data: data.measurement.voltage_sag_l2,
    ),
    EcoPilotSensorEntityDescription(
        key="voltage_sag_l3",
        translation_key="voltage_sag_phase",
        translation_placeholders={"phase": "3"},
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.measurement.voltage_sag_l3 is not None,
        value_fn=lambda data: data.measurement.voltage_sag_l3,
    ),
    EcoPilotSensorEntityDescription(
        key="voltage_swell_l1",
        translation_key="voltage_swell_phase",
        translation_placeholders={"phase": "1"},
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.measurement.voltage_swell_l1 is not None,
        value_fn=lambda data: data.measurement.voltage_swell_l1,
    ),
    EcoPilotSensorEntityDescription(
        key="voltage_swell_l2",
        translation_key="voltage_swell_phase",
        translation_placeholders={"phase": "2"},
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.measurement.voltage_swell_l2 is not None,
        value_fn=lambda data: data.measurement.voltage_swell_l2,
    ),
    EcoPilotSensorEntityDescription(
        key="voltage_swell_l3",
        translation_key="voltage_swell_phase",
        translation_placeholders={"phase": "3"},
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.measurement.voltage_swell_l3 is not None,
        value_fn=lambda data: data.measurement.voltage_swell_l3,
    ),
    EcoPilotSensorEntityDescription(
        key="any_power_fail_count",
        translation_key="any_power_fail_count",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.measurement.any_power_fail_count is not None,
        value_fn=lambda data: data.measurement.any_power_fail_count,
    ),
    EcoPilotSensorEntityDescription(
        key="long_power_fail_count",
        translation_key="long_power_fail_count",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        has_fn=lambda data: data.measurement.long_power_fail_count is not None,
        value_fn=lambda data: data.measurement.long_power_fail_count,
    ),
    EcoPilotSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        has_fn=lambda data: data.measurement.temperature is not None,
        value_fn=lambda data: data.measurement.temperature,
    ),
    EcoPilotSensorEntityDescription(
        key="internal_temperature",
        translation_key="internal_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=1,
        has_fn=lambda data: data.measurement.internal_temperature is not None,
        value_fn=lambda data: data.measurement.internal_temperature,
    ),
    EcoPilotSensorEntityDescription(
        key="external_temperature",
        translation_key="external_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        has_fn=lambda data: data.measurement.external_temperature is not None,
        value_fn=lambda data: data.measurement.external_temperature,
    ),
    EcoPilotSensorEntityDescription(
        key="water_flow_rate",
        translation_key="water_flow_rate",
        native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT,
        has_fn=lambda data: data.measurement.water_flow_rate is not None,
        value_fn=lambda data: data.measurement.water_flow_rate,
    ),
    EcoPilotSensorEntityDescription(
        key="water_consumed",
        translation_key="water_consumed",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: data.measurement.water_consumed is not None,
        value_fn=lambda data: data.measurement.water_consumed,
    ),
    EcoPilotSensorEntityDescription(
        key="heating_oil_consumed",
        translation_key="heating_oil_consumed",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.VOLUME,
        state_class=SensorStateClass.TOTAL_INCREASING,
        has_fn=lambda data: data.measurement.heating_oil_consumed is not None,
        value_fn=lambda data: data.measurement.heating_oil_consumed,
    ),
    EcoPilotSensorEntityDescription(
        key="remaining_heating_oil_level",
        translation_key="remaining_heating_oil_level",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.VOLUME_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        has_fn=lambda data: data.measurement.remaining_heating_oil_level is not None,
        value_fn=lambda data: data.measurement.remaining_heating_oil_level,
    ),
    EcoPilotSensorEntityDescription(
        key="distance",
        translation_key="distance",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        has_fn=lambda data: data.measurement.distance is not None,
        value_fn=lambda data: data.measurement.distance,
    ),
    EcoPilotSensorEntityDescription(
        key="level",
        translation_key="level",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        has_fn=lambda data: data.measurement.level is not None,
        value_fn=lambda data: data.measurement.level,
    ),
    EcoPilotSensorEntityDescription(
        key="battery_level",
        translation_key="battery_level",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        has_fn=lambda data: data.measurement.battery_level is not None,
        value_fn=lambda data: data.measurement.battery_level,
    ),
    EcoPilotSensorEntityDescription(
        key="battery_voltage",
        translation_key="battery_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=1,
        has_fn=lambda data: data.measurement.battery_voltage is not None,
        value_fn=lambda data: data.measurement.battery_voltage,
    ),
    EcoPilotSensorEntityDescription(
        key="volume",
        translation_key="volume",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.VOLUME_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        has_fn=lambda data: data.measurement.volume is not None,
        value_fn=lambda data: data.measurement.volume,
    ),
    EcoPilotSensorEntityDescription(
        key="srssi",
        translation_key="srssi",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        has_fn=lambda data: data.measurement.srssi is not None,
        value_fn=lambda data: data.measurement.srssi,
    ),
    EcoPilotSensorEntityDescription(
        key="src",
        translation_key="src",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        has_fn=lambda data: data.measurement.src is not None,
        value_fn=lambda data: data.measurement.src,
    ),
    EcoPilotSensorEntityDescription(
        key="uptime",
        translation_key="uptime",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        has_fn=(
            lambda data: data.system is not None and data.system.uptime is not None
        ),
        value_fn=(
            lambda data: time_to_datetime(data.system.uptime) if data.system else None
        ),
    ),
    EcoPilotSensorEntityDescription(
        key="distance_offset",
        translation_key="distance_offset",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=1,
        has_fn=lambda api: api.config.distance_offset is not None,
        value_fn=lambda api: api.config.distance_offset,
    ),
    EcoPilotSensorEntityDescription(
        key="tank_shape",
        translation_key="tank_shape",
        device_class=SensorDeviceClass.ENUM,
        options=list(TANK_SHAPE_MAP.values()),
        entity_category=EntityCategory.DIAGNOSTIC,
        has_fn=lambda api: api.config.tank_shape is not None,
        value_fn=lambda api: TANK_SHAPE_MAP.get(api.config.tank_shape, "Unknown"),
    ),
    EcoPilotSensorEntityDescription(
        key="height_max",
        translation_key="height_max",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        entity_category=EntityCategory.DIAGNOSTIC,
        has_fn=lambda api: api.config.height_max is not None,
        value_fn=lambda api: api.config.height_max,
    ),
    EcoPilotSensorEntityDescription(
        key="tank_capacity",
        translation_key="tank_capacity",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.VOLUME,
        entity_category=EntityCategory.DIAGNOSTIC,
        has_fn=lambda api: api.config.tank_capacity is not None,
        value_fn=lambda api: api.config.tank_capacity,
    ),
    EcoPilotSensorEntityDescription(
        key="tank_length",
        translation_key="tank_length",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        has_fn=lambda api: api.config.tank_length is not None,
        value_fn=lambda api: api.config.tank_length,
    ),
    EcoPilotSensorEntityDescription(
        key="tank_width",
        translation_key="tank_width",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        has_fn=lambda api: api.config.tank_width is not None,
        value_fn=lambda api: api.config.tank_width,
    ),
    EcoPilotSensorEntityDescription(
        key="tank_height",
        translation_key="tank_height",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        has_fn=lambda api: api.config.tank_height is not None,
        value_fn=lambda api: api.config.tank_height,
    ),
    EcoPilotSensorEntityDescription(
        key="tank_cylinder_radius",
        translation_key="tank_cylinder_radius",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        has_fn=lambda api: api.config.tank_cylinder_radius is not None,
        value_fn=lambda api: api.config.tank_cylinder_radius,
    ),
    EcoPilotSensorEntityDescription(
        key="tank_cylinder_height",
        translation_key="tank_cylinder_height",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        has_fn=lambda api: api.config.tank_cylinder_height is not None,
        value_fn=lambda api: api.config.tank_cylinder_height,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcoPilotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Initialize sensors."""
    coordinator: EcoPilotDeviceUpdateCoordinator = entry.runtime_data

    # Initialize default sensors
    entities: list = [
        EcoPilotSensorEntity(entry.runtime_data, description)
        for description in SENSORS
        if description.has_fn(entry.runtime_data.data)
    ]

    # Initialize P1 meter
    measurement = entry.runtime_data.data.measurement
    if measurement.p1 is not None:
        p1_unique_id = measurement.p1.unique_id
        p1_entities: list = [
            EcoPilotP1SensorEntity(entry.runtime_data, description, p1_unique_id)
            for description in P1_METER
            if description.has_fn(measurement.p1)
        ]

        # Add P1 meter entities
        entities.extend(p1_entities)

    async_add_entities(entities)

    # Check for entities that no longer exist and remove them
    entity_reg = er.async_get(hass)
    reg_entities = er.async_entries_for_config_entry(entity_reg, entry.entry_id)

    for entity in reg_entities:
        if entity.domain != SENSOR_DOMAIN:
            continue

        part = entity.unique_id.split("_")
        part_right = "_".join(part[2:])

        if part_right:
            key = part_right

            if key in [
                "height_max",
                "tank_length",
                "tank_width",
                "tank_height",
                "tank_radius",
            ]:
                attribute_value = getattr(coordinator.data.config, key, None)
                if attribute_value is None:
                    LOGGER.warning("remove:", entity.entity_id)
                    entity_reg.async_remove(entity.entity_id)


class EcoPilotSensorEntity(EcoPilotEntity, SensorEntity):
    """Representation of a EcoPilot Sensor."""

    entity_description: EcoPilotSensorEntityDescription

    def __init__(
        self,
        coordinator: EcoPilotDeviceUpdateCoordinator,
        description: EcoPilotSensorEntityDescription,
    ) -> None:
        """Initialize Sensor Domain."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.unique_id}_{description.key}"
        if not description.enabled_fn(self.coordinator.data):
            self._attr_entity_registry_enabled_default = False

        if (
            description.key == "temperature"
            and coordinator.data.device.product_model == "tankSense"
        ):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> StateType | datetime | None:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Return availability."""
        return super().available and self.native_value is not None


class EcoPilotP1SensorEntity(EcoPilotEntity, SensorEntity):
    """Representation of P1 Sensor."""

    def __init__(
        self,
        coordinator: EcoPilotDeviceUpdateCoordinator,
        description: EcoPilotP1SensorEntityDescription,
        device_unique_id: str,
    ) -> None:
        """Initialize P1 Sensors."""
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device_unique_id
        self._attr_unique_id = f"{DOMAIN}_{device_unique_id}_{description.key}"
        meter_model = coordinator.data.measurement.p1.meter_model
        manufacturer = meter_model.split(" ", 1)[0]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_unique_id)},
            name="P1 meter",
            manufacturer="Domintell",
            # manufacturer=manufacturer if manufacturer != "" else "Domintell", #TODO
            model="Smart meter",
            model_id=meter_model if meter_model else None,  # what is in parentheses
            serial_number=device_unique_id,
        )

        device_identifier = f"{coordinator.data.device.product_model}_{coordinator.data.device.serial_number}"
        self._attr_device_info[ATTR_VIA_DEVICE] = (
            DOMAIN,
            device_identifier,
        )

    @property
    def native_value(self) -> StateType | datetime | None:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data.measurement.p1)

    @property
    def device(self) -> Device | None:
        """Return P1 device object."""
        return (
            self.coordinator.data.measurement.p1
            if self.coordinator.data.measurement.p1 is not None
            else None
        )

    @property
    def available(self) -> bool:
        """Return availability of P1 meter."""
        return super().available and self.device is not None
