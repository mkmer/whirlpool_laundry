"""Config flow for test integration."""
from __future__ import annotations

import logging
from typing import Any
import requests
import voluptuous as vol
import aiohttp
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data["username"], data["password"]
    # )
    user = data["username"]
    password = data["password"]

    auth_url = "https://api.whrcloud.com/oauth/token"
    auth_header = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    auth_data = {
        "client_id": "maytag_ios",
        "client_secret": "OfTy3A3rV4BHuhujkPThVDE9-SFgOymJyUrSbixjViATjCGviXucSKq2OxmPWm8DDj9D1IFno_mZezTYduP-Ig",
        "grant_type": "password",
        "username": user,
        "password": password,
    }

    # result = await hass.async_add_executor_job(hub.update)
    headers = {}
    async with aiohttp.ClientSession() as session:
        async with session.post(auth_url, data=auth_data, headers=auth_header) as r:
            if not r.ok:
                raise CannotConnect
            data = await r.json()

        session.close()

    # Return info that you want to store in the config entry.
    if "error" in data:  # we found and error in the connection
        if data["error"] == "invalid_request":
            raise InvalidAuth
        else:
            raise Exception

    return {"title": "Whirlpool Laundry"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for test."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

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
            self.data = user_input
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
