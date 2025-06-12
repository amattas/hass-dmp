"""Test DMP Sender module."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from custom_components.dmp.dmp_sender import DMPSender, DMPCharReply, StatusResponse


@pytest.mark.parametrize("acct,expected", [
    ("123", "  123"),
    ("12345", "12345"),
    ("123456", "123456"),
])
def test_account_number_padding(acct, expected):
    sender = DMPSender("192.168.1.1", 40001, acct, "")
    assert sender.accountNumber == expected
    assert len(sender.accountNumber) == len(expected)

@pytest.mark.parametrize("payload", ["!C05", ""])
def test_get_encoded_payload(payload):
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
    sender = DMPSender("192.168.1.1", 40001, "123", "testkey")
    with patch.object(sender, 'connectAndSend', new_callable=AsyncMock) as mock_send:
        await sender.setBypass(zoneNum, enable)
        mock_send.assert_called_once_with(expected)

class TestDMPSenderStatus:
    """Test DMPSender.status command."""

    @pytest.mark.asyncio
    async def test_status(self):
        """Test status command sends correct zone queries."""
        sender = DMPSender("192.168.1.1", 40001, "123", "testkey")
        
        with patch.object(sender, 'connectAndSend', new_callable=AsyncMock) as mock_send:
            await sender.status()
            # PANEL_AREA_COUNT is 3, so we expect 1 initial query + 4 additional
            expected_commands = ['?WB**Y001', '?WB', '?WB', '?WB', '?WB']
            mock_send.assert_called_once_with(expected_commands)
        
@pytest.mark.parametrize(
    "char,expected", [
        ('ACK', '+'),
        ('NAK', '-'),
        ('X', 'X'),
    ]
)
def test_get_ack_type(char, expected):
    assert DMPCharReply.getAckType(char) == expected

class TestStatusResponse:
    """Test status response parsing and flushing."""
    def test_parse_and_flush(self):
        sr = StatusResponse()
        # Simulate a response with one area and one zone entry
        # Format: A<area_number><status><name><RS>L<zone_number><status><name><RS>
        rs = '\x1e'
        reply = f'A001DHome{rs}L002OZone2{rs}'
        sr.parseReply(reply)
        assert sr.hasData is True
        areas, zones = sr.flush()
        # After flushing, status codes are mapped to status strings
        assert areas == {'01': {'status': 'Disarmed', 'name': 'Home'}}
        assert zones == {'002': {'status': 'Open', 'name': 'Zone2'}}