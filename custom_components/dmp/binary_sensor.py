"""Platform for DMP Alarm Panel integration"""
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
import logging
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.binary_sensor import (
    BinarySensorEntity
)
from .const import (DOMAIN, LISTENER, CONF_PANEL_ACCOUNT_NUMBER,
                    CONF_ZONE_NAME, CONF_ZONE_NUMBER, CONF_ZONE_CLASS,
                    CONF_ZONES)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities,):
    """Setup sensors from a config entry created in the integrations UI."""
    _LOGGER.debug("Setting up binary sensors.")
    hass.data.setdefault(DOMAIN, {})
    config = hass.data[DOMAIN][entry.entry_id]
    # if entry.options:
    #     config.update(entry.options)
    _LOGGER.debug("Binary sensor config: %s" % config)
    # Add all zones to trouble zones
    troubleZones = [
        DMPZoneTrouble(
            hass, zone,
            config.get(CONF_PANEL_ACCOUNT_NUMBER)
            )
        for zone in config[CONF_ZONES]
    ]
    # Only Windows and doors for Open/Close zones.
    openCloseZones = []
    for zone in config[CONF_ZONES]:
        if (
            "window" in zone[CONF_ZONE_CLASS]
            or "door" in zone[CONF_ZONE_CLASS]
        ):
            openCloseZones.append(
                DMPZoneOpenClose(
                    hass, zone,
                    config.get(CONF_PANEL_ACCOUNT_NUMBER)
                )
            )
    # Only battery zones
    batteryZones = []
    for zone in config[CONF_ZONES]:
        if ("battery" in zone[CONF_ZONE_CLASS]):
            batteryZones.append(
                DMPZoneBattery(
                    hass, zone,
                    config.get(CONF_PANEL_ACCOUNT_NUMBER)
                )
            )
    # Bypass and Alarm Zones should be the same
    bypassZones = []
    alarmZones = []
    for zone in config[CONF_ZONES]:
        if (
            "window" in zone[CONF_ZONE_CLASS]
            or "door" in zone[CONF_ZONE_CLASS]
            or "glassbreak" in zone[CONF_ZONE_CLASS]
            or "motion" in zone[CONF_ZONE_CLASS]
        ):
            alarmZones.append(
                DMPZoneAlarm(
                    hass, zone,
                    config.get(CONF_PANEL_ACCOUNT_NUMBER)
                )
            )
            bypassZones.append(
                DMPZoneBypass(
                    hass, zone,
                    config.get(CONF_PANEL_ACCOUNT_NUMBER)
                )
            )
    async_add_entities(openCloseZones, update_before_add=True)
    async_add_entities(batteryZones, update_before_add=True)
    async_add_entities(troubleZones, update_before_add=True)
    async_add_entities(bypassZones, update_before_add=True)
    async_add_entities(alarmZones, update_before_add=True)


class DMPZoneOpenClose(BinarySensorEntity):
    def __init__(self, hass, config, accountNum):
        self._hass = hass
        self._listener = self._hass.data[DOMAIN][LISTENER]
        self._name = "%s Open/Close" % config.get(CONF_ZONE_NAME)
        self._device_name = config.get(CONF_ZONE_NAME)
        self._number = config.get(CONF_ZONE_NUMBER)
        self._account_number = accountNum
        if "door" in config.get(CONF_ZONE_CLASS):
            self._device_class = "door"
        elif "window" in config.get(CONF_ZONE_CLASS):
            self._device_class = "window"
        self._panel = self._listener.getPanels()[str(self._account_number)]
        self._state = False
        zoneOpenCloseObj = {
            "zoneName": self._device_name,
            "zoneNumber": str(self._number),
            "zoneState": self._state
            }
        self._panel.updateOpenCloseZone(str(self._number), zoneOpenCloseObj)

    async def async_added_to_hass(self):
        _LOGGER.debug("Registering DMPZoneOpenClose Callback")
        self._listener.register_callback(self.process_zone_callback)

    async def async_will_remove_from_hass(self):
        device_registry = dr.async_get(self._hass)
        _LOGGER.debug("Device Registry %s" % device_registry)
        device_registry.async_remove_device(self.device_info.identifiers[0])
        _LOGGER.debug("Removing DMPZoneOpenClose Callback")
        self._listener.remove_callback(self.process_zone_callback)

    async def process_zone_callback(self):
        _LOGGER.debug("DMPZoneOpenClose Callback Executed")
        self._state = self._panel.getOpenCloseZone(self._number)["zoneState"]
        self.async_write_ha_state()

    @property
    def device_name(self):
        """Return the name of the device."""
        return self._device_name

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def is_on(self):
        """Return the state of the device."""
        _LOGGER.debug("Called DMPZoneOpenClose.is_on: {}".format(self._state))
        return self._state

    @property
    def device_class(self):
        """Return the class of the device"""
        _LOGGER.debug("Called DMPZoneOpenClose.device_class: {}"
                      .format(self._device_class))
        return self._device_class

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "last_contact": self._panel.getContactTime(),
        }

    @property
    def unique_id(self):
        """Return unique ID"""
        return "dmp-%s-zone-%s-openclose" % (self._account_number,
                                             self._number)

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, "dmp-%s-zone-%s" % (self._account_number,
                                             self._number))
            },
            name=self.name,
            manufacturer='Digital Monitoring Products',
            via_device=(DOMAIN, "dmp-%s-panel" % (self._account_number))
        )


