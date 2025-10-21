"""Creates EcoPilot update entities."""

from __future__ import annotations

import asyncio
from typing import Any

from awesomeversion import AwesomeVersion, AwesomeVersionStrategy
from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityDescription,
    UpdateEntityFeature,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import LOGGER
from .coordinator import (
    EcoPilotConfigEntry,
    EcoPilotDeviceUpdateCoordinator,
)
from .entity import EcoPilotEntity

PARALLEL_UPDATES = 1

UPDATE_ENTITY_TYPES = UpdateEntityDescription(
    key="firmware",
    translation_key="firmware",
    device_class=UpdateDeviceClass.FIRMWARE,
    entity_category=EntityCategory.CONFIG,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcoPilotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up update entity."""
    entities = [EcoPilotUpdateEntity(entry.runtime_data, UPDATE_ENTITY_TYPES)]
    async_add_entities(entities)


class EcoPilotUpdateEntity(EcoPilotEntity, UpdateEntity):
    """Representation of a EcoPilot Update entity."""

    entity_description: UpdateEntityDescription
    _attr_supported_features = (
        UpdateEntityFeature.INSTALL
        | UpdateEntityFeature.PROGRESS
        | UpdateEntityFeature.RELEASE_NOTES
    )

    def __init__(
        self,
        coordinator: EcoPilotDeviceUpdateCoordinator,
        description: UpdateEntityDescription,
    ) -> None:
        """Initialize the update entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.unique_id}_{description.key}"

        self._attr_title: str = (
            "EcoPilot " + coordinator.data.device.product_model + " Firmware"
        )

    @property
    def installed_version(self) -> str | None:
        """Version installed and in use."""
        return self.coordinator.data.device.firmware_version

    @property
    def latest_version(self) -> str | None:
        """Latest version available for install."""

        fw_coord = self.coordinator.fw_update_coordinator

        if fw_coord and fw_coord.data:
            if fw_coord.data.get("update_available"):
                fw_info = fw_coord.data.get("latest_firmware_info")
                if fw_info:
                    return fw_info.get("version", "")

        return self.installed_version

    @property
    def release_url(self) -> str | None:
        """Return release url."""
        fw_coord = self.coordinator.fw_update_coordinator

        if fw_coord and fw_coord.data:
            fw_info = fw_coord.data.get("latest_firmware_info")
            if fw_info:
                return fw_info.get("changelog_url", None)

        return None

    def version_is_newer(self, latest_version: str, installed_version: str) -> bool:
        """Return True if latest_version is newer than installed_version."""
        return AwesomeVersion(
            latest_version,
            find_first_match=True,
            ensure_strategy=[AwesomeVersionStrategy.SEMVER],
        ) > AwesomeVersion(
            installed_version,
            find_first_match=True,
            ensure_strategy=[AwesomeVersionStrategy.SEMVER],
        )

    @callback
    async def update_progress(self, percentage: int, state: str | None = None) -> None:
        """Called during firmware update."""
        self._attr_update_percentage = percentage
        self.async_write_ha_state()

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        """Install an update."""

        LOGGER.info(
            "Starting update of device %s from '%s' to '%s'",
            self.name,
            self.coordinator.data.device.firmware_version,
            version,
        )

        self._attr_in_progress = True
        self._attr_update_percentage = None
        self.async_write_ha_state()

        try:
            metadata = self.coordinator.latest_firmware_metadata
            fw_size = metadata.size
            integrity = metadata.integrity
            updater = self.coordinator.fw_updater

            # Enable update mode
            await self.coordinator.api.update(fw_size=fw_size, fw_integrity=integrity)
            await asyncio.sleep(1)  # Wait for the device to be ready

            # Start download and transfert to device
            await updater.download_and_transfer(
                metadata,
                progress_callback=self.update_progress,
            )
        except Exception as ex:
            raise HomeAssistantError(ex) from ex
        finally:
            self._attr_in_progress = False
            self._attr_update_percentage = None
            self.async_write_ha_state()

    async def async_release_notes(self) -> str | None:
        """Return release notes."""

        fw_coord = self.coordinator.fw_update_coordinator

        if fw_coord and fw_coord.data:
            fw_info = fw_coord.data.get("latest_firmware_info")
            if fw_info:
                return fw_info.get("release_notes", "")

        return ""
