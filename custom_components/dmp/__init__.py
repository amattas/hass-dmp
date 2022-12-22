"""The DMP Integration Component"""
import homeassistant.helpers.config_validation as cv
from datetime import datetime
import voluptuous as vol
import asyncio
import logging

from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.template import Template
from homeassistant.helpers.script import Script
from homeassistant.core import callback, Context
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry as dr
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
    STATE_ALARM_TRIGGERED
)
from .const import (DOMAIN, LISTENER, CONF_PANEL_IP, LISTENER,
                    CONF_PANEL_LISTEN_PORT, CONF_PANEL_REMOTE_PORT,
                    CONF_PANEL_ACCOUNT_NUMBER, CONF_PANEL_REMOTE_KEY,
                    CONF_HOME_AREA, CONF_AWAY_AREA, DOMAIN, CONF_ZONES)
from .dmp_codes import DMP_EVENTS, DMP_TYPES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    config = dict(entry.data)
    # Create Options Callback
    unsub_options_update_listener = (
        entry.add_update_listener(options_update_listener)
    )
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
        "alarm_control_panel")
    await hass.config_entries.async_forward_entry_setup(entry, "binary_sensor")
    return True


async def async_unload_entry(hass, entry):
    listener = hass.data[DOMAIN][LISTENER]
    listener.stop


async def options_update_listener(hass, entry):
    if entry.options:
        """Handle options update."""
        config = dict(entry.data)
        options = dict(entry.options)
        config["zones"] = options["zones"]
        await hass.config_entries.async_update_entry(
            entry,
            data=config,
            options={}
            )
        device_registry = dr.async_get(hass)
        entity_registry = er.async_get(hass)
        dr.async_cleanup(hass, device_registry, entity_registry)
        await entry.async_reload(entry.entry_id)


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
        self._area = None
        self._open_close_zones = {}
        self._battery_zones = {}
        self._trouble_zones = {}
        self._bypass_zones = {}
        self._alarm_zones = {}

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
        return self._open_close_zones[zoneNumber]

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

    def getBatteryZone(self, zoneNumber):
        return self._open_close_zones[zoneNumber]

    def getBatteryZones(self):
        return self._open_close_zones

    def updateBatteryZone(self, zoneNum, eventObj):
        if (zoneNum in self._battery_zones):
            zone = self._battery_zones[zoneNum]
            zone.update({"zoneState": eventObj["zoneState"]})
            self._battery_zones[zoneNum] = zone
        else:
            self._battery_zones[zoneNum] = eventObj
        _LOGGER.debug("Battery Zone %s has been updated to %s",
                      zoneNum, eventObj['zoneState'])

    def getTroubleZone(self, zoneNumber):
        return self._trouble_zones[zoneNumber]

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

    def getBypassZone(self, zoneNumber):
        return self._bypass_zones[zoneNumber]

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

    def getAlarmZone(self, zoneNumber):
        return self._alarm_zones[zoneNumber]

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

    def getAccountNumber(self):
        return self._accountNumber

    async def connectAndSend(self, sToSend):
        reader, writer = await asyncio.open_connection(self._ipAddress,
                                                       self._panelPort)

        # drop any existing connection
        writer.write('@ {}!V0\r'.format(self._accountNumber).encode())
        await writer.drain()
        await asyncio.sleep(2)
        # send auth string
        writer.write('@ {}!V2{}\r'.format(self._accountNumber,
                                          self._remoteKey).encode())
        await writer.drain()
        await asyncio.sleep(0.2)
        # write single string to the receiver
        writer.write('@ {}{}\r'.format(self._accountNumber, sToSend).encode())
        await writer.drain()
        await asyncio.sleep(0.2)
        # disconnect
        writer.write('@ {}!V0\r'.format(self._accountNumber).encode())
        await writer.drain()
        # close the socket
        writer.close()
        await writer.wait_closed()

        data = await reader.read(256)
        _LOGGER.debug("DMP: Received data after command: {}".format(data))


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
        self._server = server
        addr = server.sockets[0].getsockname()
        _LOGGER.info(f"Listening on {addr}:{self._port}")
        server.serve_forever()

    async def stop(self, other_arg):
        """ Stop TCP server """
        _LOGGER.info("Stop called. Closing server")
        self._server.close()

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
                # call to update the hass object
                for callback in self._callbacks:
                    await callback()
            else:
                _LOGGER.debug("Connection disconnected")
                connected = False
