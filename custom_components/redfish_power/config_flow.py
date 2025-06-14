"""Config flow for Redfish Power integration."""
from __future__ import annotations

import logging
from typing import Any
import fnmatch
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

import aiohttp

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("host"): str,
        vol.Required("username"): str,
        vol.Required("password"): str,
    }
)


class RedfishPowerHub:
    def __init__(self, host: str, username: str, password: str) -> None:
        """Initialize."""
        self.host = host
        self.username = username
        self.password = password
        self.session = aiohttp.ClientSession(
            base_url=f"https://{host}",
            auth=aiohttp.BasicAuth(login=username, password=password),
            connector=aiohttp.TCPConnector(ssl=False)
        )

    async def test_connection(self) -> bool:
        async with self.session.get("/redfish/v1") as resp:
            return (
                resp.status == 200
                and fnmatch.fnmatch(
                    (await resp.json())["@odata.type"],
                    "#ServiceRoot.v1_?_0.ServiceRoot"
                    )
            )

    async def authenticate(self) -> bool:
        async with self.session.get(
            "/redfish/v1/Systems/1"
        ) as resp:
            return (
                resp.status == 200
                and fnmatch.fnmatch(
                    (await resp.json())["@odata.type"],
                    "#ComputerSystem.v1_?_0.ComputerSystem"
                    )
            )

    async def get_device_hostname(self) -> str:
        async with self.session.get(
            "/redfish/v1/Managers/1/EthernetInterfaces/1"
        ) as resp:
            json_resp = await resp.json()
            if json_resp["HostName"]:
                return json_resp["HostName"]

            return "Unknown Hostname"

    async def get_power_consumption(self) -> int:
        async with self.session.get(
            "/redfish/v1/Chassis/1/Power"
        ) as resp:
            json_resp = await resp.json()
            return json_resp["PowerControl"][0]["PowerMetrics"]["AverageConsumedWatts"]


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data["username"], data["password"]
    # )

    hub = RedfishPowerHub(data["host"], data["username"], data["password"])

    if not await hub.test_connection():
        raise CannotConnect

    if not await hub.authenticate():
        raise InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": await hub.get_device_hostname()}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Redfish Power."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
