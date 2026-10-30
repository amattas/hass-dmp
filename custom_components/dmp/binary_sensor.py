"""Platform for DMP Alarm Panel integration"""

import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.binary_sensor.const import BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DMPListener
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


def _device_class(name: str) -> BinarySensorDeviceClass | None:
    """Map a zone's device class name to Home Assistant's (None when unknown)."""
    try:
        return BinarySensorDeviceClass(name)
    except ValueError:
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup sensors from a config entry created in the integrations UI."""
    _LOGGER.debug("Setting up binary sensors.")
    hass.data.setdefault(DOMAIN, {})
    config = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.debug(f"Binary sensor config: {config}")
    # Add all zones to trouble zones
    troubleZones = [
        DMPZoneTrouble(hass, config_entry, zone) for zone in config[CONF_ZONES]
    ]
    openCloseZones: list[DMPZoneOpenClose] = []
    for zone in config[CONF_ZONES]:
        if (
            "window" in zone[CONF_ZONE_CLASS]
            or "door" in zone[CONF_ZONE_CLASS]
            or "motion" in zone[CONF_ZONE_CLASS]
            or "default" in zone[CONF_ZONE_CLASS]
        ):
            openCloseZones.append(DMPZoneOpenClose(hass, config_entry, zone))
    # Only battery zones
    batteryZones: list[DMPZoneBattery] = []
    for zone in config[CONF_ZONES]:
        if "battery" in zone[CONF_ZONE_CLASS]:
            batteryZones.append(DMPZoneBattery(hass, config_entry, zone))
    # Bypass and Alarm Zones should be the same
    bypassZones: list[DMPZoneBypass] = []
    alarmZones: list[DMPZoneAlarm] = []
    for zone in config[CONF_ZONES]:
        if (
            "window" in zone[CONF_ZONE_CLASS]
            or "door" in zone[CONF_ZONE_CLASS]
            or "glassbreak" in zone[CONF_ZONE_CLASS]
            or "motion" in zone[CONF_ZONE_CLASS]
        ):
            alarmZones.append(DMPZoneAlarm(hass, config_entry, zone))
            bypassZones.append(DMPZoneBypass(hass, config_entry, zone))
    # Don't update before add or you have a race condition with the
    # status zone.
    async_add_entities(openCloseZones, update_before_add=False)
    async_add_entities(batteryZones, update_before_add=False)
    async_add_entities(troubleZones, update_before_add=False)
    async_add_entities(alarmZones, update_before_add=False)


class DMPZoneOpenClose(BinarySensorEntity):
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
        self._name = entity_config.get(CONF_ZONE_NAME)
        self._device_name: str | None = entity_config.get(CONF_ZONE_NAME)
        self._number: str = entity_config.get(CONF_ZONE_NUMBER, "")
        zone_class: str = entity_config.get(CONF_ZONE_CLASS) or ""
        if "door" in zone_class:
            self._device_class = "door"
        elif "window" in zone_class:
            self._device_class = "window"
        elif "motion" in zone_class:
            self._device_class = "motion"
        else:
            self._device_class = "sensors"
        self._panel = self._listener.getPanels()[str(self._accountNum)]
        self._zone = self._panel.ensure_zone(self._number)
        self._state = False

    async def async_added_to_hass(self) -> None:
        _LOGGER.debug("Registering DMPZoneOpenClose Callback")
        self._listener.register_callback(self.process_zone_callback)

    async def async_will_remove_from_hass(self) -> None:
        _LOGGER.debug("Removing DMPZoneOpenClose Callback")
        self._listener.remove_callback(self.process_zone_callback)

    async def process_zone_callback(self) -> None:
        self._state = self._zone is not None and self._zone.is_open
        self.async_write_ha_state()

    @property
    def device_name(self) -> str | None:
        """Return the name of the device."""
        return self._device_name

    @property
    def name(self) -> str | None:
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self) -> bool:
        """Return the polling state."""
        return False

    @property
    def is_on(self) -> bool:
        """Return the state of the device."""
        return self._state

    @property
    def icon(self) -> str | None:
        """Icon to show for status"""
        state = self.is_on
        device_class = self._device_class
        if state:
            if device_class == "window":
                return "mdi:window-open"
            elif device_class == "motion":
                return "mdi:motion-sensor"
            else:
                return "mdi:door-open"
        else:
            if device_class == "window":
                return "mdi:window-closed"
            elif device_class == "motion":
                return "mdi:motion-sensor-off"
            else:
                return "mdi:door-closed"

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return the class of the device"""
        return _device_class(self._device_class)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {"last_contact": self._panel.getContactTime()}

    @property
    def unique_id(self) -> str:
        """Return unique ID"""
        return f"dmp-{self._accountNum}-zone-{self._number}-openclose"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"dmp-{self._accountNum}-zone-{self._number}")},
            name=self.name,
            manufacturer="Digital Monitoring Products",
            # HA 2026.8 deprecated via_device for via_device_id (removal in 2027.8)
            via_device=(DOMAIN, f"dmp-{self._accountNum}-panel"),  # type: ignore[typeddict-unknown-key]
        )


