"""Firmware update helpers for Domintell Ecopilot devices."""

import asyncio
import hashlib
import aiohttp
from typing import Callable, Coroutine, Any, Dict, Optional

from .const import LOGGER, METADATA_BASE_FW_URL, FW_UPDATE_PORT
from .errors import (
    MetadataError,
    DownloadError,
    IntegrityError,
    TransferError,
)


class FirmwareMetadata:
    """Structure of firmware information."""

    def __init__(
        self,
        product: str,
        version: str,
        url: str,
        integrity: str,
        size: int,
        release_notes: str,
        changelog_url: str,
    ):
        self.product = product
        self.version = version
        self.url = url
        self.integrity = integrity
        self.size = size
        self.release_notes = release_notes
        self.changelog_url = changelog_url

    def to_dict(self) -> Dict[str, Any]:
        """Converts the metadata object to a dictionary."""
        return {
            "product": self.product,
            "version": self.version,
            "url": self.url,
            "integrity": self.integrity,
            "size": self.size,
            "release_notes": self.release_notes,
            "changelog_url": self.changelog_url,
        }


class FirmwareUpdater:
    """Manages downloading, verifying and sending firmware to a device."""

    def __init__(self, host: str, clientsession: aiohttp.ClientSession):
        self._device_ip = host
        self._port = FW_UPDATE_PORT
        self._client_session = clientsession

        # Weight of steps for calculating progress (0-100)
        self.DOWNLOAD_WEIGHT = 50
        self.TRANSFER_WEIGHT = 50

    async def async_get_firmware_size(self, url: str) -> Optional[int]:
        """Retrieves the firmware size (in bytes)."""
        try:
            # Use the HEAD method
            async with self._client_session.head(url) as resp:

                if resp.status != 200:
                    LOGGER.warning(
                        f"HEAD request for firmware size failed. "
                        f"HTTP status: {resp.status} for URL: {url}"
                    )
                    return None

                content_length = resp.headers.get("Content-Length")

                if content_length:
                    try:
                        size_bytes = int(content_length)
                        LOGGER.info(f"Firmware size found : {size_bytes} bytes.")
                        return size_bytes
                    except ValueError:
                        LOGGER.error(
                            f"The Content-Length header is invalid: {content_length}"
                        )
                        return None

                LOGGER.warning(
                    "The server did not return the Content-Length header in the HEAD response."
                )
                return None

        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            LOGGER.error(f"Network error during HEAD request for {url}: {err}")
            return None
        except Exception as err:
            LOGGER.error(f"Unexpected error while retrieving firmware size : {err}")
            return None

    async def async_get_latest_firmware_metadata(
        self, product_model: str, current_version: str
    ) -> FirmwareMetadata | None:
        """
        Retrieves and parses the remote JSON file to find the latest available version.
        """

        metadata_url = METADATA_BASE_FW_URL + product_model.lower() + "/versions.json"

        LOGGER.debug(f"Checking metadata from: {metadata_url}")

        try:
            async with self._client_session.get(metadata_url, timeout=10) as response:
                if response.status != 200:
                    raise MetadataError(
                        f"HTTP Request failed: Status {response.status}"
                    )

                metadata_json = await response.json()

        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise MetadataError(
                f"Network error or timeout while getting metadata: {err}"
            ) from err
        except Exception as err:
            raise MetadataError(f"Error parsing metadata JSON: {err}") from err

        # Check if the product matches
        if metadata_json.get("product") != product_model:
            LOGGER.warning(
                f"Product mismatch in metadata. Expected: {product_model}, Got: {metadata_json.get('product')}"
            )
            return None

        # Extract information from the latest version
        latest_fw_info = metadata_json.get("latest_version")
        firmware_changelog_url = metadata_json.get("changelog")

        if not latest_fw_info:
            LOGGER.warning("Key 'latest_version' not found in metadata.")
            return None

        latest_version = latest_fw_info.get("version")
        latest_url = latest_fw_info.get("url")
        integrity_str = latest_fw_info.get("integrity", "")
        release_notes = latest_fw_info.get("release_notes", "")
        changelog_url = firmware_changelog_url

        # Validation and extraction of the hash
        if not latest_version or not latest_url or not integrity_str:
            LOGGER.error("Incomplete data in 'latest_version' section.")
            return None

        if integrity_str.lower().startswith("sha256:"):
            sha256_hash = integrity_str[7:].strip()
        else:
            LOGGER.error(f"Unsupported integrity format: {integrity_str}")
            return None

        # Recover firmware size
        try:
            firmware_size = await self.async_get_firmware_size(latest_url)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise MetadataError(
                f"Network error or timeout while getting firmware size: {err}"
            ) from err
        except Exception as err:
            raise MetadataError(f"Error getting firmware size: {err}") from err

        # Check if there is a new version
        if latest_version and latest_version > current_version:
            LOGGER.info(f"New firmware available: {latest_version}")
            return FirmwareMetadata(
                product=product_model,
                version=latest_version,
                url=latest_url,
                integrity=integrity_str,
                size=firmware_size,
                release_notes=release_notes,
                changelog_url=changelog_url,
            )

        LOGGER.info("No new firmware available.")
        return None

    async def download_and_transfer(
        self,
        metadata: FirmwareMetadata,
        progress_callback: (
            Callable[[int, str], Coroutine[Any, Any, None]] | None
        ) = None,
    ):
        """
        Manages the complete process: Download, SHA256 verification and TCP transfer.
        """

        # Download and verification (0 to 50%)
        firmware_data, total_size = await self._async_download_firmware(
            metadata.url, metadata.integrity, progress_callback
        )

        # Transfert (50 to 100%)
        await self._async_send_firmware_tcp(
            firmware_data, total_size, progress_callback
        )

    async def _async_download_firmware(
        self,
        url: str,
        expected_sha256: str,
        callback: Callable[[int, str], Coroutine[Any, Any, None]] | None,
    ) -> tuple[bytes, int]:
        """Streaming download with SHA256 verification."""

        LOGGER.info(f"Starting download from: {url}")
        firmware_data = bytearray()
        hasher = hashlib.sha256()
        total_size = 0

        try:
            async with self._client_session.get(url) as response:
                if response.status != 200:
                    raise DownloadError(f"HTTP failed: Status {response.status}")

                total_size = int(response.headers.get("Content-Length", 0))

                async for chunk in response.content.iter_chunked(1024):
                    firmware_data.extend(chunk)
                    hasher.update(chunk)

                    # Download Progress Report
                    if callback and total_size:
                        downloaded_progress = (
                            len(firmware_data) / total_size
                        ) * self.DOWNLOAD_WEIGHT
                        await callback(int(downloaded_progress), "downloading")

        except aiohttp.ClientError as err:
            raise DownloadError(f"Network error during download: {err}") from err

        calculated_sha256 = hasher.hexdigest().upper()
        expected_sha256_upper = expected_sha256.upper()

        if calculated_sha256 != expected_sha256_upper:
            LOGGER.error(
                f"SHA256 mismatch. Expected: {expected_sha256_upper}, Got: {calculated_sha256}"
            )
            raise IntegrityError("SHA256 verification failed.")

        LOGGER.info("[Firmware transfer completed].")
        return bytes(firmware_data), total_size

    async def _async_send_firmware_tcp(
        self,
        firmware_data: bytes,
        total_size: int,
        callback: Callable[[int, str], Coroutine[Any, Any, None]] | None,
    ):
        """Sending firmware data via TCP/IP."""

        LOGGER.info(f"Starting TCP/IP transfer to {self._device_ip}:{self._port}")
        writer = None

        try:
            # Open connection
            _, writer = await asyncio.open_connection(self._device_ip, self._port)

            await asyncio.sleep(3)  # Wait for the device to be ready

            # Send firmware by packet
            chunk_size = 1024
            total_sent = 0

            for i in range(0, total_size, chunk_size):
                chunk = firmware_data[i : i + chunk_size]
                writer.write(chunk)
                await writer.drain()

                total_sent += len(chunk)

                # Send Progress Report
                if callback:
                    send_range = self.TRANSFER_WEIGHT
                    send_progress = (total_sent / total_size) * send_range
                    # Total progress = Download weight + upload progress
                    await callback(
                        self.DOWNLOAD_WEIGHT + int(send_progress), "transferring"
                    )

            # Signify the end of writing
            writer.write_eof()
            await writer.drain()

            LOGGER.info("[Firmware donwload completed.]")

        except ConnectionRefusedError:
            raise TransferError(
                "TCP connection refused. Device not listening on dedicated port."
            )
        except Exception as err:
            raise TransferError(f"Critical TCP/IP error: {err}") from err
        finally:
            if writer:
                writer.close()
                await writer.wait_closed()