class DMPZoneBattery(BinarySensorEntity):
    def __init__(self, hass, config, accountNum):
        self._hass = hass
        self._listener = self._hass.data[DOMAIN][LISTENER]
        self._device_name = config.get(CONF_ZONE_NAME)
        self._name = "%s Battery" % config.get(CONF_ZONE_NAME)
        self._number = config.get(CONF_ZONE_NUMBER)
        self._account_number = accountNum
        self._device_class = "battery"
        self._panel = self._listener.getPanels()[str(self._account_number)]
        self._state = False
        zoneBatteryObj = {
            "zoneName": self._device_name,
            "zoneNumber": str(self._number),
            "zoneState": self._state
            }
        self._panel.updateBatteryZone(str(self._number), zoneBatteryObj)

    async def async_added_to_hass(self):
        _LOGGER.debug("Registering DMPZoneBattery Callback")
        self._listener.register_callback(self.process_zone_callback)

    async def async_will_remove_from_hass(self):
        _LOGGER.debug("Removing DMPZoneBattery Callback")
        self._listener.remove_callback(self.process_zone_callback)

    async def process_zone_callback(self):
        _LOGGER.debug("DMPZoneBattery Callback Executed")
        self._state = self._panel.getBatteryZone(self._number)["zoneState"]
        self.async_write_ha_state()

    @property
    def device_name(self):
        """Return the name of the device."""
        return self._device_name

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def is_on(self):
        """Return the state of the device."""
        _LOGGER.debug("Called DMPZoneBattery.is_on: {}".format(self._state))
        return self._state

    @property
    def device_class(self):
        """Return the class of the device"""
        _LOGGER.debug("Called DMPZoneBattery.device_class: {}"
                      .format(self._device_class))
        return self._device_class

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "last_contact": self._panel.getContactTime(),
        }

    @property
    def unique_id(self):
        """Return unique ID"""
        return "dmp-%s-zone-%s-battery" % (
            self._account_number,
            self._number
            )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, "dmp-%s-zone-%s" % (self._account_number,
                                             self._number))
            },
            name=self.name,
            manufacturer='Digital Monitoring Products',
            via_device=(DOMAIN, "dmp-%s-panel" % (self._account_number))
        )


class DMPZoneTrouble(BinarySensorEntity):
    def __init__(self, hass, config, accountNum):
        self._hass = hass
        self._listener = self._hass.data[DOMAIN][LISTENER]
        self._device_name = config.get(CONF_ZONE_NAME)
        self._name = "%s Trouble" % config.get(CONF_ZONE_NAME)
        self._number = config.get(CONF_ZONE_NUMBER)
        self._account_number = accountNum
        self._device_class = "problem"
        self._panel = self._listener.getPanels()[str(self._account_number)]
        self._state = False
        zoneTroubleObj = {
            "zoneName": self._device_name,
            "zoneNumber": str(self._number),
            "zoneState": self._state
            }
        self._panel.updateTroubleZone(str(self._number), zoneTroubleObj)

    async def async_added_to_hass(self):
        _LOGGER.debug("Registering DMPZoneTrouble Callback")
        self._listener.register_callback(self.process_zone_callback)

    async def async_will_remove_from_hass(self):
        _LOGGER.debug("Removing DMPZoneTrouble Callback")
        self._listener.remove_callback(self.process_zone_callback)

    async def process_zone_callback(self):
        _LOGGER.debug("DMPZoneTrouble Callback Executed")
        self._state = self._panel.getTroubleZone(self._number)["zoneState"]
        self.async_write_ha_state()

    @property
    def device_name(self):
        """Return the name of the device."""
        return self._device_name

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def is_on(self):
        """Return the state of the device."""
        _LOGGER.debug("Called DMPTroubleZone.is_on: {}".format(self._state))
        return self._state

    @property
    def device_class(self):
        """Return the class of the device"""
        _LOGGER.debug("Called DMPTrouble.device_class: {}"
                      .format(self._device_class))
        return self._device_class

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "last_contact": self._panel.getContactTime(),
        }

    @property
    def unique_id(self):
        """Return unique ID"""
        return "dmp-%s-zone-%s-trouble" % (
            self._account_number,
            self._number
            )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, "dmp-%s-zone-%s" % (self._account_number,
                                             self._number))
            },
            name=self.name,
            manufacturer='Digital Monitoring Products',
            via_device=(DOMAIN, "dmp-%s-panel" % (self._account_number))
        )


