"""Test binary sensor module."""
import pytest
from unittest.mock import Mock, patch
from homeassistant.core import HomeAssistant
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmp.binary_sensor import DMPZoneOpenClose, async_setup_entry
from custom_components.dmp.const import DOMAIN, CONF_ZONES, CONF_ZONE_NAME, CONF_ZONE_NUMBER, CONF_ZONE_CLASS


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
        }
    )


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


async def test_async_setup_entry(hass: HomeAssistant, mock_config_entry, mock_zone_config):
    """Test setting up binary sensors."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][mock_config_entry.entry_id] = {
        CONF_ZONES: mock_zone_config
    }
    
    entities = []
    async_add_entities_callback = lambda new_entities: entities.extend(new_entities)
    
    await async_setup_entry(hass, mock_config_entry, async_add_entities_callback)
    
    # Should create trouble zones for all 4 zones
    trouble_zones = [e for e in entities if "Trouble" in e.name]
    assert len(trouble_zones) == 4
    
    # Should create open/close zones for door, window, motion (not smoke)
    open_close_zones = [e for e in entities if "Trouble" not in e.name and "Battery" not in e.name]
    assert len(open_close_zones) == 3
    
    # Should create battery zone for battery_window
    battery_zones = [e for e in entities if "Battery" in e.name]
    assert len(battery_zones) == 1


class TestDMPZoneOpenClose:
    """Test DMPZoneOpenClose sensor."""

    @pytest.fixture
    def mock_panel(self):
        """Create a mock panel."""
        panel = Mock()
        panel._zones = {"001": {"Status": "0001"}}  # Open
        return panel

    def test_icon_door_closed(self, hass: HomeAssistant, mock_config_entry, mock_panel):
        """Test icon for closed door."""
        zone_config = {
            CONF_ZONE_NAME: "Test Door",
            CONF_ZONE_NUMBER: "001",
            CONF_ZONE_CLASS: "wired_door"
        }
        
        with patch.object(hass.data[DOMAIN], 'get', return_value=mock_panel):
            sensor = DMPZoneOpenClose(hass, mock_config_entry, zone_config)
            mock_panel._zones["001"]["Status"] = "0000"  # Closed
            sensor.update()
            assert sensor.icon == "mdi:door-closed"

    def test_icon_door_open(self, hass: HomeAssistant, mock_config_entry, mock_panel):
        """Test icon for open door."""
        zone_config = {
            CONF_ZONE_NAME: "Test Door",
            CONF_ZONE_NUMBER: "001",
            CONF_ZONE_CLASS: "wired_door"
        }
        
        with patch.object(hass.data[DOMAIN], 'get', return_value=mock_panel):
            sensor = DMPZoneOpenClose(hass, mock_config_entry, zone_config)
            mock_panel._zones["001"]["Status"] = "0001"  # Open
            sensor.update()
            assert sensor.icon == "mdi:door-open"