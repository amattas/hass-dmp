"""Platform for DMP Alarm Panel integration"""

from __future__ import annotations

from typing import Any

from homeassistant.components.alarm_control_panel import AlarmControlPanelEntity
from homeassistant.components.alarm_control_panel.const import (
    AlarmControlPanelEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pydmp import DMPPanel as PyDMPPanel

from . import DMPConfigEntry, DMPListener, DMPPanel
from .const import CONF_HOME_AREA, CONF_PANEL_ACCOUNT_NUMBER
from .entity import DMPPanelEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DMPConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the panel's arming control from a config entry."""
    data = entry.runtime_data
    account = data.config[CONF_PANEL_ACCOUNT_NUMBER]
    async_add_entities([DMPArea(data.listener, data.panel, account, data.config)])


class DMPArea(DMPPanelEntity, AlarmControlPanelEntity):
    _attr_translation_key = "arming"
    _attr_code_arm_required = False
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_NIGHT
    )

    def __init__(
        self,
        listener: DMPListener,
        panel: DMPPanel,
        account: str,
        config: dict[str, Any],
    ) -> None:
        super().__init__(listener, panel, account, config)
        self._attr_unique_id = f"dmp-{account}-panel-arming"
        self._home_area = int(config[CONF_HOME_AREA])

    @property
    def _pydmp_panel(self) -> PyDMPPanel:
        """Return the connected pyDMP panel."""
        pydmp_panel = self._panel._pydmp_panel
        if pydmp_panel is None:
            raise HomeAssistantError("DMP panel is not connected")
        return pydmp_panel

    @callback
    def _update_from_panel(self) -> None:
        self._attr_alarm_state = self._panel.getArea()["areaState"]

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        await self._pydmp_panel.disarm_areas([1, 2, 3])

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        await self._pydmp_panel.arm_areas([1, 2, 3])

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        await self._pydmp_panel.arm_areas([self._home_area])

    # arm night is just an arm home with no exit/entry delay
    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        """Send arm night command."""
        await self._pydmp_panel.arm_areas([self._home_area], instant=True)
