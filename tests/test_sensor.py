"""Test sensor module for DMP integration."""
import pytest
from unittest.mock import Mock
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmp.sensor import async_setup_entry, DMPZoneStatus
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


class TestSensorAsyncSetup:
    """Test async_setup_entry for sensor platform."""

    @pytest.mark.asyncio
    async def test_async_setup_entry(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
        listener, panel = mock_listener_panel
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][LISTENER] = listener
        hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
        entities = []
        async_add = lambda new_entities, update_before_add=True: entities.extend(new_entities)

        await async_setup_entry(hass, mock_config_entry, async_add)
        assert len(entities) == 1
        sensor = entities[0]
        assert isinstance(sensor, DMPZoneStatus)


# Import other test classes
from .test_sensor_dmp_zone_status import TestDMPZoneStatus
from .test_sensor_dmp_zone_status_complete import TestDMPZoneStatusComplete

__all__ = [
    "TestSensorAsyncSetup",
    "TestDMPZoneStatus",
    "TestDMPZoneStatusComplete",
]