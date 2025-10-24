"""Complete tests for DMPPanel class."""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from homeassistant.components.alarm_control_panel import AlarmControlPanelState

from custom_components.dmp import DMPPanel
from custom_components.dmp.const import (
    CONF_PANEL_IP, CONF_PANEL_REMOTE_PORT, CONF_PANEL_ACCOUNT_NUMBER, CONF_PANEL_REMOTE_KEY
)

def test_panel_initialization_with_defaults():
    """Test panel initialization with missing optional fields."""
    config = {
        CONF_PANEL_ACCOUNT_NUMBER: "12345",
        CONF_PANEL_IP: "192.168.1.100"
    }
    
    panel = DMPPanel(Mock(), config)
    
    assert panel._accountNumber == "12345"
    assert panel._ipAddress == "192.168.1.100"
    assert panel._panelPort == 2001
    assert panel._remoteKey == "                "
    assert panel._panel_last_contact is None
    assert panel._area == AlarmControlPanelState.DISARMED

def test_panel_initialization_with_all_fields():
    """Test panel initialization with all fields provided."""
    config = {
        CONF_PANEL_ACCOUNT_NUMBER: "12345",
        CONF_PANEL_IP: "192.168.1.100",
        CONF_PANEL_REMOTE_PORT: 3000,
        CONF_PANEL_REMOTE_KEY: "mykey123"
    }
    
    panel = DMPPanel(Mock(), config)
    
    assert panel._accountNumber == "12345"
    assert panel._ipAddress == "192.168.1.100"
    assert panel._panelPort == 3000
    assert panel._remoteKey == "mykey123"

def test_panel_str_representation():
    """Test string representation of panel."""
    config = {
        CONF_PANEL_ACCOUNT_NUMBER: "12345",
        CONF_PANEL_IP: "192.168.1.100"
    }
    
    panel = DMPPanel(Mock(), config)
    
    assert str(panel) == "DMP Panel with account number 12345 at addr 192.168.1.100"

def test_panel_contact_time_methods():
    """Test contact time update and retrieval."""
    panel = DMPPanel(Mock(), {CONF_PANEL_ACCOUNT_NUMBER: "12345", CONF_PANEL_IP: "1.1.1.1"})
    
    test_time = datetime.now()
    panel.updateContactTime(test_time)
    assert panel.getContactTime() == test_time

def test_panel_area_methods():
    """Test area update and retrieval."""
    panel = DMPPanel(Mock(), {CONF_PANEL_ACCOUNT_NUMBER: "12345", CONF_PANEL_IP: "1.1.1.1"})
    
    area_obj = {"areaName": "Main", "areaState": AlarmControlPanelState.ARMED_AWAY}
    panel.updateArea(area_obj)
    assert panel.getArea() == area_obj

def test_panel_get_all_zone_collections():
    """Test getting all zone collections."""
    panel = DMPPanel(Mock(), {CONF_PANEL_ACCOUNT_NUMBER: "12345", CONF_PANEL_IP: "1.1.1.1"})
    
    panel._open_close_zones = {"001": {"state": "open"}}
    panel._battery_zones = {"002": {"state": "low"}}
    panel._trouble_zones = {"003": {"state": "trouble"}}
    panel._bypass_zones = {"004": {"state": "bypassed"}}
    panel._alarm_zones = {"005": {"state": "alarm"}}
    panel._status_zones = {"006": {"state": "ready"}}
    
    assert panel.getOpenCloseZones() == {"001": {"state": "open"}}
    assert panel.getBatteryZones() == {"002": {"state": "low"}}
    assert panel.getTroubleZones() == {"003": {"state": "trouble"}}
    assert panel.getBypassZones() == {"004": {"state": "bypassed"}}
    assert panel.getAlarmZones() == {"005": {"state": "alarm"}}
    assert panel.getStatusZones() == {"006": {"state": "ready"}}

