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


async def async_setup_entry(hass, config_entry, async_add_entities,):
    """Setup sensors from a config entry created in the integrations UI."""
    _LOGGER.debug("Setting up binary sensors.")
    hass.data.setdefault(DOMAIN, {})
    config = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.debug("Binary sensor config: %s" % config)
    # Add all zones to trouble zones
    troubleZones = [
        DMPZoneTrouble(
            hass, config_entry, zone
            )
        for zone in config[CONF_ZONES]
    ]
    openCloseZones = []
    for zone in config[CONF_ZONES]:
        if (
            "window" in zone[CONF_ZONE_CLASS]
            or "door" in zone[CONF_ZONE_CLASS]
            or "default" in zone[CONF_ZONE_CLASS]
        ):
            openCloseZones.append(
                DMPZoneOpenClose(
                    hass, config_entry, zone
                )
            )
    # Only battery zones
    batteryZones = []
    for zone in config[CONF_ZONES]:
        if ("battery" in zone[CONF_ZONE_CLASS]):
            batteryZones.append(
                DMPZoneBattery(
                    hass, config_entry, zone
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
                    hass, config_entry, zone
                )
            )
            bypassZones.append(
                DMPZoneBypass(
                    hass, config_entry, zone
                )
            )
    # Don't update before add or you have a race condition with the
    # status zone.
    async_add_entities(openCloseZones, update_before_add=False)
    async_add_entities(batteryZones, update_before_add=False)
    async_add_entities(troubleZones, update_before_add=False)
    # using bypass switch instead 
    # async_add_entities(bypassZones, update_before_add=False)
    async_add_entities(alarmZones, update_before_add=False)


class DMPZoneOpenClose(BinarySensorEntity):
    def __init__(self, hass, config_entry, entity_config):
        self._hass = hass
        self._config_entry = config_entry
        config = hass.data[DOMAIN][config_entry.entry_id]
        _LOGGER.debug("Config is: %s" % entity_config)
        self._accountNum = config.get(CONF_PANEL_ACCOUNT_NUMBER)
        self._listener = self._hass.data[DOMAIN][LISTENER]
        self._name = entity_config.get(CONF_ZONE_NAME)
        self._device_name = entity_config.get(CONF_ZONE_NAME)
        self._number = entity_config.get(CONF_ZONE_NUMBER)
        if "door" in entity_config.get(CONF_ZONE_CLASS):
            self._device_class = "door"
        elif "window" in entity_config.get(CONF_ZONE_CLASS):
            self._device_class = "window"
        else:
            self._device_class = "sensors"
        self._panel = self._listener.getPanels()[str(self._accountNum)]
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
        _LOGGER.debug("Removing DMPZoneOpenClose Callback")
        self._listener.remove_callback(self.process_zone_callback)

    async def process_zone_callback(self):
        # _LOGGER.debug("DMPZoneOpenClose Callback Executed")
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
        # _LOGGER.debug("Called DMPZoneOpenClose.is_on: {}".format(self._state))
        return self._state

    @property
    def icon(self):
        """Icon to show for status"""
        state = self.is_on
        device_class = self._device_class
        if state:
            if device_class == "window":
                return 'mdi:window-open'
            else:
                return 'mdi:door-open'
        else:
            if device_class == "window":
                return 'mdi:window-closed'
            else:
                return 'mdi:door-closed'

    @property
    def device_class(self):
        """Return the class of the device"""
        # _LOGGER.debug("Called DMPZoneOpenClose.device_class: {}"
                    #   .format(self._device_class))
        return self._device_class

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "last_contact": self._panel.getContactTime()
        }

    @property
    def unique_id(self):
        """Return unique ID"""
        return "dmp-%s-zone-%s-openclose" % (self._accountNum,
                                             self._number)

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, "dmp-%s-zone-%s" % (self._accountNum,
                                             self._number))
            },
            name=self.name,
            manufacturer='Digital Monitoring Products',
            via_device=(DOMAIN, "dmp-%s-panel" % (self._accountNum))
        )


class DMPZoneBattery(BinarySensorEntity):
    def __init__(self, hass, config_entry, entity_config):
        self._hass = hass
        self._config_entry = config_entry
        config = hass.data[DOMAIN][config_entry.entry_id]
        self._accountNum = config.get(CONF_PANEL_ACCOUNT_NUMBER)
        self._listener = self._hass.data[DOMAIN][LISTENER]
        self._device_name = entity_config.get(CONF_ZONE_NAME)
        self._name = "%s Battery" % entity_config.get(CONF_ZONE_NAME)
        self._number = entity_config.get(CONF_ZONE_NUMBER)
        self._device_class = "battery"
        self._panel = self._listener.getPanels()[str(self._accountNum)]
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
        # _LOGGER.debug("DMPZoneBattery Callback Executed")
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
        # _LOGGER.debug("Called DMPZoneBattery.is_on: {}".format(self._state))
        return self._state

    @property
    def icon(self):
        """Icon to show for status"""
        state = self.is_on
        if state:
            return 'mdi:battery-alert-variant-outline'
        else:
            return 'mdi:battery'

    @property
    def device_class(self):
        """Return the class of the device"""
        # _LOGGER.debug("Called DMPZoneBattery.device_class: {}"
                    #   .format(self._device_class))
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
            self._accountNum,
            self._number
            )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, "dmp-%s-zone-%s" % (self._accountNum,
                                             self._number))
            },
            name=self.name,
            manufacturer='Digital Monitoring Products',
            via_device=(DOMAIN, "dmp-%s-panel" % (self._accountNum))
        )


