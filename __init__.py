"""The DMP Integration Component"""

import asyncio
import logging
from datetime import datetime

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.event import TrackTemplate, async_track_template_result
from homeassistant.helpers.template import Template
from homeassistant.helpers.script import Script
from homeassistant.core import callback, Context
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STOP,
    CONF_VALUE_TEMPLATE,
    CONF_ATTRIBUTE,
    CONF_ENTITY_ID,
    STATE_ON,
    STATE_OFF,
    CONF_SERVICE,
    CONF_SERVICE_DATA,
)

from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_DISARMED,
    STATE_ALARM_TRIGGERED,
)

from .const import DOMAIN, LISTENER, CONF_LISTEN_PORT, CONF_PANELS, CONF_PANEL_IP, CONF_PANEL_ACCOUNT_NUMBER, CONF_PANEL_REMOTE_KEY, CONF_PANEL_REMOTE_PORT
from .dmp_codes import DMP_EVENTS, DMP_TYPES

_LOGGER = logging.getLogger(__name__)

PANEL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PANEL_IP): cv.string,
        vol.Required(CONF_PANEL_ACCOUNT_NUMBER): cv.string,
        vol.Optional(CONF_PANEL_REMOTE_KEY): cv.string,
        vol.Optional(CONF_PANEL_REMOTE_PORT): cv.port,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_LISTEN_PORT): cv.port,
                vol.Optional(CONF_PANELS): vol.All(cv.ensure_list, [PANEL_SCHEMA]),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


PLATFORMS = [
    "alarm_control_panel",
]


async def async_setup(hass, config):
    """ Set up the DMP component """

    if config.get(DOMAIN) is not None:
        hass.data[DOMAIN] = {}
        #create and start the listener
        listener = DMPListener(hass, config[DOMAIN])
        await listener.start()
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, listener.stop)
        hass.data[DOMAIN][LISTENER] = listener

        for i in config[DOMAIN][CONF_PANELS]:
            panel = DMPPanel(hass, i)
        _LOGGER.debug("Panel account number: %s", panel.getAccountNumber())

        listener.addPanel(panel)

        _LOGGER.debug("Panels attached to listener: %s", str(listener.getPanels()))

        #for platform in PLATFORMS:
        #    await async_load_platform(hass, platform, DOMAIN, {}, config)

    return True

class DMPPanel():
    def __init__(self, hass, config):
        self._hass = hass
        self._domain = config
        self._accountNumber = config.get(CONF_PANEL_ACCOUNT_NUMBER)
        self._ipAddress = config.get(CONF_PANEL_IP)
        #if no remote key specified, then send 16 spaces, this is required or auth will fail
        self._remoteKey = config.get(CONF_PANEL_REMOTE_KEY) or "                "
        self._panelPort = config.get(CONF_PANEL_REMOTE_PORT) or 2001
        self._panel_last_contact = None
        self._zones = {}
        self._areas = {}
        self._doors = {}

    def __str__(self):
        return 'DMP Panel with account number %s at addr %s' % (self._accountNumber, self._ipAddress)

    def updateContactTime(self, contactTime):
        self._panel_last_contact = contactTime
    
    def getContactTime(self):
        return self._panel_last_contact

    def updateArea(self, areaNum, eventObj):
        self._areas[areaNum] = eventObj
        _LOGGER.debug("Area %s has been updated", areaNum)

    def getArea(self, areaNumber):
        return self._areas[areaNumber]

    def getAreas(self):
        return self._areas

    def getAccountNumber(self):
        return self._accountNumber
    
    async def connectAndSend(self, sToSend):
        reader, writer = await asyncio.open_connection(self._ipAddress, self._panelPort)

        # drop any existing connection
        writer.write('@ {}!V0\r'.format(self._accountNumber).encode())
        await writer.drain()
        await asyncio.sleep(2)
        # send auth string
        writer.write('@ {}!V2{}\r'.format(self._accountNumber, self._remoteKey).encode())
        await writer.drain()
        await asyncio.sleep(0.2)
        # write single string to the receiver
        writer.write('@ {}{}\r'.format(self._accountNumber, sToSend).encode())
        await writer.drain()
        await asyncio.sleep(0.2)
        #disconnect
        writer.write('@ {}!V0\r'.format(self._accountNumber).encode())
        await writer.drain()
        #close the socket
        writer.close()
        await writer.wait_closed()

        data = await reader.read(256)
        _LOGGER.debug("DMP: Received data after command: {}".format(data))
