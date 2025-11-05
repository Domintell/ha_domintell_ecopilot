"""Update coordinator for EcoPilot."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed


from .const import DOMAIN, LOGGER, DATA_UPDATE_INTERVAL, FIRMWARE_DATA_UPDATE_INTERVAL
from .ecopilot_api import DomintellEcopilotV1
from .ecopilot_api.errors import RequestError, UnauthorizedError, MetadataError
from .ecopilot_api.models import CombinedModels as DeviceResponseEntry
from .ecopilot_api.fw_update import FirmwareMetadata, FirmwareUpdater

type EcoPilotConfigEntry = ConfigEntry[EcoPilotDeviceUpdateCoordinator]


class EcoPilotDeviceUpdateCoordinator(DataUpdateCoordinator[DeviceResponseEntry]):
    """Gather data for the device."""

    api: DomintellEcopilotV1
    config_entry: EcoPilotConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: EcoPilotConfigEntry,
        api: DomintellEcopilotV1,
        fw_updater: FirmwareUpdater,
    ) -> None:
        """Initialize update coordinator."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=DATA_UPDATE_INTERVAL,
        )

        self.api = api
        self.fw_updater = fw_updater
        self._last_firmware = None

        # Initiates the creation and startup of the firmware coordinator
        self.hass.async_create_task(self._async_setup_fw_coordinator())

    async def _async_setup_fw_coordinator(self):
        """
        Creates the internal coordinator for firmware verification and starts it.
        """

        self.fw_update_coordinator = DataUpdateCoordinator(
            self.hass,
            LOGGER,
            name=f"{DOMAIN} Firmware Update Checker",
            update_method=self._async_fw_update_data,
            update_interval=FIRMWARE_DATA_UPDATE_INTERVAL,
        )

        # Starts the first firmware check refresh
        await self.fw_update_coordinator.async_config_entry_first_refresh()

    async def _async_update_data(self) -> DeviceResponseEntry:
        """Fetch all device and sensor data from api."""
        try:
            data = await self.api.combined()

        except RequestError as ex:
            raise UpdateFailed(
                ex, translation_domain=DOMAIN, translation_key="communication_error"
            ) from ex

        except UnauthorizedError as ex:
            raise ConfigEntryAuthFailed from ex

        try:
            new_fw = getattr(data.device, "firmware_version", None)
            last_fw = getattr(self, "_last_firmware", None)

            if new_fw and last_fw != new_fw:
                self._last_firmware = new_fw

                device_registry = dr.async_get(self.hass)
                device_identifier = (
                    f"{data.device.product_model}_{data.device.serial_number}"
                )
                device = device_registry.async_get_device(
                    identifiers={(DOMAIN, device_identifier)}
                )

                if device:
                    device_registry.async_update_device(device.id, sw_version=new_fw)

        except Exception as ex:
            pass

        self.data = data
        return data

    async def _async_fw_update_data(self) -> FirmwareMetadata:
        """Fetch the latest firmware information."""

        if not self.data:
            try:
                await self.async_config_entry_first_refresh()
            except Exception as ex:
                return self.fw_update_coordinator.data or {
                    "update_available": False,
                    "latest_firmware_info": None,
                }

        product_model = self.data.device.product_model
        current_fw_version = self.data.device.firmware_version

        try:
            metadata = await self.fw_updater.async_get_latest_firmware_metadata(
                product_model, current_fw_version
            )
        except MetadataError as ex:
            raise UpdateFailed(
                ex, translation_domain=DOMAIN, translation_key="communication_error"
            ) from ex

        if metadata:
            self.latest_firmware_metadata = metadata
            latest_info_dict = metadata.to_dict()
            return {"update_available": True, "latest_firmware_info": latest_info_dict}

        # No update available
        self.latest_firmware_metadata = None
        return {"update_available": False, "latest_firmware_info": None}

    async def async_unload(self) -> bool:
        """Cleans up the firmware coordinator when unloading integration."""
        if self.fw_update_coordinator:
            await self.fw_update_coordinator.async_shutdown()
        return await super().async_unload()

    async def async_update_device_info(hass, device_id, new_firmware):
        device_registry = dr.async_get(hass)
        device = device_registry.async_get(device_id)
        if device:
            device_registry.async_update_device(device.id, sw_version=new_firmware)
