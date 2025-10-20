"""Config flow to configure EcoPilot."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import voluptuous as vol

from homeassistant.components import onboarding
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import AbortFlow
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import instance_id
from homeassistant.helpers.selector import (
    TextSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .ecopilot_api import DomintellEcopilotV1
from .ecopilot_api.const import TankShape
from .ecopilot_api.errors import (
    RequestError,
    UnauthorizedError,
    UnsupportedError,
)
from .ecopilot_api.models import Device
from .const import (
    DOMAIN,
    LOGGER,
    CONF_PRODUCT_NAME,
    CONF_PRODUCT_MODEL,
    CONF_SERIAL_NUMBER,
    CONF_TANK_SHAPE,
    CONF_TANK_CAPACITY,
    CONF_HEIGHT_MAX,
    CONF_TANK_LENGTH,
    CONF_TANK_WIDTH,
    CONF_TANK_HEIGHT,
    CONF_TANK_CYLINDER_RADIUS,
    CONF_TANK_CYLINDER_HEIGHT,
    TANK_SHAPE_CHOICES,
)


class EcoPilotConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EcoPilot devices"""

    VERSION = 1

    host: str | None = None
    token: str | None = None
    product_name: str | None = None
    product_model: str | None = None
    serial: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initiated by the user."""
        errors: dict[str, str] | None = None

        if user_input is not None:
            try:
                device_info = await async_try_connect(user_input[CONF_HOST])
            except RecoverableError as ex:
                LOGGER.error(ex)
                errors = {"base": ex.error_code}
            except UnauthorizedError:
                # Device responded, so hostname of IP is correct. But we have to authorize
                self.host = user_input[CONF_HOST]
                return await self.async_step_authorize()
            else:
                await self.async_set_unique_id(
                    f"{device_info.product_model}_{device_info.serial_number}"
                )
                self._abort_if_unique_id_configured(updates=user_input)
                return self.async_create_entry(
                    title=f"{device_info.product_name}",
                    data=user_input,
                )

        user_input = user_input or {}
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST, default=user_input.get(CONF_HOST)
                    ): TextSelector(),
                }
            ),
            errors=errors,
        )

    async def async_step_tank_sensor_config(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the tank configuration step."""

        if user_input is not None:
            self.config_data.update(user_input)

            return await self.async_step_tank_config()

        # Displays the form with the drop-down list of tank shapes
        distance_offset = (
            self.reconfigure_entry.data.get("distance_offset")
            if hasattr(self, "reconfigure_entry")
            else 0.0
        )
        return self.async_show_form(
            step_id="tank_sensor_config",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "distance_offset", default=distance_offset
                    ): NumberSelector(
                        NumberSelectorConfig(
                            mode=NumberSelectorMode.BOX,
                            step=0.1,
                        )
                    ),
                }
            ),
        )

    async def async_step_tank_config(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the tank configuration step."""

        if user_input is not None:
            self.config_data.update(user_input)

            # Selecting the right step
            if user_input[CONF_TANK_SHAPE] == TankShape.LINEAR:
                return await self.async_step_linear_tank()
            elif user_input[CONF_TANK_SHAPE] == TankShape.RECTANGULAR:
                return await self.async_step_rectangular_tank()
            elif user_input[CONF_TANK_SHAPE] == TankShape.CYLINDRICAL_H:
                return await self.async_step_cylindrical_tank()
            elif user_input[CONF_TANK_SHAPE] == TankShape.CYLINDRICAL_V:
                return await self.async_step_cylindrical_tank()
            else:
                # Default set to linear
                return await self.async_step_linear_tank()

        # Displays the form with the drop-down list of tank shapes
        tank_shape = (
            self.reconfigure_entry.data.get(CONF_TANK_SHAPE)
            if hasattr(self, "reconfigure_entry")
            else "Linear"
        )
        return self.async_show_form(
            step_id="tank_config",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TANK_SHAPE, default=tank_shape): vol.In(
                        TANK_SHAPE_CHOICES
                    ),
                }
            ),
        )

    async def async_step_linear_tank(self, user_input=None):
        """Handle the linear tank step."""

        if user_input is not None:
            self.config_data.update(user_input)

            if self.source == SOURCE_RECONFIGURE:
                return self.async_update_reload_and_abort(
                    self.reconfigure_entry,
                    data_updates=self.config_data,
                )
            else:
                return self.async_create_entry(
                    title=f"{self.device_info.product_name}", data=self.config_data
                )

        height_max = (
            self.reconfigure_entry.data.get(CONF_HEIGHT_MAX)
            if hasattr(self, "reconfigure_entry")
            else 0
        )
        tank_capacity = (
            self.reconfigure_entry.data.get(CONF_TANK_CAPACITY)
            if hasattr(self, "reconfigure_entry")
            else 0
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_HEIGHT_MAX, default=height_max): NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX,
                        step=0.1,
                    )
                ),
                vol.Required(CONF_TANK_CAPACITY, default=tank_capacity): NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX,
                        step=0.1,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="linear_tank", data_schema=schema)

    async def async_step_rectangular_tank(self, user_input=None):
        """Handle the rectangular tank step."""

        if user_input is not None:
            self.config_data.update(user_input)

            if self.source == SOURCE_RECONFIGURE:
                return self.async_update_reload_and_abort(
                    self.reconfigure_entry,
                    data_updates=self.config_data,
                )
            else:
                return self.async_create_entry(
                    title=f"{self.device_info.product_name}", data=self.config_data
                )

        tank_length = (
            self.reconfigure_entry.data.get(CONF_TANK_LENGTH)
            if hasattr(self, "reconfigure_entry")
            else 0.0
        )
        tank_width = (
            self.reconfigure_entry.data.get(CONF_TANK_WIDTH)
            if hasattr(self, "reconfigure_entry")
            else 0.0
        )
        tank_height = (
            self.reconfigure_entry.data.get(CONF_TANK_HEIGHT)
            if hasattr(self, "reconfigure_entry")
            else 0.0
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_TANK_LENGTH, default=tank_length): NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX,
                        step=0.1,
                    )
                ),
                vol.Required(CONF_TANK_WIDTH, default=tank_width): NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX,
                        step=0.1,
                    )
                ),
                vol.Required(CONF_TANK_HEIGHT, default=tank_height): NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX,
                        step=0.1,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="rectangular_tank", data_schema=schema)

    async def async_step_cylindrical_tank(self, user_input=None):
        """Handle the cylindrical tank step."""

        if user_input is not None:
            self.config_data.update(user_input)

            if self.source == SOURCE_RECONFIGURE:
                return self.async_update_reload_and_abort(
                    self.reconfigure_entry,
                    data_updates=self.config_data,
                )
            else:
                return self.async_create_entry(
                    title=f"{self.device_info.product_name}", data=self.config_data
                )

        tank_cylinder_radius = (
            self.reconfigure_entry.data.get(CONF_TANK_CYLINDER_RADIUS)
            if hasattr(self, "reconfigure_entry")
            else 0.0
        )
        tank_cylinder_height = (
            self.reconfigure_entry.data.get(CONF_TANK_CYLINDER_HEIGHT)
            if hasattr(self, "reconfigure_entry")
            else 0.0
        )
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_TANK_CYLINDER_RADIUS, default=tank_cylinder_radius
                ): NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX,
                        step=0.1,
                    )
                ),
                vol.Required(
                    CONF_TANK_CYLINDER_HEIGHT, default=tank_cylinder_height
                ): NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX,
                        step=0.1,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="cylindrical_tank", data_schema=schema)

    async def async_step_authorize(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step where we attempt to get a token."""

        assert self.host

        # Tell device we want a token, user must now press the button within 30 seconds
        # The first attempt will always fail, but this opens the window to press the button
        token = await async_request_token(self.hass, self.host)
        errors: dict[str, str] | None = None

        if token is None:
            if user_input is not None:
                errors = {"base": "authorization_failed"}

            return self.async_show_form(step_id="authorize", errors=errors)

        # Now we got a token, we can ask for some more info
        self.token = token

        async with DomintellEcopilotV1(self.host, token=token) as api:
            device_info = await api.device()

        self.device_info = device_info
        self.config_data = {
            CONF_HOST: self.host,
            CONF_TOKEN: token,
        }

        await self.async_set_unique_id(
            f"{device_info.product_model}_{device_info.serial_number}"
        )
        self._abort_if_unique_id_configured(updates=self.config_data)

        # Checking the product model for the "tankSense" configuration
        if device_info.product_model == "tankSense":
            return await self.async_step_tank_sensor_config()

        return self.async_create_entry(
            title=f"{device_info.product_name}",
            data=self.config_data,
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle zeroconf discovery."""
        # LOGGER.warning(f"---->discovery_info : {discovery_info}")

        if (
            CONF_PRODUCT_NAME not in discovery_info.properties
            or CONF_PRODUCT_MODEL not in discovery_info.properties
            or CONF_SERIAL_NUMBER not in discovery_info.properties
        ):
            return self.async_abort(reason="invalid_discovery_parameters")

        self.host = discovery_info.hostname.rstrip(".")
        self.ip = discovery_info.addresses[0]  # ip address V4
        self.product_model = discovery_info.properties[CONF_PRODUCT_MODEL]
        self.product_name = discovery_info.properties[CONF_PRODUCT_NAME]
        self.serial_number = discovery_info.properties[CONF_SERIAL_NUMBER]

        await self.async_set_unique_id(f"{self.product_model}_{self.serial_number}")
        self._abort_if_unique_id_configured(updates={CONF_HOST: discovery_info.host})

        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovery."""

        assert self.host
        assert self.ip
        assert self.product_name
        assert self.product_model
        assert self.serial_number

        errors: dict[str, str] | None = None
        if user_input is not None or not onboarding.async_is_onboarded(self.hass):
            try:
                device_info = await async_try_connect(self.host)
            except RecoverableError as ex:
                LOGGER.error(ex)
                errors = {"base": ex.error_code}
            except UnauthorizedError:
                return await self.async_step_authorize()
            else:
                self.device_info = device_info
                return self.async_create_entry(
                    title=self.product_name,
                    data={CONF_HOST: self.host},
                )

        self._set_confirm_only()

        # We do not add mac/serial to the title for devices
        # that users do not typically own multiple copies of.
        name = self.product_name
        if self.product_model not in ["ecoP1", "ecoDrive-P1", "ecoDrive-LK"]:
            name = f"{name} ({self.serial_number})"

        self.context["title_placeholders"] = {"name": name}

        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={
                CONF_PRODUCT_MODEL: self.product_model,
                CONF_SERIAL_NUMBER: self.serial_number,
                CONF_HOST: self.ip,
            },
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-auth if API was disabled."""
        self.host = entry_data[CONF_HOST]

        # If token exists, we assume that the token has been invalidated
        if entry_data.get(CONF_TOKEN):
            return await self.async_step_reauth_confirm_update_token()

        # Else we assume that the API has been disabled
        return await self.async_step_reauth_enable_api()

    async def async_step_reauth_enable_api(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauth dialog, where user is asked to re-enable the EcoPilot API."""
        errors: dict[str, str] | None = None
        if user_input is not None:
            reauth_entry = self._get_reauth_entry()
            try:
                await async_try_connect(reauth_entry.data[CONF_HOST])
            except RecoverableError as ex:
                LOGGER.error(ex)
                errors = {"base": ex.error_code}
            else:
                await self.hass.config_entries.async_reload(reauth_entry.entry_id)
                return self.async_abort(reason="reauth_enable_api_successful")

        return self.async_show_form(step_id="reauth_enable_api", errors=errors)

    async def async_step_reauth_confirm_update_token(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauth dialog."""
        assert self.host

        errors: dict[str, str] | None = None

        token = await async_request_token(self.hass, self.host)

        if user_input is not None:
            if token is None:
                errors = {"base": "authorization_failed"}
            else:
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data_updates={
                        CONF_TOKEN: token,
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm_update_token", errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the integration."""
        errors: dict[str, str] = {}
        self.reconfigure_entry = self._get_reconfigure_entry()

        if user_input:
            try:
                self.config_data = {
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_TOKEN: self.reconfigure_entry.data.get(CONF_TOKEN),
                }
                self.config_data.update(user_input)

                device_info = await async_try_connect(
                    user_input[CONF_HOST],
                    token=self.reconfigure_entry.data.get(CONF_TOKEN),
                )

            except RecoverableError as ex:
                LOGGER.error(ex)
                errors = {"base": ex.error_code}
            else:
                self.device_info = device_info

                await self.async_set_unique_id(
                    f"{device_info.product_model}_{device_info.serial_number}"
                )
                self._abort_if_unique_id_mismatch(reason="wrong_device")

                # Condition to check the "tankSense" model
                if device_info.product_model == "tankSense":
                    return await self.async_step_tank_sensor_config()

                return self.async_update_reload_and_abort(
                    self.reconfigure_entry,
                    data_updates=user_input,
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST,
                        default=self.reconfigure_entry.data.get(CONF_HOST),
                    ): TextSelector(),
                }
            ),
            description_placeholders={
                "title": self.reconfigure_entry.title,
            },
            errors=errors,
        )


