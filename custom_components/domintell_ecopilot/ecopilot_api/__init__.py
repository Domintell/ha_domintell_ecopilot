"""Domintell EcoPilot API library."""

from __future__ import annotations


import asyncio
import json
import ssl
from collections.abc import Callable, Coroutine
from http import HTTPStatus
from dataclasses import dataclass, field, fields
from typing import Any, TypeVar

import async_timeout
import backoff
from aiohttp import ClientSession
from aiohttp.client import ClientError, ClientResponseError, ClientSession
from aiohttp.hdrs import METH_DELETE, METH_GET, METH_POST, METH_PUT
from mashumaro.exceptions import InvalidFieldValue, MissingField

from .const import LOGGER
from .errors import (
    InvalidUserNameError,
    NotFoundError,
    RequestError,
    ResponseError,
    UnauthorizedError,
    UnsupportedError,
)
from .ecopilot import DomintellEcopilot
from .models import (
    Device,
    Measurement,
    State,
    StateUpdate,
    Config,
    ConfigUpdate,
    System,
    Token,
)

from .cacert import CACERT

__all__ = [
    "DomintellEcopilot",
    "InvalidStateError",
    "RequestError",
    "UnsupportedError",
]

T = TypeVar("T")


def authorized_method(
    func: Callable[..., Coroutine[Any, Any, T]],
) -> Callable[..., Coroutine[Any, Any, T]]:
    """Decorator method to check if token is set."""

    async def wrapper(self, *args, **kwargs) -> T:
        # pylint: disable=protected-access
        if self._token is None:
            raise UnauthorizedError("Token missing")

        return await func(self, *args, **kwargs)

    return wrapper