class DMPZoneTrouble(BinarySensorEntity):
    def __init__(self, hass, config_entry, entity_config):
        self._hass = hass
        self._config_entry = config_entry
        config = hass.data[DOMAIN][config_entry.entry_id]
        self._accountNum = config.get(CONF_PANEL_ACCOUNT_NUMBER)
        self._listener = self._hass.data[DOMAIN][LISTENER]
        self._device_name = entity_config.get(CONF_ZONE_NAME)
        self._name = "%s Trouble" % entity_config.get(CONF_ZONE_NAME)
        self._number = entity_config.get(CONF_ZONE_NUMBER)
        self._device_class = "problem"
        self._panel = self._listener.getPanels()[str(self._accountNum)]
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
        # _LOGGER.debug("DMPZoneTrouble Callback Executed")
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
        # _LOGGER.debug("Called DMPTroubleZone.is_on: {}".format(self._state))
        return self._state

    @property
    def icon(self):
        """Icon to show for status"""
        state = self.is_on
        if state:
            return 'mdi:alert-outline'
        else:
            return 'mdi:check'

    @property
    def device_class(self):
        """Return the class of the device"""
        # _LOGGER.debug("Called DMPTrouble.device_class: {}"
                    #   .format(self._device_class))
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
            self._accountNum,
            self._number
            )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, "dmp-%s-zone-%s" % (self._accountNum,
                                             self._number))
            },
            name=self.name,
            manufacturer='Digital Monitoring Products',
            via_device=(DOMAIN, "dmp-%s-panel" % (self._accountNum))
        )


class DMPZoneBypass(BinarySensorEntity):
    def __init__(self, hass, config_entry, entity_config):
        self._hass = hass
        self._config_entry = config_entry
        config = hass.data[DOMAIN][config_entry.entry_id]
        self._accountNum = config.get(CONF_PANEL_ACCOUNT_NUMBER)
        self._listener = self._hass.data[DOMAIN][LISTENER]
        self._device_name = entity_config.get(CONF_ZONE_NAME)
        self._name = "%s Bypass" % entity_config.get(CONF_ZONE_NAME)
        self._number = entity_config.get(CONF_ZONE_NUMBER)
        self._device_class = "problem"
        self._panel = self._listener.getPanels()[str(self._accountNum)]
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
        # _LOGGER.debug("DMPZoneBypass Callback Executed")
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
        # _LOGGER.debug("Called DMPZoneBypass.is_on: {}".format(self._state))
        return self._state

    @property
    def icon(self):
        """Icon to show for status"""
        state = self.is_on
        if state:
            return 'mdi:alert-outline'
        else:
            return 'mdi:check'

    @property
    def device_class(self):
        """Return the class of the device"""
        # _LOGGER.debug("Called DMPZoneBypass.device_class: {}"
                    #   .format(self._device_class))
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
            self._accountNum,
            self._number
            )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, "dmp-%s-zone-%s" % (self._accountNum,
                                             self._number))
            },
            name=self.name,
            manufacturer='Digital Monitoring Products',
            via_device=(DOMAIN, "dmp-%s-panel" % (self._accountNum))
        )


class DMPZoneAlarm(BinarySensorEntity):
    def __init__(self, hass, config_entry, entity_config):
        self._hass = hass
        self._config_entry = config_entry
        config = hass.data[DOMAIN][config_entry.entry_id]
        self._accountNum = config.get(CONF_PANEL_ACCOUNT_NUMBER)
        self._listener = self._hass.data[DOMAIN][LISTENER]
        self._device_name = entity_config.get(CONF_ZONE_NAME)
        self._name = "%s Alarm" % entity_config.get(CONF_ZONE_NAME)
        self._number = entity_config.get(CONF_ZONE_NUMBER)
        self._device_class = "problem"
        self._panel = self._listener.getPanels()[str(self._accountNum)]
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
        # _LOGGER.debug("DMPZoneAlarm Callback Executed")
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
        # _LOGGER.debug("Called DMPZoneAlarm.is_on: {}".format(self._state))
        return self._state

    @property
    def icon(self):
        """Icon to show for status"""
        state = self.is_on
        if state:
            return 'mdi:alarm-bell'
        else:
            return 'mdi:check'

    @property
    def device_class(self):
        """Return the class of the device"""
        # _LOGGER.debug("Called DMPZoneAlarm.device_class: {}"
                    #   .format(self._device_class))
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
            self._accountNum,
            self._number
            )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, "dmp-%s-zone-%s" % (self._accountNum,
                                             self._number))
            },
            name=self.device_name,
            manufacturer='Digital Monitoring Products',
            via_device=(DOMAIN, "dmp-%s-panel" % (self._accountNum))
        )
