"""Test DMPZoneStatus sensor initialization and basic functionality."""
import pytest
from unittest.mock import Mock, patch
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
pytestmark = pytest.mark.usefixtures("init_integration")

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


class TestDMPZoneStatus:
    """Test DMPZoneStatus sensor initialization and basic functionality."""

    def test_zone_status_initialization(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
        listener, panel = mock_listener_panel

        zone_config = mock_config_entry.data[CONF_ZONES][0]
        sensor = DMPZoneStatus(hass, mock_config_entry, zone_config)
        assert sensor.name == "Test Zone Status"
        assert sensor.state == "Ready"
        panel.updateStatusZone.assert_called_once_with("001", {
            "zoneName": "Test Zone",
            "zoneNumber": "001",
            "zoneState": "Ready"
        })

    def test_properties_and_icon(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
        listener, panel = mock_listener_panel

        zone_config = mock_config_entry.data[CONF_ZONES][0]
        sensor = DMPZoneStatus(hass, mock_config_entry, zone_config)
        sensor._state = "Open"
        assert sensor.icon == "mdi:door-open"
        assert sensor.unique_id == "dmp-12345-zone-001-status"
        device_info = sensor.device_info
        identifiers = device_info["identifiers"]
        assert (DOMAIN, "dmp-12345-zone-001") in identifiers
        assert sensor.extra_state_attributes == {"last_contact": "2023-01-02T00:00:00"}

    @pytest.mark.asyncio
    async def test_callbacks_registration(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
        listener, panel = mock_listener_panel

        sensor = DMPZoneStatus(hass, mock_config_entry, mock_config_entry.data[CONF_ZONES][0])
        await sensor.async_added_to_hass()
        listener.register_callback.assert_called_once_with(sensor.process_zone_callback)
        await sensor.async_will_remove_from_hass()
        listener.remove_callback.assert_called_once_with(sensor.process_zone_callback)
    
    def test_native_value_property(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
        """Test native_value returns None."""
        listener, panel = mock_listener_panel
        zone_config = mock_config_entry.data[CONF_ZONES][0]
        sensor = DMPZoneStatus(hass, mock_config_entry, zone_config)
        assert sensor.native_value is None

    def test_device_name_property(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
        """Test device_name property."""
        listener, panel = mock_listener_panel
        zone_config = mock_config_entry.data[CONF_ZONES][0]
        sensor = DMPZoneStatus(hass, mock_config_entry, zone_config)
        assert sensor.device_name == "Test Zone"

    @pytest.mark.parametrize(
        "zone_class,state,expected_icon",
        [
            ("wired_door", "Alarm", "mdi:alarm-bell"),
            ("battery_window", "Trouble", "mdi:alert"),
            ("wired_motion", "Bypass", "mdi:alert"),
            ("wired_smoke", "Low Battery", "mdi:battery-alert-variant-outline"),
            ("wired_door", "Open", "mdi:door-open"),
            ("battery_window", "Open", "mdi:window-open"),
            ("wired_motion", "Open", "mdi:door-open"),
            ("wired_door", "Ready", "mdi:check"),
            ("unknown_type", "Open", "mdi:door-open"),
        ],
    )
    def test_icon_mapping_all_states(self, hass, mock_config_entry, mock_listener_panel, init_integration,
                                     zone_class, state, expected_icon):
        zone_config = {
            CONF_ZONE_NAME: "Test Zone",
            CONF_ZONE_NUMBER: "001",
            CONF_ZONE_CLASS: zone_class,
        }
        sensor = DMPZoneStatus(hass, mock_config_entry, zone_config)
        sensor._state = state
        assert sensor.icon == expected_icon

    @pytest.mark.parametrize(
        "zone_class,expected_device_class",
        [
            ("wired_door", "door"),
            ("battery_door", "door"),
            ("wired_window", "window"),
            ("battery_window", "window"),
            ("wired_motion", "motion"),
            ("battery_motion", "motion"),
            ("wired_smoke", "default"),
            ("unknown_type", "default"),
        ],
    )
    def test_device_class_mapping(self, hass, mock_config_entry, mock_listener_panel, init_integration,
                                  zone_class, expected_device_class):
        zone_config = {
            CONF_ZONE_NAME: "Test Zone",
            CONF_ZONE_NUMBER: "001",
            CONF_ZONE_CLASS: zone_class,
        }
        sensor = DMPZoneStatus(hass, mock_config_entry, zone_config)
        assert sensor._device_class == expected_device_class

    @pytest.mark.asyncio
    async def test_process_zone_callback_updates_state(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
        """Test that process_zone_callback updates state from panel and writes state."""
        listener, panel = mock_listener_panel
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][LISTENER] = listener
        hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
        zone_config = mock_config_entry.data[CONF_ZONES][0]
        sensor = DMPZoneStatus(hass, mock_config_entry, zone_config)
        sensor.async_write_ha_state = Mock()
        panel.getStatusZone.return_value = {"zoneState": "Alarm"}
        await sensor.process_zone_callback()
        assert sensor._state == "Alarm"
        sensor.async_write_ha_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_will_remove_from_hass_with_device_registry(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
        """Test device removal when sensor is removed from hass."""
        listener, panel = mock_listener_panel
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][LISTENER] = listener
        hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
        zone_config = mock_config_entry.data[CONF_ZONES][0]
        sensor = DMPZoneStatus(hass, mock_config_entry, zone_config)
        mock_device_registry = Mock()
        mock_device = Mock()
        mock_device.id = "device_id"
        mock_device.identifiers = {(DOMAIN, "dmp-12345-zone-001")}
        mock_entity_devices = [mock_device]
        with patch('custom_components.dmp.sensor.dr.async_get', return_value=mock_device_registry), \
             patch('custom_components.dmp.sensor.dr.async_entries_for_config_entry', return_value=mock_entity_devices):
            sensor._device_info = {"identifiers": {(DOMAIN, "dmp-12345-zone-001")}}
            await sensor.async_will_remove_from_hass()
            mock_device_registry.async_remove_device.assert_called_once_with("device_id")