"""Helpers for EcoPilot."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any, Concatenate

from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .entity import EcoPilotEntity
from .ecopilot_api.errors import RequestError, UnauthorizedError


def ecopilot_exception_handler[_EcoPilotEntityT: EcoPilotEntity, **_P](
    func: Callable[Concatenate[_EcoPilotEntityT, _P], Coroutine[Any, Any, Any]],
) -> Callable[Concatenate[_EcoPilotEntityT, _P], Coroutine[Any, Any, None]]:
    """Decorate EcoPilot calls to handle Domintell EcoPilot exceptions.

    A decorator that wraps the passed in function, catches Domintell EcoPilot errors,
    and reloads the integration when the API was disabled so the reauth flow is
    triggered.
    """

    async def handler(
        self: _EcoPilotEntityT, *args: _P.args, **kwargs: _P.kwargs
    ) -> None:
        try:
            await func(self, *args, **kwargs)
        except RequestError as ex:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="communication_error",
            ) from ex
        except UnauthorizedError as ex:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="api_unauthorized",
            ) from ex

    return handler
