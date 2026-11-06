"""Test zone state to status mapping and alarm tracking in DMPPanel."""

from unittest.mock import Mock

import pytest

from custom_components.dmp import ZONE_STATE_TO_STATUS, DMPPanel


@pytest.fixture
def mock_panel():
    """Create a mock panel with initialized alarm zones."""
    panel_config = {
        "ip": "192.168.1.1",
        "listen_port": 40002,
        "remote_port": 40001,
        "account_number": "12345",
        "panel_name": "Test Panel",
    }
    panel = DMPPanel(Mock(), panel_config)
    return panel


def test_alarm_zone_set_and_get(mock_panel):
    """Test setting and getting alarm zones."""
    zone = "001"
    assert mock_panel.get_alarm(zone) is False
    mock_panel.set_alarm(zone)
    assert mock_panel.get_alarm(zone) is True


def test_alarm_zone_clear(mock_panel):
    """Test clearing alarm zone."""
    zone = "001"
    mock_panel.set_alarm(zone)
    assert mock_panel.get_alarm(zone) is True
    mock_panel.clear_alarm(zone)
    assert mock_panel.get_alarm(zone) is False


def test_alarm_zone_default_false(mock_panel):
    """Test that alarm zone defaults to False for unknown zones."""
    assert mock_panel.get_alarm("999") is False


@pytest.mark.parametrize(
    "zone_state,expected_status",
    [
        ("N", "ready"),
        ("O", "open"),
        ("S", "trouble"),
        ("X", "bypass"),
        ("L", "low_battery"),
        ("M", "trouble"),
    ],
)
def test_zone_state_to_status_all_states(zone_state, expected_status):
    """Every pyDMP zone state maps to a status sensor enum option."""
    assert ZONE_STATE_TO_STATUS[zone_state] == expected_status
