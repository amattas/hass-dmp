"""The DMP Integration Component"""

from datetime import datetime, timezone
import logging

from copy import deepcopy

from homeassistant.helpers import entity_registry as er
from homeassistant.components.alarm_control_panel import AlarmControlPanelState
from homeassistant.const import Platform

from pydmp import DMPPanel as PyDMPPanel, DMPStatusServer, parse_s3_message, Zone
from pydmp.const.events import DMPEventType

from .const import (
    CONF_PANEL_IP,
    LISTENER,
    CONF_PANEL_LISTEN_PORT,
    CONF_PANEL_REMOTE_PORT,
    CONF_PANEL_ACCOUNT_NUMBER,
    CONF_PANEL_REMOTE_KEY,
    CONF_HOME_AREA,
    CONF_AWAY_AREA,
    DOMAIN,
    CONF_ZONES,
    CONF_ZONE_NUMBER,
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

# Maps pyDMP single-char zone state to HA status string
ZONE_STATUS_MAP = {
    "N": "Normal",
    "O": "Open",
    "S": "Short",
    "X": "Bypassed",
    "L": "Low Battery",
    "M": "Missing",
}

# Maps pyDMP single-char area state to HA status string
AREA_STATUS_MAP = {
    "A": "Armed",
    "D": "Disarmed",
}


async def async_setup_entry(hass, entry) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    config = dict(entry.data)
    # Create Options Callback
    entry.add_update_listener(options_update_listener)
    _LOGGER.debug("Loaded config %s", config)

    # Create pyDMP panel and connect
    panel_port = config.get(CONF_PANEL_REMOTE_PORT) or 2001
    pydmp_panel = PyDMPPanel(port=panel_port)
    ip = config.get(CONF_PANEL_IP)
    account = config.get(CONF_PANEL_ACCOUNT_NUMBER)
    remote_key = config.get(CONF_PANEL_REMOTE_KEY) or "                "
    await pydmp_panel.connect(ip, account, remote_key)
    await pydmp_panel.start_keepalive()

    # Create status server for realtime events
    listen_port = config.get(CONF_PANEL_LISTEN_PORT)
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


async def async_unload_entry(hass, entry):
    _LOGGER.debug("Unloading entry.")
    status_server = hass.data[DOMAIN][STATUS_SERVER]
    pydmp_panel = hass.data[DOMAIN][PYDMP_PANEL]

    # Stop status server
    await status_server.stop()

    # Stop keepalive and disconnect
    await pydmp_panel.stop_keepalive()
    await pydmp_panel.disconnect()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def options_update_listener(hass, entry):
    _LOGGER.debug("Options flow completed.")
    entity_registry = er.async_get(hass)
    config = dict(entry.data)
    options = dict(entry.options)
    if options:
        _LOGGER.debug("Updated options found: %s" % options)
        """Handle options update."""
        # Remove Entities
        entries = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
        entry_map = {e.entity_id: e for e in entries}
        active_zones = [z[CONF_ZONE_NUMBER] for z in options[CONF_ZONES]]
        _LOGGER.debug("Zones found in options: %s" % active_zones)
        deleted_entries = []
        for emk in entry_map.keys():
            if entry_map[emk].unique_id.split("-")[2] == "zone" and (
                entry_map[emk].unique_id.split("-")[3] not in active_zones
            ):
                deleted_entries.append(emk)
        _LOGGER.debug("Zone entities to be deleted: %s" % deleted_entries)
        for de in deleted_entries:
            entity_registry.async_remove(de)

        # Get and replace zones config
        _LOGGER.debug("Current config zones: %s" % config[CONF_ZONES])
        _LOGGER.debug("New config zones: %s" % config[CONF_ZONES])
        config[CONF_ZONES] = options[CONF_ZONES]
        hass.config_entries.async_update_entry(entry, data=config, options={})
        await hass.config_entries.async_reload(entry.entry_id)


class DMPPanel:
    def __init__(self, hass, config, pydmp_panel=None):
        self._accountNumber = config.get(CONF_PANEL_ACCOUNT_NUMBER)
        self._ipAddress = config.get(CONF_PANEL_IP)
        self._panel_last_contact = None
        self._area = AlarmControlPanelState.DISARMED  # Default Value
        self._pydmp_panel = pydmp_panel
        self._open_close_zones = {}
        self._battery_zones = {}
        self._trouble_zones = {}
        self._bypass_zones = {}
        self._alarm_zones = {}
        self._status_zones = {}

    def __str__(self):
        return "DMP Panel with account number %s at addr %s" % (
            self._accountNumber,
            self._ipAddress,
        )

    def updateContactTime(self, contactTime):
        self._panel_last_contact = contactTime

    def getContactTime(self):
        return self._panel_last_contact

    def updateArea(self, eventObj):
        self._area = eventObj
        _LOGGER.debug("Area has been updated to %s", eventObj["areaState"])

    def getArea(self):
        return self._area

    def getOpenCloseZone(self, zoneNumber):
        if zoneNumber in self._open_close_zones:
            return self._open_close_zones[zoneNumber]
        else:
            return None

    def getOpenCloseZones(self):
        return self._open_close_zones

    def updateOpenCloseZone(self, zoneNum, eventObj):
        if zoneNum in self._open_close_zones:
            zone = self._open_close_zones[zoneNum]
            zone.update({"zoneState": eventObj["zoneState"]})
            self._open_close_zones[zoneNum] = zone
        else:
            self._open_close_zones[zoneNum] = eventObj
        _LOGGER.debug(
            "Open Close Zone %s has been updated to %s", zoneNum, eventObj["zoneState"]
        )
        self.updateStatusZone(zoneNum, eventObj)

    def getBatteryZone(self, zoneNumber):
        if zoneNumber in self._battery_zones:
            return self._battery_zones[zoneNumber]
        else:
            return None

    def getBatteryZones(self):
        return self._battery_zones

    def updateBatteryZone(self, zoneNum, eventObj):
        if zoneNum in self._battery_zones:
            zone = self._battery_zones[zoneNum]
            zone.update({"zoneState": eventObj["zoneState"]})
            self._battery_zones[zoneNum] = zone
        else:
            self._battery_zones[zoneNum] = eventObj
        _LOGGER.debug(
            "Battery Zone %s has been updated to %s", zoneNum, eventObj["zoneState"]
        )
        self.updateStatusZone(zoneNum, eventObj)

    def getTroubleZone(self, zoneNumber):
        if zoneNumber in self._trouble_zones:
            return self._trouble_zones[zoneNumber]
        else:
            return None

    def getTroubleZones(self):
        return self._trouble_zones

    def updateTroubleZone(self, zoneNum, eventObj):
        if zoneNum in self._trouble_zones:
            zone = self._trouble_zones[zoneNum]
            zone.update({"zoneState": eventObj["zoneState"]})
            self._trouble_zones[zoneNum] = zone
        else:
            self._trouble_zones[zoneNum] = eventObj
        _LOGGER.debug(
            "Trouble Zone %s has been updated to %s", zoneNum, eventObj["zoneState"]
        )
        self.updateStatusZone(zoneNum, eventObj)

    def getBypassZone(self, zoneNumber):
        if zoneNumber in self._bypass_zones:
            return self._bypass_zones[zoneNumber]
        else:
            return None

    def getBypassZones(self):
        return self._bypass_zones

    def updateBypassZone(self, zoneNum, eventObj):
        if zoneNum in self._bypass_zones:
            zone = self._bypass_zones[zoneNum]
            zone.update({"zoneState": eventObj["zoneState"]})
            self._bypass_zones[zoneNum] = zone
        else:
            self._bypass_zones[zoneNum] = eventObj
        _LOGGER.debug(
            "Bypass Zone %s has been updated to %s", zoneNum, eventObj["zoneState"]
        )
        self.updateStatusZone(zoneNum, eventObj)

    def getAlarmZone(self, zoneNumber):
        if zoneNumber in self._alarm_zones:
            return self._alarm_zones[zoneNumber]
        else:
            return None

    def getAlarmZones(self):
        return self._alarm_zones

    def updateAlarmZone(self, zoneNum, eventObj):
        if zoneNum in self._alarm_zones:
            zone = self._alarm_zones[zoneNum]
            zone.update({"zoneState": eventObj["zoneState"]})
            self._alarm_zones[zoneNum] = zone
        else:
            self._alarm_zones[zoneNum] = eventObj
        _LOGGER.debug(
            "Alarm Zone %s has been updated to %s", zoneNum, eventObj["zoneState"]
        )
        self.updateStatusZone(zoneNum, eventObj)

    def getStatusZone(self, zoneNumber):
        return self._status_zones[zoneNumber]

    def getStatusZones(self):
        return self._status_zones

    def updateStatusZone(self, zoneNum, eventObj):
        statusObj = deepcopy(eventObj)
        zone_state = "Ready"
        if self.getAlarmZone(zoneNum) and self.getAlarmZone(zoneNum)["zoneState"]:
            zone_state = "Alarm"
        elif self.getTroubleZone(zoneNum) and self.getTroubleZone(zoneNum)["zoneState"]:
            zone_state = "Trouble"
        elif self.getBypassZone(zoneNum) and self.getBypassZone(zoneNum)["zoneState"]:
            zone_state = "Bypass"
        elif self.getBatteryZone(zoneNum) and self.getBatteryZone(zoneNum)["zoneState"]:
            zone_state = "Low Battery"
        elif (
            self.getOpenCloseZone(zoneNum)
            and self.getOpenCloseZone(zoneNum)["zoneState"]
        ):
            zone_state = "Open"
        if zoneNum in self._status_zones:
            zone = self._status_zones[zoneNum]
            zone.update({"zoneState": zone_state})
            self._status_zones[zoneNum] = zone
        else:
            statusObj.update({"zoneState": zone_state})
            self._status_zones[zoneNum] = statusObj

        _LOGGER.debug("Status Zone %s has been updated to %s", zoneNum, zone_state)

    def getAccountNumber(self):
        return self._accountNumber

    async def _zone_command(self, zone_num, command):
        zone_int = int(zone_num)
        if zone_int in self._pydmp_panel._zones:
            await getattr(self._pydmp_panel._zones[zone_int], command)()
        else:
            zone = Zone(self._pydmp_panel, zone_int)
            await getattr(zone, command)()

    async def bypass_zone(self, zone_num):
        await self._zone_command(zone_num, "bypass")

    async def restore_zone(self, zone_num):
        await self._zone_command(zone_num, "restore")


class DMPListener:
    def __init__(self, hass, config, pydmp_panel=None, status_server=None):
        self._hass = hass
        self._domain = config
        self._home_area = config[CONF_HOME_AREA]
        self._away_area = config[CONF_AWAY_AREA]
        self._port = config.get(CONF_PANEL_LISTEN_PORT)
        self._pydmp_panel = pydmp_panel
        self._status_server = status_server
        self._panels = {}
        self.statusAttributes = {}
        # callbacks to call when an event gets posted in
        self._callbacks = set()

        # Register S3 event callback with status server
        if status_server is not None:
            status_server.register_callback(self._handle_s3_event)

    def __str__(self):
        return "DMP Listener on port %s" % (self._port)

    def register_callback(self, callback):
        """Allow callbacks to be registered for when dict entries change"""
        self._callbacks.add(callback)

    def remove_callback(self, callback):
        """Allow callbacks to be de-registered"""
        self._callbacks.discard(callback)

    def addPanel(self, panelToAdd):
        self._panels[panelToAdd.getAccountNumber()] = panelToAdd

    def getPanels(self):
        return self._panels

    async def _handle_s3_event(self, msg):
        """Handle incoming S3 event from DMPStatusServer."""
        try:
            event = parse_s3_message(msg)
        except Exception:
            _LOGGER.warning(
                "Failed to parse S3 message: %s",
                msg.raw if hasattr(msg, "raw") else msg,
            )
            return

        account = event.account.strip()
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

        if category == DMPEventType.WIRELESS_LOW_BATTERY:  # Zd
            zoneObj = {"zoneNumber": zone_number, "zoneState": True}
            panel.updateBatteryZone(zone_number, zoneObj)

        elif category == DMPEventType.ZONE_BYPASS:  # Zx
            zoneObj = {"zoneNumber": zone_number, "zoneState": True}
            panel.updateBypassZone(zone_number, zoneObj)

        elif category in (
            DMPEventType.ZONE_FAIL,  # Zf
            DMPEventType.WIRELESS_ZONE_MISSING,  # Zh
            DMPEventType.ZONE_TROUBLE,  # Zt
            DMPEventType.ZONE_FAULT,  # Zw
        ):
            zoneObj = {"zoneNumber": zone_number, "zoneState": True}
            panel.updateTroubleZone(zone_number, zoneObj)

        elif category in (
            DMPEventType.ZONE_RESET,  # Zy
            DMPEventType.ZONE_RESTORE,  # Zr
        ):
            zoneObj = {"zoneNumber": zone_number, "zoneState": False}
            panel.updateOpenCloseZone(zone_number, zoneObj)
            panel.updateTroubleZone(zone_number, zoneObj)
            panel.updateBatteryZone(zone_number, zoneObj)
            panel.updateBypassZone(zone_number, zoneObj)
            panel.updateAlarmZone(zone_number, zoneObj)

        elif category in (
            DMPEventType.ZONE_ALARM,  # Za
            DMPEventType.ZONE_FORCE_ARM,  # Zb
        ):
            zoneObj = {"zoneNumber": zone_number, "zoneState": True}
            panel.updateAlarmZone(zone_number, zoneObj)
            areaObj = {
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
                areaState = AlarmControlPanelState.DISARMED
            areaObj = {"areaName": area_name, "areaState": areaState}
            _LOGGER.debug("Updated area: %s" % areaObj)
            panel.updateArea(areaObj)

        elif category == DMPEventType.REAL_TIME_STATUS:  # Zc
            if type_code in ("DO", "HO", "FO"):
                zoneObj = {"zoneNumber": zone_number, "zoneState": True}
                panel.updateOpenCloseZone(zone_number, zoneObj)
            elif type_code == "DC":
                zoneObj = {"zoneNumber": zone_number, "zoneState": False}
                panel.updateOpenCloseZone(zone_number, zoneObj)

        elif category in (
            DMPEventType.SYSTEM_MESSAGE,  # Zs
            DMPEventType.DOOR_ACCESS,  # Zj
            DMPEventType.SCHEDULES,  # Zl
        ):
            pass  # Ignored
        else:
            _LOGGER.warning("%s: Unhandled event category - %s", account, category)

        # update contact time on successful message
        panel.updateContactTime(datetime.now(timezone.utc))
        await self.updateHASS()

    async def updateStatus(self):
        for panelName, panel in self._panels.items():
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

            # Update HA zone state dicts based on status
            for zone, zoneData in zoneStatus.items():
                faultZone = {"zoneNumber": zone, "zoneState": True}
                clearZone = {"zoneNumber": zone, "zoneState": False}

                if zone in panel._open_close_zones:
                    if zoneData["status"] == "Open" or zoneData["status"] == "Short":
                        panel.updateOpenCloseZone(zone, faultZone)
                    elif zoneData["status"] == "Normal":
                        panel.updateOpenCloseZone(zone, clearZone)
                if zone in panel._bypass_zones:
                    if zoneData["status"] == "Bypassed":
                        panel.updateBypassZone(zone, faultZone)
                    else:
                        panel.updateBypassZone(zone, clearZone)
                if zone in panel._trouble_zones:
                    if zoneData["status"] == "Missing":
                        panel.updateTroubleZone(zone, faultZone)
                    elif zoneData["status"] == "Normal":
                        panel.updateTroubleZone(zone, clearZone)
                if zone in panel._battery_zones:
                    if zoneData["status"] == "Low Battery":
                        panel.updateBatteryZone(zone, faultZone)
                    elif zoneData["status"] == "Normal":
                        panel.updateBatteryZone(zone, clearZone)
        self.setStatusAttributes(areaStatus, zoneStatus)
        await self.updateHASS()

    def setStatusAttributes(self, areaStatus, zoneStatus):
        attr = {}
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

    def getStatusAttributes(self):
        return self.statusAttributes

    async def updateHASS(self):
        # call to update the hass object
        for callback in self._callbacks:
            await callback()
