"""Domintell Ecopilot base class"""

from __future__ import annotations

import asyncio
from typing import Any

from aiohttp.client import ClientSession, ClientTimeout, TCPConnector

from .errors import UnsupportedError
from .const import LOGGER
from .models import CombinedModels, Device, Measurement, State, Config, System


class DomintellEcopilot:
    """Base class for Domintell Ecopilot API."""

    _session: ClientSession | None = None
    _close_session: bool = False
    _request_timeout: int = 15
    _host: str
    _device: Device | None = None
    _lock: asyncio.Lock

    def __init__(
        self,
        host: str,
        clientsession: ClientSession = None,
        timeout: int = 10,
    ):
        """Create a Domintell Ecopilot object.

        Args:
            host: IP or URL for device.
            clientsession: The clientsession.
            timeout: Request timeout in seconds.
        """
        self._host = host
        self._session = clientsession
        self._close_session = clientsession is None
        self._request_timeout = timeout

        self._lock = asyncio.Lock()

    @property
    def host(self) -> str:
        """Return the hostname of the device.

        Returns:
            host: The used host

        """
        return self._host

    async def combined(self) -> CombinedModels:
        """Get all information."""

        async def fetch_data(coroutine):
            try:
                return await coroutine
            except (UnsupportedError, NotImplementedError):
                return None

        device, measurement, state, config, system = await asyncio.gather(
            fetch_data(self.device()),
            fetch_data(self.measurement()),
            fetch_data(self.state()),
            fetch_data(self.config()),
            fetch_data(self.system()),
        )

        return CombinedModels(
            device=device,
            measurement=measurement,
            state=state,
            config=config,
            system=system,
        )

    async def device(self, reset_cache: bool = False) -> Device:
        """Get the device information."""
        raise NotImplementedError

    async def measurement(self) -> Measurement:
        """Get the current measurement."""
        raise NotImplementedError

    async def system(self) -> System:
        """Get/set the system."""
        raise NotImplementedError

    async def state(self) -> State:
        """Get/set the state."""
        raise UnsupportedError("State is not supported")

    async def config(self) -> Config:
        """Get/set the configuration."""
        raise NotImplementedError

    async def identify(
        self,
    ) -> None:
        """Identify the device."""
        raise UnsupportedError("Identify is not supported")

    async def reboot(
        self,
    ) -> None:
        """Reboot the device."""
        raise UnsupportedError("Reboot is not supported")

    async def close(self) -> None:
        """Close client session."""
        LOGGER.debug("Closing clientsession")
        if self._session and self._close_session:
            await self._session.close()

    async def _create_clientsession(self) -> None:
        """Create a client session."""

        LOGGER.debug("Creating clientsession")

        if self._session is not None:
            raise RuntimeError("Session already exists")

        connector = TCPConnector(
            enable_cleanup_closed=True,
            limit_per_host=1,
        )

        self._close_session = True

        self._session = ClientSession(
            connector=connector, timeout=ClientTimeout(total=self._request_timeout)
        )

    async def __aenter__(self) -> DomintellEcopilot:
        """Async enter.

        Returns:
            The DomintellEcopilot object.
        """
        return self

    async def __aexit__(self, *_exc_info: Any) -> None:
        """Async exit.

        Args:
            _exc_info: Exec type.
        """
        await self.close()
