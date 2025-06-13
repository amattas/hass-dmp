import pytest
pytest.skip("Consolidated into test_binary_sensor.py", allow_module_level=True)
"""Test DMPZoneTrouble sensor."""
import pytest
from unittest.mock import Mock
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmp.binary_sensor import DMPZoneTrouble
from custom_components.dmp.const import (
    DOMAIN, LISTENER, CONF_ZONE_NAME, CONF_ZONE_NUMBER,
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


class TestDMPZoneTrouble:
    """Test DMPZoneTrouble sensor."""

    @pytest.fixture
    def setup_trouble_sensor(self, hass: HomeAssistant, mock_config_entry, mock_listener):
        hass.data.setdefault(DOMAIN, {})
        listener = mock_listener
        panel = listener.getPanels()["12345"]
        panel.updateTroubleZone = Mock()
        panel.getTroubleZone = Mock(return_value={"zoneState": False})
        panel.getContactTime = Mock(return_value="t1")
        hass.data[DOMAIN][LISTENER] = listener
        hass.data[DOMAIN][mock_config_entry.entry_id] = {CONF_PANEL_ACCOUNT_NUMBER: "12345"}
        return hass, panel

    def test_trouble_sensor_initialization(self, setup_trouble_sensor, mock_config_entry):
        hass, panel = setup_trouble_sensor
        zone_config = {CONF_ZONE_NAME: "Test Trouble", CONF_ZONE_NUMBER: "011", CONF_ZONE_CLASS: "wired_motion"}
        sensor = DMPZoneTrouble(hass, mock_config_entry, zone_config)
        assert sensor._device_class == "problem"
        assert sensor.name == "Test Trouble Trouble"
        assert sensor.is_on is False
        panel.updateTroubleZone.assert_called_once()

    @pytest.mark.parametrize("state,icon", [(False, 'mdi:check'), (True, 'mdi:alert-outline')])
    def test_trouble_icon(self, setup_trouble_sensor, mock_config_entry, state, icon):
        hass, panel = setup_trouble_sensor
        zone_config = {CONF_ZONE_NAME: "Test Trouble", CONF_ZONE_NUMBER: "011", CONF_ZONE_CLASS: "wired_motion"}
        sensor = DMPZoneTrouble(hass, mock_config_entry, zone_config)
        sensor._state = state
        assert sensor.icon == icon

    @pytest.mark.asyncio
    async def test_trouble_callbacks(self, setup_trouble_sensor, mock_config_entry, mock_listener):
        hass, panel = setup_trouble_sensor
        zone_config = {CONF_ZONE_NAME: "Test Trouble", CONF_ZONE_NUMBER: "011", CONF_ZONE_CLASS: "wired_motion"}
        sensor = DMPZoneTrouble(hass, mock_config_entry, zone_config)
        sensor.async_write_ha_state = Mock()
        panel.getTroubleZone.return_value = {"zoneState": True}
        await sensor.process_zone_callback()
        assert sensor._state is True
        sensor.async_write_ha_state.assert_called_once()
        await sensor.async_added_to_hass()
        mock_listener.register_callback.assert_called_with(sensor.process_zone_callback)
        await sensor.async_will_remove_from_hass()
        mock_listener.remove_callback.assert_called_with(sensor.process_zone_callback)