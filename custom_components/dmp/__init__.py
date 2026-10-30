"""The DMP Integration Component"""

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, TypedDict

from homeassistant.components.alarm_control_panel.const import AlarmControlPanelState
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pydmp import DMPPanel as PyDMPPanel
from pydmp import DMPStatusServer, S3Message, Zone, parse_s3_message
from pydmp.const.events import DMPEventType

from .const import (
    CONF_AWAY_AREA,
    CONF_HOME_AREA,
    CONF_PANEL_ACCOUNT_NUMBER,
    CONF_PANEL_IP,
    CONF_PANEL_LISTEN_PORT,
    CONF_PANEL_REMOTE_KEY,
    CONF_PANEL_REMOTE_PORT,
    CONF_ZONE_NUMBER,
    CONF_ZONES,
    DOMAIN,
    LISTENER,
    PYDMP_PANEL,
    STATUS_SERVER,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.ALARM_CONTROL_PANEL,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.SWITCH,
]

# Maps pyDMP single-char zone state to HA status string (for status attributes display)
ZONE_STATUS_MAP = {
    "N": "Normal",
    "O": "Open",
    "S": "Short",
    "X": "Bypassed",
    "L": "Low Battery",
    "M": "Missing",
}

# Maps pyDMP single-char zone state to sensor status string (for DMPZoneStatus entity)
ZONE_STATE_TO_STATUS = {
    "N": "Ready",
    "O": "Open",
    "S": "Trouble",
    "X": "Bypass",
    "L": "Low Battery",
    "M": "Trouble",
}

# Maps pyDMP single-char area state to HA status string
AREA_STATUS_MAP = {
    "A": "Armed",
    "D": "Disarmed",
}

UpdateCallback = Callable[[], Awaitable[None]]


class AreaStatus(TypedDict):
    """Last known arming state of the panel's area."""

    areaName: str
    areaState: AlarmControlPanelState


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    config = dict(entry.data)
    # Create Options Callback
    entry.add_update_listener(options_update_listener)
    _LOGGER.debug("Loaded config %s", config)

    # Create pyDMP panel and connect
    panel_port = config.get(CONF_PANEL_REMOTE_PORT) or 2001
    pydmp_panel = PyDMPPanel(port=panel_port)
    ip: str = config[CONF_PANEL_IP]
    account: str = config[CONF_PANEL_ACCOUNT_NUMBER]
    remote_key = config.get(CONF_PANEL_REMOTE_KEY) or "                "
    await pydmp_panel.connect(ip, account, remote_key)
    await pydmp_panel.start_keepalive()

    # Create status server for realtime events
    listen_port: int = config[CONF_PANEL_LISTEN_PORT]
    status_server = DMPStatusServer("0.0.0.0", listen_port)

    # Create HA state container
    panel = DMPPanel(hass, config, pydmp_panel)
    _LOGGER.debug("Panel account number: %s", panel.getAccountNumber())

    # Create listener and wire up S3 event callback
    listener = DMPListener(hass, config, pydmp_panel, status_server)
    listener.addPanel(panel)
    _LOGGER.debug("Panels attached to listener: %s", str(listener.getPanels()))

    # Start status server
    await status_server.start()

    # Store everything in hass.data
    hass.data[DOMAIN][LISTENER] = listener
    hass.data[DOMAIN][PYDMP_PANEL] = pydmp_panel
    hass.data[DOMAIN][STATUS_SERVER] = status_server
    hass.data[DOMAIN][entry.entry_id] = config

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    hass.async_create_task(listener.updateStatus())
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("Unloading entry.")
    status_server = hass.data[DOMAIN][STATUS_SERVER]
    pydmp_panel = hass.data[DOMAIN][PYDMP_PANEL]

    # Stop status server
    await status_server.stop()

    # Stop keepalive and disconnect
    await pydmp_panel.stop_keepalive()
    await pydmp_panel.disconnect()

    unload_ok: bool = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def options_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    _LOGGER.debug("Options flow completed.")
    entity_registry = er.async_get(hass)
    config = dict(entry.data)
    options = dict(entry.options)
    if options:
        _LOGGER.debug(f"Updated options found: {options}")
        """Handle options update."""
        # Remove Entities
        entries = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
        entry_map = {e.entity_id: e for e in entries}
        active_zones = [z[CONF_ZONE_NUMBER] for z in options[CONF_ZONES]]
        _LOGGER.debug(f"Zones found in options: {active_zones}")
        deleted_entries = []
        for emk in entry_map:
            if entry_map[emk].unique_id.split("-")[2] == "zone" and (
                entry_map[emk].unique_id.split("-")[3] not in active_zones
            ):
                deleted_entries.append(emk)
        _LOGGER.debug(f"Zone entities to be deleted: {deleted_entries}")
        for de in deleted_entries:
            entity_registry.async_remove(de)

        # Get and replace zones config
        _LOGGER.debug(f"Current config zones: {config[CONF_ZONES]}")
        _LOGGER.debug(f"New config zones: {options[CONF_ZONES]}")
        config[CONF_ZONES] = options[CONF_ZONES]
        hass.config_entries.async_update_entry(entry, data=config, options={})
        await hass.config_entries.async_reload(entry.entry_id)