async def async_try_connect(host: str, token: str | None = None) -> Device:
    """Try to connect.

    Make connection with device to test the connection
    and to get info for unique_id.
    """
    api = DomintellEcopilotV1(host, token=token)

    try:
        return await api.device()

    except UnsupportedError as ex:
        LOGGER.error("API version unsuppored")
        raise AbortFlow("unsupported_api_version") from ex

    except RequestError as ex:
        raise RecoverableError(
            "Device unreachable or unexpected response", "network_error"
        ) from ex

    except UnauthorizedError as ex:
        raise UnauthorizedError("Unauthorized") from ex

    except Exception as ex:
        LOGGER.exception("Unexpected exception")
        raise AbortFlow("unknown_error") from ex

    finally:
        await api.close()


async def async_request_token(hass: HomeAssistant, host: str) -> str | None:
    """Try to request a token from the device.

    This method is used to request a token from the device,
    it will return None if the token request failed.
    """

    api = DomintellEcopilotV1(host)

    # Get a part of the unique id to make the token unique
    # This is to prevent token conflicts when multiple HA instances are used
    uuid = await instance_id.async_get(hass)

    try:
        return await api.get_token(f"home-assistant#{uuid[:6]}")
    except UnauthorizedError:
        return None
    finally:
        await api.close()


class RecoverableError(HomeAssistantError):
    """Raised when a connection has been failed but can be retried."""

    def __init__(self, message: str, error_code: str) -> None:
        """Init RecoverableError."""
        super().__init__(message)
        self.error_code = error_code
