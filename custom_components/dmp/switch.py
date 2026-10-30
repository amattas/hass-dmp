from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import (  # type: ignore[attr-defined]  # HA 2024.11 has no SwitchDeviceClass in switch.const
    SwitchDeviceClass,
    SwitchEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DMPListener
from .const import (
    CONF_PANEL_ACCOUNT_NUMBER,
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
    _LOGGER.debug("Setting up bypass switches")
    hass.data.setdefault(DOMAIN, {})
    config = hass.data[DOMAIN][config_entry.entry_id]
    # broken out from binary_sensor
    bypassZones: list[DMPZoneBypassSwitch] = []
    for zone in config[CONF_ZONES]:
        # allow all zones to be bypassed
        bypassZones.append(DMPZoneBypassSwitch(hass, config_entry, zone))
    # Don't update before add or you have a race condition with the
    # status zone.
    async_add_entities(bypassZones, update_before_add=False)


class DMPZoneBypassSwitch(SwitchEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        entity_config: dict[str, Any],
    ) -> None:
        self._hass = hass
        self._config_entry = config_entry
        config = hass.data[DOMAIN][config_entry.entry_id]
        self._accountNum: str | None = config.get(CONF_PANEL_ACCOUNT_NUMBER)
        self._listener: DMPListener = self._hass.data[DOMAIN][LISTENER]
        self._device_name: str | None = entity_config.get(CONF_ZONE_NAME)
        self._name = f"{entity_config.get(CONF_ZONE_NAME)} Bypass"
        self._number: str = entity_config.get(CONF_ZONE_NUMBER, "")
        self._device_class = SwitchDeviceClass.SWITCH
        self._panel = self._listener.getPanels()[str(self._accountNum)]
        self._zone = self._panel.ensure_zone(self._number)
        self._state = False

    async def async_added_to_hass(self) -> None:
        _LOGGER.debug("Registering DMPZoneBypassSwitch Callback")
        self._listener.register_callback(self.process_zone_callback)

    async def async_will_remove_from_hass(self) -> None:
        _LOGGER.debug("Removing DMPZoneBypassSwitch Callback")
        self._listener.remove_callback(self.process_zone_callback)

    async def process_zone_callback(self) -> None:
        self._state = self._zone is not None and self._zone.is_bypassed
        self.async_write_ha_state()

    @property
    def device_name(self) -> str | None:
        return self._device_name

    @property
    def name(self) -> str | None:
        return self._name

    @property
    def is_on(self) -> bool:
        return self._state

    @property
    def device_class(self) -> SwitchDeviceClass:
        """Return the class of the device"""
        return self._device_class

    @property
    def unique_id(self) -> str:
        return f"dmp-{self._accountNum}-zone-{self._number}-bypass-switch"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"dmp-{self._accountNum}-zone-{self._number}")},
            # HA 2026.8 deprecated via_device for via_device_id (removal in 2027.8)
            via_device=(DOMAIN, f"dmp-{self._accountNum}-panel"),  # type: ignore[typeddict-unknown-key]
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._panel.bypass_zone(self._number)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._panel.restore_zone(self._number)
