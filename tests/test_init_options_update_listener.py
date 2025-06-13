"""Test the options update listener function."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmp import options_update_listener
from custom_components.dmp.const import (
    DOMAIN,
    LISTENER,
    CONF_ZONES,
    CONF_ZONE_NUMBER,
    CONF_ZONE_NAME,
    CONF_ZONE_CLASS,
)


pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_config_entry():
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
def mock_entity_entries():
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
def mock_entity_registry(mock_entity_entries):
    """Mock entity registry."""
    registry = Mock(spec=er.EntityRegistry)
    registry.entities = {e.entity_id: e for e in mock_entity_entries}
    registry.async_remove = Mock()
    return registry

async def test_options_update_no_changes(hass: HomeAssistant, mock_config_entry):
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

    # Should not modify stored configuration
    assert hass.data[DOMAIN][mock_config_entry.entry_id] == mock_config_entry.data

async def test_options_update_zone_removed(hass: HomeAssistant, mock_config_entry, mock_entity_registry, mock_entity_entries):
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

async def test_options_update_zone_added(hass: HomeAssistant, mock_config_entry, mock_entity_registry):
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

async def test_options_update_zone_modified(hass: HomeAssistant, mock_config_entry, mock_entity_registry):
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

async def test_options_update_handles_missing_platform(hass: HomeAssistant, mock_config_entry, mock_entity_registry):
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
        assert mock_entity_registry.async_remove.called

async def test_options_update_filters_by_zone_number(hass: HomeAssistant, mock_config_entry, mock_entity_registry):
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
