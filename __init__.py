"""The Whirlpool Laundry integration."""
# from __future__ import annotations
import logging
import asyncio
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant import config_entries, core
from .const import DOMAIN

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)

# # Only one sensor update once every 60 seconds to avoid
# entity_next = 0

# @callback
# def do_update(time):
# nonlocal entity_next
# entities[entity_next].async_schedule_update_ha_state(True)
# entity_next = (entity_next + 1) % len(entities)

# track_time_interval(hass, do_update, BASE_INTERVAL)


# async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
#    """Set up Whirlpool Laundry from a config entry."""
#    # TODO Store an API object for your platforms to access
##    # hass.data[DOMAIN][entry.entry_id] = MyApi(...)

# hass.config_entries.async_setup_platforms(entry, PLATFORMS)

# hass.data[DOMAIN][entry.entry_id] =
# return True


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    hass_data = dict(entry.data)
    # Registers update listener to update config entry when options are updated.
    # unsub_options_update_listener = entry.add_update_listener(options_update_listener)
    # Store a reference to the unsubscribe function to cleanup if an entry is unloaded.
    # hass_data["unsub_options_update_listener"] = unsub_options_update_listener
    hass.data[DOMAIN][entry.entry_id] = hass_data

    # Forward the setup to the sensor platform.
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Set up the GitHub Custom component from yaml configuration."""
    hass.data.setdefault(DOMAIN, {})
    return True