@pytest.mark.parametrize(
    "update_method,get_method,container",
    [
        ("updateOpenCloseZone", "getOpenCloseZone", "_open_close_zones"),
        ("updateBatteryZone", "getBatteryZone", "_battery_zones"),
        ("updateTroubleZone", "getTroubleZone", "_trouble_zones"),
        ("updateBypassZone", "getBypassZone", "_bypass_zones"),
        ("updateAlarmZone", "getAlarmZone", "_alarm_zones"),
    ],
)
def test_panel_zone_update_preserves_existing_data(update_method, get_method, container):
    """Zone updates should preserve previously stored attributes."""
    panel = DMPPanel(Mock(), {CONF_PANEL_ACCOUNT_NUMBER: "12345", CONF_PANEL_IP: "1.1.1.1"})

    getattr(panel, container)["001"] = {
        "zoneState": False,
        "zoneName": "Front Door",
        "extra": "keep",
    }

    getattr(panel, update_method)("001", {"zoneState": True})

    zone = getattr(panel, get_method)("001")
    assert zone["zoneState"] is True
    assert zone["zoneName"] == "Front Door"
    assert zone["extra"] == "keep"

def test_panel_methods_with_dmp_sender():
    """Test panel methods that interact with DMPSender."""
    config = {
        CONF_PANEL_ACCOUNT_NUMBER: "12345",
        CONF_PANEL_IP: "192.168.1.100"
    }
    
    with patch('custom_components.dmp.DMPSender') as mock_sender_class:
        mock_sender = Mock()
        mock_sender_class.return_value = mock_sender
        
        panel = DMPPanel(Mock(), config)
        
        assert panel.getAccountNumber() == "12345"
        assert panel._dmpSender == mock_sender
        assert panel._dmpSender == mock_sender

@pytest.mark.parametrize(
    "getter",
    [
        "getOpenCloseZone",
        "getBatteryZone",
        "getTroubleZone",
        "getBypassZone",
        "getAlarmZone",
    ],
)
def test_panel_getters_return_none_when_empty(getter):
    """Zone getter methods return None when the zone does not exist."""
    panel = DMPPanel(Mock(), {CONF_PANEL_ACCOUNT_NUMBER: "12345", CONF_PANEL_IP: "1.1.1.1"})

    assert getattr(panel, getter)("999") is None


def test_panel_get_status_zone_raises():
    """getStatusZone should raise KeyError when zone is missing."""
    panel = DMPPanel(Mock(), {CONF_PANEL_ACCOUNT_NUMBER: "12345", CONF_PANEL_IP: "1.1.1.1"})

    with pytest.raises(KeyError):
        panel.getStatusZone("999")


def test_panel_status_zones_default():
    """Status zones should be empty on initialization."""
    panel = DMPPanel(Mock(), {CONF_PANEL_ACCOUNT_NUMBER: "12345", CONF_PANEL_IP: "1.1.1.1"})
    assert panel.getStatusZones() == {}

@pytest.mark.parametrize(
    "update_method,get_method,zone_dict",
    [
        ("updateOpenCloseZone", "getOpenCloseZone", "_open_close_zones"),
        ("updateBatteryZone", "getBatteryZone", "_battery_zones"),
        ("updateTroubleZone", "getTroubleZone", "_trouble_zones"),
        ("updateBypassZone", "getBypassZone", "_bypass_zones"),
        ("updateAlarmZone", "getAlarmZone", "_alarm_zones"),
    ],
)
def test_panel_zone_state_updates(update_method, get_method, zone_dict):
    """Test zone state update methods for all zone types."""
    panel = DMPPanel(
        Mock(), {CONF_PANEL_ACCOUNT_NUMBER: "12345", CONF_PANEL_IP: "1.1.1.1"}
    )

    panel.updateStatusZone = Mock()
    zone_data = {"zoneState": True, "zoneName": "Test Zone"}

    getattr(panel, update_method)("001", zone_data)

    assert "001" in getattr(panel, zone_dict)
    panel.updateStatusZone.assert_called_with("001", zone_data)

    result = getattr(panel, get_method)("001")
    assert result["zoneState"] is True