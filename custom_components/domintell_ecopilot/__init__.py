"""The Domintell EcoPilot integration."""

from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import instance_id
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    PLATFORMS,
    LOGGER,
    CONF_TANK_SHAPE,
    TANK_SHAPE_REVERSE_MAP,
)
from .ecopilot_api import DomintellEcopilotV1
from .ecopilot_api.fw_update import FirmwareUpdater
from .ecopilot_api.const import Model
from .coordinator import (
    EcoPilotConfigEntry,
    EcoPilotDeviceUpdateCoordinator,
)


async def async_setup_entry(hass: HomeAssistant, entry: EcoPilotConfigEntry) -> bool:
    """Set up Domintell EcoPilot from a config entry."""

    token = entry.data.get(CONF_TOKEN)
    api = DomintellEcopilotV1(
        entry.data[CONF_HOST],
        token=token,
        clientsession=async_get_clientsession(hass),
    )

    fw_updater = FirmwareUpdater(
        entry.data[CONF_HOST],
        clientsession=async_get_clientsession(hass),
    )

    coordinator = EcoPilotDeviceUpdateCoordinator(hass, entry, api, fw_updater)

    try:
        await coordinator.async_config_entry_first_refresh()

        product_model = coordinator.data.device.product_model

        # In case of tankSense we need to send sensor and tank configuration
        if product_model == Model.TANKSENSE:
            tank_shape = entry.data.get(CONF_TANK_SHAPE)
            tank_shape_code = TANK_SHAPE_REVERSE_MAP.get(entry.data[CONF_TANK_SHAPE])
            if tank_shape == "Linear":
                result = await coordinator.api.config(
                    distance_offset=entry.data["distance_offset"],
                    tank_shape=tank_shape_code,
                    height_max=entry.data["height_max"],
                    tank_capacity=entry.data["tank_capacity"],
                )
            elif tank_shape == "Rectangular":
                result = await coordinator.api.config(
                    distance_offset=entry.data["distance_offset"],
                    tank_shape=tank_shape_code,
                    tank_length=entry.data["tank_length"],
                    tank_width=entry.data["tank_width"],
                    tank_height=entry.data["tank_height"],
                )
            elif tank_shape in ["Horizontal Cylindrical", "Vertical Cylindrical"]:
                result = await coordinator.api.config(
                    distance_offset=entry.data["distance_offset"],
                    tank_shape=tank_shape_code,
                    tank_cylinder_radius=entry.data["tank_cylinder_radius"],
                    tank_cylinder_height=entry.data["tank_cylinder_height"],
                )

            if "error" in result.__dict__:
                LOGGER.error("Tank configuration error:", result.error)

        await coordinator.async_refresh()

    except ConfigEntryNotReady:
        await coordinator.api.close()

        raise

    entry.runtime_data = coordinator

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
    }

    # Abort reauth config flow if active
    for progress_flow in hass.config_entries.flow.async_progress_by_handler(DOMAIN):
        if (
            "context" in progress_flow
            and progress_flow["context"].get("source") == SOURCE_REAUTH
        ):
            hass.config_entries.flow.async_abort(progress_flow["flow_id"])

    # Finalize
    entry.async_on_unload(coordinator.api.close)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: EcoPilotConfigEntry) -> bool:
    """Unload a config entry."""

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: EcoPilotConfigEntry) -> None:
    """Handle removal of an entry."""

    # Delete token from device
    entry_data = hass.data[DOMAIN].get(entry.entry_id)

    if entry_data and (coordinator := entry_data.get("coordinator")):

        uuid = await instance_id.async_get(hass)

        try:
            await coordinator.api.delete_token(f"home-assistant#{uuid[:6]}")
        except Exception as ex:
            LOGGER.warning("Error deleting token:", ex)
        finally:
            await coordinator.api.close()

        hass.data[DOMAIN].pop(entry.entry_id)
