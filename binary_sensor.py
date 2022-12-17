"""Platform for DMP Alarm Panel integration"""

import voluptuous as vol
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity
)

import homeassistant.helpers.config_validation as cv

from .const import (DOMAIN, LISTENER, CONF_ZONE_NAME, CONF_ZONE_NUMBER,
                    CONF_ZONE_CLASS, CONF_ZONE_ACCTNUM, CONF_ZONES)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ZONE_NAME): cv.string,
        vol.Required(CONF_ZONE_ACCTNUM): cv.string,
        vol.Required(CONF_ZONE_NUMBER): cv.string,
        vol.Required(CONF_ZONE_CLASS): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup_entry(hass, entry, async_add_entities,):
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][entry.entry_id]
    # Update our config to include new repos and remove those that have
    # been removed.
    if config.options:
        config.update(config.options)
    listener = hass.data[DOMAIN][LISTENER]
    zones = [DMPZoneOpenClose(listener, config) for area in config[CONF_ZONES]]
    async_add_entities(zones, update_before_add=True)


async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    listener = hass.data[DOMAIN][LISTENER]
    zone = [DMPZoneOpenClose(listener, config)]
    async_add_entities(zone)


class DMPZoneOpenClose(BinarySensorEntity):
    def __init__(self, listener, config):
        self._listener = listener
        self._name = config.get(CONF_ZONE_NAME)
        self._number = config.get(CONF_ZONE_NUMBER)
        self._account_number = config.get(CONF_ZONE_ACCTNUM)
        self._device_class = config.get(CONF_ZONE_CLASS)
        self._panel = listener.getPanels()[str(self._account_number)]
        self._state = False
        zoneObj = {"zoneName": self._name, "zoneNumber": str(self._number),
                   "zoneState": self._state}
        self._panel.updateZone(str(self._number), zoneObj)

    async def async_added_to_hass(self):
        _LOGGER.debug("Registering DMPZone Callback")
        self._listener.register_callback(self.process_zone_callback)

    async def async_will_remove_from_hass(self):
        _LOGGER.debug("Removing DMPZone Callback")
        self._listener.remove_callback(self.process_zone_callback)

    async def process_zone_callback(self):
        _LOGGER.debug("DMPZone Callback Executed")
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
        return "dmp-%s-zone-%s" % (self._account_number, self._number)
