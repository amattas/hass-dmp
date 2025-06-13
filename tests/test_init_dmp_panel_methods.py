"""Unit tests for DMPPanel in __init__.py."""
import pytest
from unittest.mock import Mock, patch

from custom_components.dmp import DMPPanel
from custom_components.dmp.const import (
    CONF_PANEL_IP, CONF_PANEL_REMOTE_PORT,
    CONF_PANEL_ACCOUNT_NUMBER
)


@pytest.fixture
def panel_fixture():
    """Create a DMPPanel with mocked dependencies."""
    config = {
        CONF_PANEL_ACCOUNT_NUMBER: "12345",
        CONF_PANEL_IP: "10.0.0.1",
        CONF_PANEL_REMOTE_PORT: 8000,
        # No remote key to test default padding
    }
    with patch('custom_components.dmp.DMPListener'), patch('custom_components.dmp.DMPSender'):
        panel = DMPPanel(None, config)
    return panel, config


def test_str_and_account_number(panel_fixture):
    panel, config = panel_fixture
    # __str__ contains account number and IP
    s = str(panel)
    assert f"account number {config[CONF_PANEL_ACCOUNT_NUMBER]}" in s
    assert f"addr {config[CONF_PANEL_IP]}" in s
    # getAccountNumber returns the account number
    assert panel.getAccountNumber() == config[CONF_PANEL_ACCOUNT_NUMBER]


def test_contact_time(panel_fixture):
    panel, _ = panel_fixture
    # Initially None
    assert panel.getContactTime() is None
    # Update and retrieve
    panel.updateContactTime('2025-01-01T00:00:00')
    assert panel.getContactTime() == '2025-01-01T00:00:00'


@pytest.mark.parametrize("zone_method,get_method,container_name", [
    ('updateOpenCloseZone', 'getOpenCloseZone', '_open_close_zones'),
    ('updateBatteryZone',   'getBatteryZone',    '_battery_zones'),
    ('updateTroubleZone',   'getTroubleZone',    '_trouble_zones'),
    ('updateBypassZone',    'getBypassZone',     '_bypass_zones'),
    ('updateAlarmZone',     'getAlarmZone',      '_alarm_zones'),
])
def test_zone_update_and_get(panel_fixture, zone_method, get_method, container_name):
    panel, _ = panel_fixture
    # Prepare dummy data
    zone_num = '007'
    event = {'zoneName': 'Zone7', 'zoneNumber': zone_num, 'zoneState': True}
    # Patch updateStatusZone to avoid side-effects
    panel.updateStatusZone = Mock()
    # Invoke updateX
    getattr(panel, zone_method)(zone_num, event)
    # Internal container has key
    cont = getattr(panel, container_name)
    assert zone_num in cont and cont[zone_num] == event
    # Getter returns event
    result = getattr(panel, get_method)(zone_num)
    assert result == event


def test_get_zone_none(panel_fixture):
    panel, _ = panel_fixture
    # Non-existent zones return None
    for get_method in ['getOpenCloseZone', 'getBatteryZone', 'getTroubleZone', 'getBypassZone', 'getAlarmZone']:
        assert getattr(panel, get_method)('999') is None


def test_status_zones_default(panel_fixture):
    panel, _ = panel_fixture
    # Initially empty
    assert panel.getStatusZones() == {}