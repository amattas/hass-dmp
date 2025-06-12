"""Test DMP Sender module."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from custom_components.dmp.dmp_sender import DMPSender, DMPCharReply, StatusResponse


class TestDMPAccountNumbers:
    """Test account number formatting."""

    def test_account_number_padding_short(self):
        """Test that account numbers less than 5 chars are padded."""
        sender = DMPSender("192.168.1.1", 40001, "123", "")
        assert sender.accountNumber == "  123"
        assert len(sender.accountNumber) == 5

    def test_account_number_padding_exact(self):
        """Test that 5-char account numbers are not padded."""
        sender = DMPSender("192.168.1.1", 40001, "12345", "")
        assert sender.accountNumber == "12345"
        assert len(sender.accountNumber) == 5

    def test_account_number_padding_long(self):
        """Test that account numbers longer than 5 chars are not truncated."""
        sender = DMPSender("192.168.1.1", 40001, "123456", "")
        assert sender.accountNumber == "123456"
        assert len(sender.accountNumber) == 6

    def test_get_encoded_payload(self):
        """Test payload encoding with account number."""
        sender = DMPSender("192.168.1.1", 40001, "123", "")
        encoded = sender.getEncodedPayload("!C05")
        assert encoded == b"@  123!C05\r"

    def test_get_encoded_payload_empty(self):
        """Test payload encoding with empty command."""
        sender = DMPSender("192.168.1.1", 40001, "123", "")
        encoded = sender.getEncodedPayload("")
        assert encoded == b"@  123\r"


class TestDMPArming:
    """Test arming commands."""
    @pytest.mark.asyncio
    async def test_arm_with_instant(self):
        """Test arm command with instant flag enabled."""
        sender = DMPSender("192.168.1.1", 40001, "123", "testkey")
        
        with patch.object(sender, 'connectAndSend', new_callable=AsyncMock) as mock_send:
            await sender.arm("010203", True)
            mock_send.assert_called_once_with("!C010203,YNY")

    @pytest.mark.asyncio
    async def test_arm_without_instant(self):
        """Test arm command with instant flag disabled."""
        sender = DMPSender("192.168.1.1", 40001, "123", "testkey")
        
        with patch.object(sender, 'connectAndSend', new_callable=AsyncMock) as mock_send:
            await sender.arm("01", False)
            mock_send.assert_called_once_with("!C01,YNN")

    @pytest.mark.asyncio
    async def test_disarm(self):
        """Test disarm command."""
        sender = DMPSender("192.168.1.1", 40001, "123", "testkey")
        
        with patch.object(sender, 'connectAndSend', new_callable=AsyncMock) as mock_send:
            await sender.disarm("010203")
            mock_send.assert_called_once_with("!O010203,")

    @pytest.mark.asyncio
    async def test_disarm_single_zone(self):
        """Test disarm command with single zone."""
        sender = DMPSender("192.168.1.1", 40001, "123", "testkey")
        
        with patch.object(sender, 'connectAndSend', new_callable=AsyncMock) as mock_send:
            await sender.disarm("02")
            mock_send.assert_called_once_with("!O02,")

class TestDMPBypass:
    """Test bypass commands."""

    @pytest.mark.asyncio
    async def test_setBypass_enable(self):
        """Test setBypass command to enable bypass."""
        sender = DMPSender("192.168.1.1", 40001, "123", "testkey")
        
        with patch.object(sender, 'connectAndSend', new_callable=AsyncMock) as mock_send:
            await sender.setBypass(5, True)
            mock_send.assert_called_once_with("!X005")

    @pytest.mark.asyncio
    async def test_setBypass_disable(self):
        """Test setBypass command to disable bypass."""
        sender = DMPSender("192.168.1.1", 40001, "123", "testkey")
        
        with patch.object(sender, 'connectAndSend', new_callable=AsyncMock) as mock_send:
            await sender.setBypass(12, False)
            mock_send.assert_called_once_with("!Y012")

    @pytest.mark.asyncio
    async def test_setBypass_large_zone_number(self):
        """Test setBypass with zone number > 99."""
        sender = DMPSender("192.168.1.1", 40001, "123", "testkey")
        
        with patch.object(sender, 'connectAndSend', new_callable=AsyncMock) as mock_send:
            await sender.setBypass(123, True)
            mock_send.assert_called_once_with("!X123")

class TestDMPStatus:
    """Test status command."""

    @pytest.mark.asyncio
    async def test_status(self):
        """Test status command sends correct zone queries."""
        sender = DMPSender("192.168.1.1", 40001, "123", "testkey")
        
        with patch.object(sender, 'connectAndSend', new_callable=AsyncMock) as mock_send:
            await sender.status()
            # PANEL_AREA_COUNT is 3, so we expect 1 initial query + 4 additional
            expected_commands = ['?WB**Y001', '?WB', '?WB', '?WB', '?WB']
            mock_send.assert_called_once_with(expected_commands)