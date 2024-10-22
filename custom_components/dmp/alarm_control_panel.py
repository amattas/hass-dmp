"""Platform for DMP Alarm Panel integration"""

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
import logging

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.const import STATE_ALARM_DISARMED
from homeassistant.components.alarm_control_panel.const import (
    SUPPORT_ALARM_ARM_HOME,
    SUPPORT_ALARM_ARM_AWAY
)
from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity
)
from .const import (DOMAIN, LISTENER, CONF_PANEL_NAME,
                    CONF_PANEL_ACCOUNT_NUMBER, CONF_HOME_AREA,
                    CONF_AWAY_AREA, PANEL_ALL_AREAS)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities,):
    _LOGGER.info("Setting up alarm control panels.")
    """Setup sensors from a config entry created in the integrations UI."""
    hass.data.setdefault(DOMAIN, {})
    config = hass.data[DOMAIN][entry.entry_id]
    # if entry.options:
    #     config.update(entry.options)
    _LOGGER.debug("Alarm control panel config: %s" % config)
    listener = hass.data[DOMAIN][LISTENER]
    area = DMPArea(listener, config)
    areas = []
    areas.append(area)
    async_add_entities(areas, update_before_add=True)


class DMPArea(AlarmControlPanelEntity):
    def __init__(self, listener, config):
        self._listener = listener
        self._panel_name = config.get(CONF_PANEL_NAME)
        self._name = "%s Arming Control" % self._panel_name
        self._account_number = config.get(CONF_PANEL_ACCOUNT_NUMBER)
        self._number = config.get(CONF_HOME_AREA)
        self._panel = listener.getPanels()[str(self._account_number)]
        self._home_zone = (config.get(CONF_HOME_AREA)
                           or self._number[1:])
        self._away_zone = (config.get(CONF_AWAY_AREA)
                           or self._number[1:])
        areaObj = {"areaName": self._name, "areaState": STATE_ALARM_DISARMED}
        self._panel.updateArea(areaObj)

    async def async_added_to_hass(self):
        _LOGGER.debug("Registering DMPArea Callback")
        self._listener.register_callback(self.process_area_callback)

    async def async_will_remove_from_hass(self):
        _LOGGER.debug("Removing DMPArea Callback")
        self._listener.remove_callback(self.process_area_callback)

    async def process_area_callback(self):
        self.async_write_ha_state()
        # _LOGGER.debug("DMPArea Callback Executed")

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
        state = self._panel.getArea()["areaState"]
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
        return "dmp-%s-panel-arming" % self._account_number

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, "dmp-%s-panel" % self._account_number)
            },
            name=self._panel_name,
            manufacturer='Digital Monitoring Products'
        )

    async def async_alarm_disarm(self, code=None):
        """Send disarm command."""
        await self._panel._dmpSender.disarm(PANEL_ALL_AREAS)

    async def async_alarm_arm_away(self, code=None):
        """Send arm away command."""
        await self._panel._dmpSender.arm(PANEL_ALL_AREAS)

    async def async_alarm_arm_home(self, code=None):
        """Send arm home command."""
        await self._panel._dmpSender.arm(self._home_zone)
