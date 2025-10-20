"""Constants for the EcoPilot integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.const import Platform
from homeassistant.helpers.typing import StateType

LOGGER = logging.getLogger(__package__)

DOMAIN = "domintell_ecopilot"
PLATFORMS = [
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.UPDATE,
]


# Platform config.
CONF_PRODUCT_NAME = "product_name"
CONF_PRODUCT_MODEL = "product_model"
CONF_SERIAL_NUMBER = "serial_number"

CONF_TANK_SHAPE = "tank_shape"
CONF_TANK_CAPACITY = "tank_capacity"
CONF_HEIGHT_MAX = "height_max"
CONF_TANK_LENGTH = "tank_length"
CONF_TANK_WIDTH = "tank_width"
CONF_TANK_HEIGHT = "tank_height"
CONF_TANK_CYLINDER_RADIUS = "tank_cylinder_radius"
CONF_TANK_CYLINDER_HEIGHT = "tank_cylinder_height"

DATA_UPDATE_INTERVAL = timedelta(seconds=5)
FIRMWARE_DATA_UPDATE_INTERVAL = timedelta(hours=1)

# Tank const
TANK_SHAPE_MAP: dict[StateType, str] = {
    0: "Linear",
    1: "Rectangular",
    2: "Horizontal Cylindrical",
    3: "Vertical Cylindrical",
    # TODO unsupported for now
    # 4: "Horizontal Spherical Ends",
    # 5: "Horizontal Elliptical Ends",
    # 6: "Horizontal Elliptical Cylinder",
}

TANK_SHAPE_REVERSE_MAP = {v: k for k, v in TANK_SHAPE_MAP.items()}

TANK_SHAPE_CHOICES = {
    "Linear": "Linear",
    "Rectangular": "Rectangular",
    "Horizontal Cylindrical": "Horizontal Cylindrical",
    "Vertical Cylindrical": "Vertical Cylindrical",
    # TODO unsupported for now
    # "Horizontal Spherical Ends": "Horizontal Spherical Ends",
    # "Horizontal Elliptical Ends": "Horizontal Elliptical Ends",
    # "Horizontal Elliptical Cylinder": "Horizontal Elliptical Cylinder",
}
