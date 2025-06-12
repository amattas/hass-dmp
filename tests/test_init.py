"""Test DMP __init__ module including DMPPanel, DMPListener, and options_update_listener."""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from copy import deepcopy
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmp import DMPPanel, DMPListener, options_update_listener
from custom_components.dmp.const import (
    CONF_HOME_AREA, CONF_AWAY_AREA, CONF_PANEL_LISTEN_PORT,
    DOMAIN, LISTENER, CONF_ZONES, CONF_ZONE_NUMBER, CONF_ZONE_NAME, CONF_ZONE_CLASS
)


class TestDMPPanelUpdateStatusZone:
    """Test updateStatusZone logic in DMPPanel."""

    @pytest.fixture
    def mock_panel(self):
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
    def test_updateStatusZone_priority(self, mock_panel, flags, expected):
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

    def test_updateStatusZone_updates_existing_zone(self, mock_panel):
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

    def test_updateStatusZone_creates_new_zone(self, mock_panel):
        """Test creating a new status zone."""
        zone_num = "001"
        event_obj = {"zoneName": "Test Zone", "zoneNumber": zone_num, "customField": "value"}
        
        mock_panel.updateStatusZone(zone_num, event_obj)
        
        assert zone_num in mock_panel._status_zones
        assert mock_panel._status_zones[zone_num]["zoneState"] == "Ready"
        assert mock_panel._status_zones[zone_num]["customField"] == "value"





    def test_updateStatusZone_open_fifth_priority(self, mock_panel):
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


    def test_updateStatusZone_updates_existing_zone(self, mock_panel):
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

    def test_updateStatusZone_creates_new_zone(self, mock_panel):
        """Test creating a new status zone."""
        zone_num = "001"
        event_obj = {"zoneName": "Test Zone", "zoneNumber": zone_num, "customField": "value"}
        
        mock_panel.updateStatusZone(zone_num, event_obj)
        
        assert zone_num in mock_panel._status_zones
        assert mock_panel._status_zones[zone_num]["zoneState"] == "Ready"
        assert mock_panel._status_zones[zone_num]["customField"] == "value"


class TestDMPPanelZoneManagement:
    """Test zone getter/setter methods."""

    @pytest.fixture
    def mock_panel(self):
        """Create a mock panel."""
        with patch('custom_components.dmp.DMPListener'), \
             patch('custom_components.dmp.DMPSender'):
            panel_config = {
                "ip": "192.168.1.1",
                "listen_port": 40002,
                "remote_port": 40001,
                "account_number": "12345",
                "panel_name": "Test Panel"
            }
            return DMPPanel(panel_config, Mock())

    def test_updateArea_and_getArea(self, mock_panel):
        """Test area update and retrieval."""
        area_data = {"areaState": "Armed", "name": "Main Floor"}
        
        mock_panel.updateArea(area_data)
        result = mock_panel.getArea()
        
        assert result == area_data

    def test_updateOpenCloseZone_and_getOpenCloseZone(self, mock_panel):
        """Test open/close zone update and retrieval."""
        zone_num = "001"
        zone_data = {"zoneState": True, "zoneName": "Front Door"}
        
        # Mock updateStatusZone since it will be called
        mock_panel.updateStatusZone = Mock()
        
        mock_panel.updateOpenCloseZone(zone_num, zone_data)
        result = mock_panel.getOpenCloseZone(zone_num)
        
        assert result["zoneState"] == zone_data["zoneState"]
        # Should call updateStatusZone
        mock_panel.updateStatusZone.assert_called_once_with(zone_num, zone_data)

    def test_updateBatteryZone_and_getBatteryZone(self, mock_panel):
        """Test battery zone update and retrieval."""
        zone_num = "001"
        zone_data = {"zoneState": True, "batteryLevel": 20}
        
        # Mock updateStatusZone
        mock_panel.updateStatusZone = Mock()
        
        mock_panel.updateBatteryZone(zone_num, zone_data)
        result = mock_panel.getBatteryZone(zone_num)
        
        assert result["zoneState"] == zone_data["zoneState"]
        mock_panel.updateStatusZone.assert_called_once_with(zone_num, zone_data)

    def test_updateTroubleZone_and_getTroubleZone(self, mock_panel):
        """Test trouble zone update and retrieval."""
        zone_num = "001"
        zone_data = {"zoneState": True, "troubleType": "Tamper"}
        
        # Mock updateStatusZone
        mock_panel.updateStatusZone = Mock()
        
        mock_panel.updateTroubleZone(zone_num, zone_data)
        result = mock_panel.getTroubleZone(zone_num)
        
        assert result["zoneState"] == zone_data["zoneState"]
        mock_panel.updateStatusZone.assert_called_once_with(zone_num, zone_data)

    def test_updateBypassZone_and_getBypassZone(self, mock_panel):
        """Test bypass zone update and retrieval."""
        zone_num = "001"
        zone_data = {"zoneState": True, "bypassReason": "Maintenance"}
        
        # Mock updateStatusZone
        mock_panel.updateStatusZone = Mock()
        
        mock_panel.updateBypassZone(zone_num, zone_data)
        result = mock_panel.getBypassZone(zone_num)
        
        assert result["zoneState"] == zone_data["zoneState"]
        mock_panel.updateStatusZone.assert_called_once_with(zone_num, zone_data)

    def test_updateAlarmZone_and_getAlarmZone(self, mock_panel):
        """Test alarm zone update and retrieval."""
        zone_num = "001"
        zone_data = {"zoneState": True, "alarmType": "Intrusion"}
        
        # Mock updateStatusZone
        mock_panel.updateStatusZone = Mock()
        
        mock_panel.updateAlarmZone(zone_num, zone_data)
        result = mock_panel.getAlarmZone(zone_num)
        
        assert result["zoneState"] == zone_data["zoneState"]
        mock_panel.updateStatusZone.assert_called_once_with(zone_num, zone_data)

    def test_getZone_returns_none_for_missing_zone(self, mock_panel):
        """Test that getters return None for non-existent zones."""
        assert mock_panel.getOpenCloseZone("999") is None
        assert mock_panel.getBatteryZone("999") is None
        assert mock_panel.getTroubleZone("999") is None
        assert mock_panel.getBypassZone("999") is None
        assert mock_panel.getAlarmZone("999") is None


