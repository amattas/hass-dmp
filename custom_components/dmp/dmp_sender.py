import asyncio
import logging
from enum import Enum

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
        _LOGGER.debug("DMP: Decoded: {}".format(ret))
        return ret

    def getEncodedPayload(self, payload):
        return '@{}{}\r'.format(self.accountNumber, payload).encode()

    def decodeResponse(self, response):
        _LOGGER.debug("DMP: Received data after command: {}".format(response))
        responseLines = response.decode("utf-8").split('\x02')
        for responseLine in responseLines:
            messageType = responseLine[7:9]
            if 'V' in messageType: # Auth/Drop Reply 
                pass
            elif 'C' in messageType: # Arm Reply 
                return DMPResponse.charToEnum(responseLine[7:8])

    async def sendCommand(self, writer, cmd):
        # print("Sending cmd: {}".format(cmd))
        _LOGGER.debug("DMP: Sending cmd: {}".format(cmd))
        writer.write(cmd)
        await writer.drain()
        await asyncio.sleep(0.3) # need some sleep or read buffer will be empty

class DMPResponse(Enum):
    ACK = '+'
    NAK = '-'
    NA = ''

    def charToEnum(char):
        if char == DMPResponse.ACK.value:
            return DMPResponse.ACK
        elif char == DMPResponse.NAK.value:
            return DMPResponse.NAK
        else:
            return DMPResponse.NA
