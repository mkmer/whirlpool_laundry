"""The Whirlpool Laundry integration."""
import asyncio
import logging

import aiohttp

from homeassistant import config_entries, core
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import PlatformNotReady

from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    # Registers update listener to update config entry when options are updated.
    # unsub_options_update_listener = entry.add_update_listener(options_update_listener)
    # Store a reference to the unsubscribe function to cleanup if an entry is unloaded.
    # hass_data["unsub_options_update_listener"] = unsub_options_update_listener

    hass_data = dict(entry.data)
    config = hass_data
    user = config["username"]
    password = config["password"]

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
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                auth_url, data=auth_data, headers=auth_header
            ) as response:
                data = await response.json()
            await session.close()
    except (aiohttp.ClientConnectionError, asyncio.TimeoutError) as ex:
        raise PlatformNotReady(f"Failed to connect: {ex}") from ex

    hass_data.update({"data": data})
    hass.data[DOMAIN][entry.entry_id] = hass_data
    # Forward the setup to the sensor platform.
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