class DMPListener():
    def __init__(self, hass, config):
        self._hass = hass
        self._domain = config
        self._port = config.get(CONF_LISTEN_PORT)
        self._server = None
        self._panels = {}
        #callbacks to call when an event gets posted in
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
        #find the char we're looking for
        start = input.find(charToFind) + 1
        #index -1 means not found, but plus one from above, so we're really looking for index 0 to mean none found
        #returning None breaks it so we return empty string
        if (start == 0):
            return ""
        #strip everything before it
        tempString = input[start:]
        #search substring till we find the \ delimeter (double \ so we don't escape the quote)
        end = tempString.find('\\')
        #strip everything after and return it, as well as strip the letter and space
        return tempString[2:end]

    def _searchS3Segment(self, input):
        #example data to be passed to the function: 009"PULL STATION
        #find the single double quote that separates the number from name
        quotePos = input.find('"')
        #split the number and name out
        number = input[:quotePos]
        name = input[quotePos + 1:]
        if name is None:
            name = ""
        if number is None:
            number = ""
        return number, name

    def _event_types(self, arg):
        return (DMP_TYPES.get(arg, "Unknown Type " + arg))

    def _events(self, arg):
        return (DMP_EVENTS.get(arg, "Unknown Event " + arg))

    async def start(self):
        await self.listen()

    async def listen(self):
        """ Start TCP server listening on configured port """
        server = await asyncio.start_server(self.handle_connection, "0.0.0.0", self._port)
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

                if data:
                    acctNum = data[7:12]
                    eventCode = data[13:15]
                    areaNumber = None
                    try:
                        panel = self._panels[acctNum.strip()]
                    except:
                        _LOGGER.warn("Unknown account number sending data - %s", acctNum.strip())
                        break
                    _LOGGER.debug("Received data from panel %s: %s", panel.getAccountNumber(), data)
                    
                    eventObj = {"accountNumber": acctNum.strip(),}

                    if (data.find(acctNum + ' s0700240') != -1):
                        _LOGGER.info('{}: Received checkin message'.format(acctNum))
                    elif (data.find(acctNum + ' S71') != -1):
                        #time update request, if we see this it means we're on network monitoring not pc log
                        #normally the receiver will send back the current time to keep the panel in sync,
                        #but i don't have any reference for how to send that so we'll drop it on the floor
                        _LOGGER.info('{}: Received request for time update'.format(acctNum))
                        
                    elif (eventCode == 'Zs'):
                        systemCode = self._getS3Segment('\\t ', data)
                        codeName = self._event_types(systemCode)
                        eventObj['eventType'] = codeName
                    elif (eventCode == 'Zx' or eventCode == 'Zy'):
                        #bypass or reset
                        systemCode = self._getS3Segment('\\t ', data)[1:]
                        codeName = self._events(eventCode)
                        typeName = self._event_types(systemCode)
                        zoneNumber, zoneName = self._searchS3Segment(self._getS3Segment('\\z ', data).strip())
                        userNumber, userName = self._searchS3Segment(self._getS3Segment('\\u ', data).strip())
                        eventObj['eventType'] = codeName + ': ' + typeName
                        eventObj['zoneName'] = zoneName
                        eventObj['zoneNumber'] = zoneNumber
                        eventObj['userName'] = userName
                        eventObj['userNumber'] = userNumber
                    elif (eventCode == 'Za'):
                        #ALARM!
                        systemCode = self._getS3Segment('\\t ', data)[1:]
                        codeName = self._events(eventCode)
                        typeName = self._event_types(systemCode)
                        zoneNumber, zoneName = self._searchS3Segment(self._getS3Segment('\\z ', data).strip())
                        areaNumber, areaName = self._searchS3Segment(self._getS3Segment('\\a ', data).strip())
                        areaObj = {"areaName": areaName, "areaNumber": areaNumber, "areaState": STATE_ALARM_TRIGGERED,}
                        panel.updateArea(areaNumber, areaObj)
                    elif (eventCode == 'Zr'):
                        #zone restore - what do we even use this for?
                        systemCode = self._getS3Segment('\\t ', data)[1:]
                        codeName = self._events(eventCode)
                        typeName = self._event_types(systemCode)
                        zoneNumber, zoneName = self._searchS3Segment(self._getS3Segment('\\z ', data).strip())
                        areaNumber, areaName = self._searchS3Segment(self._getS3Segment('\\a ', data).strip())
                    elif (eventCode == 'Zj'):
                        #door access
                        systemCode = self._getS3Segment('\\t ', data)[1:]
                        typeName = self._event_types(systemCode)
                        doorNumber, doorName = self._searchS3Segment(self._getS3Segment('\\v ', data).strip())
                        userNumber, userName = self._searchS3Segment(self._getS3Segment('\\u ', data).strip())
                        eventObj['eventType'] = typeName
                        eventObj['doorName'] = doorName
                        eventObj['doorNumber'] = doorNumber
                        eventObj['userName'] = userName
                        eventObj['userNumber'] = userNumber
                    elif (eventCode == 'Zq'):
                        #armed/disarmed
                        systemCode = self._getS3Segment('\\t ', data)[1:]
                        codeName = self._event_types(systemCode)
                        areaNumber, areaName = self._searchS3Segment(self._getS3Segment('\\a ', data).strip())
                        userNumber, userName = self._searchS3Segment(self._getS3Segment('\\u ', data).strip())
                        if (systemCode == "OP"):
                            #opening, or disarm
                            areaState = STATE_ALARM_DISARMED
                        elif (systemCode == "CL"):
                            #closing, or arm
                            areaState = STATE_ALARM_ARMED_AWAY
                        areaObj = {"areaName": areaName, "areaNumber": areaNumber, "areaState": areaState,}
                        panel.updateArea(areaNumber, areaObj)
                    elif (eventCode == 'Zl'):
                        #schedule change
                        #generally used if someone extends closing time from the keypad
                        #drop it on the floor, we don't care
                        systemCode = self._getS3Segment('\\t ', data)[1:]
                        codeName = self._event_types(systemCode)
                    else:
                        _LOGGER.warning('{}: Unknown event received - {}'.format(acctNum, data))

                    ackString = '\x02' + acctNum + '\x06\x0D'
                    writer.write(ackString.encode())
                    #update contact time last to ensure we only log contact time on a successful message
                    panel.updateContactTime(datetime.utcnow())
                    #call to update the hass object
                    for callback in self._callbacks:
                        await callback()
                else:
                    _LOGGER.debug("Connection disconnected")
                    connected = False
