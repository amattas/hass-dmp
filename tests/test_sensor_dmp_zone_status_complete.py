"""Test complete properties and edge cases for DMPZoneStatus sensor."""
import pytest
from unittest.mock import Mock, patch
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmp.sensor import DMPZoneStatus
from custom_components.dmp.const import DOMAIN, LISTENER, CONF_PANEL_ACCOUNT_NUMBER, CONF_ZONES, CONF_ZONE_NAME, CONF_ZONE_NUMBER, CONF_ZONE_CLASS


@pytest.fixture
def mock_config_entry():
    entry = MockConfigEntry(
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
        entry_id="test_entry_id"
    )
    return entry


@pytest.fixture
def mock_listener_panel():
    listener = Mock()
    panel = Mock()
    panel.getAccountNumber.return_value = "12345"
    panel.updateStatusZone = Mock()
    panel.getContactTime.return_value = "2023-01-02T00:00:00"
    panel.getStatusZone = Mock(return_value={"zoneState": "Open"})
    listener.getPanels.return_value = {"12345": panel}
    listener.register_callback = Mock()
    listener.remove_callback = Mock()
    return listener, panel


class TestDMPZoneStatusComplete:
    """Test complete properties and edge cases for DMPZoneStatus sensor."""

    @pytest.fixture
    def setup_sensor(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
        listener, panel = mock_listener_panel
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][LISTENER] = listener
        hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
        return hass, panel

    def test_native_value_property(self, setup_sensor, mock_config_entry):
        """Test native_value returns None."""
        hass, panel = setup_sensor
        zone_config = mock_config_entry.data[CONF_ZONES][0]
        sensor = DMPZoneStatus(hass, mock_config_entry, zone_config)
        assert sensor.native_value is None

    def test_device_name_property(self, setup_sensor, mock_config_entry):
        """Test device_name property."""
        hass, panel = setup_sensor
        zone_config = mock_config_entry.data[CONF_ZONES][0]
        sensor = DMPZoneStatus(hass, mock_config_entry, zone_config)
        assert sensor.device_name == "Test Zone"

    def test_icon_mapping_all_states(self, setup_sensor, mock_config_entry):
        """Test icon mapping for all possible states."""
        hass, panel = setup_sensor
        
        # Test different zone classes
        test_cases = [
            # (zone_class, state, expected_icon)
            ("wired_door", "Alarm", "mdi:alarm-bell"),
            ("battery_window", "Trouble", "mdi:alert"),
            ("wired_motion", "Bypass", "mdi:alert"),
            ("wired_smoke", "Low Battery", "mdi:battery-alert-variant-outline"),
            ("wired_door", "Open", "mdi:door-open"),
            ("battery_window", "Open", "mdi:window-open"),
            ("wired_motion", "Open", "mdi:door-open"),  # motion defaults to door
            ("wired_door", "Ready", "mdi:check"),
            ("unknown_type", "Open", "mdi:door-open"),  # default device class
        ]
        
        for zone_class, state, expected_icon in test_cases:
            zone_config = {
                CONF_ZONE_NAME: "Test Zone",
                CONF_ZONE_NUMBER: "001",
                CONF_ZONE_CLASS: zone_class
            }
            sensor = DMPZoneStatus(hass, mock_config_entry, zone_config)
            sensor._state = state
            assert sensor.icon == expected_icon

    def test_device_class_mapping(self, setup_sensor, mock_config_entry):
        """Test device class mapping based on zone class."""
        hass, panel = setup_sensor
        
        test_cases = [
            ("wired_door", "door"),
            ("battery_door", "door"),
            ("wired_window", "window"),
            ("battery_window", "window"),
            ("wired_motion", "motion"),
            ("battery_motion", "motion"),
            ("wired_smoke", "default"),
            ("unknown_type", "default"),
        ]
        
        for zone_class, expected_device_class in test_cases:
            zone_config = {
                CONF_ZONE_NAME: "Test Zone",
                CONF_ZONE_NUMBER: "001",
                CONF_ZONE_CLASS: zone_class
            }
            sensor = DMPZoneStatus(hass, mock_config_entry, zone_config)
            assert sensor._device_class == expected_device_class

    @pytest.mark.asyncio
    async def test_async_will_remove_from_hass_with_device_registry(self, setup_sensor, mock_config_entry):
        """Test device removal when sensor is removed from hass."""
        hass, panel = setup_sensor
        zone_config = mock_config_entry.data[CONF_ZONES][0]
        sensor = DMPZoneStatus(hass, mock_config_entry, zone_config)
        
        # Mock device registry
        mock_device_registry = Mock()
        mock_device = Mock()
        mock_device.id = "device_id"
        mock_device.identifiers = {(DOMAIN, "dmp-12345-zone-001")}
        
        # Mock entity devices
        mock_entity_devices = [mock_device]
        
        with patch('custom_components.dmp.sensor.dr.async_get', return_value=mock_device_registry), \
             patch('custom_components.dmp.sensor.dr.async_entries_for_config_entry', return_value=mock_entity_devices):
            
            # Simulate device_info property access
            sensor._device_info = {"identifiers": {(DOMAIN, "dmp-12345-zone-001")}}
            
            await sensor.async_will_remove_from_hass()
            
            # Device should be removed
            mock_device_registry.async_remove_device.assert_called_once_with("device_id")

    @pytest.mark.asyncio
    async def test_process_zone_callback_updates_state(self, setup_sensor, mock_config_entry):
        """Test that process_zone_callback updates state from panel."""
        hass, panel = setup_sensor
        zone_config = mock_config_entry.data[CONF_ZONES][0]
        sensor = DMPZoneStatus(hass, mock_config_entry, zone_config)
        
        # Mock async_write_ha_state
        sensor.async_write_ha_state = Mock()
        
        # Set panel to return different state
        panel.getStatusZone.return_value = {"zoneState": "Alarm"}
        
        await sensor.process_zone_callback()
        
        assert sensor._state == "Alarm"
        sensor.async_write_ha_state.assert_called_once()

    def test_initialization_updates_panel_status_zone(self, setup_sensor, mock_config_entry):
        """Test that initialization calls updateStatusZone on panel."""
        hass, panel = setup_sensor
        zone_config = mock_config_entry.data[CONF_ZONES][0]
        
        # Reset mock to clear any previous calls
        panel.updateStatusZone.reset_mock()
        
        sensor = DMPZoneStatus(hass, mock_config_entry, zone_config)
        
        # Verify updateStatusZone was called with correct parameters
        panel.updateStatusZone.assert_called_once_with(
            "001",
            {
                "zoneName": "Test Zone",
                "zoneNumber": "001",
                "zoneState": "Ready"
            }
        )