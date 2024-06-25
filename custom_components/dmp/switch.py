from homeassistant.components.switch import (
    SwitchEntity
)
from homeassistant.helpers.entity import DeviceInfo

from .const import (DOMAIN, LISTENER, CONF_PANEL_ACCOUNT_NUMBER,
                    CONF_ZONE_NAME, CONF_ZONE_NUMBER, CONF_ZONE_CLASS,
                    CONF_ZONES)
import logging


_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities,):
    _LOGGER.debug("Setting up bypass switches")
    hass.data.setdefault(DOMAIN, {})
    config = hass.data[DOMAIN][config_entry.entry_id]
    # broken out from binary_sensor
    bypassZones = []
    for zone in config[CONF_ZONES]:
        # allow all zones to be bypassed 
        # if (
        #     "window" in zone[CONF_ZONE_CLASS]
        #     or "door" in zone[CONF_ZONE_CLASS]
        #     or "glassbreak" in zone[CONF_ZONE_CLASS]
        #     or "motion" in zone[CONF_ZONE_CLASS]
        # ):
            bypassZones.append(
                DMPZoneBypassSwitch(
                    hass, config_entry, zone
                )
            )
    # Don't update before add or you have a race condition with the
    # status zone.
    async_add_entities(bypassZones, update_before_add=False)

class DMPZoneBypassSwitch(SwitchEntity):
    def __init__(self, hass, config_entry, entity_config):
        self._hass = hass
        self._config_entry = config_entry
        config = hass.data[DOMAIN][config_entry.entry_id]
        self._accountNum = config.get(CONF_PANEL_ACCOUNT_NUMBER)
        self._listener = self._hass.data[DOMAIN][LISTENER]
        self._device_name = entity_config.get(CONF_ZONE_NAME)
        self._name = "%s Bypass" % entity_config.get(CONF_ZONE_NAME)
        self._number = entity_config.get(CONF_ZONE_NUMBER)
        self._device_class = "switch"
        self._panel = self._listener.getPanels()[str(self._accountNum)]
        self._state = False
        zoneBypassObj = {
            "zoneName": self._device_name,
            "zoneNumber": str(self._number),
            "zoneState": self._state
            }
        self._panel.updateBypassZone(str(self._number), zoneBypassObj)

    async def async_added_to_hass(self):
        _LOGGER.debug("Registering DMPZoneBypassSwitch Callback")
        self._listener.register_callback(self.process_zone_callback)

    async def async_will_remove_from_hass(self):
        _LOGGER.debug("Removing DMPZoneBypassSwitch Callback")
        self._listener.remove_callback(self.process_zone_callback)

    async def process_zone_callback(self):
        # _LOGGER.debug("DMPZoneBypassSwitch Callback Executed")
        self._state = self._panel.getBypassZone(self._number)["zoneState"]
        self.async_write_ha_state()

    @property
    def device_name(self):
        return self._device_name

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return self._state

    @property
    def device_class(self):
        """Return the class of the device"""
        # _LOGGER.debug("Called DMPZoneBypassSwitch.device_class: {}"
                    #   .format(self._device_class))
        return self._device_class

    @property
    def unique_id(self):
        return "dmp-%s-zone-%s-bypass-switch" % (self._accountNum, self._number)

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, "dmp-%s-zone-%s" % (self._accountNum,
                                             self._number))
            },
            via_device=(DOMAIN, "dmp-%s-panel" % (self._accountNum))
        )

    async def async_turn_on(self):
        await self._panel._dmpSender.setBypass(self._number, True)

    async def async_turn_off(self):
        await self._panel._dmpSender.setBypass(self._number, False)
