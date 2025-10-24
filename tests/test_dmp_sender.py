"""Test dmp_sender module."""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, Mock
from custom_components.dmp.dmp_sender import DMPSender, DMPCharReply, StatusResponse



@pytest.mark.parametrize("acct,expected", [
    ("123", "  123"),
    ("12345", "12345"),
    ("123456", "123456"),
])
def test_account_number_padding(acct, expected):
    """Ensure account numbers are padded to five characters."""
    sender = DMPSender("192.168.1.1", 40001, acct, "")
    assert sender.accountNumber == expected
    assert len(sender.accountNumber) == len(expected)

@pytest.mark.parametrize("payload", ["!C05", ""])
def test_get_encoded_payload(payload):
    """Verify payload encoding prepends account information."""
    sender = DMPSender("192.168.1.1", 40001, "123", "")
    expected = b"@" + sender.accountNumber.encode() + payload.encode() + b"\r"
    assert sender.getEncodedPayload(payload) == expected

@pytest.mark.parametrize(
    "zones,instant,expected", [
        ("010203", True, "!C010203,YNY"),
        ("01", False, "!C01,YNN"),
    ]
)
@pytest.mark.asyncio
async def test_arm_commands(zones, instant, expected):
    """Confirm arm command sends correct payload."""
    sender = DMPSender("192.168.1.1", 40001, "123", "testkey")
    with patch.object(sender, 'connectAndSend', new_callable=AsyncMock) as mock_send:
        await sender.arm(zones, instant)
        mock_send.assert_called_once_with(expected)

@pytest.mark.parametrize(
    "zones,expected", [
        ("010203", "!O010203,"),
        ("02", "!O02,"),
    ]
)
@pytest.mark.asyncio
async def test_disarm_commands(zones, expected):
    """Confirm disarm command sends correct payload."""
    sender = DMPSender("192.168.1.1", 40001, "123", "testkey")
    with patch.object(sender, 'connectAndSend', new_callable=AsyncMock) as mock_send:
        await sender.disarm(zones)
        mock_send.assert_called_once_with(expected)

@pytest.mark.parametrize(
    "zoneNum,enable,expected", [
        (5, True, "!X005"),
        (12, False, "!Y012"),
        (123, True, "!X123"),
    ]
)
@pytest.mark.asyncio
async def test_set_bypass_commands(zoneNum, enable, expected):
    """Ensure bypass commands send appropriate zone codes."""
    sender = DMPSender("192.168.1.1", 40001, "123", "testkey")
    with patch.object(sender, 'connectAndSend', new_callable=AsyncMock) as mock_send:
        await sender.setBypass(zoneNum, enable)
        mock_send.assert_called_once_with(expected)

@pytest.mark.asyncio
async def test_status():
    """Test status command sends correct zone queries."""
    sender = DMPSender("192.168.1.1", 40001, "123", "testkey")
    
    with patch.object(sender, 'connectAndSend', new_callable=AsyncMock) as mock_send:
        await sender.status()
        expected_commands = ['?WB**Y001', '?WB', '?WB', '?WB', '?WB']
        mock_send.assert_called_once_with(expected_commands)

def test_parse_and_flush():
    """Test parsing reply and flushing data."""
    sr = StatusResponse()
    rs = '\x1e'
    reply = f'A001DHome{rs}L002OZone2{rs}'
    sr.parseReply(reply)
    assert sr.hasData is True
    areas, zones = sr.flush()
    assert areas == {'01': {'status': 'Disarmed', 'name': 'Home'}}
    assert zones == {'002': {'status': 'Open', 'name': 'Zone2'}}

@pytest.mark.parametrize(
    "char,expected", [
        ('ACK', '+'),
        ('NAK', '-'),
        ('X', 'X'),
    ]
)
def test_get_ack_type(char, expected):
    """Test getAckType method with different characters."""
    assert DMPCharReply.getAckType(char) == expected

@pytest.mark.asyncio
async def test_connect_and_send_string(monkeypatch):
    """Check sending a single command sequence over the network."""
    sender = DMPSender("1.1.1.1", 4000, "123", "key")
    class DummyWriter:
        def __init__(self):
            self.writes = []
        def write(self, data):
            self.writes.append(data)
        async def drain(self):
            pass
        def close(self):
            self.closed = True
        async def wait_closed(self):
            pass
    class DummyReader:
        async def read(self):
            return b"resp"
    dummy_reader = DummyReader()
    dummy_writer = DummyWriter()
    async def fake_open(ip, port):
        assert ip == "1.1.1.1" and port == 4000
        return dummy_reader, dummy_writer
    monkeypatch.setattr(asyncio, "open_connection", fake_open)
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    monkeypatch.setattr(sender, "decodeResponse", Mock(return_value="decoded"))
    result = await sender.connectAndSend("!CMD")
    assert result == "decoded"
    expected = [
        sender.getEncodedPayload("!V2key"),
        sender.getEncodedPayload("!CMD"),
        sender.getEncodedPayload("!V0"),
    ]
    assert dummy_writer.writes == expected

@pytest.mark.asyncio
async def test_connect_and_send_list(monkeypatch):
    """Check sending multiple commands over the network."""
    sender = DMPSender("1.1.1.1", 4000, "123", "key")
    class DummyWriter:
        def __init__(self):
            self.writes = []
        def write(self, data):
            self.writes.append(data)
        async def drain(self):
            pass
        def close(self):
            self.closed = True
        async def wait_closed(self):
            pass
    class DummyReader:
        async def read(self):
            return b"resp"
    dummy_reader = DummyReader()
    dummy_writer = DummyWriter()
    async def fake_open(ip, port):
        return dummy_reader, dummy_writer
    monkeypatch.setattr(asyncio, "open_connection", fake_open)
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    monkeypatch.setattr(sender, "decodeResponse", Mock(return_value="ok"))
    result = await sender.connectAndSend(["!A", "!B"])
    assert result == "ok"
    expected = [
        sender.getEncodedPayload("!V2key"),
        sender.getEncodedPayload("!A"),
        sender.getEncodedPayload("!B"),
        sender.getEncodedPayload("!V0"),
    ]
    assert dummy_writer.writes == expected

def test_decode_response_ack():
    """Decode an ACK response payload."""
    sender = DMPSender("0", 0, "123", "k")
    data = b"AAAAAAA+C\r"
    assert sender.decodeResponse(data) == "+"

def test_decode_response_status():
    """Decode a status message response."""
    sender = DMPSender("0", 0, "123", "k")
    reply = "A001DHome\x1eL002OZone2\x1e-\r"
    data = ("AAAAAAA-WB" + reply).encode()
    areas, zones = sender.decodeResponse(data)
    assert areas == {'01': {'status': 'Disarmed', 'name': 'Home'}}
    assert zones == {'002': {'status': 'Open', 'name': 'Zone2'}}

def test_decode_response_unknown():
    """Unknown responses should return None."""
    sender = DMPSender("0", 0, "123", "k")
    data = b"AAAAAAA-ZZignored\r"
    assert sender.decodeResponse(data) is None

def test_decode_response_auth_only():
    """Authorization-only responses should return None."""
    sender = DMPSender("0", 0, "123", "k")
    data = b"AAAAAAA+VBwhatever\r"
    assert sender.decodeResponse(data) is None
