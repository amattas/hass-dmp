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

from .const import (CONF_PANEL_NAME, CONF_PANEL_IP, CONF_PANEL_LISTEN_PORT,
                    CONF_PANEL_REMOTE_PORT, CONF_PANEL_ACCOUNT_NUMBER,
                    CONF_PANEL_REMOTE_KEY, CONF_AREA_HOME_ZONE,
                    CONF_AREA_AWAY_ZONE, CONF_ZONE_NAME, CONF_ZONE_NUMBER,
                    CONF_ZONE_CLASS, CONF_ADD_ANOTHER)

from .const import CONF_PANELS, CONF_AREAS, CONF_ZONES, DOMAIN

PANEL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PANEL_NAME, default='DMP XR 150'): cv.string,
        vol.Required(CONF_PANEL_IP, default='0.0.0.0'): cv.string,
        vol.Optional(CONF_PANEL_REMOTE_PORT, default=8011): cv.port,
        vol.Optional(CONF_PANEL_LISTEN_PORT, default=8001): cv.port,
        vol.Required(CONF_PANEL_ACCOUNT_NUMBER): cv.string,
        vol.Optional(CONF_PANEL_REMOTE_KEY): cv.string,
    }
)


AREA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_AREA_HOME_ZONE): cv.string,
        vol.Optional(CONF_AREA_AWAY_ZONE, default='010203'): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)


ZONE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ZONE_NAME): cv.string,
        vol.Required(CONF_ZONE_NUMBER): cv.string,
        vol.Required(CONF_ZONE_CLASS): cv.string,
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
            self.data[CONF_AREAS].append(user_input)
            if user_input.get("add_another", False):
                return await self.async_step_areas()
            return await self.async_step_zones()
        return self.async_show_form(step_id="areas", data_schema=AREA_SCHEMA,
                                    errors=errors)

    async def async_step_zones(self,
                               user_input: Optional[Dict[str, Any]] = None):
        errors: Dict[str, str] = {}
        if user_input is not None:
            self.data[CONF_ZONES].append(user_input)
            if user_input.get("add_another", False):
                return await self.async_step_zones()
            return self.async_create_entry(title=self.data[CONF_PANEL_NAME],
                                           data=self.data)
        return self.async_show_form(step_id="zones", data_schema=ZONE_SCHEMA,
                                    errors=errors)