class DMPPanel:
    def __init__(
        self,
        hass: HomeAssistant,
        config: dict[str, Any],
        pydmp_panel: PyDMPPanel | None = None,
    ) -> None:
        self._accountNumber: str = config.get(CONF_PANEL_ACCOUNT_NUMBER, "")
        self._ipAddress: str | None = config.get(CONF_PANEL_IP)
        self._panel_last_contact: datetime | None = None
        self._area: AreaStatus = {
            "areaName": "",
            "areaState": AlarmControlPanelState.DISARMED,  # Default Value
        }
        self._pydmp_panel = pydmp_panel
        self._alarm_zones: dict[str | None, bool] = {}

    def __str__(self) -> str:
        return f"DMP Panel with account number {self._accountNumber} at addr {self._ipAddress}"

    def updateContactTime(self, contactTime: datetime) -> None:
        self._panel_last_contact = contactTime

    def getContactTime(self) -> datetime | None:
        return self._panel_last_contact

    def updateArea(self, eventObj: AreaStatus) -> None:
        self._area = eventObj
        _LOGGER.debug("Area has been updated to %s", eventObj["areaState"])

    def getArea(self) -> AreaStatus:
        return self._area

    def set_alarm(self, zone_number: str | None) -> None:
        self._alarm_zones[zone_number] = True

    def clear_alarm(self, zone_number: str | None) -> None:
        self._alarm_zones[zone_number] = False

    def get_alarm(self, zone_number: str) -> bool:
        return self._alarm_zones.get(zone_number, False)

    def ensure_zone(self, zone_num: str | int) -> Zone | None:
        try:
            zone_int = int(zone_num)
        except ValueError, TypeError:
            _LOGGER.error("Invalid zone number: %s", zone_num)
            return None
        if self._pydmp_panel is not None:
            if zone_int not in self._pydmp_panel._zones:
                self._pydmp_panel._zones[zone_int] = Zone(self._pydmp_panel, zone_int)
            return self._pydmp_panel._zones[zone_int]
        return None

    def getAccountNumber(self) -> str:
        return self._accountNumber

    async def _zone_command(self, zone_num: str | int, command: str) -> None:
        try:
            zone_int = int(zone_num)
        except ValueError, TypeError:
            _LOGGER.error("Invalid zone number for %s command: %s", command, zone_num)
            return
        if self._pydmp_panel is None:
            _LOGGER.error("No panel connection for %s command: %s", command, zone_num)
            return
        if zone_int in self._pydmp_panel._zones:
            await getattr(self._pydmp_panel._zones[zone_int], command)()
        else:
            zone = Zone(self._pydmp_panel, zone_int)
            await getattr(zone, command)()

    async def bypass_zone(self, zone_num: str | int) -> None:
        await self._zone_command(zone_num, "bypass")

    async def restore_zone(self, zone_num: str | int) -> None:
        await self._zone_command(zone_num, "restore")