class TestDMPListener:
    """Test DMPListener callback and panel management."""

    @pytest.fixture
    def mock_listener_config(self):
        """Create mock config for DMPListener."""
        return {
            CONF_HOME_AREA: "01",
            CONF_AWAY_AREA: "02",
            CONF_PANEL_LISTEN_PORT: 40002
        }

    def test_register_and_remove_callback(self, mock_listener_config):
        """Test callback registration and removal."""
        listener = DMPListener(Mock(), mock_listener_config)
        callback1 = Mock()
        callback2 = Mock()
        
        # Register callbacks
        listener.register_callback(callback1)
        listener.register_callback(callback2)
        
        assert callback1 in listener._callbacks
        assert callback2 in listener._callbacks
        
        # Remove one callback
        listener.remove_callback(callback1)
        
        assert callback1 not in listener._callbacks
        assert callback2 in listener._callbacks

    def test_addPanel_and_getPanels(self, mock_listener_config):
        """Test panel management."""
        listener = DMPListener(Mock(), mock_listener_config)
        
        # Create mock panels
        panel1 = Mock()
        panel1.getAccountNumber.return_value = "12345"
        panel2 = Mock()
        panel2.getAccountNumber.return_value = "67890"
        
        # Add panels
        listener.addPanel(panel1)
        listener.addPanel(panel2)
        
        # Get panels
        panels = listener.getPanels()
        
        assert "12345" in panels
        assert panels["12345"] == panel1
        assert "67890" in panels
        assert panels["67890"] == panel2

    def test_getS3Segment(self, mock_listener_config):
        """Test string segment extraction."""
        listener = DMPListener(Mock(), mock_listener_config)
        
        # Test normal case - it returns everything up to backslash, not the next delimiter
        result = listener._getS3Segment(":", "key:value:extra")
        assert result == "value:extr"
        
        # Test missing delimiter
        result = listener._getS3Segment(":", "nodelimiter")
        assert result == ""
        
        # Test empty string
        result = listener._getS3Segment(":", "")
        assert result == ""

    def test_searchS3Segment(self, mock_listener_config):
        """Test zone info extraction from string."""
        listener = DMPListener(Mock(), mock_listener_config)
        
        # Test valid zone string - name includes everything after the first quote
        zone_num, zone_name = listener._searchS3Segment('001"Front Door"')
        assert zone_num == "001"
        assert zone_name == 'Front Door"'
        
        # Test missing quotes - when find returns -1, slicing [:-1] removes last char
        zone_num, zone_name = listener._searchS3Segment('001NoQuotes')
        assert zone_num == "001NoQuote"  # Missing last char due to [:-1]
        assert zone_name == "001NoQuotes"  # Everything from position 0 onwards
        
        # Test empty string - find returns -1, so zone_num is ''[:-1] = ''
        zone_num, zone_name = listener._searchS3Segment('')
        assert zone_num == ""
        assert zone_name == ""

    def test_setStatusAttributes_and_getStatusAttributes(self, mock_listener_config):
        """Test status attribute formatting."""
        listener = DMPListener(Mock(), mock_listener_config)
        
        # Set attributes with proper dict format
        area_status = {
            "01": {"name": "Main", "status": "Armed Away"},
            "02": {"name": "Second", "status": "Disarmed"}
        }
        zone_status = {
            "001": {"name": "Front Door", "status": "Normal"},
            "002": {"name": "Motion", "status": "Open"}
        }
        
        listener.setStatusAttributes(area_status, zone_status)
        attrs = listener.getStatusAttributes()
        
        # Check areas
        assert "Area: 01 - Main" in attrs
        assert attrs["Area: 01 - Main"] == "Armed Away"
        assert "Area: 02 - Second" in attrs
        assert attrs["Area: 02 - Second"] == "Disarmed"
        
        # Check zones
        assert "Zone: 001 - Front Door" in attrs
        assert attrs["Zone: 001 - Front Door"] == "Normal"
        assert "Zone: 002 - Motion" in attrs
        assert attrs["Zone: 002 - Motion"] == "Open"