class DMPZoneBypass(BinarySensorEntity):
    def __init__(self, hass, config, accountNum):
        self._hass = hass
        self._listener = self._hass.data[DOMAIN][LISTENER]
        self._device_name = config.get(CONF_ZONE_NAME)
        self._name = "%s Bypass" % config.get(CONF_ZONE_NAME)
        self._number = config.get(CONF_ZONE_NUMBER)
        self._account_number = accountNum
        self._device_class = "problem"
        self._panel = self._listener.getPanels()[str(self._account_number)]
        self._state = False
        zoneBypassObj = {
            "zoneName": self._device_name,
            "zoneNumber": str(self._number),
            "zoneState": self._state
            }
        self._panel.updateBypassZone(str(self._number), zoneBypassObj)

    async def async_added_to_hass(self):
        _LOGGER.debug("Registering DMPZoneBypass Callback")
        self._listener.register_callback(self.process_zone_callback)

    async def async_will_remove_from_hass(self):
        _LOGGER.debug("Removing DMPZoneBypass Callback")
        self._listener.remove_callback(self.process_zone_callback)

    async def process_zone_callback(self):
        _LOGGER.debug("DMPZoneBypass Callback Executed")
        self._state = self._panel.getBypassZone(self._number)["zoneState"]
        self.async_write_ha_state()

    @property
    def device_name(self):
        """Return the name of the device."""
        return self._device_name

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def is_on(self):
        """Return the state of the device."""
        _LOGGER.debug("Called DMPZoneBypass.is_on: {}".format(self._state))
        return self._state

    @property
    def device_class(self):
        """Return the class of the device"""
        _LOGGER.debug("Called DMPZoneBypass.device_class: {}"
                      .format(self._device_class))
        return self._device_class

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "last_contact": self._panel.getContactTime(),
        }

    @property
    def unique_id(self):
        """Return unique ID"""
        return "dmp-%s-zone-%s-bypass" % (
            self._account_number,
            self._number
            )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, "dmp-%s-zone-%s" % (self._account_number,
                                             self._number))
            },
            name=self.name,
            manufacturer='Digital Monitoring Products',
            via_device=(DOMAIN, "dmp-%s-panel" % (self._account_number))
        )


class DMPZoneAlarm(BinarySensorEntity):
    def __init__(self, hass, config, accountNum):
        self._hass = hass
        self._listener = self._hass.data[DOMAIN][LISTENER]
        self._device_name = config.get(CONF_ZONE_NAME)
        self._name = "%s Alarm" % config.get(CONF_ZONE_NAME)
        self._number = config.get(CONF_ZONE_NUMBER)
        self._account_number = accountNum
        self._device_class = "problem"
        self._panel = self._listener.getPanels()[str(self._account_number)]
        self._state = False
        zoneAlarmObj = {
            "zoneName": self._device_name,
            "zoneNumber": str(self._number),
            "zoneState": self._state
            }
        self._panel.updateAlarmZone(str(self._number), zoneAlarmObj)

    async def async_added_to_hass(self):
        _LOGGER.debug("Registering DMPZoneAlarm Callback")
        self._listener.register_callback(self.process_zone_callback)

    async def async_will_remove_from_hass(self):
        _LOGGER.debug("Removing DMPZoneAlarm Callback")
        self._listener.remove_callback(self.process_zone_callback)

    async def process_zone_callback(self):
        _LOGGER.debug("DMPZoneAlarm Callback Executed")
        self._state = self._panel.getAlarmZone(self._number)["zoneState"]
        self.async_write_ha_state()

    @property
    def device_name(self):
        """Return the name of the device."""
        return self._device_name

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def is_on(self):
        """Return the state of the device."""
        _LOGGER.debug("Called DMPZoneAlarm.is_on: {}".format(self._state))
        return self._state

    @property
    def device_class(self):
        """Return the class of the device"""
        _LOGGER.debug("Called DMPZoneAlarm.device_class: {}"
                      .format(self._device_class))
        return self._device_class

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "last_contact": self._panel.getContactTime(),
        }

    @property
    def unique_id(self):
        """Return unique ID"""
        return "dmp-%s-zone-%s-alarm" % (
            self._account_number,
            self._number
            )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, "dmp-%s-zone-%s" % (self._account_number,
                                             self._number))
            },
            name=self.device_name,
            manufacturer='Digital Monitoring Products',
            via_device=(DOMAIN, "dmp-%s-panel" % (self._account_number))
        )
