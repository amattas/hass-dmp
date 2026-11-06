"""Platform for the DMP refresh status button."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DMPConfigEntry, DMPListener, DMPPanel
from .const import CONF_PANEL_ACCOUNT_NUMBER
from .entity import DMPPanelEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DMPConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the panel's refresh status button from a config entry."""
    data = config_entry.runtime_data
    account = data.config[CONF_PANEL_ACCOUNT_NUMBER]
    async_add_entities(
        [DMPRefreshStatusButton(data.listener, data.panel, account, data.config)]
    )


class DMPRefreshStatusButton(DMPPanelEntity, ButtonEntity):
    """Query the panel for the full zone and arming status."""

    _attr_translation_key = "refresh_status"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        listener: DMPListener,
        panel: DMPPanel,
        account: str,
        config: dict[str, Any],
    ) -> None:
        super().__init__(listener, panel, account, config)
        self._attr_unique_id = f"dmp-{account}-panel-refresh-status"

    async def async_press(self) -> None:
        await self._async_command(self._listener.updateStatus)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the consolidated panel status from the last full query."""
        return self._listener.getStatusAttributes()
