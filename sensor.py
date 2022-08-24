"""The Sensor for Whirlpool Laundry account."""
from datetime import datetime, timedelta
import logging
import asyncio
import voluptuous as vol

import aiohttp
from homeassistant import config_entries
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

# from types import NoneType


_LOGGER = logging.getLogger(__name__)

CONF_USER = "user"
CONF_PASSWORD = "password"
ICON_D = "mdi:tumble-dryer"
ICON_W = "mdi:washing-machine"
UNIT_STATES = {
    "0": "Ready",
    "1": "Not Running",
    "6": "Paused",
    "7": "Running",
    "8": "Wrinkle Prevent",
    "10": "Cycle Complete",
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USER): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)


BASE_INTERVAL = timedelta(minutes=5)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Config flow entry for Whrilpool Laundry."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    user = config["username"]
    password = config["password"]
    data = config["data"]
    session = hass.data[DOMAIN][config_entry.entry_id]["session"]
    entities = [
        MaytagSensor(user, password, said, session) for said in data.get("SAID")
    ]
    if entities:
        async_add_entities(entities, True)


class MaytagSensor(Entity):
    """A class for the Maytag account."""

    def __init__(self, user, password, said, session):
        """Initialize the sensor."""
        self._user = user
        self._password = password
        self._said = said
        self._device_id = said
        self._reauthorize = True
        self._access_token = None
        self._state = "offline"
        self._status = "Unknown"
        self.attrib = {}
        self._endtime = None
        self._timeremaining = None
        self._modelnumber = None
        self._attr_unique_id = f"{self._said}"
        self._attr_has_entity_name = True
        self._session = session

    @property
    def device_info(self) -> DeviceInfo:
        """Device information for Aladdin Connect sensors."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._said,
            manufacturer="Whirlpool",
        )

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def should_poll(self):
        """Turn off polling, will do ourselves."""
        return True

    async def authorize(self):
        """Update device state."""
        try:
            auth_url = "https://api.whrcloud.com/oauth/token"
            auth_header = {
                "Content-Type": "application/x-www-form-urlencoded",
            }

            auth_data = {
                "client_id": "maytag_ios",
                "client_secret": "OfTy3A3rV4BHuhujkPThVDE9-SFgOymJyUrSbixjViATjCGviXucSKq2OxmPWm8DDj9D1IFno_mZezTYduP-Ig",
                "grant_type": "password",
                "username": self._user,
                "password": self._password,
            }

            response = await self._session.post(
                auth_url, data=auth_data, headers=auth_header
            )
            data = await response.json()

            self._access_token = data.get("access_token")

            new_url = "https://api.whrcloud.com/api/v1/appliance/" + self._said

            new_header = {
                "Authorization": "Bearer " + self._access_token,
                "Content-Type": "application/json",
                "Host": "api.whrcloud.com",
                "User-Agent": "okhttp/3.12.0",
                "Pragma": "no-cache",
                "Cache-Control": "no-cache",
            }

            response = await self._session.get(new_url, data={}, headers=new_header)
            data = await response.json()
            if data is not None:
                self._modelnumber = (
                    data.get("attributes").get("ModelNumber").get("value")
                )
#                if self._modelnumber[2] == "W":
#                    self._name = "Washer"
#                elif self._modelnumber[2] == "D":
#                    self._name = "Dryer"

            self._reauthorize = False

        except (aiohttp.ClientConnectionError, aiohttp.ClientConnectorError):
            self._access_token = None
            self._reauthorize = True
            self._status = "Authorization failed"
            self._state = "Authorization failed"
            self.attrib = {}
            self._endtime = None
            self._timeremaining = None

    async def async_update(self):
        """Update device state."""
        if self._reauthorize:
            await self.authorize()

        if self._access_token is not None:
            try:
                new_url = "https://api.whrcloud.com/api/v1/appliance/" + self._said

                new_header = {
                    "Authorization": "Bearer " + self._access_token,
                    "Content-Type": "application/json",
                    "Host": "api.whrcloud.com",
                    "User-Agent": "okhttp/3.12.0",
                    "Pragma": "no-cache",
                    "Cache-Control": "no-cache",
                }

                response = await self._session.get(new_url, data={}, headers=new_header)
                data = await response.json()
                _LOGGER.info("Message Received: %s", data)
                if data is None:
                    self._reauthorize = True
                    self.authorize()
                elif data.get("error") is not None:
                    self._reauthorize = True
                    self.authorize()
                else:    
                    self.attrib = data.get("attributes")
                    if not isinstance(self.attrib, type(None)):

                        self._status = self.attrib.get(
                            "Cavity_CycleStatusMachineState"
                        ).get("value")
                        self._timeremaining = self.attrib.get(
                            "Cavity_TimeStatusEstTimeRemaining"
                        ).get("value")
                        if int(self._status) == 7:
                            self._endtime = datetime.now() + timedelta(
                                seconds=int(self._timeremaining)
                            )
                        else:
                            self._endtime = datetime.now()

                    # status: [0=off, 1=on but not running, 7=running, 6=paused, 10=cycle complete]
                    else:
                        _LOGGER.error(f"Bad Message Received: {data}")
                    self._state = UNIT_STATES.get(self._status, self._status)

            except (
                aiohttp.ClientConnectionError,
                aiohttp.ClientConnectorError,
                asyncio.TimeoutError,
            ):

                self._status = "Data Update Failed"
                self._state = "Data Update Failed"
                self.attrib = {}
                self._reauthorize = True
                self._timeremaining = None
                self._endtime = None

        else:  # No token... try again!
            self._reauthorize = True

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attr = {}
        for key, value in self.attrib.items():
            attr[key] = value["value"]
        attr["end_time"] = self._endtime
        return attr

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        if self._modelnumber is not None and self._modelnumber[2] == "D":
            return ICON_D

        return ICON_W