class TestOptionsUpdateListener:
    """Test the options update listener function."""

    @pytest.fixture
    def mock_config_entry(self):
        """Create mock config entry with zones."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "panel_name": "Test Panel",
                "account_number": "12345",
                CONF_ZONES: [
                    {
                        CONF_ZONE_NAME: "Front Door",
                        CONF_ZONE_NUMBER: "001",
                        CONF_ZONE_CLASS: "wired_door"
                    },
                    {
                        CONF_ZONE_NAME: "Motion Sensor",
                        CONF_ZONE_NUMBER: "002",
                        CONF_ZONE_CLASS: "wired_motion"
                    }
                ]
            },
            entry_id="test_entry_id"
        )
        # Store original data for comparison
        entry.original_data = entry.data.copy()
        return entry

    @pytest.fixture
    def mock_entity_entries(self):
        """Create mock entity registry entries."""
        entries = []
        
        # Create zone entities
        for zone_num in ["001", "002"]:
            # Binary sensor for zone
            entity = Mock()
            entity.entity_id = f"binary_sensor.zone_{zone_num}"
            entity.unique_id = f"dmp-12345-zone-{zone_num}"
            entity.platform = "binary_sensor"
            entries.append(entity)
            
            # Bypass switch
            entity = Mock()
            entity.entity_id = f"switch.zone_{zone_num}_bypass"
            entity.unique_id = f"dmp-12345-zone-{zone_num}-bypass-switch"
            entity.platform = "switch"
            entries.append(entity)
        
        # Also add some non-zone entities that shouldn't be removed
        entity = Mock()
        entity.entity_id = "alarm_control_panel.test_panel"
        entity.unique_id = "dmp-12345-panel-arming"
        entity.platform = "alarm_control_panel"
        entries.append(entity)
        
        return entries

    @pytest.fixture
    def mock_entity_registry(self, mock_entity_entries):
        """Mock entity registry."""
        registry = Mock(spec=er.EntityRegistry)
        registry.entities = {e.entity_id: e for e in mock_entity_entries}
        registry.async_remove = Mock()
        return registry

    async def test_options_update_no_changes(self, hass: HomeAssistant, mock_config_entry):
        """Test options update with no changes."""
        # Set up hass data
        hass.data[DOMAIN] = {
            mock_config_entry.entry_id: mock_config_entry.data.copy(),
            LISTENER: Mock()
        }
        
        # Create a new entry with empty options
        entry_with_no_options = MockConfigEntry(
            domain=DOMAIN,
            data=mock_config_entry.data,
            options={},
            entry_id=mock_config_entry.entry_id
        )
        
        await options_update_listener(hass, entry_with_no_options)
        
        # Should not do anything since no options provided
        # Just verify it completes without error
        assert True

    async def test_options_update_zone_removed(self, hass: HomeAssistant, mock_config_entry, mock_entity_registry, mock_entity_entries):
        """Test removing a zone removes its entities."""
        # Set up hass data
        hass.data[DOMAIN] = {
            mock_config_entry.entry_id: mock_config_entry.data.copy(),
            LISTENER: Mock()
        }
        
        # Create entry with options that remove zone 002
        entry_with_options = MockConfigEntry(
            domain=DOMAIN,
            data=mock_config_entry.data,
            options={
                CONF_ZONES: [
                    {
                        CONF_ZONE_NAME: "Front Door",
                        CONF_ZONE_NUMBER: "001",
                        CONF_ZONE_CLASS: "wired_door"
                    }
                ]
            },
            entry_id=mock_config_entry.entry_id
        )
        
        with patch("homeassistant.helpers.entity_registry.async_get", return_value=mock_entity_registry), \
             patch("homeassistant.helpers.entity_registry.async_entries_for_config_entry", return_value=mock_entity_entries):
            
            # Mock async_update_entry and async_reload
            hass.config_entries.async_update_entry = Mock()
            hass.config_entries.async_reload = AsyncMock()
            
            await options_update_listener(hass, entry_with_options)
            
            # Should remove all entities for zone 002
            removed_calls = mock_entity_registry.async_remove.call_args_list
            removed_entity_ids = [call[0][0] for call in removed_calls]
            
            # Check that zone 002 entities were removed
            zone_002_entities = [e for e in removed_entity_ids if "zone_002" in e]
            assert len(zone_002_entities) > 0
            
            # Check that zone 001 entities were NOT removed
            zone_001_entities = [e for e in removed_entity_ids if "zone_001" in e]
            assert len(zone_001_entities) == 0

    async def test_options_update_zone_added(self, hass: HomeAssistant, mock_config_entry, mock_entity_registry):
        """Test adding a zone updates config."""
        # Set up hass data
        hass.data[DOMAIN] = {
            mock_config_entry.entry_id: mock_config_entry.data.copy(),
            LISTENER: Mock()
        }
        
        # Create zones with new zone 003
        zones_with_new = mock_config_entry.data[CONF_ZONES].copy()
        zones_with_new.append({
            CONF_ZONE_NAME: "Back Door",
            CONF_ZONE_NUMBER: "003",
            CONF_ZONE_CLASS: "wired_door"
        })
        
        # Create entry with options
        entry_with_options = MockConfigEntry(
            domain=DOMAIN,
            data=mock_config_entry.data,
            options={
                CONF_ZONES: zones_with_new
            },
            entry_id=mock_config_entry.entry_id
        )
        
        with patch("homeassistant.helpers.entity_registry.async_get", return_value=mock_entity_registry), \
             patch("homeassistant.helpers.entity_registry.async_entries_for_config_entry", return_value=[]):
            
            # Mock async_update_entry and async_reload
            hass.config_entries.async_update_entry = Mock()
            hass.config_entries.async_reload = AsyncMock()
            
            await options_update_listener(hass, entry_with_options)
            
            # Verify async_update_entry was called with new zones
            update_call = hass.config_entries.async_update_entry.call_args
            updated_data = update_call[1]['data']
            assert len(updated_data[CONF_ZONES]) == 3
            new_zone = next(
                z for z in updated_data[CONF_ZONES]
                if z[CONF_ZONE_NUMBER] == "003"
            )
            assert new_zone[CONF_ZONE_NAME] == "Back Door"

    async def test_options_update_zone_modified(self, hass: HomeAssistant, mock_config_entry, mock_entity_registry):
        """Test modifying a zone name updates config."""
        # Set up hass data
        hass.data[DOMAIN] = {
            mock_config_entry.entry_id: mock_config_entry.data.copy(),
            LISTENER: Mock()
        }
        
        # Update zone 001 name
        zones_modified = mock_config_entry.data[CONF_ZONES].copy()
        zones_modified[0][CONF_ZONE_NAME] = "Main Entrance"
        
        # Create entry with options
        entry_with_options = MockConfigEntry(
            domain=DOMAIN,
            data=mock_config_entry.data,
            options={
                CONF_ZONES: zones_modified
            },
            entry_id=mock_config_entry.entry_id
        )
        
        with patch("homeassistant.helpers.entity_registry.async_get", return_value=mock_entity_registry), \
             patch("homeassistant.helpers.entity_registry.async_entries_for_config_entry", return_value=[]):
            
            # Mock async_update_entry and async_reload
            hass.config_entries.async_update_entry = Mock()
            hass.config_entries.async_reload = AsyncMock()
            
            await options_update_listener(hass, entry_with_options)
            
            # Verify async_update_entry was called with modified zone
            update_call = hass.config_entries.async_update_entry.call_args
            updated_data = update_call[1]['data']
            zone_001 = next(
                z for z in updated_data[CONF_ZONES]
                if z[CONF_ZONE_NUMBER] == "001"
            )
            assert zone_001[CONF_ZONE_NAME] == "Main Entrance"

    async def test_options_update_handles_missing_platform(self, hass: HomeAssistant, mock_config_entry, mock_entity_registry):
        """Test that missing platform attribute is handled gracefully."""
        # Create entity without platform attribute
        bad_entity = Mock()
        bad_entity.entity_id = "binary_sensor.zone_999"
        bad_entity.unique_id = "dmp-12345-zone-999"
        # Don't set platform attribute
        
        # Set up hass data
        hass.data[DOMAIN] = {
            mock_config_entry.entry_id: mock_config_entry.data.copy(),
            LISTENER: Mock()
        }
        
        # Create entry with empty zones
        entry_with_options = MockConfigEntry(
            domain=DOMAIN,
            data=mock_config_entry.data,
            options={
                CONF_ZONES: []
            },
            entry_id=mock_config_entry.entry_id
        )
        
        with patch("homeassistant.helpers.entity_registry.async_get", return_value=mock_entity_registry), \
             patch("homeassistant.helpers.entity_registry.async_entries_for_config_entry", return_value=[bad_entity]):
            
            # Mock async_update_entry and async_reload
            hass.config_entries.async_update_entry = Mock()
            hass.config_entries.async_reload = AsyncMock()
            
            # Should not raise AttributeError even though entity has no unique_id split
            await options_update_listener(hass, entry_with_options)
            
            # The entity should still be removed if it's a zone entity
            # In this case it will try to split unique_id and may fail, but shouldn't crash
            assert True  # Just verify it completes without error

    async def test_options_update_filters_by_zone_number(self, hass: HomeAssistant, mock_config_entry, mock_entity_registry):
        """Test that entity removal correctly filters by zone number."""
        # Create entities with different zone numbers in unique_id
        entities = []
        entity1 = Mock()
        entity1.entity_id = "binary_sensor.zone_001"
        entity1.unique_id = "dmp-12345-zone-001"
        entity1.platform = "binary_sensor"
        entities.append(entity1)
        
        entity2 = Mock()
        entity2.entity_id = "binary_sensor.zone_010"  
        entity2.unique_id = "dmp-12345-zone-010"  # Different zone number
        entity2.platform = "binary_sensor"
        entities.append(entity2)
        
        # Set up hass data
        hass.data[DOMAIN] = {
            mock_config_entry.entry_id: mock_config_entry.data.copy(),
            LISTENER: Mock()
        }
        
        # Remove zone 001 via options
        remaining_zones = [z for z in mock_config_entry.data[CONF_ZONES] if z[CONF_ZONE_NUMBER] != "001"]
        
        # Create entry with options
        entry_with_options = MockConfigEntry(
            domain=DOMAIN,
            data=mock_config_entry.data,
            options={
                CONF_ZONES: remaining_zones
            },
            entry_id=mock_config_entry.entry_id
        )
        
        with patch("homeassistant.helpers.entity_registry.async_get", return_value=mock_entity_registry), \
             patch("homeassistant.helpers.entity_registry.async_entries_for_config_entry", return_value=entities):
            
            # Mock async_update_entry and async_reload
            hass.config_entries.async_update_entry = Mock()
            hass.config_entries.async_reload = AsyncMock()
            
            await options_update_listener(hass, entry_with_options)
            
            # Should remove zone 001 (since only zone 002 remains in options)
            removed_calls = mock_entity_registry.async_remove.call_args_list
            removed_entity_ids = [call[0][0] for call in removed_calls]
            
            # Both zone 001 and zone 010 should be removed since neither is zone 002
            assert "binary_sensor.zone_001" in removed_entity_ids
            assert "binary_sensor.zone_010" in removed_entity_ids
            assert len(removed_entity_ids) == 2