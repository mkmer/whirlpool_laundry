"""The Sensor for Whirlpool Laundry account."""
from datetime import datetime, timedelta
import logging

import aiohttp

# from typing import Callable
import requests
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

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
    async with aiohttp.ClientSession() as session:
        async with session.post(
            auth_url, data=auth_data, headers=auth_header
        ) as response:
            data = await response.json()
        await session.close()

    entities = [MaytagSensor(user, password, said) for said in data.get("SAID")]
    if entities:
        async_add_entities(entities,True)


class MaytagSensor(Entity):
    """A class for the Maytag account."""

    def __init__(self, user, password, said):
        """Initialize the sensor."""
        self._name = "maytag_" + (said).lower()
        self._user = user
        self._password = password
        self._said = said
        self._reauthorize = True
        self._access_token = None
        self._state = "offline"
        self._status = "Unknown"
        self.attrib = {}
        self._endtime = None
        self._timeremaining = None
        self._modelnumber = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique identifier for this client."""
        return f"{self._said}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def should_poll(self):
        """Turn off polling, will do ourselves."""
        return True

    def authorize(self):
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

            response = requests.post(auth_url, data=auth_data, headers=auth_header)
            data = response.json()

            self._access_token = data.get("access_token")

            self._reauthorize = False

        except requests.ConnectionError:
            self._access_token = None
            self._reauthorize = True
            self._status = "Authorization failed"
            self._state = "Authorization failed"
            self.attrib = {}
            self._endtime = None
            self._timeremaining = None

    def update(self):
        """Update device state."""
        if self._reauthorize :
            self.authorize()

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

                response = requests.get(new_url, data={}, headers=new_header)
                data = response.json()
                self.attrib = data.get("attributes")
                self._modelnumber = (
                    data.get("attributes").get("ModelNumber").get("value")
                )
                self._status = (
                    data.get("attributes")
                    .get("Cavity_CycleStatusMachineState")
                    .get("value")
                )
                self._timeremaining = (
                    data.get("attributes")
                    .get("Cavity_TimeStatusEstTimeRemaining")
                    .get("value")
                )
                if int(self._status) == 7:
                    self._endtime = datetime.now() + timedelta(
                        seconds=int(self._timeremaining)
                    )
                else:
                    self._endtime = datetime.now()

                # status: [0=off, 1=on but not running, 7=running, 6=paused, 10=cycle complete]

                self._state = UNIT_STATES.get(self._status, self._status)
                if self._modelnumber[2] == "W":
                    self._name = "Washer"
                elif self._modelnumber[2] == "D":
                    self._name = "Dryer"

            except requests.ConnectionError:

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
