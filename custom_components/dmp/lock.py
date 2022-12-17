"""Platform for DMP Alarm Panel integration"""

import voluptuous as vol
import logging

from homeassistant.components.lock import LockEntity
from homeassistant.const import STATE_LOCKED, STATE_UNLOCKED
from homeassistant.components.lock import (
    SUPPORT_OPEN,
)
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, LISTENER, CONF_LOCK_NAME, CONF_LOCK_NUMBER, CONF_LOCK_ACCOUNT_NUMBER

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_LOCK_NAME): cv.string,
        vol.Required(CONF_LOCK_NUMBER): cv.string,
        vol.Required(CONF_LOCK_ACCOUNT_NUMBER): cv.string
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    listener = hass.data[DOMAIN][LISTENER]
    entity = [DMPDoor(listener, config)]
    async_add_entities(entity)


class DMPDoor(LockEntity):
    def __init__(self, listener, config):
        self._name = config.get(CONF_LOCK_NAME)
        self._listener = listener
        self._account_number = config.get(CONF_LOCK_ACCOUNT_NUMBER)
        self._number = config.get(CONF_LOCK_NUMBER)
        self._panel = listener.getPanels()[str(self._account_number)]

    async def async_added_to_hass(self):
        self._listener.register_callback(self.process_callback)

    async def async_will_remove_from_hass(self):
        self._listener.remove_callback(self.process_callback)

    async def process_callback(self):
        self.async_write_ha_state()

    async def async_open(self, **kwargs):
        await self._panel.connectAndSend('!J{}'.format(self._number))
    async def async_unlock(self, **kwargs):
        await self._panel.connectAndSend('!QD{}S'.format(self._number))
    async def async_lock(self, **kwargs):
        await self._panel.connectAndSend('!QD{}O'.format(self._number))

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_OPEN

    @property
    def is_locked(self) -> bool:
        """Return true if the lock is locked."""
        """Will generally always be locked, we'll implement checking later via the zone real time status feature of PC log reports"""
        return True

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self):
        """Return the polling state."""
        return False