"""Diagnostics support for EcoPilot."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .coordinator import EcoPilotConfigEntry

TO_REDACT = {
    CONF_HOST,
    "id",
    "serial",
    "serial_number",
    "token",
    "unique_id",
    "wifi_ssid",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: EcoPilotConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = entry.runtime_data.data

    return async_redact_data(
        {
            "entry": async_redact_data(entry.data, TO_REDACT),
            "data": asdict(data),
        },
        TO_REDACT,
    )
