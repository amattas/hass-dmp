"""Platform for DMP zone bypass switches."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import (  # type: ignore[attr-defined]  # HA 2024.11 has no SwitchDeviceClass in switch.const
    SwitchDeviceClass,
    SwitchEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DMPConfigEntry, DMPListener, DMPPanel
from .const import CONF_PANEL_ACCOUNT_NUMBER, CONF_ZONES
from .entity import DMPZoneEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DMPConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a bypass switch for every zone from a config entry."""
    data = config_entry.runtime_data
    account = data.config[CONF_PANEL_ACCOUNT_NUMBER]
    async_add_entities(
        DMPZoneBypassSwitch(data.listener, data.panel, account, zone)
        for zone in data.config[CONF_ZONES]
    )


class DMPZoneBypassSwitch(DMPZoneEntity, SwitchEntity):
    """Bypass (on) or restore (off) a zone."""

    _attr_translation_key = "bypass"
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        listener: DMPListener,
        panel: DMPPanel,
        account: str,
        config: dict[str, Any],
    ) -> None:
        super().__init__(listener, panel, account, config)
        self._attr_unique_id = self._unique_id("bypass-switch")

    @callback
    def _update_from_panel(self) -> None:
        self._attr_is_on = self._zone is not None and self._zone.is_bypassed

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._panel.bypass_zone(self._number)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._panel.restore_zone(self._number)
