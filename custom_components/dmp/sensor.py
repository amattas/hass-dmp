"""Platform for DMP Alarm Panel integration"""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ZONE_STATE_TO_STATUS, DMPConfigEntry, DMPListener, DMPPanel
from .const import CONF_PANEL_ACCOUNT_NUMBER, CONF_ZONES
from .entity import DMPZoneEntity

PARALLEL_UPDATES = 0

STATUS_OPTIONS = ["ready", "open", "trouble", "bypass", "low_battery", "alarm"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DMPConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a status sensor for every zone from a config entry."""
    data = config_entry.runtime_data
    account = data.config[CONF_PANEL_ACCOUNT_NUMBER]
    async_add_entities(
        DMPZoneStatus(data.listener, data.panel, account, zone)
        for zone in data.config[CONF_ZONES]
    )


class DMPZoneStatus(DMPZoneEntity, SensorEntity):
    """Rollup of a zone's state: ready, open, trouble, bypass, low battery, alarm."""

    _attr_translation_key = "status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUS_OPTIONS
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        listener: DMPListener,
        panel: DMPPanel,
        account: str,
        config: dict[str, Any],
    ) -> None:
        super().__init__(listener, panel, account, config)
        self._attr_unique_id = self._unique_id("status")

    @callback
    def _update_from_panel(self) -> None:
        if self._panel.get_alarm(self._number):
            self._attr_native_value = "alarm"
        else:
            zone_state = self._zone.state if self._zone else "N"
            self._attr_native_value = ZONE_STATE_TO_STATUS.get(zone_state, "ready")