class DMPZoneBattery(BinarySensorEntity):
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
        self._name = f"{entity_config.get(CONF_ZONE_NAME)} Battery"
        self._number: str = entity_config.get(CONF_ZONE_NUMBER, "")
        self._device_class = "battery"
        self._panel = self._listener.getPanels()[str(self._accountNum)]
        self._zone = self._panel.ensure_zone(self._number)
        self._state = False

    async def async_added_to_hass(self) -> None:
        _LOGGER.debug("Registering DMPZoneBattery Callback")
        self._listener.register_callback(self.process_zone_callback)

    async def async_will_remove_from_hass(self) -> None:
        _LOGGER.debug("Removing DMPZoneBattery Callback")
        self._listener.remove_callback(self.process_zone_callback)

    async def process_zone_callback(self) -> None:
        self._state = self._zone is not None and self._zone.state == "L"
        self.async_write_ha_state()

    @property
    def device_name(self) -> str | None:
        """Return the name of the device."""
        return self._device_name

    @property
    def name(self) -> str | None:
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self) -> bool:
        """Return the polling state."""
        return False

    @property
    def is_on(self) -> bool:
        """Return the state of the device."""
        return self._state

    @property
    def icon(self) -> str | None:
        """Icon to show for status"""
        state = self.is_on
        if state:
            return "mdi:battery-alert-variant-outline"
        else:
            return "mdi:battery"

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return the class of the device"""
        return _device_class(self._device_class)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "last_contact": self._panel.getContactTime(),
        }

    @property
    def unique_id(self) -> str:
        """Return unique ID"""
        return f"dmp-{self._accountNum}-zone-{self._number}-battery"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"dmp-{self._accountNum}-zone-{self._number}")},
            name=self.name,
            manufacturer="Digital Monitoring Products",
            # HA 2026.8 deprecated via_device for via_device_id (removal in 2027.8)
            via_device=(DOMAIN, f"dmp-{self._accountNum}-panel"),  # type: ignore[typeddict-unknown-key]
        )


class DMPZoneTrouble(BinarySensorEntity):
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
        self._name = f"{entity_config.get(CONF_ZONE_NAME)} Trouble"
        self._number: str = entity_config.get(CONF_ZONE_NUMBER, "")
        self._device_class = "problem"
        self._panel = self._listener.getPanels()[str(self._accountNum)]
        self._zone = self._panel.ensure_zone(self._number)
        self._state = False

    async def async_added_to_hass(self) -> None:
        _LOGGER.debug("Registering DMPZoneTrouble Callback")
        self._listener.register_callback(self.process_zone_callback)

    async def async_will_remove_from_hass(self) -> None:
        _LOGGER.debug("Removing DMPZoneTrouble Callback")
        self._listener.remove_callback(self.process_zone_callback)

    async def process_zone_callback(self) -> None:
        self._state = self._zone is not None and self._zone.has_fault
        self.async_write_ha_state()

    @property
    def device_name(self) -> str | None:
        """Return the name of the device."""
        return self._device_name

    @property
    def name(self) -> str | None:
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self) -> bool:
        """Return the polling state."""
        return False

    @property
    def is_on(self) -> bool:
        """Return the state of the device."""
        return self._state

    @property
    def icon(self) -> str | None:
        """Icon to show for status"""
        state = self.is_on
        if state:
            return "mdi:alert-outline"
        else:
            return "mdi:check"

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return the class of the device"""
        return _device_class(self._device_class)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "last_contact": self._panel.getContactTime(),
        }

    @property
    def unique_id(self) -> str:
        """Return unique ID"""
        return f"dmp-{self._accountNum}-zone-{self._number}-trouble"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"dmp-{self._accountNum}-zone-{self._number}")},
            name=self.name,
            manufacturer="Digital Monitoring Products",
            # HA 2026.8 deprecated via_device for via_device_id (removal in 2027.8)
            via_device=(DOMAIN, f"dmp-{self._accountNum}-panel"),  # type: ignore[typeddict-unknown-key]
        )


