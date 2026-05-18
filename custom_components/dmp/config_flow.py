from copy import deepcopy
import logging
from typing import Any, Dict, Optional

from homeassistant import config_entries

from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import selector
import voluptuous as vol

from .const import (
    CONF_PANEL_NAME,
    CONF_PANEL_IP,
    CONF_PANEL_LISTEN_PORT,
    CONF_PANEL_REMOTE_PORT,
    CONF_PANEL_ACCOUNT_NUMBER,
    CONF_PANEL_REMOTE_KEY,
    CONF_HOME_AREA,
    CONF_AWAY_AREA,
    CONF_ZONE_NAME,
    CONF_ZONE_NUMBER,
    CONF_ZONE_CLASS,
    CONF_ADD_ANOTHER,
    DEV_TYPE_BATTERY_DOOR,
    DEV_TYPE_BATTERY_GLASSBREAK,
    DEV_TYPE_BATTERY_MOTION,
    DEV_TYPE_BATTERY_SIREN,
    DEV_TYPE_BATTERY_SMOKE,
    DEV_TYPE_BATTERY_WINDOW,
    DEV_TYPE_WIRED_DOOR,
    DEV_TYPE_WIRED_GLASSBREAK,
    DEV_TYPE_WIRED_MOTION,
    DEV_TYPE_WIRED_SMOKE,
    DEV_TYPE_WIRED_WINDOW,
)

from .const import CONF_ZONES, DOMAIN

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = selector(
    {
        "select": {
            "options": [
                {"label": "-Select a Device Type-", "value": "default"},
                {"label": "Door (Battery Powered)", "value": DEV_TYPE_BATTERY_DOOR},
                {"label": "Door (Wired)", "value": DEV_TYPE_WIRED_DOOR},
                {
                    "label": "Glass Break Detector (Battery Powered)",
                    "value": DEV_TYPE_BATTERY_GLASSBREAK,
                },
                {
                    "label": "Glass Break Detector (Wired)",
                    "value": DEV_TYPE_WIRED_GLASSBREAK,
                },
                {
                    "label": "Motion Detector (Battery Powered)",
                    "value": DEV_TYPE_BATTERY_MOTION,
                },
                {"label": "Motion Detector (Wired)", "value": DEV_TYPE_WIRED_MOTION},
                {"label": "Siren (Battery Powered)", "value": DEV_TYPE_BATTERY_SIREN},
                {"label": "Siren (Wired)", "value": DEV_TYPE_WIRED_MOTION},
                {
                    "label": "Smoke Detector (Battery Powered)",
                    "value": DEV_TYPE_BATTERY_SMOKE,
                },
                {"label": "Smoke Detector (Wired)", "value": DEV_TYPE_WIRED_SMOKE},
                {"label": "Window (Battery Powered)", "value": DEV_TYPE_BATTERY_WINDOW},
                {"label": "Window (Wired)", "value": DEV_TYPE_WIRED_WINDOW},
            ],
            "mode": "dropdown",
            "multiple": False,
        }
    }
)


PANEL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PANEL_NAME, default="DMP XR150"): cv.string,
        vol.Required(CONF_PANEL_IP, default="192.168.1.2"): cv.string,
        vol.Optional(CONF_PANEL_REMOTE_PORT, default=8011): cv.port,
        vol.Optional(CONF_PANEL_LISTEN_PORT, default=8001): cv.port,
        vol.Required(CONF_PANEL_ACCOUNT_NUMBER): cv.string,
        vol.Optional(CONF_PANEL_REMOTE_KEY): cv.string,
    }
)


AREA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_HOME_AREA, default="01"): cv.string,
        vol.Optional(CONF_AWAY_AREA, default="02"): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)


ZONE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ZONE_NAME): cv.string,
        vol.Required(CONF_ZONE_NUMBER): cv.string,
        vol.Optional(CONF_ZONE_CLASS, default="default"): SENSOR_TYPES,
        vol.Optional(CONF_ADD_ANOTHER): cv.boolean,
    },
    extra=vol.ALLOW_EXTRA,
)


def _is_numeric(value: Any) -> bool:
    """Return True when a config flow field contains only digits."""
    return isinstance(value, str) and value.isdecimal()


class DMPCustomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """DMP Custom config flow."""

    data: Optional[Dict[str, Any]]

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        errors: Dict[str, str] = {}
        if user_input is not None:
            self.data = user_input
            self.data[CONF_ZONES] = []
            return await self.async_step_areas()
        return self.async_show_form(
            step_id="user", data_schema=PANEL_SCHEMA, errors=errors
        )

    async def async_step_areas(self, user_input: Optional[Dict[str, Any]] = None):
        errors: Dict[str, str] = {}
        if user_input is not None:
            if not _is_numeric(user_input[CONF_HOME_AREA]):
                errors[CONF_HOME_AREA] = "invalid_area_number"
            if not _is_numeric(user_input[CONF_AWAY_AREA]):
                errors[CONF_AWAY_AREA] = "invalid_area_number"
            if errors:
                return self.async_show_form(
                    step_id="areas", data_schema=AREA_SCHEMA, errors=errors
                )

            self.data[CONF_HOME_AREA] = user_input[CONF_HOME_AREA]
            self.data[CONF_AWAY_AREA] = user_input[CONF_AWAY_AREA]
            if user_input.get("add_another", False):
                return await self.async_step_areas()
            return await self.async_step_zones()
        return self.async_show_form(
            step_id="areas", data_schema=AREA_SCHEMA, errors=errors
        )

    async def async_step_zones(self, user_input: Optional[Dict[str, Any]] = None):
        errors: Dict[str, str] = {}
        if user_input is not None:
            if not _is_numeric(user_input[CONF_ZONE_NUMBER]):
                errors[CONF_ZONE_NUMBER] = "invalid_zone_number"
            if errors:
                return self.async_show_form(
                    step_id="zones", data_schema=ZONE_SCHEMA, errors=errors
                )

            self.data[CONF_ZONES].append(user_input)
            if user_input.get("add_another", False):
                return await self.async_step_zones()
            return self.async_create_entry(
                title=self.data[CONF_PANEL_NAME], data=self.data
            )
        return self.async_show_form(
            step_id="zones", data_schema=ZONE_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handles options flow for the component."""

    async def async_step_init(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Manage the options for the custom component."""
        errors: Dict[str, str] = {}
        # Get a list of zones for the UI since each zone has multiple
        # sensors.
        zones = dict(self.config_entry.data)[CONF_ZONES]
        zones_dict = {z[CONF_ZONE_NUMBER]: z[CONF_ZONE_NAME] for z in zones}
        if user_input is not None:
            selected_zones = user_input.get(CONF_ZONES, [])
            zone_class = user_input.get(CONF_ZONE_CLASS, "default")
            zone_number = user_input.get(CONF_ZONE_NUMBER, "")
            updated_zones = deepcopy(self.config_entry.data[CONF_ZONES])
            deleted_zones = [
                z[CONF_ZONE_NUMBER]
                for z in zones
                if z[CONF_ZONE_NUMBER] not in selected_zones
            ]

            # Get lisf of deleted entity_id and remove from config
            for d in deleted_zones:
                updated_zones = [e for e in updated_zones if e["zone_number"] != d]

            # Add new zones to config
            if zone_number and not _is_numeric(zone_number):
                errors[CONF_ZONE_NUMBER] = "invalid_zone_number"
            if zone_class != "default":
                if not user_input.get(CONF_ZONE_NAME):
                    errors[CONF_ZONE_NAME] = "missing_zone_name"
                if not zone_number:
                    errors[CONF_ZONE_NUMBER] = "missing_zone_number"

            if not errors and zone_class != "default":
                updated_zones.append(
                    {
                        CONF_ZONE_NAME: user_input[CONF_ZONE_NAME],
                        CONF_ZONE_NUMBER: zone_number,
                        CONF_ZONE_CLASS: zone_class,
                    }
                )

            if not errors:
                return self.async_create_entry(
                    title="",
                    data={CONF_ZONES: updated_zones},
                )

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ZONES, default=list(zones_dict.keys())
                ): cv.multi_select(zones_dict),
                vol.Optional(CONF_ZONE_NAME): cv.string,
                vol.Optional(CONF_ZONE_NUMBER): cv.string,
                vol.Optional(CONF_ZONE_CLASS, default="default"): SENSOR_TYPES,
            }
        )
        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )
