"""Platform for DMP Alarm Panel integration"""
import voluptuous as vol
import logging


from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity
)
from homeassistant.helpers.entity import (
    DeviceInfo
)
import homeassistant.helpers.config_validation as cv

from .const import (DOMAIN, LISTENER, CONF_PANEL_NAME, CONF_PANEL_IP,
                    CONF_PANEL_LISTEN_PORT, CONF_PANEL_REMOTE_PORT,
                    CONF_PANEL_ACCOUNT_NUMBER, CONF_PANEL_REMOTE_KEY,
                    CONF_HOME_AREA, CONF_AWAY_AREA,
                    CONF_ZONE_NAME, CONF_ZONE_NUMBER, CONF_ZONE_CLASS,
                    CONF_ADD_ANOTHER, CONF_ZONES)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities,):
    """Setup sensors from a config entry created in the integrations UI."""
    _LOGGER.debug("Setting up binary sensors.")
    hass.data.setdefault(DOMAIN, {})
    config = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug("Binary sensor config: %s" % config)
    listener = hass.data[DOMAIN][LISTENER]
    zones = [DMPZoneOpenClose(listener, area,
             config.get(CONF_PANEL_ACCOUNT_NUMBER))
             for area in config[CONF_ZONES]]
    async_add_entities(zones, update_before_add=True)


class DMPZoneOpenClose(BinarySensorEntity):
    def __init__(self, listener, config, accountNum):
        self._listener = listener
        self._name = "%s Open/Close" % config.get(CONF_ZONE_NAME)
        self._number = config.get(CONF_ZONE_NUMBER)
        self._account_number = accountNum
        self._device_class = config.get(CONF_ZONE_CLASS)
        self._panel = listener.getPanels()[str(self._account_number)]
        self._state = False
        zoneOpenCloseObj = {
            "zoneName": self._name,
            "zoneNumber": str(self._number),
            "zoneState": self._state
            }
        self._panel.updateZone(str(self._number), zoneOpenCloseObj)

    async def async_added_to_hass(self):
        _LOGGER.debug("Registering DMPZoneOpenClose Callback")
        self._listener.register_callback(self.process_zone_callback)

    async def async_will_remove_from_hass(self):
        _LOGGER.debug("Removing DMPZoneOpenClose Callback")
        self._listener.remove_callback(self.process_zone_callback)

    async def process_zone_callback(self):
        _LOGGER.debug("DMPZoneOpenClose Callback Executed")
        self._state = self._panel.getZone(self._number)["zoneState"]
        self.async_write_ha_state()

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
    def __init__(self, listener, config, accountNum):
        self._listener = listener
        self._name = "%s Battery" % config.get(CONF_ZONE_NAME)
        self._number = config.get(CONF_ZONE_NUMBER)
        self._account_number = accountNum
        self._device_class = config.get(CONF_ZONE_CLASS)
        self._panel = listener.getPanels()[str(self._account_number)]
        self._state = False
        zoneBatteryObj = {
            "zoneName": self._name,
            "zoneNumber": str(self._number),
            "zoneState": self._state
            }
        self._panel.updateZone(str(self._number), zoneBatteryObj)

    async def async_added_to_hass(self):
        _LOGGER.debug("Registering DMPZoneBattery Callback")
        self._listener.register_callback(self.process_zone_callback)

    async def async_will_remove_from_hass(self):
        _LOGGER.debug("Removing DMPZoneBattery Callback")
        self._listener.remove_callback(self.process_zone_callback)

    async def process_zone_callback(self):
        _LOGGER.debug("DMPZoneBattery Callback Executed")
        self._state = self._panel.getZone(self._number)["zoneState"]
        self.async_write_ha_state()

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
        _LOGGER.debug("Called DMPZone.is_on: {}".format(self._state))
        return self._state

    @property
    def device_class(self):
        """Return the class of the device"""
        _LOGGER.debug("Called DMPZone.device_class: {}"
                      .format("battery"))
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
