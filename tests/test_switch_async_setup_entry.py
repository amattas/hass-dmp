"""Test async_setup_entry for switch platform."""
import pytest
from unittest.mock import Mock
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmp.const import (
    DOMAIN, LISTENER, CONF_PANEL_ACCOUNT_NUMBER,
    CONF_ZONES, CONF_ZONE_NAME, CONF_ZONE_NUMBER, CONF_ZONE_CLASS
)


@pytest.mark.asyncio
async def test_async_setup_entry_all_zones(self, hass: HomeAssistant):
    """Test async_setup_entry creates bypass switches for all zones."""
    from custom_components.dmp.switch import async_setup_entry
    
    # Set up data
    listener = Mock()
    panel = Mock()
    panel.updateBypassZone = Mock()
    listener.getPanels.return_value = {"12345": panel}
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = listener
    
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PANEL_ACCOUNT_NUMBER: "12345",
            CONF_ZONES: [
                {
                    CONF_ZONE_NAME: "Door Zone",
                    CONF_ZONE_NUMBER: "001",
                    CONF_ZONE_CLASS: "wired_door"
                },
                {
                    CONF_ZONE_NAME: "Window Zone",
                    CONF_ZONE_NUMBER: "002",
                    CONF_ZONE_CLASS: "battery_window"
                },
                {
                    CONF_ZONE_NAME: "Motion Zone",
                    CONF_ZONE_NUMBER: "003",
                    CONF_ZONE_CLASS: "wired_motion"
                },
                {
                    CONF_ZONE_NAME: "Smoke Zone",
                    CONF_ZONE_NUMBER: "004",
                    CONF_ZONE_CLASS: "wired_smoke"
                },
                {
                    CONF_ZONE_NAME: "Glass Break",
                    CONF_ZONE_NUMBER: "005",
                    CONF_ZONE_CLASS: "wired_glassbreak"
                }
            ]
        },
        entry_id="test_entry"
    )
    
    hass.data[DOMAIN][config_entry.entry_id] = config_entry.data
    
    entities = []
    async_add_entities = lambda new_entities, update_before_add=True: entities.extend(new_entities)
    
    await async_setup_entry(hass, config_entry, async_add_entities)
    
    # All zones should get bypass switches (commented out filter)
    assert len(entities) == 5
    
    # Check all are DMPZoneBypassSwitch instances
    from custom_components.dmp.switch import DMPZoneBypassSwitch
    for entity in entities:
        assert isinstance(entity, DMPZoneBypassSwitch)
    
    # Check names
    entity_names = [e.name for e in entities]
    assert "Door Zone Bypass" in entity_names
    assert "Window Zone Bypass" in entity_names
    assert "Motion Zone Bypass" in entity_names
    assert "Smoke Zone Bypass" in entity_names
    assert "Glass Break Bypass" in entity_names

@pytest.mark.asyncio
async def test_async_setup_entry_empty_zones(self, hass: HomeAssistant):
    """Test async_setup_entry with no zones."""
    from custom_components.dmp.switch import async_setup_entry
    
    listener = Mock()
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = listener
    
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PANEL_ACCOUNT_NUMBER: "12345",
            CONF_ZONES: []  # No zones
        },
        entry_id="test_entry"
    )
    
    hass.data[DOMAIN][config_entry.entry_id] = config_entry.data
    
    entities = []
    async_add_entities = lambda new_entities, update_before_add=True: entities.extend(new_entities)
    
    await async_setup_entry(hass, config_entry, async_add_entities)
    
    # No zones, no entities
    assert len(entities) == 0

@pytest.mark.asyncio
async def test_async_setup_entry_update_before_add_false(self, hass: HomeAssistant):
    """Test async_setup_entry calls async_add_entities with update_before_add=False."""
    from custom_components.dmp.switch import async_setup_entry
    
    listener = Mock()
    panel = Mock()
    panel.updateBypassZone = Mock()
    listener.getPanels.return_value = {"12345": panel}
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = listener
    
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PANEL_ACCOUNT_NUMBER: "12345",
            CONF_ZONES: [
                {
                    CONF_ZONE_NAME: "Test Zone",
                    CONF_ZONE_NUMBER: "001",
                    CONF_ZONE_CLASS: "wired_door"
                }
            ]
        },
        entry_id="test_entry"
    )
    
    hass.data[DOMAIN][config_entry.entry_id] = config_entry.data
    
    update_before_add_values = []
    
    def mock_add_entities(entities, update_before_add=True):
        update_before_add_values.append(update_before_add)
    
    await async_setup_entry(hass, config_entry, mock_add_entities)
    
    # Should be called with update_before_add=False
    assert len(update_before_add_values) == 1
    assert update_before_add_values[0] is False