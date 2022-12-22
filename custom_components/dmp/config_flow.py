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
from homeassistant.helpers.selector import selector
import voluptuous as vol

from .const import (CONF_PANEL_NAME, CONF_PANEL_IP, CONF_PANEL_LISTEN_PORT,
                    CONF_PANEL_REMOTE_PORT, CONF_PANEL_ACCOUNT_NUMBER,
                    CONF_PANEL_REMOTE_KEY, CONF_HOME_AREA,
                    CONF_AWAY_AREA, CONF_ZONE_NAME, CONF_ZONE_NUMBER,
                    CONF_ZONE_CLASS, CONF_ADD_ANOTHER,
                    DEV_TYPE_BATTERY_DOOR, DEV_TYPE_BATTERY_GLASSBREAK,
                    DEV_TYPE_BATTERY_MOTION, DEV_TYPE_BATTERY_SIREN,
                    DEV_TYPE_BATTERY_SMOKE, DEV_TYPE_BATTERY_WINDOW,
                    DEV_TYPE_WIRED_DOOR, DEV_TYPE_WIRED_GLASSBREAK,
                    DEV_TYPE_WIRED_MOTION, DEV_TYPE_WIRED_SIREN,
                    DEV_TYPE_WIRED_SMOKE, DEV_TYPE_WIRED_WINDOW)

from .const import CONF_ZONES, DOMAIN

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = selector({
            "select": {
                "options": [
                    {
                        "label": "Battery - Door",
                        "value": DEV_TYPE_BATTERY_DOOR
                    },
                    {
                        "label": "Battery - Glass Break",
                        "value": DEV_TYPE_BATTERY_GLASSBREAK
                    },
                    {
                        "label": "Battery - Motion",
                        "value": DEV_TYPE_BATTERY_MOTION
                    },
                    {
                        "label": "Battery - Siren",
                        "value": DEV_TYPE_BATTERY_SIREN
                    },
                    {
                        "label": "Battery - Smoke",
                        "value": DEV_TYPE_BATTERY_SMOKE
                    },
                    {
                        "label": "Battery - Window",
                        "value": DEV_TYPE_BATTERY_WINDOW
                    },
                    {
                        "label": "Wired - Door",
                        "value": DEV_TYPE_WIRED_DOOR
                    },
                    {
                        "label": "Wired - Glass Break",
                        "value": DEV_TYPE_WIRED_GLASSBREAK
                    },
                    {
                        "label": "Wired - Motion",
                        "value": DEV_TYPE_WIRED_MOTION
                    },
                    {
                        "label": "Battery - Siren",
                        "value": DEV_TYPE_WIRED_MOTION
                    },
                    {
                        "label": "Battery - Smoke",
                        "value": DEV_TYPE_WIRED_SMOKE
                    },
                    {
                        "label": "Wired - Window",
                        "value": DEV_TYPE_WIRED_WINDOW
                    },
                ],
                "mode": "dropdown",
                "multiple": False
            }
        })


PANEL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PANEL_NAME, default='DMP XR150'): cv.string,
        vol.Required(CONF_PANEL_IP, default='0.0.0.0'): cv.string,
        vol.Optional(CONF_PANEL_REMOTE_PORT, default=8011): cv.port,
        vol.Optional(CONF_PANEL_LISTEN_PORT, default=8001): cv.port,
        vol.Required(CONF_PANEL_ACCOUNT_NUMBER): cv.string,
        vol.Optional(CONF_PANEL_REMOTE_KEY): cv.string,
    }
)


AREA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_HOME_AREA, default='01'): cv.string,
        vol.Optional(CONF_AWAY_AREA, default='02'): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)


ZONE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ZONE_NAME): cv.string,
        vol.Required(CONF_ZONE_NUMBER): cv.string,
        vol.Optional(CONF_ZONE_CLASS, default=[]): SENSOR_TYPES,
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
            self.data[CONF_ZONES] = []
            return await self.async_step_areas()
        return self.async_show_form(step_id="user", data_schema=PANEL_SCHEMA,
                                    errors=errors)

    async def async_step_areas(self,
                               user_input: Optional[Dict[str, Any]] = None):
        errors: Dict[str, str] = {}
        if user_input is not None:
            self.data[CONF_HOME_AREA] = user_input[CONF_HOME_AREA]
            self.data[CONF_AWAY_AREA] = user_input[CONF_AWAY_AREA]
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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handles options flow for the component."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Manage the options for the custom component."""
        errors: Dict[str, str] = {}
        entity_registry = await async_get_registry(self.hass)
        entries = async_entries_for_config_entry(
            entity_registry, self.config_entry.entry_id
        )
        zones = dict(self.config_entry.data)[CONF_ZONES]
        _LOGGER.debug("Zones: %s" % zones)
        zones_dict = {
            z.zone_name: z.zone_number for z in zones
            }
        _LOGGER.debug("Dictionary: %s" % zones_dict)

        if user_input is not None:
            updated_zones = deepcopy(zones_dict)
            _LOGGER("updated_zones %s" % updated_zones)
            _LOGGER("user_input %s" % user_input[CONF_ZONES])

        # # Default value for our multi-select.
        # all_zones = {
        #     e.device_id: e.original_name
        #     for e in entries
        #     if e.unique_id.split('-')[2] == 'zone'
        #     }
        # zone_map = {e.entity_id: e for e in entries}

        # if user_input is not None:
        #     updated_zones = deepcopy(self.config_entry.data[CONF_ZONES])
        #     removed_entities = [
        #         entity_id
        #         for entity_id in zone_map.keys()
        #         if entity_id not in user_input[CONF_ZONES]
        #     ]
        #     for entity_id in removed_entities:
        #         # entity_registry.async_remove(entity_id)
        #         entry = zone_map[entity_id]
        #         entry_path = entry.unique_id
        #         updated_zones = [
        #             e for e in updated_zones
        #             if e["path"] != entry_path
        #             ]

        #         if not errors:
        #             updated_zones.append(
        #                 {
        #                     CONF_ZONE_NAME: user_input[CONF_ZONE_NAME],
        #                     CONF_ZONE_NUMBER: user_input[CONF_ZONE_NUMBER],
        #                     CONF_ZONE_CLASS: user_input[CONF_ZONE_CLASS]
        #                 }
        #             )

            # if not errors:
            #     return self.async_create_entry(
            #         title="",
            #         data={CONF_ZONES: updated_zones},
            #     )

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ZONES, default=list(
                        zones_dict.keys())
                    ): cv.multi_select(
                    zones_dict
                    ),
                vol.Required(CONF_ZONE_NAME): cv.string,
                vol.Required(CONF_ZONE_NUMBER): cv.string,
                vol.Optional(CONF_ZONE_CLASS, default=[]): SENSOR_TYPES,
            }
        )
        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )
