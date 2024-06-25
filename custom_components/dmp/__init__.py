"""The DMP Integration Component"""
import homeassistant.helpers.config_validation as cv
from datetime import datetime
import asyncio
import logging

from copy import deepcopy
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers.event import (
    TrackTemplate,
    async_track_template_result
    )
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_DISARMED,
    STATE_ALARM_TRIGGERED,
    Platform
)
from .const import (DOMAIN, LISTENER, CONF_PANEL_IP, LISTENER,
                    CONF_PANEL_LISTEN_PORT, CONF_PANEL_REMOTE_PORT,
                    CONF_PANEL_ACCOUNT_NUMBER, CONF_PANEL_REMOTE_KEY,
                    CONF_HOME_AREA, CONF_AWAY_AREA, DOMAIN, CONF_ZONES,
                    CONF_ZONE_NUMBER)
from .dmp_codes import DMP_EVENTS, DMP_TYPES
from .dmp_sender import DMPSender

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass, entry) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    config = dict(entry.data)
    # Create Options Callback
    entry.add_update_listener(options_update_listener)
    # if entry.options:
    #     config.update(entry.options)
    _LOGGER.debug("Loaded config %s", config)
    # Create and start the DMP Listener
    listener = DMPListener(hass, config)
    await listener.start()
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, listener.stop)
    hass.data[DOMAIN][LISTENER] = listener
    hass.data[DOMAIN][entry.entry_id] = config
    panel = DMPPanel(hass, config)
    _LOGGER.debug("Panel account number: %s", panel.getAccountNumber())
    listener.addPanel(panel)
    _LOGGER.debug("Panels attached to listener: %s",
                  str(listener.getPanels()))
    await hass.config_entries.async_forward_entry_setup(
        entry,
        "alarm_control_panel"
    )
    await hass.config_entries.async_forward_entry_setup(entry, "binary_sensor")
    await hass.config_entries.async_forward_entry_setup(entry, "sensor")
    await hass.config_entries.async_forward_entry_setup(entry, "switch")
    await hass.config_entries.async_forward_entry_setup(entry, "button")
    hass.async_create_task(listener.updateStatus())
    return True


async def async_unload_entry(hass, entry):
    _LOGGER.debug("Unloading entry.")
    listener = hass.data[DOMAIN][LISTENER]
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
        ) and await listener.stop()
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
        entries = er.async_entries_for_config_entry(
            entity_registry, entry.entry_id
        )
        entry_map = {e.entity_id: e for e in entries}
        active_zones = [
            z[CONF_ZONE_NUMBER]
            for z in options[CONF_ZONES]
        ]
        _LOGGER.debug("Zones found in options: %s" % active_zones)
        deleted_entries = []
        for emk in entry_map.keys():
            if (
                entry_map[emk].unique_id.split('-')[2] == 'zone'
                and (
                    entry_map[emk].unique_id.split('-')[3]
                    not in active_zones
                    )
            ):
                deleted_entries.append(emk)
        _LOGGER.debug("Zone entities to be deleted: " % deleted_entries)
        for de in deleted_entries:
            entity_registry.async_remove(de)

        # Get and replace zones config
        _LOGGER.debug("Current config zones: %s" % config[CONF_ZONES])
        _LOGGER.debug("New config zones: %s" % config[CONF_ZONES])
        config[CONF_ZONES] = options[CONF_ZONES]
        hass.config_entries.async_update_entry(
            entry,
            data=config,
            options={}
            )
        await hass.config_entries.async_reload(entry.entry_id)


class DMPPanel():
    def __init__(self, hass, config):
        self._hass = hass
        self._domain = config
        self._accountNumber = config.get(CONF_PANEL_ACCOUNT_NUMBER)
        self._ipAddress = config.get(CONF_PANEL_IP)
        # if no remote key specified, then send 16 spaces, this is required or
        # auth will fail
        self._remoteKey = (config.get(CONF_PANEL_REMOTE_KEY)
                           or "                ")
        self._panelPort = config.get(CONF_PANEL_REMOTE_PORT) or 2001
        self._panel_last_contact = None
        self._area = STATE_ALARM_DISARMED  # Default Value
        self._dmpSender = DMPSender(self._ipAddress, self._panelPort, self._accountNumber, self._remoteKey)
        self._open_close_zones = {}
        self._battery_zones = {}
        self._trouble_zones = {}
        self._bypass_zones = {}
        self._alarm_zones = {}
        self._status_zones = {}

    def __str__(self):
        return ('DMP Panel with account number %s at addr %s'
                % (self._accountNumber, self._ipAddress))

    def updateContactTime(self, contactTime):
        self._panel_last_contact = contactTime

    def getContactTime(self):
        return self._panel_last_contact

    def updateArea(self, eventObj):
        self._area = eventObj
        _LOGGER.debug("Area has been updated to %s",
                      eventObj['areaState'])

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
        if (zoneNum in self._open_close_zones):
            zone = self._open_close_zones[zoneNum]
            zone.update({"zoneState": eventObj["zoneState"]})
            self._open_close_zones[zoneNum] = zone
        else:
            self._open_close_zones[zoneNum] = eventObj
        _LOGGER.debug("Open Close Zone %s has been updated to %s",
                      zoneNum, eventObj['zoneState'])
        self.updateStatusZone(zoneNum, eventObj)

    def getBatteryZone(self, zoneNumber):
        if zoneNumber in self._battery_zones:
            return self._battery_zones[zoneNumber]
        else:
            return None

    def getBatteryZones(self):
        return self._battery_zones

    def updateBatteryZone(self, zoneNum, eventObj):
        if (zoneNum in self._battery_zones):
            zone = self._battery_zones[zoneNum]
            zone.update({"zoneState": eventObj["zoneState"]})
            self._battery_zones[zoneNum] = zone
        else:
            self._battery_zones[zoneNum] = eventObj
        _LOGGER.debug("Battery Zone %s has been updated to %s",
                      zoneNum, eventObj['zoneState'])
        self.updateStatusZone(zoneNum, eventObj)

    def getTroubleZone(self, zoneNumber):
        if zoneNumber in self._trouble_zones:
            return self._trouble_zones[zoneNumber]
        else:
            return None

    def getTroubleZones(self):
        return self._trouble_zones

    def updateTroubleZone(self, zoneNum, eventObj):
        if (zoneNum in self._trouble_zones):
            zone = self._trouble_zones[zoneNum]
            zone.update({"zoneState": eventObj["zoneState"]})
            self._trouble_zones[zoneNum] = zone
        else:
            self._trouble_zones[zoneNum] = eventObj
        _LOGGER.debug("Trouble Zone %s has been updated to %s",
                      zoneNum, eventObj['zoneState'])
        self.updateStatusZone(zoneNum, eventObj)

    def getBypassZone(self, zoneNumber):
        if zoneNumber in self._bypass_zones:
            return self._bypass_zones[zoneNumber]
        else:
            return None

    def getBypassZones(self):
        return self._bypass_zones

    def updateBypassZone(self, zoneNum, eventObj):
        if (zoneNum in self._bypass_zones):
            zone = self._bypass_zones[zoneNum]
            zone.update({"zoneState": eventObj["zoneState"]})
            self._bypass_zones[zoneNum] = zone
        else:
            self._bypass_zones[zoneNum] = eventObj
        _LOGGER.debug("Bypass Zone %s has been updated to %s",
                      zoneNum, eventObj['zoneState'])
        self.updateStatusZone(zoneNum, eventObj)

    def getAlarmZone(self, zoneNumber):
        if zoneNumber in self._alarm_zones:
            return self._alarm_zones[zoneNumber]
        else:
            return None

    def getAlarmZones(self):
        return self._alarm_zones

    def updateAlarmZone(self, zoneNum, eventObj):
        if (zoneNum in self._alarm_zones):
            zone = self._alarm_zones[zoneNum]
            zone.update({"zoneState": eventObj["zoneState"]})
            self._alarm_zones[zoneNum] = zone
        else:
            self._alarm_zones[zoneNum] = eventObj
        _LOGGER.debug("Alarm Zone %s has been updated to %s",
                      zoneNum, eventObj['zoneState'])
        self.updateStatusZone(zoneNum, eventObj)

    def getStatusZone(self, zoneNumber):
        return self._status_zones[zoneNumber]

    def getStatusZones(self):
        return self._status_zones

    def updateStatusZone(self, zoneNum, eventObj):
        statusObj = deepcopy(eventObj)
        zone_state = 'Ready'
        if (self.getAlarmZone(zoneNum)
           and self.getAlarmZone(zoneNum)['zoneState']):
            zone_state = 'Alarm'
        elif (self.getTroubleZone(zoneNum)
              and self.getTroubleZone(zoneNum)['zoneState']):
            zone_state = 'Trouble'
        elif (self.getBypassZone(zoneNum)
              and self.getBypassZone(zoneNum)['zoneState']):
            zone_state = 'Bypass'
        elif (self.getBatteryZone(zoneNum)
              and self.getBatteryZone(zoneNum)['zoneState']):
            zone_state = 'Bypass'
        elif (self.getOpenCloseZone(zoneNum)
              and self.getOpenCloseZone(zoneNum)['zoneState']):
            zone_state = 'Open'
        if (zoneNum in self._status_zones):
            zone = self._status_zones[zoneNum]
            zone.update({"zoneState": zone_state})
            self._status_zones[zoneNum] = zone
        else:
            statusObj.update({"zoneState": zone_state})
            self._status_zones[zoneNum] = statusObj

        _LOGGER.debug("Status Zone %s has been updated to %s",
                      zoneNum, zone_state)

    def getAccountNumber(self):
        return self._accountNumber
    
