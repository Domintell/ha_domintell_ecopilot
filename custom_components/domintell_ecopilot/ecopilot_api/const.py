"""Constants for Domintell EcoPilot."""

import logging
from enum import StrEnum

LOGGER = logging.getLogger(__name__)

METADATA_BASE_FW_URL = "https://pro.mydomintell.com/private/fw/ecopilot/"
FW_UPDATE_PORT = 9000


class Model(StrEnum):
    """Model of the Domintell Ecopilot device."""

    ECOP1 = "ecoP1"
    ECOPLUG = "ecoPlug"
    ECODRIVE_P1 = "ecoDrive-P1"
    ECODRIVE_LK = "ecoDrive-LK"
    TANKSENSE = "tankSense"
    HUBSENSE = "hubSense"
    HUBSENSE_ETH = "hubSense-ETH"


MODEL_TO_ID = {
    Model.ECOP1: "eco-p1",
    Model.ECOPLUG: "ecoplug",
    Model.ECODRIVE_P1: "ecodrive-p1",
    Model.ECODRIVE_LK: "ecodrive-lk",
    Model.TANKSENSE: "tanksense",
    Model.HUBSENSE: "hubsense-wifi",
    Model.HUBSENSE_ETH: "hubsense-eth",
}

MODEL_TO_NAME = {
    Model.ECOP1: "Wi-Fi P1 Meter",
    Model.ECOPLUG: "Smart Plug",
    Model.ECODRIVE_P1: "ecoDrive P1",
    Model.ECODRIVE_LK: "ecoDrive Linky",
    Model.TANKSENSE: "tankSense",
    Model.HUBSENSE: "hubSense Wi-Fi",
    Model.HUBSENSE_ETH: "hubSense Ethernet",
}


class TankShape(StrEnum):
    """Type of tank shape."""

    LINEAR = "Linear"
    RECTANGULAR = "Rectangular"
    CYLINDRICAL_H = "Horizontal Cylindrical"
    CYLINDRICAL_V = "Vertical Cylindrical"
    SPHERICAL_ENDS_H = "Horizontal Spherical Ends"
    ELLIPTICAL_ENDS_H = "Horizontal Elliptical Ends"
    ELLIPTICAL_CYLINDER_H = "Horizontal Elliptical Cylinder"
