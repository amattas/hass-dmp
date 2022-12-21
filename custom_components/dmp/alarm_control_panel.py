"""Platform for DMP Alarm Panel integration"""

import voluptuous as vol
import logging

from homeassistant.components.alarm_control_panel import (
    FORMAT_NUMBER,
    AlarmControlPanelEntity,
)
from homeassistant.helpers.entity import (
    DeviceInfo
)
from homeassistant.const import (
    STATE_ALARM_DISARMED
)

from homeassistant.components.alarm_control_panel.const import (
    SUPPORT_ALARM_ARM_HOME,
    SUPPORT_ALARM_ARM_AWAY
)
import homeassistant.helpers.config_validation as cv

from .const import (DOMAIN, LISTENER, CONF_AREA_NAME,
                    CONF_PANEL_ACCOUNT_NUMBER, CONF_AREA_NUMBER,
                    CONF_AREA_DISARM_ZONE, CONF_AREA_HOME_ZONE,
                    CONF_AREA_AWAY_ZONE, CONF_AREAS)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities,):
    """Setup sensors from a config entry created in the integrations UI."""
    hass.data.setdefault(DOMAIN, {})
    config = hass.data[DOMAIN][entry.entry_id]
    listener = hass.data[DOMAIN][LISTENER]
    areas = [DMPArea(listener, area, config.get(CONF_PANEL_ACCOUNT_NUMBER))
             for area in config[CONF_AREAS]]
    async_add_entities(areas, update_before_add=True)


class DMPArea(AlarmControlPanelEntity):
    def __init__(self, listener, config, accountNum):
        self._listener = listener
        self._name = config.get(CONF_AREA_NAME)
        self._account_number = accountNum
        self._number = config.get(CONF_AREA_NUMBER)
        self._panel = listener.getPanels()[str(self._account_number)]
        self._disarm_zone = (config.get(CONF_AREA_DISARM_ZONE)
                             or self._number[1:])
        self._home_zone = (config.get(CONF_AREA_HOME_ZONE)
                           or self._number[1:])
        self._away_zone = (config.get(CONF_AREA_AWAY_ZONE)
                           or self._number[1:])
        areaObj = {"areaName": self._name, "areaNumber": str(self._number),
                   "areaState": STATE_ALARM_DISARMED}
        self._panel.updateArea(str(self._number), areaObj)

    async def async_added_to_hass(self):
        _LOGGER.debug("Registering DMPArea Callback")
        self._listener.register_callback(self.process_area_callback)

    async def async_will_remove_from_hass(self):
        _LOGGER.debug("Removing DMPArea Callback")
        self._listener.remove_callback(self.process_area_callback)

    async def process_area_callback(self):
        self.async_write_ha_state()
        _LOGGER.debug("DMPArea Callback Executed")

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def state(self):
        """Return the state of the device."""
        state = self._panel.getArea(self._number)["areaState"]
        return state

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return SUPPORT_ALARM_ARM_HOME | SUPPORT_ALARM_ARM_AWAY

    @property
    def code_arm_required(self):
        """Whether the code is required for arm actions."""
        return False

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "last_contact": self._panel.getContactTime(),
        }

    @property
    def unique_id(self):
        """Return unique ID"""
        return "dmp-%s-area-%s" % (self._account_number, self._number)

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

    async def async_alarm_disarm(self, code=None):
        """Send disarm command."""
        await self._panel.connectAndSend('!O{},'.format(self._disarm_zone))

    async def async_alarm_arm_away(self, code=None):
        """Send arm away command."""
        await self._panel.connectAndSend('!C{},YN'.format(self._away_zone))

    async def async_alarm_arm_home(self, code=None):
        """Send arm away command."""
        await self._panel.connectAndSend('!C{},YN'.format(self._home_zone))
