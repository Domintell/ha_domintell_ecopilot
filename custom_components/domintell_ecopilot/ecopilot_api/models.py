"""Common models for Domintell Ecopilot API."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from mashumaro.mixins.orjson import DataClassORJSONMixin

from .const import LOGGER, MODEL_TO_ID, MODEL_TO_NAME, Model


def get_verification_hostname(model: str, serial_number: str) -> str:
    """Helper method to convert device model and serial to identifier

    The identifier is used to verify the device in the Domintell Ecopilot API via HTTPS.
    """

    if model not in MODEL_TO_ID:
        raise ValueError(f"Unsupported model: {model}")

    return f"{MODEL_TO_ID[model]}_{serial_number}"


class BaseModel(DataClassORJSONMixin):
    """Base model for all Domintell EcoPilot models."""

    pass


class UpdateBaseModel(BaseModel):
    """Base model for all 'update' models."""

    def __post_serialize__(self, d: dict, context: dict | None = None):
        """Post serialize hook for UpdateBaseModel object."""
        _ = context  # Unused

        if not d:
            raise ValueError("No values to update")

        return d


@dataclass(kw_only=True)
class CombinedModels:
    """All values."""

    device: Device
    measurement: Measurement
    state: State | None
    config: Config | None
    system: System | None

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments
    def __init__(
        self,
        device: Device,
        measurement: Measurement,
        state: State | None,
        config: Config | None,
        system: System | None,
    ):
        self.device = device
        self.measurement = measurement
        self.state = state
        self.config = config
        self.system = system


@dataclass(kw_only=True)
class Device(BaseModel):
    """Represent Device config."""

    model_name: str | None = None
    id: str | None = None

    product_name: str = field()
    product_model: str = field()
    serial_number: str = field()
    firmware_version: str = field()
    hardware_version: str = field()
    api_version: str = field()

    @classmethod
    def __post_deserialize__(cls, obj: Device) -> Device:
        """Post deserialize hook for Device object."""
        _ = cls  # Unused

        obj.model_name = MODEL_TO_NAME.get(obj.product_model)
        obj.id = get_verification_hostname(obj.product_model, obj.serial_number)
        return obj

    def supports_state(self) -> bool:
        """Return if the device supports state."""
        return self.product_model not in (Model.ECOP1, Model.TANKSENSE)

    def supports_config(self) -> bool:
        """Return if the device supports config."""
        return self.product_model not in (Model.ECOP1)

    def supports_system(self) -> bool:
        """Return if the device supports system."""
        return self.product_model not in (Model.TANKSENSE,)

    def supports_reboot(self) -> bool:
        """Return if the device supports reboot."""
        return self.product_model in (
            Model.ECOP1,
            Model.ECOPLUG,
            Model.ECODRIVE_P1,
            Model.ECODRIVE_LK,
            Model.TANKSENSE,
            Model.HUBSENSE,
            Model.HUBSENSE_ETH,
        )

    def supports_identify(self) -> bool:
        """Return if the device supports identify."""
        return self.product_model in (
            Model.ECOP1,
            Model.ECOPLUG,
            Model.ECODRIVE_P1,
            Model.ECODRIVE_LK,
            Model.TANKSENSE,
            Model.HUBSENSE,
            Model.HUBSENSE_ETH,
        )

    def supports_update(self) -> bool:
        """Return if the device supports update."""
        return self.product_model in (
            Model.ECOP1,
            Model.ECOPLUG,
            Model.ECODRIVE_P1,
            Model.ECODRIVE_LK,
            Model.TANKSENSE,
            Model.HUBSENSE,
            Model.HUBSENSE_ETH,
        )


@dataclass(kw_only=True)
class Measurement(BaseModel):
    """Represent Measurement."""

    # Generic
    p1: P1 | None = field(
        default=None,
        metadata={
            "alias": "p1",
            "deserialize": lambda obj: Measurement.to_p1(obj),
        },
    )

    # ecoP1 Specific
    unique_id: str | None = field(
        default=None,
        metadata={"deserialize": lambda x: Measurement.hex_to_readable(x)},
    )
    dsmr_version: int | None = field(
        default=None,
    )
    meter_model: str | None = field(
        default=None,
    )
    voltage: float | None = field(
        default=None,
    )
    voltage_l1: float | None = field(
        default=None,
    )
    voltage_l2: float | None = field(
        default=None,
    )
    voltage_l3: float | None = field(
        default=None,
    )
    current: float | None = field(
        default=None,
    )
    current_l1: float | None = field(
        default=None,
    )
    current_l2: float | None = field(
        default=None,
    )
    current_l3: float | None = field(
        default=None,
    )
    power: float | None = field(
        default=None,
    )
    power_l1: float | None = field(
        default=None,
    )
    power_l2: float | None = field(
        default=None,
    )
    power_l3: float | None = field(
        default=None,
    )
    energy_import: float | None = field(
        default=None,
    )
    energy_import_t1: float | None = field(
        default=None,
    )
    energy_import_t2: float | None = field(
        default=None,
    )
    energy_import_t3: float | None = field(
        default=None,
    )
    energy_import_t4: float | None = field(
        default=None,
    )
    energy_export: float | None = field(
        default=None,
    )
    energy_export_t1: float | None = field(
        default=None,
    )
    energy_export_t2: float | None = field(
        default=None,
    )
    energy_export_t3: float | None = field(
        default=None,
    )
    energy_export_t4: float | None = field(
        default=None,
    )
    voltage_sag_l1: int | None = field(
        default=None,
    )
    voltage_sag_l2: int | None = field(
        default=None,
    )
    voltage_sag_l3: int | None = field(
        default=None,
    )
    voltage_swell_l1: int | None = field(
        default=None,
    )
    voltage_swell_l2: int | None = field(
        default=None,
    )
    voltage_swell_l3: int | None = field(
        default=None,
    )
    tariff_indicator: int | None = field(
        default=None,
    )
    any_power_fail_count: int | None = field(
        default=None,
    )
    long_power_fail_count: int | None = field(
        default=None,
    )

    # ECOPLUG Specific
    frequency: float | None = field(
        default=None,
    )
    voltage: float | None = field(
        default=None,
    )
    current: float | None = field(
        default=None,
    )
    power: float | None = field(
        default=None,
    )
    energy: float | None = field(
        default=None,
    )
    temperature: float | None = field(
        default=None,
    )
    consumer_connected: bool | None = field(
        default=None,
    )

    # ECODRIVE Specific
    internal_temperature: float | None = field(
        default=None,
    )
    external_temperature: float | None = field(
        default=None,
    )

    # TANKSENSE Specific
    product_model: str | None = field(
        default=None,
    )
    serial_number: str | None = field(
        default=None,
    )
    hw_version: str | None = field(
        default=None,
    )
    fw_version: str | None = field(
        default=None,
    )
    distance: float | None = field(
        default=None,
    )
    level: float | None = field(
        default=None,
    )
    volume: float | None = field(
        default=None,
    )
    srssi: int | None = field(
        default=None,
    )
    src: int | None = field(
        default=None,
    )
    temperature: float | None = field(
        default=None,
    )
    battery_level: int | None = field(
        default=None,
    )
    battery_voltage: float | None = field(
        default=None,
    )

    timestamp: str | None = field(
        default=None,
    )

    # HUBSENSE Specific
    water_flow_rate: float | None = field(
        default=None,
    )
    water_consumed: float | None = field(
        default=None,
    )
    burner_state: bool | None = field(
        default=None,
    )
    heating_oil_consumed: float | None = field(
        default=None,
    )
    remaining_heating_oil_level: float | None = field(
        default=None,
    )

    @staticmethod
    def to_p1(obj: dict) -> P1:
        """Convert external device dict to list of ExternalDevice objects."""
        rv: P1 = {}

        try:
            p1_obj = P1.from_dict(obj)
        except Exception as e:
            LOGGER.error("Error converting P1 data: %s", e)
        rv = p1_obj

        return rv

    @staticmethod
    def hex_to_readable(value: str | None) -> str | None:
        """Convert hex string to readable string, if possible.

        Args:
            value: String to convert, e.g. '4E47475955'

        Returns:
            A string formatted or original value when failed.
        """
        try:
            return bytes.fromhex(value).decode("utf-8")
        except (TypeError, ValueError):
            return value


@dataclass(kw_only=True)
class P1(BaseModel):
    """Represents P1 device."""

    unique_id: str | None = field(
        default=None,
        metadata={"deserialize": lambda x: Measurement.hex_to_readable(x)},
    )
    dsmr_version: str | None = field(
        default=None,
    )
    meter_model: str | None = field(
        default=None,
    )
    voltage: float | None = field(
        default=None,
    )
    voltage_l1: float | None = field(
        default=None,
    )
    voltage_l2: float | None = field(
        default=None,
    )
    voltage_l3: float | None = field(
        default=None,
    )
    current: float | None = field(
        default=None,
    )
    current_l1: float | None = field(
        default=None,
    )
    current_l2: float | None = field(
        default=None,
    )
    current_l3: float | None = field(
        default=None,
    )
    power: float | None = field(
        default=None,
    )
    power_l1: float | None = field(
        default=None,
    )
    power_l2: float | None = field(
        default=None,
    )
    power_l3: float | None = field(
        default=None,
    )
    energy_import: float | None = field(
        default=None,
    )
    energy_import_t1: float | None = field(
        default=None,
    )
    energy_import_t2: float | None = field(
        default=None,
    )
    energy_import_t3: float | None = field(
        default=None,
    )
    energy_import_t4: float | None = field(
        default=None,
    )
    energy_export: float | None = field(
        default=None,
    )
    energy_export_t1: float | None = field(
        default=None,
    )
    energy_export_t2: float | None = field(
        default=None,
    )
    energy_export_t3: float | None = field(
        default=None,
    )
    energy_export_t4: float | None = field(
        default=None,
    )
    voltage_sag_l1: int | None = field(
        default=None,
    )
    voltage_sag_l2: int | None = field(
        default=None,
    )
    voltage_sag_l3: int | None = field(
        default=None,
    )
    voltage_swell_l1: int | None = field(
        default=None,
    )
    voltage_swell_l2: int | None = field(
        default=None,
    )
    voltage_swell_l3: int | None = field(
        default=None,
    )
    tariff_indicator: int | None = field(
        default=None,
    )
    any_power_fail_count: int | None = field(
        default=None,
    )
    long_power_fail_count: int | None = field(
        default=None,
    )


@dataclass(kw_only=True)
class State(BaseModel):
    """Represent current state."""

    # ECOPLUG Specific
    power_on: bool | None = field(
        default=None,
    )

    # ECODRIVE Specific
    pwm_state: int | None = field(
        default=None,
    )
    relay1_state: bool | None = field(
        default=None,
    )
    relay2_state: bool | None = field(
        default=None,
    )

    # HUBSENSE Specific
    current_heating_oil_volume: float | None = field(
        default=None,
    )


@dataclass(kw_only=True)
class StateUpdate(UpdateBaseModel):
    """Represent State update config."""

    # ecoPlug Specific
    power_on: bool | None = field(default=None)

    # ecoDrive Specific
    pwm_state: int | None = field(default=None)
    relay1_state: bool | None = field(default=None)
    relay2_state: bool | None = field(default=None)

    # hubSense Specific
    current_heating_oil_volume: float | None = field(default=None)


@dataclass(kw_only=True)
class Config(BaseModel):

    # ecoPlug Specific
    switch_lock: bool | None = field(
        default=None,
    )
    restore_state: bool | None = field(
        default=None,
    )
    overload_protection: int | None = field(
        default=None,
    )

    # ecoDrive Specific
    mode: int | None = field(
        default=None,
    )
    max_temperature: float | None = field(
        default=None,
    )
    max_peak_power: float | None = field(
        default=None,
    )

    # tankSense Specific
    distance_offset: float | None = field(
        default=None,
    )
    tank_shape: int | None = field(
        default=None,
    )
    height_max: float | None = field(
        default=None,
    )
    tank_capacity: float | None = field(
        default=None,
    )
    tank_length: float | None = field(
        default=None,
    )
    tank_width: float | None = field(
        default=None,
    )
    tank_height: float | None = field(
        default=None,
    )
    tank_cylinder_radius: float | None = field(
        default=None,
    )
    tank_cylinder_height: float | None = field(
        default=None,
    )

    # hubSense Specific
    heating_oil_energy_density: float | None = field(
        default=None,
    )
    heating_oil_consumption_rate: float | None = field(
        default=None,
    )


@dataclass
class ConfigUpdate:
    """Represent Config update config."""

    # ecoPlug Specific
    switch_lock: bool | None = field(default=None)
    restore_state: bool | None = field(default=None)
    overload_protection: int | None = field(default=None)

    # ecoDrive Specific
    mode: int | None = field(default=None)
    max_temperature: float | None = field(default=None)
    max_peak_power: float | None = field(default=None)

    # tankSense Specific
    distance_offset: float | None = field(default=None)
    tank_shape: int | None = field(default=None)
    height_max: float | None = field(default=None)
    tank_capacity: float | None = field(default=None)
    tank_length: float | None = field(default=None)
    tank_width: float | None = field(default=None)
    tank_height: float | None = field(default=None)
    tank_cylinder_radius: float | None = field(default=None)
    tank_cylinder_height: float | None = field(default=None)

    # hubSense Specific
    heating_oil_energy_density: float | None = field(default=None)
    heating_oil_consumption_rate: float | None = field(default=None)


@dataclass(kw_only=True)
class System(BaseModel):
    """Represent System config."""

    wifi_ssid: str | None = field(default=None)
    wifi_strength: int | None = None
    uptime: int | None = field(default=None)


@dataclass(kw_only=True)
class Token(BaseModel):
    """Represent Token."""

    token: str = field()