class DomintellEcopilotV1(DomintellEcopilot):
    """Communicate with a Domintell EcoPilot device."""

    _ssl: ssl.SSLContext | bool = False
    _identifier: str | None = None

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments
    def __init__(
        self,
        host: str,
        identifier: str | None = None,
        token: str | None = None,
        clientsession: ClientSession = None,
        timeout: int = 10,
    ):
        """Create a Domintell EcoPilot object.

        Args:
            host: IP or URL for device.
            id: ID for device.
            token: Token for device.
            timeout: Request timeout in seconds.
        """
        super().__init__(host, clientsession, timeout)
        self._identifier = identifier
        self._token = token

    @authorized_method
    async def device(self, reset_cache: bool = False) -> Device:
        """Return the device object."""
        if self._device is not None and not reset_cache:
            return self._device

        _, response = await self._request("/api/info")
        device = Device.from_json(response)

        # Cache device object
        self._device = device
        return device

    @authorized_method
    async def measurement(self) -> Measurement:
        """Return the measurement object."""
        _, response = await self._request("/api/data")

        measurement = Measurement.from_json(response)

        return measurement

    @authorized_method
    async def state(
        self,
        **kwargs: Any,
    ) -> State:
        """Return or update the state object."""

        if self._device is not None and self._device.supports_state() is False:
            raise UnsupportedError("State is not supported")

        if kwargs:
            # Create a new dictionary excluding None values
            filtered_data = {k: v for k, v in kwargs.items() if v is not None}

            # Validate parameters
            valid_fields = {f.name for f in fields(StateUpdate)}
            is_valid_update = any(k in valid_fields for k in kwargs)

            if not is_valid_update:
                raise ValueError("No valid parameters provided for StateUpdate.")

            _, response = await self._request(
                "/api/state", method=METH_PUT, data=filtered_data
            )

        else:
            _, response = await self._request("/api/state")

        state = State.from_json(response)
        return state

    @authorized_method
    async def config(
        self,
        **kwargs: Any,
    ) -> Config:
        """Return or update the config object."""

        if self._device is not None and self._device.supports_config() is False:
            raise UnsupportedError("Config is not supported")

        if kwargs:
            # Create a new dictionary excluding None values
            filtered_data = {k: v for k, v in kwargs.items() if v is not None}

            # Validate parameters
            valid_fields = {f.name for f in fields(ConfigUpdate)}
            is_valid_update = any(k in valid_fields for k in kwargs)

            if not is_valid_update:
                raise ValueError("No valid parameters provided for ConfigUpdate.")

            _, response = await self._request(
                "/api/config", method=METH_PUT, data=filtered_data
            )
        else:
            _, response = await self._request("/api/config")

        config = Config.from_json(response)

        return config

    @authorized_method
    async def system(self) -> Config:
        """Return the system object."""

        if self._device is not None and self._device.supports_system() is False:
            raise UnsupportedError("System is not supported")

        status, response = await self._request("/api/system")

        if status != HTTPStatus.OK:
            error = json.loads(response).get("error", response)
            raise RequestError(f"Failed to get system: {error}")

        system = System.from_json(response)
        return system

    @authorized_method
    async def identify(
        self,
    ) -> None:
        """Send identify request."""

        if self._device is not None and self._device.supports_identify() is False:
            raise UnsupportedError("Identify is not supported")

        await self._request("/api/system/identify", method=METH_PUT)

    @authorized_method
    async def reboot(
        self,
    ) -> None:
        """Reboot the Domintell EcoPilot device."""

        if self._device is not None and self._device.supports_reboot() is False:
            raise UnsupportedError("Reboot is not supported")

        await self._request("/api/system/reboot", method=METH_PUT)

    @authorized_method
    async def update(self, fw_size: int | None, fw_signature: str | None) -> None:
        """Enable update mode on the Domintell EcoPilot device."""

        if self._device is not None and self._device.supports_update() is False:
            raise UnsupportedError("Update is not supported")

        data = {}
        if fw_size is not None:
            data["fw_size"] = fw_size
        if fw_signature is not None:
            data["fw_signature"] = fw_signature

        await self._request("/api/system/firmware/update", method=METH_POST, data=data)

    async def get_token(
        self,
        name: str,
    ) -> str:
        """Get authorization token from device."""
        status, response = await self._request(
            "/api/authorization", method=METH_POST, data={"name": f"local/{name}"}
        )

        if status == HTTPStatus.FORBIDDEN:
            raise UnauthorizedError("Client creation is not enabled on the device")

        if status != HTTPStatus.OK and status != HTTPStatus.CREATED:
            error = json.loads(response).get("error", response)
            raise InvalidUserNameError(
                f"Error occurred while getting token: {error}", error
            )

        try:
            token = Token.from_json(response).token
        except (InvalidFieldValue, MissingField) as ex:
            raise ResponseError("Failed to get token") from ex

        self._token = token
        return token

    @authorized_method
    async def delete_token(
        self,
        name: str | None = None,
    ) -> None:
        """Delete authorization token from device."""
        status, response = await self._request(
            "/api/authorization",
            method=METH_DELETE,
            data={"name": f"local/{name}"} if name is not None else None,
        )

        if status != HTTPStatus.OK:
            error = json.loads(response).get("error", response)
            raise RequestError(f"Error occurred while getting token: {error}", error)

        # Our token was invalided, resetting it
        if name is None:
            self._token = None

    async def _get_ssl_context(self) -> ssl.SSLContext:
        """
        Get a clientsession that is tuned for communication with the Domintell EcoPilot Device
        """

        def _build_ssl_context() -> ssl.SSLContext:
            context = ssl.create_default_context(cadata=CACERT)
            context.verify_flags = (
                ssl.VERIFY_X509_PARTIAL_CHAIN
            )  # pylint: disable=no-member
            if self._identifier is not None:
                context.hostname_checks_common_name = True
            else:
                context.check_hostname = False  # Skip hostname validation
                context.verify_mode = ssl.CERT_REQUIRED  # Keep SSL verification active
            return context

        # Creating an SSL context has some blocking IO so need to run it in the executor
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _build_ssl_context)

    @backoff.on_exception(backoff.expo, RequestError, max_tries=3, logger=None)
    async def _request(
        self, path: str, method: str = METH_GET, data: object = None
    ) -> tuple[HTTPStatus, dict[str, Any] | None]:
        """Make a request to the API."""

        async with self._lock:
            if self._session is None:
                await self._create_clientsession()

        # TODO Disable for now
        # async with self._lock:
        #     if self._ssl is False:
        #         self._ssl = await self._get_ssl_context()

        # Construct request
        url = f"https://{self.host}{path}"
        headers = {
            "Content-Type": "application/json",
        }
        if self._token is not None:
            headers["Authorization"] = f"Bearer {self._token}"

        LOGGER.debug("%s, %s, %s", method, url, data)

        try:
            async with async_timeout.timeout(self._request_timeout):
                async with self._lock:
                    resp = await self._session.request(
                        method,
                        url,
                        json=data,
                        headers=headers,
                        ssl=self._ssl,
                        server_hostname=self._identifier,
                    )
                LOGGER.debug("%s, %s", resp.status, await resp.text("utf-8"))
        except asyncio.TimeoutError as exception:
            raise RequestError(
                f"Timeout occurred while connecting to the Domintell Ecopilot device at {self.host}"
            ) from exception
        except (ClientError, ClientResponseError) as exception:
            raise RequestError(
                f"Error occurred while communicating with the Domintell Ecopilot device at {self.host}"
            ) from exception

        match resp.status:
            case HTTPStatus.UNAUTHORIZED:
                raise UnauthorizedError("Token rejected")
            case HTTPStatus.NO_CONTENT:
                # No content, just return
                return (HTTPStatus.NO_CONTENT, None)
            case HTTPStatus.NOT_FOUND:
                raise NotFoundError("Resource not found")
            case HTTPStatus.OK:
                pass

        return (resp.status, await resp.text())

    async def __aenter__(self) -> DomintellEcopilotV1:
        """Async enter.

        Returns:
            The DomintellEcopilotV1 object.
        """
        return self
