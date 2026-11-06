from __future__ import annotations

import logging
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

import homeassistant.helpers.config_validation as cv

# Home Assistant 2026.10 aliases voluptuous to probatio at runtime but types
# data_schema as probatio.Schema; voluptuous keeps HA 2024.11 (hacs.json) working,
# hence the arg-type ignores on data_schema below.
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState, ConfigFlowResult
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import selector
from pydmp import DMPAuthenticationError
from pydmp import DMPPanel as PyDMPPanel
from pydmp.exceptions import DMPConnectionError

from .const import (
    BLANK_REMOTE_KEY,
    CONF_ADD_ANOTHER,
    CONF_AWAY_AREA,
    CONF_HOME_AREA,
    CONF_PANEL_ACCOUNT_NUMBER,
    CONF_PANEL_IP,
    CONF_PANEL_LISTEN_PORT,
    CONF_PANEL_NAME,
    CONF_PANEL_REMOTE_KEY,
    CONF_PANEL_REMOTE_PORT,
    CONF_ZONE_CLASS,
    CONF_ZONE_NAME,
    CONF_ZONE_NUMBER,
    CONF_ZONES,
    DEFAULT_PANEL_REMOTE_PORT,
    DEV_TYPE_BATTERY_DOOR,
    DEV_TYPE_BATTERY_GLASSBREAK,
    DEV_TYPE_BATTERY_MOTION,
    DEV_TYPE_BATTERY_SIREN,
    DEV_TYPE_BATTERY_SMOKE,
    DEV_TYPE_BATTERY_WINDOW,
    DEV_TYPE_WIRED_DOOR,
    DEV_TYPE_WIRED_GLASSBREAK,
    DEV_TYPE_WIRED_MOTION,
    DEV_TYPE_WIRED_SIREN,
    DEV_TYPE_WIRED_SMOKE,
    DEV_TYPE_WIRED_WINDOW,
    DOMAIN,
)

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
                {"label": "Siren (Wired)", "value": DEV_TYPE_WIRED_SIREN},
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


REAUTH_SCHEMA = vol.Schema({vol.Optional(CONF_PANEL_REMOTE_KEY): cv.string})


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


async def _async_validate_connection(
    hass: HomeAssistant, host: str, port: int, account: str, remote_key: str | None
) -> None:
    """Connect to and authenticate with the panel, then release the connection.

    pydmp allows one connection per (host, port, account) at a time, so the test
    connection is always closed, whether or not it succeeded.
    """
    panel = PyDMPPanel(port=port)
    try:
        await panel.connect(host, account, remote_key or BLANK_REMOTE_KEY)
    finally:
        await panel.disconnect()


async def _async_connection_error(
    hass: HomeAssistant, data: Mapping[str, Any]
) -> str | None:
    """Test the panel settings in data; return the flow error key, or None."""
    try:
        await _async_validate_connection(
            hass,
            data[CONF_PANEL_IP],
            data.get(CONF_PANEL_REMOTE_PORT) or DEFAULT_PANEL_REMOTE_PORT,
            data[CONF_PANEL_ACCOUNT_NUMBER],
            data.get(CONF_PANEL_REMOTE_KEY),
        )
    except DMPAuthenticationError:
        return "invalid_auth"
    except (DMPConnectionError, OSError, TimeoutError):
        return "cannot_connect"
    except Exception:
        _LOGGER.exception("Unexpected error testing the DMP panel connection")
        return "unknown"
    return None


class DMPCustomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """DMP Custom config flow."""

    data: dict[str, Any]

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_PANEL_ACCOUNT_NUMBER])
            self._abort_if_unique_id_configured()
            if self._listen_port_in_use(user_input):
                errors[CONF_PANEL_LISTEN_PORT] = "listen_port_in_use"
            elif error := await _async_connection_error(self.hass, user_input):
                errors["base"] = error
            else:
                self.data = user_input
                self.data[CONF_ZONES] = []
                return await self.async_step_areas()
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                PANEL_SCHEMA,  # type: ignore[arg-type]
                user_input,
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication after the panel rejected the remote key."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the panel's current remote key and test it."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            remote_key = user_input.get(CONF_PANEL_REMOTE_KEY, "")
            if error := await _async_connection_error(
                self.hass, {**entry.data, CONF_PANEL_REMOTE_KEY: remote_key}
            ):
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PANEL_REMOTE_KEY: remote_key}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,  # type: ignore[arg-type]
            errors=errors,
            description_placeholders={"account": entry.data[CONF_PANEL_ACCOUNT_NUMBER]},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the panel connection settings of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_PANEL_ACCOUNT_NUMBER])
            self._abort_if_unique_id_mismatch()
            if self._listen_port_in_use(user_input, entry.entry_id):
                errors[CONF_PANEL_LISTEN_PORT] = "listen_port_in_use"
            elif error := await self._async_reconfigure_connection_error(
                entry, user_input
            ):
                errors["base"] = error
            else:
                # The key is optional: a cleared field is absent, not blank.
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        **user_input,
                        CONF_PANEL_REMOTE_KEY: user_input.get(
                            CONF_PANEL_REMOTE_KEY, ""
                        ),
                    },
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                PANEL_SCHEMA,  # type: ignore[arg-type]
                user_input or entry.data,
            ),
            errors=errors,
        )

    async def _async_reconfigure_connection_error(
        self, entry: config_entries.ConfigEntry, user_input: dict[str, Any]
    ) -> str | None:
        """Test new settings while the entry's own panel connection is released.

        The panel and pydmp each allow one connection per account, so a loaded
        entry would make the test fail. It is unloaded for the test; on failure it
        is set up again, on success the update reloads it.
        """
        loaded = entry.state is ConfigEntryState.LOADED
        if loaded:
            await self.hass.config_entries.async_unload(entry.entry_id)
        error = await _async_connection_error(self.hass, user_input)
        if error and loaded:
            await self.hass.config_entries.async_setup(entry.entry_id)
        return error

    @callback
    def _listen_port_in_use(
        self, user_input: Mapping[str, Any], entry_id: str | None = None
    ) -> bool:
        """Return True when another entry already listens on the requested port."""
        listen_port = user_input.get(CONF_PANEL_LISTEN_PORT)
        return any(
            entry.data.get(CONF_PANEL_LISTEN_PORT) == listen_port
            for entry in self._async_current_entries()
            if entry.entry_id != entry_id
        )

    async def async_step_areas(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if not _is_numeric(user_input[CONF_HOME_AREA]):
                errors[CONF_HOME_AREA] = "invalid_area_number"
            if not _is_numeric(user_input[CONF_AWAY_AREA]):
                errors[CONF_AWAY_AREA] = "invalid_area_number"
            if errors:
                return self.async_show_form(
                    step_id="areas",
                    data_schema=AREA_SCHEMA,  # type: ignore[arg-type]
                    errors=errors,
                )

            self.data[CONF_HOME_AREA] = user_input[CONF_HOME_AREA]
            self.data[CONF_AWAY_AREA] = user_input[CONF_AWAY_AREA]
            if user_input.get("add_another", False):
                return await self.async_step_areas()
            return await self.async_step_zones()
        return self.async_show_form(
            step_id="areas",
            data_schema=AREA_SCHEMA,  # type: ignore[arg-type]
            errors=errors,
        )

    async def async_step_zones(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if not _is_numeric(user_input[CONF_ZONE_NUMBER]):
                errors[CONF_ZONE_NUMBER] = "invalid_zone_number"
            if errors:
                return self.async_show_form(
                    step_id="zones",
                    data_schema=ZONE_SCHEMA,  # type: ignore[arg-type]
                    errors=errors,
                )

            self.data[CONF_ZONES].append(user_input)
            if user_input.get("add_another", False):
                return await self.async_step_zones()
            return self.async_create_entry(
                title=self.data[CONF_PANEL_NAME], data=self.data
            )
        return self.async_show_form(
            step_id="zones",
            data_schema=ZONE_SCHEMA,  # type: ignore[arg-type]
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handles options flow for the component."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options for the custom component."""
        errors: dict[str, str] = {}
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
            step_id="init",
            data_schema=options_schema,  # type: ignore[arg-type]
            errors=errors,
        )
