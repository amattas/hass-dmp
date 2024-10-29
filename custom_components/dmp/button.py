import logging

from homeassistant.helpers.entity import DeviceInfo

from homeassistant.components.button import ButtonEntity

from .const import (DOMAIN, LISTENER, CONF_PANEL_NAME,
                    CONF_PANEL_ACCOUNT_NUMBER)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities,):
    _LOGGER.info("Setting up alarm refresh button")
    hass.data.setdefault(DOMAIN, {})
    refreshButtons = []
    refreshButtons.append(DMPRefreshStatusButton(hass, config_entry))
    async_add_entities(refreshButtons, update_before_add=False)

class DMPRefreshStatusButton(ButtonEntity):
    def __init__(self, hass, config_entry):
        self._hass = hass
        self._config_entry = config_entry
        config = hass.data[DOMAIN][config_entry.entry_id]
        self._panel_name = config.get(CONF_PANEL_NAME)
        self._accountNum = config.get(CONF_PANEL_ACCOUNT_NUMBER)
        self._listener = self._hass.data[DOMAIN][LISTENER]
        self._name = "Refresh Status"

    async def async_added_to_hass(self):
        self._listener.register_callback(self.process_zone_callback)

    async def async_will_remove_from_hass(self):
        self._listener.remove_callback(self.process_zone_callback)

    async def process_zone_callback(self):
        self.async_write_ha_state()

    async def async_press(self):
        await self._listener.updateStatus()

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self):
        """Return unique ID"""
        return "dmp-%s-panel-refresh-status" % self._accountNum

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, "dmp-%s-panel" % self._accountNum)
            },
            name=self._panel_name,
            manufacturer='Digital Monitoring Products',
        )

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._listener.getStatusAttributes()
