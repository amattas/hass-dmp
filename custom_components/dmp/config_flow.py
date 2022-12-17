from copy import deepcopy
import logging
from typing import Any, Dict, Optional

from homeassistant import config_entries, core
# from homeassistant.const import CONF_ACCESS_TOKEN, CONF_NAME, CONF_PATH
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_registry import (
    async_entries_for_config_entry,
    async_get_registry,
)
import voluptuous as vol

from .const import (CONF_PANEL_IP, CONF_PANEL_ACCOUNT_NUMBER,
                    CONF_PANEL_REMOTE_KEY, CONF_PANEL_REMOTE_PORT,
                    CONF_ZONE_NAME, CONF_ZONE_NUMBER, CONF_ZONE_CLASS,
                    CONF_AREA_NAME, CONF_AREA_NUMBER, CONF_AREA_DISARM_ZONE,
                    CONF_AREA_HOME_ZONE, CONF_AREA_AWAY_ZONE, CONF_LISTEN_PORT,
                    CONF_ADD_ANOTHER)

from .const import CONF_PANELS, CONF_AREAS, CONF_ZONES, DOMAIN

ZONE_CLASSES = {
    "door": ("Door", "door"),
    "window": ("Window", "window")
}

PANEL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PANEL_IP, default='0.0.0.0'): cv.string,
        vol.Optional(CONF_PANEL_REMOTE_PORT, default=8001): cv.port,
        vol.Optional(CONF_LISTEN_PORT, default=8011): cv.port,
        vol.Required(CONF_PANEL_ACCOUNT_NUMBER): cv.string,
        vol.Optional(CONF_PANEL_REMOTE_KEY): cv.string,
    }
)


ZONE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ZONE_NAME): cv.string,
        vol.Required(CONF_ZONE_NUMBER): cv.string,
        vol.Required(CONF_ZONE_CLASS): (vol.All(cv.ensure_list,
                                        [vol.In(ZONE_CLASSES)])),
        vol.Optional(CONF_ADD_ANOTHER): cv.boolean
    },
    extra=vol.ALLOW_EXTRA,
)

AREA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_AREA_NAME): cv.string,
        vol.Required(CONF_AREA_NUMBER): cv.string,
        vol.Optional(CONF_AREA_DISARM_ZONE, default='010203'): cv.string,
        vol.Optional(CONF_AREA_HOME_ZONE): cv.string,
        vol.Optional(CONF_AREA_AWAY_ZONE, default='010203'): cv.string,
        vol.Optional(CONF_ADD_ANOTHER): cv.boolean
    },
    extra=vol.ALLOW_EXTRA,
)


class DMPCustomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """DMP Custom config flow."""

    data: Optional[Dict[str, Any]]

    async def async_step_user(self,
                              user_input: Optional[Dict[str, Any]] = None):
        errors: Dict[str, str] = {}
        if user_input is not None:
            self.data = user_input
            self.data[CONF_AREAS] = []
            self.data[CONF_ZONES] = []
            return await self.async_step_areas()
        return self.async_show_form(step_id="user", data_schema=PANEL_SCHEMA,
                                    errors=errors)

    async def async_step_areas(self,
                               user_input: Optional[Dict[str, Any]] = None):
        errors: Dict[str, str] = {}
        if user_input is not None:
            self.data = user_input
            if user_input.get("add_another", False):
                return await self.async_step_areas()
            return await self.async_step_zones()
        return self.async_show_form(step_id="areas", data_schema=AREA_SCHEMA,
                                    errors=errors)

    async def async_step_zones(self,
                               user_input: Optional[Dict[str, Any]] = None):
        errors: Dict[str, str] = {}
        if user_input is not None:
            self.data = user_input
            if user_input.get("add_another", False):
                return await self.async_step_zones()
            return self.async_create_entry(title="DMP Alarm System",
                                           data=self.data)
        return self.async_show_form(step_id="zones", data_schema=ZONE_SCHEMA,
                                    errors=errors)