class DMPListener:
    def __init__(
        self,
        hass: HomeAssistant,
        config: dict[str, Any],
        pydmp_panel: PyDMPPanel | None = None,
        status_server: DMPStatusServer | None = None,
    ) -> None:
        self._hass = hass
        self._domain = config
        self._home_area: str = config[CONF_HOME_AREA]
        self._away_area: str = config[CONF_AWAY_AREA]
        self._port: int | None = config.get(CONF_PANEL_LISTEN_PORT)
        self._pydmp_panel = pydmp_panel
        self._status_server = status_server
        self._panels: dict[str, DMPPanel] = {}
        self.statusAttributes: dict[str, str] = {}
        # callbacks to call when an event gets posted in
        self._callbacks: set[UpdateCallback] = set()

        # Register S3 event callback with status server
        if status_server is not None:
            status_server.register_callback(self._handle_s3_event)

    def __str__(self) -> str:
        return f"DMP Listener on port {self._port}"

    def register_callback(self, callback: UpdateCallback) -> None:
        """Allow callbacks to be registered for when dict entries change"""
        self._callbacks.add(callback)

    def remove_callback(self, callback: UpdateCallback) -> None:
        """Allow callbacks to be de-registered"""
        self._callbacks.discard(callback)

    def addPanel(self, panelToAdd: DMPPanel) -> None:
        self._panels[panelToAdd.getAccountNumber()] = panelToAdd

    def getPanels(self) -> dict[str, DMPPanel]:
        return self._panels

    async def _handle_s3_event(self, msg: S3Message) -> None:
        """Handle incoming S3 event from DMPStatusServer."""
        try:
            event = parse_s3_message(msg)
        except Exception:  # noqa: BLE001
            _LOGGER.warning(
                "Failed to parse S3 message: %s",
                msg.raw if hasattr(msg, "raw") else msg,
            )
            return

        account = event.account.strip()

        # Fallback: if account empty and single panel, use it
        if not account and len(self._panels) == 1:
            account = next(iter(self._panels))

        try:
            panel = self._panels[account]
        except KeyError:
            _LOGGER.warning("Unknown account number sending data - %s", account)
            return

        _LOGGER.debug(
            "Received S3 event from panel %s: category=%s", account, event.category
        )

        category = event.category
        zone_number = event.zone
        type_code = event.type_code

        # Ensure pyDMP Zone object exists for zone events
        zone = None
        if zone_number:
            zone = panel.ensure_zone(zone_number)

        if category == DMPEventType.WIRELESS_LOW_BATTERY:  # Zd
            if zone:
                zone.update_state("L")

        elif category == DMPEventType.ZONE_BYPASS:  # Zx
            if zone:
                zone.update_state("X")

        elif category in (
            DMPEventType.ZONE_FAIL,  # Zf
            DMPEventType.WIRELESS_ZONE_MISSING,  # Zh
            DMPEventType.ZONE_TROUBLE,  # Zt
            DMPEventType.ZONE_FAULT,  # Zw
        ):
            if zone:
                if category == DMPEventType.WIRELESS_ZONE_MISSING:
                    zone.update_state("M")
                else:
                    zone.update_state("S")

        elif category in (
            DMPEventType.ZONE_RESET,  # Zy
            DMPEventType.ZONE_RESTORE,  # Zr
        ):
            if zone:
                zone.update_state("N")
            panel.clear_alarm(zone_number)

        elif category in (
            DMPEventType.ZONE_ALARM,  # Za
            DMPEventType.ZONE_FORCE_ARM,  # Zb
        ):
            panel.set_alarm(zone_number)
            areaObj: AreaStatus = {
                "areaName": event.area_name or "",
                "areaState": AlarmControlPanelState.TRIGGERED,
            }
            panel.updateArea(areaObj)

        elif category == DMPEventType.ARMING_STATUS:  # Zq
            area_number = event.area
            area_name = event.area_name or ""
            if type_code == "OP":  # Disarm
                areaState = AlarmControlPanelState.DISARMED
                # do a manual status query - bypassed zones are reset but no message for it
                self._hass.async_create_task(self.updateStatus())
            elif type_code == "CL":  # Arm
                if area_number and area_number.strip().lstrip(
                    "0"
                ) == self._home_area.lstrip("0"):
                    # Make sure we're not already armed away
                    if (
                        panel.getArea()["areaState"]
                        != AlarmControlPanelState.ARMED_AWAY
                    ):
                        areaState = AlarmControlPanelState.ARMED_HOME
                    else:
                        areaState = AlarmControlPanelState.ARMED_AWAY
                else:
                    areaState = AlarmControlPanelState.ARMED_AWAY
            else:
                _LOGGER.warning("Unknown arming type_code: %s, ignoring", type_code)
                return
            areaObj = AreaStatus(areaName=area_name, areaState=areaState)
            _LOGGER.debug(f"Updated area: {areaObj}")
            panel.updateArea(areaObj)

        elif category == DMPEventType.REAL_TIME_STATUS:  # Zc
            if zone:
                if type_code in ("DO", "HO", "FO"):
                    zone.update_state("O")
                elif type_code == "DC":
                    zone.update_state("N")

        elif category in (
            DMPEventType.SYSTEM_MESSAGE,  # Zs
            DMPEventType.DOOR_ACCESS,  # Zj
            DMPEventType.SCHEDULES,  # Zl
        ):
            pass  # Ignored
        else:
            _LOGGER.warning("%s: Unhandled event category - %s", account, category)

        # update contact time on successful message
        panel.updateContactTime(datetime.now(UTC))
        await self.updateHASS()

    async def updateStatus(self) -> None:
        if self._pydmp_panel is None:
            _LOGGER.error("No panel connection; cannot update status")
            return
        zoneStatus: dict[str, dict[str, str]] = {}
        areaStatus: dict[str, dict[str, str]] = {}
        for _panel in self._panels.values():
            await self._pydmp_panel.update_status()
            # Read zone states from pyDMP
            zoneStatus = {}
            for zone_num, zone_obj in self._pydmp_panel._zones.items():
                zone_num_str = f"{zone_num:03d}"
                status_str = ZONE_STATUS_MAP.get(zone_obj.state, zone_obj.state)
                zoneStatus[zone_num_str] = {
                    "name": zone_obj.name,
                    "status": status_str,
                }

            # Read area states from pyDMP
            areaStatus = {}
            for area_num, area_obj in self._pydmp_panel._areas.items():
                area_num_str = f"{area_num:02d}"
                area_status_str = AREA_STATUS_MAP.get(area_obj.state, area_obj.state)
                areaStatus[area_num_str] = {
                    "name": area_obj.name,
                    "status": area_status_str,
                }

        self.setStatusAttributes(areaStatus, zoneStatus)
        await self.updateHASS()

    def setStatusAttributes(
        self,
        areaStatus: dict[str, dict[str, str]],
        zoneStatus: dict[str, dict[str, str]],
    ) -> None:
        attr: dict[str, str] = {}
        attr[datetime.now().strftime("%Y-%m-%d %H:%M:%S")] = ""
        attr["Areas:"] = ""
        for area in dict(sorted(areaStatus.items())):
            attr["Area: " + area + " - " + areaStatus[area]["name"]] = areaStatus[area][
                "status"
            ]
        attr["Zones:"] = ""
        for zone in dict(sorted(zoneStatus.items())):
            attr["Zone: " + zone + " - " + zoneStatus[zone]["name"]] = zoneStatus[zone][
                "status"
            ]
        self.statusAttributes = attr

    def getStatusAttributes(self) -> dict[str, str]:
        return self.statusAttributes

    async def updateHASS(self) -> None:
        # call to update the hass object
        for callback in self._callbacks:
            await callback()
