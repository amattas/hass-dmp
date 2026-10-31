"""Platform for DMP Alarm Panel integration"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ZONE_STATE_TO_STATUS, DMPListener
from .const import (
    CONF_PANEL_ACCOUNT_NUMBER,
    CONF_ZONE_CLASS,
    CONF_ZONE_NAME,
    CONF_ZONE_NUMBER,
    CONF_ZONES,
    DOMAIN,
    LISTENER,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup sensors from a config entry created in the integrations UI."""
    _LOGGER.debug("Setting up sensors.")
    hass.data.setdefault(DOMAIN, {})
    config = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.debug(f"Sensor config: {config}")
    # Add all zones to trouble zones
    statusZones = [
        DMPZoneStatus(hass, config_entry, zone) for zone in config[CONF_ZONES]
    ]
    async_add_entities(statusZones, update_before_add=True)


class DMPZoneStatus(SensorEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        entity_config: dict[str, Any],
    ) -> None:
        self._hass = hass
        self._config_entry = config_entry
        config = hass.data[DOMAIN][config_entry.entry_id]
        _LOGGER.debug(f"Config is: {entity_config}")
        self._accountNum: str | None = config.get(CONF_PANEL_ACCOUNT_NUMBER)
        self._listener: DMPListener = self._hass.data[DOMAIN][LISTENER]
        self._name = f"{entity_config.get(CONF_ZONE_NAME)} Status"
        self._device_name: str | None = entity_config.get(CONF_ZONE_NAME)
        self._number: str = entity_config.get(CONF_ZONE_NUMBER, "")
        self._panel = self._listener.getPanels()[str(self._accountNum)]
        zone_class: str = entity_config.get(CONF_ZONE_CLASS) or ""
        if "door" in zone_class:
            self._device_class = "door"
        elif "window" in zone_class:
            self._device_class = "window"
        elif "motion" in zone_class:
            self._device_class = "motion"
        else:
            self._device_class = "default"
        self._zone = self._panel.ensure_zone(self._number)
        self._state = "Ready"

    async def async_added_to_hass(self) -> None:
        _LOGGER.debug("Registering DMPZoneStatus Callback")
        self._listener.register_callback(self.process_zone_callback)

    async def async_will_remove_from_hass(self) -> None:
        _LOGGER.debug("Removing DMPZoneStatus Callback")
        self._listener.remove_callback(self.process_zone_callback)
        # Removing linked device, since all zones have a status sensor this
        # is the most logical place to execute this code.
        device_registry = dr.async_get(self._hass)
        device_identifiers = list(self.device_info["identifiers"])
        entity_devices = dr.async_entries_for_config_entry(
            device_registry, self._config_entry.entry_id
        )
        for e in entity_devices:
            for i in e.identifiers:
                if i in device_identifiers:
                    device_registry.async_remove_device(e.id)
        # for i in device_identifiers:
        # item = device_registry.async_get_device(i)

    async def process_zone_callback(self) -> None:
        if self._panel.get_alarm(self._number):
            self._state = "Alarm"
        else:
            zone_state = self._zone.state if self._zone else "N"
            self._state = ZONE_STATE_TO_STATUS.get(zone_state, "Ready")
        self.async_write_ha_state()

    @property
    def device_name(self) -> str | None:
        """Return the name of the device."""
        return self._device_name

    @property
    def native_value(self) -> str:
        """Return the zone status (Ready, Open, Alarm, ...)."""
        return self._state

    @property
    def name(self) -> str | None:
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self) -> bool:
        """Return the polling state."""
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "last_contact": self._panel.getContactTime(),
        }

    @property
    def icon(self) -> str | None:
        """Icon to show for status"""
        state = self.state
        device_class = self._device_class
        if state == "Alarm":
            return "mdi:alarm-bell"
        elif state == "Trouble" or state == "Bypass":
            return "mdi:alert"
        elif state == "Low Battery":
            return "mdi:battery-alert-variant-outline"
        elif state == "Open":
            if device_class == "window":
                return "mdi:window-open"
            else:
                return "mdi:door-open"
        elif state == "Ready":
            return "mdi:check"
        return None

    @property
    def unique_id(self) -> str:
        """Return unique ID"""
        return f"dmp-{self._accountNum}-zone-{self._number}-status"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"dmp-{self._accountNum}-zone-{self._number}")},
            name=self.device_name,
            manufacturer="Digital Monitoring Products",
            # HA 2026.8 deprecated via_device for via_device_id (removal in 2027.8)
            via_device=(DOMAIN, f"dmp-{self._accountNum}-panel"),  # type: ignore[typeddict-unknown-key]
        )
