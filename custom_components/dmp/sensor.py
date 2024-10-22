"""Platform for DMP Alarm Panel integration"""
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
import logging
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.sensor import (
    SensorEntity
)
from .const import (DOMAIN, LISTENER, CONF_PANEL_ACCOUNT_NUMBER,
                    CONF_ZONE_NAME, CONF_ZONE_NUMBER, CONF_ZONE_CLASS,
                    CONF_ZONES)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities,):
    """Setup sensors from a config entry created in the integrations UI."""
    _LOGGER.debug("Setting up sensors.")
    hass.data.setdefault(DOMAIN, {})
    config = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.debug("Sensor config: %s" % config)
    # Add all zones to trouble zones
    statusZones = [
        DMPZoneStatus(
            hass, config_entry, zone
            ) for zone in config[CONF_ZONES]
    ]
    async_add_entities(statusZones, update_before_add=True)


class DMPZoneStatus(SensorEntity):
    def __init__(self, hass, config_entry, entity_config):
        self._hass = hass
        self._config_entry = config_entry
        config = hass.data[DOMAIN][config_entry.entry_id]
        _LOGGER.debug("Config is: %s" % entity_config)
        self._accountNum = config.get(CONF_PANEL_ACCOUNT_NUMBER)
        self._listener = self._hass.data[DOMAIN][LISTENER]
        self._name = "%s Status" % entity_config.get(CONF_ZONE_NAME)
        self._device_name = entity_config.get(CONF_ZONE_NAME)
        self._number = entity_config.get(CONF_ZONE_NUMBER)
        self._panel = self._listener.getPanels()[str(self._accountNum)]
        self._number = entity_config.get(CONF_ZONE_NUMBER)
        if "door" in entity_config.get(CONF_ZONE_CLASS):
            self._device_class = "door"
        elif "window" in entity_config.get(CONF_ZONE_CLASS):
            self._device_class = "window"
        else:
            self._device_class = "default"
        self._state = 'Ready'
        zoneStatusObj = {
            "zoneName": self._device_name,
            "zoneNumber": str(self._number),
            "zoneState": self._state
            }
        self._panel.updateStatusZone(str(self._number), zoneStatusObj)

    async def async_added_to_hass(self):
        _LOGGER.debug("Registering DMPZoneStatus Callback")
        self._listener.register_callback(self.process_zone_callback)

    async def async_will_remove_from_hass(self):
        _LOGGER.debug("Removing DMPZoneStatus Callback")
        self._listener.remove_callback(self.process_zone_callback)
        # Removing linked device, since all zones have a status sensor this
        # is the most logical place to execute this code.
        device_registry = dr.async_get(self._hass)
        device_identifiers = list(self.device_info["identifiers"])
        entity_devices = dr.async_entries_for_config_entry(
            device_registry,
            self._config_entry.entry_id
            )
        for e in entity_devices:
            for i in e.identifiers:
                if i in device_identifiers:
                    device_registry.async_remove_device(e.id)
        for i in device_identifiers:
            item = device_registry.async_get_device(i)

    async def process_zone_callback(self):
        # _LOGGER.debug("DMPZoneStatus Callback Executed")
        self._state = self._panel.getStatusZone(self._number)["zoneState"]
        self.async_write_ha_state()

    @property
    def device_name(self):
        """Return the name of the device."""
        return self._device_name

    @property
    def native_value(self):
        """Return the native value of the device"""
        return None

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
        # _LOGGER.debug("Called DMPZoneStatus.state: {}".format(self._state))
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "last_contact": self._panel.getContactTime(),
        }

    @property
    def icon(self):
        """Icon to show for status"""
        state = self.state
        device_class = self._device_class
        if state == 'Alarm':
            return 'mdi:alarm-bell'
        elif state == 'Trouble':
            return 'mdi:alert'
        elif state == 'Bypass':
            return 'mdi:alert'
        elif state == 'Low Battery':
            return 'mdi:battery-alert-variant-outline'
        elif state == 'Open':
            if device_class == "window":
                return 'mdi:window-open'
            else:
                return 'mdi:door-open'
        elif state == 'Ready':
            return 'mdi:check'

    @property
    def unique_id(self):
        """Return unique ID"""
        return "dmp-%s-zone-%s-status" % (
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
