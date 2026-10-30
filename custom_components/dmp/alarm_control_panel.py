"""Platform for DMP Alarm Panel integration"""

import logging
from typing import Any

from homeassistant.components.alarm_control_panel import AlarmControlPanelEntity
from homeassistant.components.alarm_control_panel.const import (
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pydmp import DMPPanel as PyDMPPanel

from . import AreaStatus, DMPListener
from .const import (
    CONF_AWAY_AREA,
    CONF_HOME_AREA,
    CONF_PANEL_ACCOUNT_NUMBER,
    CONF_PANEL_NAME,
    DOMAIN,
    LISTENER,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    _LOGGER.info("Setting up alarm control panels.")
    """Setup sensors from a config entry created in the integrations UI."""
    hass.data.setdefault(DOMAIN, {})
    config = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug(f"Alarm control panel config: {config}")
    listener = hass.data[DOMAIN][LISTENER]
    area = DMPArea(listener, config)
    areas: list[DMPArea] = []
    areas.append(area)
    async_add_entities(areas, update_before_add=True)


class DMPArea(AlarmControlPanelEntity):
    def __init__(self, listener: DMPListener, config: dict[str, Any]) -> None:
        self._listener = listener
        self._panel_name: str | None = config.get(CONF_PANEL_NAME)
        self._name = f"{self._panel_name} Arming Control"
        self._account_number: str | None = config.get(CONF_PANEL_ACCOUNT_NUMBER)
        self._number: str = config.get(CONF_HOME_AREA, "")
        self._panel = listener.getPanels()[str(self._account_number)]
        self._home_zone: str = config.get(CONF_HOME_AREA) or self._number[1:]
        self._away_zone: str = config.get(CONF_AWAY_AREA) or self._number[1:]
        areaObj = AreaStatus(
            areaName=self._name, areaState=AlarmControlPanelState.DISARMED
        )
        self._panel.updateArea(areaObj)

    @property
    def _pydmp_panel(self) -> PyDMPPanel:
        """Return the connected pyDMP panel."""
        pydmp_panel = self._panel._pydmp_panel
        if pydmp_panel is None:
            raise HomeAssistantError("DMP panel is not connected")
        return pydmp_panel

    async def async_added_to_hass(self) -> None:
        _LOGGER.debug("Registering DMPArea Callback")
        self._listener.register_callback(self.process_area_callback)

    async def async_will_remove_from_hass(self) -> None:
        _LOGGER.debug("Removing DMPArea Callback")
        self._listener.remove_callback(self.process_area_callback)

    async def process_area_callback(self) -> None:
        self.async_write_ha_state()

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self) -> bool:
        """Return the polling state."""
        return False

    @property
    def alarm_state(self) -> AlarmControlPanelState:
        """Return the state of the device."""
        state = self._panel.getArea()["areaState"]
        return state

    @property
    def supported_features(self) -> AlarmControlPanelEntityFeature:
        """Return the list of supported features."""
        return (
            AlarmControlPanelEntityFeature.ARM_HOME
            | AlarmControlPanelEntityFeature.ARM_AWAY
            | AlarmControlPanelEntityFeature.ARM_NIGHT
        )

    @property
    def code_arm_required(self) -> bool:
        """Whether the code is required for arm actions."""
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "last_contact": self._panel.getContactTime(),
        }

    @property
    def unique_id(self) -> str:
        """Return unique ID"""
        return f"dmp-{self._account_number}-panel-arming"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"dmp-{self._account_number}-panel")},
            name=self._panel_name,
            manufacturer="Digital Monitoring Products",
        )

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        await self._pydmp_panel.disarm_areas([1, 2, 3])

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        await self._pydmp_panel.arm_areas([1, 2, 3])

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        await self._pydmp_panel.arm_areas([int(self._home_zone)])

    # arm night is just an arm home with no exit/entry delay
    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        """Send arm night command."""
        await self._pydmp_panel.arm_areas([int(self._home_zone)], instant=True)
