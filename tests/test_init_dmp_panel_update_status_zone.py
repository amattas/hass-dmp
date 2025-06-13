"""Test updateStatusZone logic in DMPPanel."""
import pytest
from unittest.mock import Mock, patch
from copy import deepcopy
from custom_components.dmp import DMPPanel
from custom_components.dmp.const import CONF_PANEL_ACCOUNT_NUMBER, CONF_PANEL_IP


@pytest.fixture
def mock_panel():
    """Create a mock panel with initialized zones."""
    with patch('custom_components.dmp.DMPListener'), \
            patch('custom_components.dmp.DMPSender'):
        panel_config = {
            "ip": "192.168.1.1",
            "listen_port": 40002,
            "remote_port": 40001,
            "account_number": "12345",
            "panel_name": "Test Panel"
        }
        panel = DMPPanel(panel_config, Mock())
        
        # Initialize zone states
        panel._alarm_zones = {}
        panel._trouble_zones = {}
        panel._bypass_zones = {}
        panel._battery_zones = {}
        panel._openclose_zones = {}
        panel._status_zones = {}
        
        return panel

@pytest.mark.parametrize(
    "flags,expected", [
        ({'alarm': True,  'trouble': True,  'bypass': True,  'battery': True,  'open': False}, 'Alarm'),
        ({'alarm': False, 'trouble': True,  'bypass': True,  'battery': True,  'open': False}, 'Trouble'),
        ({'alarm': False, 'trouble': False, 'bypass': True,  'battery': True,  'open': False}, 'Bypass'),
        ({'alarm': False, 'trouble': False, 'bypass': False, 'battery': True,  'open': False}, 'Low Battery'),
        ({'alarm': False, 'trouble': False, 'bypass': False, 'battery': False, 'open': False}, 'Ready'),
    ]
)
def test_updateStatusZone_priority(mock_panel, flags, expected):
    """Test that status zone priority yields expected state."""
    zone = '001'
    event = {'zoneName': 'Test Zone', 'zoneNumber': zone}
    mock_panel._alarm_zones[zone]    = {'zoneState': flags['alarm']}
    mock_panel._trouble_zones[zone]  = {'zoneState': flags['trouble']}
    mock_panel._bypass_zones[zone]   = {'zoneState': flags['bypass']}
    mock_panel._battery_zones[zone]  = {'zoneState': flags['battery']}
    mock_panel._openclose_zones[zone]= {'zoneState': flags['open']}
    mock_panel.updateStatusZone(zone, event)
    assert mock_panel._status_zones[zone]['zoneState'] == expected

def test_updateStatusZone_updates_existing_zone(mock_panel):
    """Test updating an existing status zone."""
    zone_num = "001"
    event_obj = {"zoneName": "Test Zone", "zoneNumber": zone_num}
    
    # Pre-populate status zone
    mock_panel._status_zones[zone_num] = {
        "zoneState": "Ready",
        "existingField": "value"
    }
    
    # Mock the getter methods
    mock_panel.getAlarmZone = Mock(return_value=None)
    mock_panel.getTroubleZone = Mock(return_value=None)
    mock_panel.getBypassZone = Mock(return_value=None)
    mock_panel.getBatteryZone = Mock(return_value=None)
    mock_panel.getOpenCloseZone = Mock(return_value={"zoneState": True})
    
    mock_panel.updateStatusZone(zone_num, event_obj)
    
    # Should update state but preserve existing fields
    assert mock_panel._status_zones[zone_num]["zoneState"] == "Open"
    assert mock_panel._status_zones[zone_num]["existingField"] == "value"

def test_updateStatusZone_creates_new_zone(mock_panel):
    """Test creating a new status zone."""
    zone_num = "001"
    event_obj = {"zoneName": "Test Zone", "zoneNumber": zone_num, "customField": "value"}
    
    mock_panel.updateStatusZone(zone_num, event_obj)
    
    assert zone_num in mock_panel._status_zones
    assert mock_panel._status_zones[zone_num]["zoneState"] == "Ready"
    assert mock_panel._status_zones[zone_num]["customField"] == "value"

def test_updateStatusZone_open_fifth_priority(mock_panel):
    """Test that open state has fifth priority."""
    zone_num = "001"
    event_obj = {"zoneName": "Test Zone", "zoneNumber": zone_num}
    
    # Need to mock the getter methods since updateStatusZone calls them
    mock_panel.getAlarmZone = Mock(return_value={"zoneState": False})
    mock_panel.getTroubleZone = Mock(return_value={"zoneState": False})
    mock_panel.getBypassZone = Mock(return_value={"zoneState": False})
    mock_panel.getBatteryZone = Mock(return_value={"zoneState": False})
    mock_panel.getOpenCloseZone = Mock(return_value={"zoneState": True})
    
    mock_panel.updateStatusZone(zone_num, event_obj)
    
    assert mock_panel._status_zones[zone_num]["zoneState"] == "Open"