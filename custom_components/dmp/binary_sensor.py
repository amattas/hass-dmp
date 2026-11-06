"""Platform for DMP Alarm Panel integration"""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (  # type: ignore[attr-defined]  # HA 2024.11 has no binary_sensor.const
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DMPConfigEntry, DMPListener, DMPPanel
from .const import CONF_PANEL_ACCOUNT_NUMBER, CONF_ZONE_CLASS, CONF_ZONES
from .entity import DMPZoneEntity

PARALLEL_UPDATES = 0

# Open/close sensor translation key (also its icon set) and device class,
# by the device type named in the zone class.
OPEN_CLOSE_TYPES: dict[str, tuple[str, BinarySensorDeviceClass | None]] = {
    "door": ("door", BinarySensorDeviceClass.DOOR),
    "window": ("window", BinarySensorDeviceClass.WINDOW),
    "motion": ("motion", BinarySensorDeviceClass.MOTION),
    "default": ("open_close", None),
}

# Zone device types that can trip an alarm
ALARM_TYPES = ("door", "window", "motion", "glassbreak")


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DMPConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up zone binary sensors from a config entry."""
    data = config_entry.runtime_data
    account = data.config[CONF_PANEL_ACCOUNT_NUMBER]
    entities: list[DMPZoneEntity] = []
    for zone in data.config[CONF_ZONES]:
        zone_class: str = zone[CONF_ZONE_CLASS]
        args = (data.listener, data.panel, account, zone)
        if any(t in zone_class for t in OPEN_CLOSE_TYPES):
            entities.append(DMPZoneOpenClose(*args))
        if "battery" in zone_class:
            entities.append(DMPZoneBattery(*args))
        entities.append(DMPZoneTrouble(*args))
        if any(t in zone_class for t in ALARM_TYPES):
            entities.append(DMPZoneAlarm(*args))
    async_add_entities(entities)


class DMPZoneOpenClose(DMPZoneEntity, BinarySensorEntity):
    """Whether the zone is open; the zone device's primary entity."""

    _attr_name = None

    def __init__(
        self,
        listener: DMPListener,
        panel: DMPPanel,
        account: str,
        config: dict[str, Any],
    ) -> None:
        super().__init__(listener, panel, account, config)
        self._attr_unique_id = self._unique_id("openclose")
        zone_class: str = config[CONF_ZONE_CLASS]
        device_type = next(t for t in OPEN_CLOSE_TYPES if t in zone_class)
        self._attr_translation_key, self._attr_device_class = OPEN_CLOSE_TYPES[
            device_type
        ]

    @callback
    def _update_from_panel(self) -> None:
        self._attr_is_on = self._zone is not None and self._zone.is_open


class DMPZoneBattery(DMPZoneEntity, BinarySensorEntity):
    """Whether a wireless zone reports a low battery."""

    _attr_translation_key = "battery"
    _attr_device_class = BinarySensorDeviceClass.BATTERY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        listener: DMPListener,
        panel: DMPPanel,
        account: str,
        config: dict[str, Any],
    ) -> None:
        super().__init__(listener, panel, account, config)
        self._attr_unique_id = self._unique_id("battery")

    @callback
    def _update_from_panel(self) -> None:
        self._attr_is_on = self._zone is not None and self._zone.state == "L"


class DMPZoneTrouble(DMPZoneEntity, BinarySensorEntity):
    """Whether the zone reports a fault (short, missing, low battery)."""

    _attr_translation_key = "trouble"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
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
        self._attr_unique_id = self._unique_id("trouble")

    @callback
    def _update_from_panel(self) -> None:
        self._attr_is_on = self._zone is not None and self._zone.has_fault


class DMPZoneAlarm(DMPZoneEntity, BinarySensorEntity):
    """Whether the zone is in alarm."""

    _attr_translation_key = "alarm"
    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(
        self,
        listener: DMPListener,
        panel: DMPPanel,
        account: str,
        config: dict[str, Any],
    ) -> None:
        super().__init__(listener, panel, account, config)
        self._attr_unique_id = self._unique_id("alarm")

    @callback
    def _update_from_panel(self) -> None:
        self._attr_is_on = self._panel.get_alarm(self._number)
