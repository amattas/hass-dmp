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
@pytest.mark.parametrize(
    "zones,expected_count,expected_names",
    [
        (
            [
                {CONF_ZONE_NAME: "Door Zone", CONF_ZONE_NUMBER: "001", CONF_ZONE_CLASS: "wired_door"},
                {CONF_ZONE_NAME: "Window Zone", CONF_ZONE_NUMBER: "002", CONF_ZONE_CLASS: "battery_window"},
                {CONF_ZONE_NAME: "Motion Zone", CONF_ZONE_NUMBER: "003", CONF_ZONE_CLASS: "wired_motion"},
                {CONF_ZONE_NAME: "Smoke Zone", CONF_ZONE_NUMBER: "004", CONF_ZONE_CLASS: "wired_smoke"},
                {CONF_ZONE_NAME: "Glass Break", CONF_ZONE_NUMBER: "005", CONF_ZONE_CLASS: "wired_glassbreak"},
            ],
            5,
            [
                "Door Zone Bypass",
                "Window Zone Bypass",
                "Motion Zone Bypass",
                "Smoke Zone Bypass",
                "Glass Break Bypass",
            ],
        ),
        ([], 0, []),
    ],
)
async def test_async_setup_entry_zones(hass: HomeAssistant, zones, expected_count, expected_names):
    """Test async_setup_entry creates bypass switches as expected."""
    from custom_components.dmp.switch import async_setup_entry, DMPZoneBypassSwitch
    
    listener = Mock()
    panel = Mock()
    panel.updateBypassZone = Mock()
    listener.getPanels.return_value = {"12345": panel}

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = listener

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PANEL_ACCOUNT_NUMBER: "12345", CONF_ZONES: zones},
        entry_id="test_entry"
    )
    
    hass.data[DOMAIN][config_entry.entry_id] = config_entry.data
    
    entities = []
    
    def async_add_entities(new_entities, update_before_add=False):
        """Async callback to append new entities to list."""
        entities.extend(new_entities)

    await async_setup_entry(hass, config_entry, async_add_entities)
    
    assert len(entities) == expected_count
    if expected_names:
        for ent in entities:
            assert isinstance(ent, DMPZoneBypassSwitch)
        entity_names = [e.name for e in entities]
        for name in expected_names:
            assert name in entity_names

@pytest.mark.asyncio
async def test_async_setup_entry_update_before_add_false(hass: HomeAssistant):
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
    
    assert len(update_before_add_values) == 1
    assert update_before_add_values[0] is False