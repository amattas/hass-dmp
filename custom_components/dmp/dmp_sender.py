import asyncio
import logging

from .const import (PANEL_AREA_COUNT)

_LOGGER = logging.getLogger(__name__)

class DMPSender:
    def __init__(self, ipAddr, port, accountNumber, remoteKey):
        self.ipAddr = ipAddr
        self.port = port
        self.accountNumber = accountNumber
        if len(self.accountNumber) < 5:
            self.accountNumber = ' ' * (5 - len(self.accountNumber)) + self.accountNumber
        self.remoteKey = remoteKey

    async def arm(self, zones):
        await self.connectAndSend('!C{},YN'.format(zones))

    async def disarm(self, zones):
        await self.connectAndSend('!O{},'.format(zones))

    async def setBypass(self, zoneNum, enableBypass):
        zoneNum = str(zoneNum).zfill(3)
        cmd = 'X' if enableBypass else 'Y'
        await self.connectAndSend('!{}{}'.format(cmd, zoneNum))

    async def status(self):
        # may need to send additional based on how many zones per area 
        zoneQuery = ['?WB**Y001'] + ['?WB'] * (PANEL_AREA_COUNT + 1)
        return await self.connectAndSend(zoneQuery)

    async def connectAndSend(self, commands):
        reader, writer = await asyncio.open_connection(self.ipAddr, self.port)
        dropConnectionStr = '!V0'
        sendAuthStr = '!V2{}'.format(self.remoteKey)

        # original code had an initial drop followed by 2 second sleep - haven't had an issue without it...
        # await self.sendCommand(writer, self.getEncodedPayload(dropConnectionStr))
        await self.sendCommand(writer, self.getEncodedPayload(sendAuthStr))

        if isinstance(commands, str):
            await self.sendCommand(writer, self.getEncodedPayload(commands))
        elif isinstance(commands, list):
            for command in commands:
                await self.sendCommand(writer, self.getEncodedPayload(command))

        await self.sendCommand(writer, self.getEncodedPayload(dropConnectionStr))
        writer.close()
        await writer.wait_closed()
        data = await reader.read()
        ret = self.decodeResponse(data)
        _LOGGER.debug("DMP Response Decoded: {}".format(ret))
        return ret

    def getEncodedPayload(self, payload):
        return '@{}{}\r'.format(self.accountNumber, payload).encode()

    def decodeResponse(self, response):
        _LOGGER.debug("DMP: Received data after command: {}".format(response))
        responseLines = response.decode("utf-8").split('\x02')
        statusResponse = StatusResponse()
        for responseLine in responseLines:
            messageType = responseLine[8:10]
            if 'V' in messageType: # Auth/Drop Reply 
                pass
            elif 'C' in messageType or 'O' in messageType or 'X' in messageType or 'Y' in messageType: # Arm/Disarm or Bypass/Reset Reply 
                return DMPCharReply.getAckType(responseLine[7:8])
            elif 'WB' in messageType: # Status Reply 
                statusResponse.parseReply(responseLine[10:])
            elif messageType != str(''):
                _LOGGER.debug("Unknown message type in line: {}".format(responseLine))

        if statusResponse.hasData:
            return statusResponse.flush()

    async def sendCommand(self, writer, cmd):
        _LOGGER.debug("DMP: Sending cmd: {}".format(cmd))
        writer.write(cmd)
        await writer.drain()
        await asyncio.sleep(0.3) # need some sleep or read buffer will be empty

class DMPCharReply():
    replyCharMap = {
        'ACK': '+',
        'NAK': '-'
    }

    def getAckType(char):
        return DMPCharReply.replyCharMap.get(char, char)

class StatusResponse():
    statusMap = {
        # Areas
        'A': 'Armed',
        'D': 'Disarmed',
        # Zones
        'N': 'Normal',
        'O': 'Open',
        'S': 'Short',
        'X': 'Bypassed',
        'L': 'Low Battery',
        'M': 'Missing'
    }
    def __init__(self):
        self.areaDict = {}
        self.zoneDict = {}
        self.hasData = False

    def addToDict(self, targetDict, number, status, name):
        targetDict[number] = {
            'status': status,
            'name': name,
        }

    def flush(self):
        self.printStatus()
        return self.areaDict, self.zoneDict

    def parseReply(self, word):
        self.hasData = True
        zones = word.split('\x1e')
        for zone in zones:
            zoneType = zone[:1]
            if zone[:2] == str('-\r'):
                break
            number = zone[1:4]
            status = zone[4:5]
            name = zone[5:]
            if zoneType == 'A':
                self.addToDict(self.areaDict, number[1:], status, name)
            elif zoneType == 'L':
                self.addToDict(self.zoneDict, number, status, name)
            else:
                _LOGGER.debug("Error: Unknown type '{}' for zone with number {}".format(zoneType, number))

    def printStatus(self):
        def printItems(title, items):
            sortedItems = dict(sorted(items.items()))
            _LOGGER.debug("{}:".format(title))
            for number, details in sortedItems.items():
                details['status'] = self.statusMap.get(details['status'], details['status'])
                _LOGGER.debug("{} Number: {}, Status: {}, Name: {}".format(
                    title[:-1].title(), number, details['status'], details['name']
                ))
        
        printItems("Areas", self.areaDict)
        printItems("Zones", self.zoneDict)