class DMPZoneBypass(BinarySensorEntity):
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
        self._device_class = "problem"
        self._panel = self._listener.getPanels()[str(self._accountNum)]
        self._zone = self._panel.ensure_zone(self._number)
        self._state = False

    async def async_added_to_hass(self) -> None:
        _LOGGER.debug("Registering DMPZoneBypass Callback")
        self._listener.register_callback(self.process_zone_callback)

    async def async_will_remove_from_hass(self) -> None:
        _LOGGER.debug("Removing DMPZoneBypass Callback")
        self._listener.remove_callback(self.process_zone_callback)

    async def process_zone_callback(self) -> None:
        self._state = self._zone is not None and self._zone.is_bypassed
        self.async_write_ha_state()

    @property
    def device_name(self) -> str | None:
        """Return the name of the device."""
        return self._device_name

    @property
    def name(self) -> str | None:
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self) -> bool:
        """Return the polling state."""
        return False

    @property
    def is_on(self) -> bool:
        """Return the state of the device."""
        return self._state

    @property
    def icon(self) -> str | None:
        """Icon to show for status"""
        state = self.is_on
        if state:
            return "mdi:alert-outline"
        else:
            return "mdi:check"

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return the class of the device"""
        return _device_class(self._device_class)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "last_contact": self._panel.getContactTime(),
        }

    @property
    def unique_id(self) -> str:
        """Return unique ID"""
        return f"dmp-{self._accountNum}-zone-{self._number}-bypass"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"dmp-{self._accountNum}-zone-{self._number}")},
            name=self.name,
            manufacturer="Digital Monitoring Products",
            # HA 2026.8 deprecated via_device for via_device_id (removal in 2027.8)
            via_device=(DOMAIN, f"dmp-{self._accountNum}-panel"),  # type: ignore[typeddict-unknown-key]
        )


class DMPZoneAlarm(BinarySensorEntity):
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
        self._name = f"{entity_config.get(CONF_ZONE_NAME)} Alarm"
        self._number: str = entity_config.get(CONF_ZONE_NUMBER, "")
        self._device_class = "problem"
        self._panel = self._listener.getPanels()[str(self._accountNum)]
        self._state = False

    async def async_added_to_hass(self) -> None:
        _LOGGER.debug("Registering DMPZoneAlarm Callback")
        self._listener.register_callback(self.process_zone_callback)

    async def async_will_remove_from_hass(self) -> None:
        _LOGGER.debug("Removing DMPZoneAlarm Callback")
        self._listener.remove_callback(self.process_zone_callback)

    async def process_zone_callback(self) -> None:
        self._state = self._panel.get_alarm(self._number)
        self.async_write_ha_state()

    @property
    def device_name(self) -> str | None:
        """Return the name of the device."""
        return self._device_name

    @property
    def name(self) -> str | None:
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self) -> bool:
        """Return the polling state."""
        return False

    @property
    def is_on(self) -> bool:
        """Return the state of the device."""
        return self._state

    @property
    def icon(self) -> str | None:
        """Icon to show for status"""
        state = self.is_on
        if state:
            return "mdi:alarm-bell"
        else:
            return "mdi:check"

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return the class of the device"""
        return _device_class(self._device_class)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "last_contact": self._panel.getContactTime(),
        }

    @property
    def unique_id(self) -> str:
        """Return unique ID"""
        return f"dmp-{self._accountNum}-zone-{self._number}-alarm"

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
