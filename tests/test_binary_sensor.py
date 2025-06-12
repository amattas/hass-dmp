"""Test binary sensor module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmp.binary_sensor import DMPZoneOpenClose, async_setup_entry
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


class TestDMPZoneOpenClose:
    """Test DMPZoneOpenClose sensor."""

    @pytest.fixture
    def setup_sensor(self, hass: HomeAssistant, mock_config_entry, mock_listener):
        """Set up sensor with mocked dependencies."""
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][LISTENER] = mock_listener
        hass.data[DOMAIN][mock_config_entry.entry_id] = {
            CONF_PANEL_ACCOUNT_NUMBER: "12345"
        }
        return hass, mock_listener.getPanels()["12345"]

    @pytest.mark.parametrize(
        "zone_class,expected_device_class", [
            ("wired_door", "door"),
            ("battery_window", "window"),
            ("wired_motion", "motion"),
            ("unknown_type", "sensors"),
        ]
    )
    def test_device_class_mapping(self, setup_sensor, mock_config_entry, zone_class, expected_device_class):
        hass, mock_panel = setup_sensor
        zone_config = {
            CONF_ZONE_NAME: "Test Zone",
            CONF_ZONE_NUMBER: "001",
            CONF_ZONE_CLASS: zone_class
        }
        sensor = DMPZoneOpenClose(hass, mock_config_entry, zone_config)
        assert sensor._device_class == expected_device_class

    @pytest.mark.parametrize(
        "zone_class,state,expected_icon", [
            ("wired_door", False, "mdi:door-closed"),
            ("wired_door", True, "mdi:door-open"),
            ("battery_window", False, "mdi:window-closed"),
            ("battery_window", True, "mdi:window-open"),
            ("wired_motion", False, "mdi:motion-sensor-off"),
            ("wired_motion", True, "mdi:motion-sensor"),
        ]
    )
    def test_icon_mapping(self, setup_sensor, mock_config_entry, zone_class, state, expected_icon):
        hass, mock_panel = setup_sensor
        zone_config = {
            CONF_ZONE_NAME: "Test Zone",
            CONF_ZONE_NUMBER: "001",
            CONF_ZONE_CLASS: zone_class
        }
        sensor = DMPZoneOpenClose(hass, mock_config_entry, zone_config)
        sensor._state = state
        assert sensor.icon == expected_icon

    @pytest.mark.asyncio
    async def test_process_zone_callback(self, setup_sensor, mock_config_entry):
        """Test processing zone state callback."""
        hass, mock_panel = setup_sensor
        zone_config = {
            CONF_ZONE_NAME: "Test Door",
            CONF_ZONE_NUMBER: "001",
            CONF_ZONE_CLASS: "wired_door"
        }
        
        sensor = DMPZoneOpenClose(hass, mock_config_entry, zone_config)
        sensor.async_write_ha_state = Mock()
        
        # Set panel to return open state
        mock_panel.getOpenCloseZone.return_value = {"zoneState": True}
        
        await sensor.process_zone_callback()
        
        assert sensor._state is True
        sensor.async_write_ha_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_added_to_hass(self, setup_sensor, mock_config_entry, mock_listener):
        """Test registering callback when added to hass."""
        hass, mock_panel = setup_sensor
        zone_config = {
            CONF_ZONE_NAME: "Test Door",
            CONF_ZONE_NUMBER: "001",
            CONF_ZONE_CLASS: "wired_door"
        }
        
        sensor = DMPZoneOpenClose(hass, mock_config_entry, zone_config)
        
        await sensor.async_added_to_hass()
        
        mock_listener.register_callback.assert_called_once_with(sensor.process_zone_callback)

    @pytest.mark.asyncio  
    async def test_async_will_remove_from_hass(self, setup_sensor, mock_config_entry, mock_listener):
        """Test removing callback when removed from hass."""
        hass, mock_panel = setup_sensor
        zone_config = {
            CONF_ZONE_NAME: "Test Door",
            CONF_ZONE_NUMBER: "001",
            CONF_ZONE_CLASS: "wired_door"
        }
        
        sensor = DMPZoneOpenClose(hass, mock_config_entry, zone_config)
        
        await sensor.async_will_remove_from_hass()
        
        mock_listener.remove_callback.assert_called_once_with(sensor.process_zone_callback)