"""Complete tests for DMPPanel class."""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from homeassistant.const import STATE_ALARM_DISARMED, STATE_ALARM_ARMED_AWAY

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
    assert panel._panelPort == 2001  # Default port
    assert panel._remoteKey == "                "  # 16 spaces default
    assert panel._panel_last_contact is None
    assert panel._area == STATE_ALARM_DISARMED

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
    
    area_obj = {"areaName": "Main", "areaState": STATE_ALARM_ARMED_AWAY}
    panel.updateArea(area_obj)
    assert panel.getArea() == area_obj

def test_panel_get_all_zone_collections():
    """Test getting all zone collections."""
    panel = DMPPanel(Mock(), {CONF_PANEL_ACCOUNT_NUMBER: "12345", CONF_PANEL_IP: "1.1.1.1"})
    
    # Add zones to different collections
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

def test_panel_zone_update_preserves_existing_data():
    """Test that zone updates preserve existing zone data."""
    panel = DMPPanel(Mock(), {CONF_PANEL_ACCOUNT_NUMBER: "12345", CONF_PANEL_IP: "1.1.1.1"})
    
    # Pre-populate zone with extra data
    panel._open_close_zones["001"] = {
        "zoneState": False,
        "zoneName": "Front Door",
        "extraField": "preserved"
    }
    
    # Update only state
    update_obj = {"zoneState": True}
    panel.updateOpenCloseZone("001", update_obj)
    
    # Check state updated but other fields preserved
    zone = panel.getOpenCloseZone("001")
    assert zone["zoneState"] is True
    assert zone["zoneName"] == "Front Door"
    assert zone["extraField"] == "preserved"

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
        
        # Test getAccountNumber
        assert panel.getAccountNumber() == "12345"
        
        # Test DMPSender instance assigned to panel
        assert panel._dmpSender == mock_sender

def test_panel_getters_return_none_when_empty():
    """Test that zone getters return None when zone doesn't exist."""
    panel = DMPPanel(Mock(), {CONF_PANEL_ACCOUNT_NUMBER: "12345", CONF_PANEL_IP: "1.1.1.1"})
    
    # All should return None for non-existent zones
    assert panel.getOpenCloseZone("999") is None
    assert panel.getBatteryZone("999") is None
    assert panel.getTroubleZone("999") is None
    assert panel.getBypassZone("999") is None
    assert panel.getAlarmZone("999") is None
    # getStatusZone raises KeyError for non-existent zones
    with pytest.raises(KeyError):
        panel.getStatusZone("999")

def test_panel_zone_state_updates():
    """Test zone state update methods."""
    panel = DMPPanel(Mock(), {CONF_PANEL_ACCOUNT_NUMBER: "12345", CONF_PANEL_IP: "1.1.1.1"})
    
    # Mock updateStatusZone method
    panel.updateStatusZone = Mock()
    
    # Test each zone type update
    zone_types = [
        ("updateOpenCloseZone", "getOpenCloseZone", "_open_close_zones"),
        ("updateBatteryZone", "getBatteryZone", "_battery_zones"),
        ("updateTroubleZone", "getTroubleZone", "_trouble_zones"),
        ("updateBypassZone", "getBypassZone", "_bypass_zones"),
        ("updateAlarmZone", "getAlarmZone", "_alarm_zones"),
    ]
    
    for update_method, get_method, zone_dict in zone_types:
        zone_data = {"zoneState": True, "zoneName": "Test Zone"}
        getattr(panel, update_method)("001", zone_data)
        
        # Verify zone was stored
        assert "001" in getattr(panel, zone_dict)
        
        # Verify updateStatusZone was called
        panel.updateStatusZone.assert_called_with("001", zone_data)
        
        # Verify getter returns the zone
        result = getattr(panel, get_method)("001")
        assert result["zoneState"] is True