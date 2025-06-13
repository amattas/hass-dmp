import pytest
pytest.skip("Consolidated into test_sensor.py", allow_module_level=True)
"""Test DMPZoneStatus sensor initialization and basic functionality."""
import pytest
from unittest.mock import Mock
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


class TestDMPZoneStatus:
    """Test DMPZoneStatus sensor initialization and basic functionality."""

    def test_zone_status_initialization(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
        listener, panel = mock_listener_panel
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][LISTENER] = listener
        hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data

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
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][LISTENER] = listener
        hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data

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
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][LISTENER] = listener
        hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data

        sensor = DMPZoneStatus(hass, mock_config_entry, mock_config_entry.data[CONF_ZONES][0])
        await sensor.async_added_to_hass()
        listener.register_callback.assert_called_once_with(sensor.process_zone_callback)
        await sensor.async_will_remove_from_hass()
        listener.remove_callback.assert_called_once_with(sensor.process_zone_callback)