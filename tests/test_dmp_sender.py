"""Test DMP Sender module."""
import pytest
from custom_components.dmp.dmp_sender import DMPSender


class TestDMPSender:
    """Test DMPSender class."""

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