class DMPListener():
    def __init__(self, hass, config):
        self._hass = hass
        self._domain = config
        self._home_area = config[CONF_HOME_AREA]
        self._away_area = config[CONF_AWAY_AREA]
        self._port = config.get(CONF_PANEL_LISTEN_PORT)
        self._server = None
        self._panels = {}
        # callbacks to call when an event gets posted in
        self._callbacks = set()

    def __str__(self):
        return 'DMP Listener on port %s' % (self._port)

    def register_callback(self, callback):
        """ Allow callbacks to be registered for when dict entries change """
        self._callbacks.add(callback)

    def remove_callback(self, callback):
        """ Allow callbacks to be de-registered """
        self._callbacks.discard(callback)

    def addPanel(self, panelToAdd):
        self._panels[panelToAdd.getAccountNumber()] = panelToAdd

    def getPanels(self):
        return self._panels

    def _getS3Segment(self, charToFind, input):
        start = input.find(charToFind)
        if (start == -1):
            return ""
        tempString = input[start+len(charToFind):]
        end = tempString.find('\\')
        returnString = tempString[0:end].strip()
        return returnString

    def _searchS3Segment(self, input):
        # example data to be passed to the function: 009"PULL STATION
        # find the single double quote that separates the number from name
        quotePos = input.find('"')
        # split the number and name out
        number = input[:quotePos]
        name = input[quotePos + 1:]
        if name is None:
            name = ""
        if number is None:
            number = ""
        _LOGGER.debug("S3Search result Number: %s Name: %s" % (number, name))
        return (number, name)

    def _event_types(self, arg):
        return (DMP_TYPES.get(arg, "Unknown Type " + arg))

    def _events(self, arg):
        return (DMP_EVENTS.get(arg, "Unknown Event " + arg))

    async def start(self):
        await self.listen()

    async def listen(self):
        """ Start TCP server listening on configured port """
        server = await asyncio.start_server(self.handle_connection, "0.0.0.0",
                                            self._port)
        addr = server.sockets[0].getsockname()
        _LOGGER.info(f"Listening on {addr}:{self._port}")
        server.serve_forever()
        self._server = server

    async def stop(self):
        """ Stop TCP server """
        _LOGGER.info("Stop called. Closing server")
        # Make sure sever is closed before reloading
        self._server.close()
        await self._server.wait_closed()
        return True

    async def handle_connection(self, reader, writer):
        """ Parse packets from DMP panel """
        peer = writer.get_extra_info("peername")
        _LOGGER.info(f"Connection from {peer}")
        connected = True
        while connected:
            data = await reader.read(2048)
            data = data.decode("utf-8")
            _LOGGER.debug('Raw Data: \'{}\''.format(data))
            if data:
                acctNum = data[7:12]
                _LOGGER.debug('\tAcct Num: \'{}\''.format(acctNum))
                eventCode = data[19:21]
                _LOGGER.debug('\tEvent Code: \'{}\''.format(eventCode))
                zoneNumber = None
                try:
                    panel = self._panels[acctNum.strip()]
                except e:
                    _LOGGER.warn("Unknown account number sending data - %s",
                                 acctNum.strip())
                    break
                _LOGGER.debug("Received data from panel %s: %s",
                              panel.getAccountNumber(), data)

                eventObj = {"accountNumber": acctNum.strip()}

                if (data.find(acctNum + ' s0700240') != -1):
                    _LOGGER.info('{}: Received checkin message'
                                 .format(acctNum))
                elif (data.find(acctNum + ' S71') != -1):  # Time Update
                    # For networking monitoring we should not respond to
                    # this and shouldn't see it on the integration port.
                    pass
                elif (eventCode == 'Zs'):  # System Message
                    pass
                elif (eventCode == 'Zj'):  # Door / Panel Access
                    pass
                elif (eventCode == 'Zd'):  # Battery
                    zoneNumber = self._searchS3Segment(
                        self._getS3Segment('\\z', data)
                    )[0]
                    zoneObj = {
                        "zoneNumber": zoneNumber,
                        "zoneState": True
                        }
                    panel.updateBatteryZone(zoneNumber, zoneObj)
                elif (eventCode == 'Zx'):  # Bypass
                    zoneNumber = self._searchS3Segment(
                        self._getS3Segment('\\z', data)
                    )[0]
                    zoneObj = {
                        "zoneNumber": zoneNumber,
                        "zoneState": True
                        }
                    panel.updateBypassZone(zoneNumber, zoneObj)
                elif (  # Trouble
                    eventCode == 'Zf'
                    or eventCode == 'Zh'
                    or eventCode == 'Zt'
                    or eventCode == 'Zw'
                ):
                    zoneNumber = self._searchS3Segment(
                        self._getS3Segment('\\z', data)
                    )[0]
                    zoneObj = {
                        "zoneNumber": zoneNumber,
                        "zoneState": True
                        }
                    panel.updateBypassZone(zoneNumber, zoneObj)
                elif (   # Restore & Reset
                    eventCode == 'Zy'
                    or eventCode == 'Zr'
                ):
                    zoneNumber = self._searchS3Segment(
                        self._getS3Segment('\\z', data)
                    )[0]
                    zoneObj = {
                        "zoneNumber": zoneNumber,
                        "zoneState": False
                        }
                    panel.updateBypassZone(zoneNumber, zoneObj)
                    panel.updateTroubleZone(zoneNumber, zoneObj)
                    panel.updateBatteryZone(zoneNumber, zoneObj)
                    panel.updateBypassZone(zoneNumber, zoneObj)
                    panel.updateAlarmZone(zoneNumber, zoneObj)
                elif (eventCode == 'Za' or eventCode == 'Zb'):  # Alarm
                    systemCode = self._getS3Segment('\\t', data)[1:]
                    codeName = self._events(eventCode)
                    typeName = self._event_types(systemCode)
                    out = self._searchS3Segment(
                        self._getS3Segment('\\z', data)
                        )
                    zoneNumber = out[0]
                    zoneName = out[1]
                    out = self._searchS3Segment(
                        self._getS3Segment('\\a', data)
                        )
                    areaNumber = out[0]
                    areaName = out[1]
                    areaObj = {"areaName": areaName,
                               "areaState": STATE_ALARM_TRIGGERED}
                    panel.updateArea(areaObj)
                elif (eventCode == 'Zq'):  # Arming Status
                    systemCode = self._getS3Segment('\\t', data)[1:]
                    out = self._searchS3Segment(
                        self._getS3Segment('\\a', data)
                        )
                    areaNumber = out[0]
                    areaName = out[1]
                    if (systemCode == "OP"):  # Disarm
                        areaState = STATE_ALARM_DISARMED
                        # do a manual status query - bypassed zones are reset but no message for it 
                        self._hass.async_create_task(self.updateStatus())
                    elif (systemCode == "CL"):  # Arm
                        if (areaNumber[1:] == self._home_area):
                            # Make sure we're not already armed away
                            if (
                                panel.getArea()["areaState"] !=
                                    STATE_ALARM_ARMED_AWAY):
                                areaState = STATE_ALARM_ARMED_HOME
                        else:
                            areaState = STATE_ALARM_ARMED_AWAY
                    areaObj = {"areaName": areaName,
                               "areaState": areaState}
                    _LOGGER.debug("Updated area: %s" % areaObj)
                    panel.updateArea(areaObj)
                elif (eventCode == 'Zc'):  # Device status
                    systemCode = self._getS3Segment('\\t', data)[1:]
                    codeName = self._event_types(systemCode)
                    zoneNumber = self._getS3Segment('\\z', data)
                    if (
                        systemCode == "DO"
                        or systemCode == "HO"
                        or systemCode == "FO"
                    ):  # Door Open
                        zoneObj = {
                            "zoneNumber": zoneNumber,
                            "zoneState": True
                            }
                        panel.updateOpenCloseZone(zoneNumber, zoneObj)
                    elif (systemCode == "DC"):  # Door Closed
                        zoneObj = {
                            "zoneNumber": zoneNumber,
                            "zoneState": False
                            }
                        panel.updateOpenCloseZone(zoneNumber, zoneObj)
                elif (eventCode == 'Zl'):  # Schedule Change
                    pass
                else:
                    _LOGGER.warning('{}: Unknown event received - {}'
                                    .format(acctNum, data))

                ackString = '\x02' + acctNum + '\x06\x0D'
                writer.write(ackString.encode())
                # update contact time last to ensure we only log contact time
                # on a successful message
                panel.updateContactTime(datetime.utcnow())
                await self.updateHASS()
            else:
                _LOGGER.debug("Connection disconnected")
                connected = False

    async def updateStatus(self):
        for panelName, panel in self._panels.items():
            status = await panel._dmpSender.status()
            areaStatus = status[0]
            zoneStatus = status[1]
            for zone, zoneData in zoneStatus.items():
                faultZone = {"zoneNumber": zone, "zoneState": True}
                clearZone = {"zoneNumber": zone, "zoneState": False}

                if zone in panel._open_close_zones:
                    if zoneData['status'] == 'Open' or zoneData['status'] == 'Short':
                        panel.updateOpenCloseZone(zone, faultZone)
                    elif zoneData['status'] == 'Normal':
                        panel.updateOpenCloseZone(zone, clearZone)
                if zone in panel._bypass_zones:
                    if zoneData['status'] == 'Bypassed':
                        panel.updateBypassZone(zone, faultZone)
                    else:
                        panel.updateBypassZone(zone, clearZone)
                if zone in panel._trouble_zones:
                    if zoneData['status'] == 'Missing':
                        panel.updateTroubleZone(zone, faultZone)
                    elif zoneData['status'] == 'Normal':
                        panel.updateTroubleZone(zone, clearZone)
                if zone in panel._battery_zones:
                    if zoneData['status'] == 'Low Battery':
                        panel.updateBatteryZone(zone, faultZone)
                    elif zoneData['status'] == 'Normal':
                        panel.updateBatteryZone(zone, clearZone)
        await self.updateHASS()

    async def updateHASS(self):
        # call to update the hass object
        for callback in self._callbacks:
            await callback()
