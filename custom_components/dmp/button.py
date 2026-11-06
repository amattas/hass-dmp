from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DMPConfigEntry, DMPListener
from .const import CONF_PANEL_ACCOUNT_NUMBER, CONF_PANEL_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DMPConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    _LOGGER.info("Setting up alarm refresh button")
    refreshButtons: list[DMPRefreshStatusButton] = []
    refreshButtons.append(DMPRefreshStatusButton(hass, config_entry))
    async_add_entities(refreshButtons, update_before_add=False)


class DMPRefreshStatusButton(ButtonEntity):
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, config_entry: DMPConfigEntry) -> None:
        self._hass = hass
        self._config_entry = config_entry
        config = config_entry.runtime_data.config
        self._panel_name: str | None = config.get(CONF_PANEL_NAME)
        self._accountNum: str | None = config.get(CONF_PANEL_ACCOUNT_NUMBER)
        self._listener: DMPListener = config_entry.runtime_data.listener
        self._name = "Refresh Status"

    async def async_added_to_hass(self) -> None:
        self._listener.register_callback(self.process_zone_callback)

    async def async_will_remove_from_hass(self) -> None:
        self._listener.remove_callback(self.process_zone_callback)

    async def process_zone_callback(self) -> None:
        self.async_write_ha_state()

    async def async_press(self) -> None:
        await self._listener.updateStatus()

    @property
    def name(self) -> str | None:
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return unique ID"""
        return f"dmp-{self._accountNum}-panel-refresh-status"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"dmp-{self._accountNum}-panel")},
            name=self._panel_name,
            manufacturer="Digital Monitoring Products",
        )

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the state attributes."""
        return self._listener.getStatusAttributes()
