"""Test binary sensor module for DMP integration."""
import pytest
from unittest.mock import Mock
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmp.binary_sensor import async_setup_entry
from custom_components.dmp.const import (
    DOMAIN, LISTENER, CONF_ZONES, CONF_ZONE_NAME, CONF_ZONE_NUMBER,
    CONF_ZONE_CLASS, CONF_PANEL_ACCOUNT_NUMBER
)


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "panel_name": "Test Panel",
            "ip": "192.168.1.1",
            "listen_port": 40002,
            "remote_port": 40001,
            "account_number": "12345"
        },
        entry_id="test_entry_id"
    )


@pytest.fixture
def mock_listener():
    """Create a mock listener with panel."""
    listener = Mock()
    panel = Mock()
    panel.updateOpenCloseZone = Mock()
    panel.getOpenCloseZone = Mock(return_value={"zoneState": False})
    listener.getPanels = Mock(return_value={"12345": panel})
    listener.register_callback = Mock()
    listener.remove_callback = Mock()
    return listener


@pytest.fixture
def mock_zone_config():
    """Create mock zone configuration."""
    return [
        {
            CONF_ZONE_NAME: "Front Door",
            CONF_ZONE_NUMBER: "001",
            CONF_ZONE_CLASS: "wired_door"
        },
        {
            CONF_ZONE_NAME: "Living Room Window",
            CONF_ZONE_NUMBER: "002",
            CONF_ZONE_CLASS: "battery_window"
        },
        {
            CONF_ZONE_NAME: "Motion Sensor",
            CONF_ZONE_NUMBER: "003",
            CONF_ZONE_CLASS: "wired_motion"
        },
        {
            CONF_ZONE_NAME: "Smoke Detector",
            CONF_ZONE_NUMBER: "004",
            CONF_ZONE_CLASS: "wired_smoke"
        }
    ]


class TestBinarySensorSetup:
    """Test setting up binary sensors"""

    @pytest.mark.asyncio
    async def test_async_setup_entry(self, hass: HomeAssistant, mock_config_entry, mock_zone_config, mock_listener):
        """Test setting up binary sensors."""
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][LISTENER] = mock_listener
        hass.data[DOMAIN][mock_config_entry.entry_id] = {
            CONF_ZONES: mock_zone_config,
            CONF_PANEL_ACCOUNT_NUMBER: "12345"
        }
        entities = []
        async_add_entities_callback = lambda new_entities, update_before_add=True: entities.extend(new_entities)   
        await async_setup_entry(hass, mock_config_entry, async_add_entities_callback)
        entity_types = {}
        for e in entities:
            entity_type = type(e).__name__
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        assert entity_types.get('DMPZoneOpenClose', 0) == 3
        assert entity_types.get('DMPZoneBattery', 0) == 1
        assert entity_types.get('DMPZoneTrouble', 0) == 4
        assert entity_types.get('DMPZoneAlarm', 0) == 3
        assert len(entities) == 11


# Import other test classes
from .test_binary_sensor_dmp_zone_open_close import TestDMPZoneOpenClose
from .test_binary_sensor_dmp_zone_battery import TestDMPZoneBattery
from .test_binary_sensor_dmp_zone_trouble import TestDMPZoneTrouble
from .test_binary_sensor_dmp_zone_alarm import TestDMPZoneAlarm
from .test_binary_sensor_dmp_zone_bypass import TestDMPZoneBypass

__all__ = [
    "TestBinarySensorSetup",
    "TestDMPZoneOpenClose",
    "TestDMPZoneBattery",
    "TestDMPZoneTrouble",
    "TestDMPZoneAlarm",
    "TestDMPZoneBypass",
]