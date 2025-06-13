"""Test alarm control panel entity for DMP integration."""
import pytest
from unittest.mock import Mock, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.const import STATE_ALARM_DISARMED, STATE_ALARM_ARMED_AWAY, STATE_ALARM_ARMED_HOME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmp.alarm_control_panel import DMPArea, async_setup_entry
from custom_components.dmp.const import (
    DOMAIN, LISTENER, CONF_PANEL_ACCOUNT_NUMBER,
    CONF_HOME_AREA, CONF_AWAY_AREA
)


@pytest.fixture
def mock_listener_panel():
    """Create mock listener with panel for DMPArea tests."""
    listener = Mock()
    panel = Mock()
    panel.getAccountNumber.return_value = "12345"
    panel._area_name = "Main Floor"
    panel.updateArea = Mock()
    panel.getArea = Mock(return_value={"areaState": STATE_ALARM_DISARMED})
    panel.getContactTime = Mock()
    listener.getPanels.return_value = {"12345": panel}
    listener.register_callback = Mock()
    listener.remove_callback = Mock()
    return listener, panel


@pytest.fixture
def mock_config_entry():
    """Create mock config entry for DMPArea tests."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "panel_name": "Test Panel",
            CONF_PANEL_ACCOUNT_NUMBER: "12345",
            CONF_HOME_AREA: "01",
            CONF_AWAY_AREA: "02"
        },
        entry_id="test_entry_id"
    )

@pytest.mark.asyncio
async def test_async_setup_entry_creates_area_entity(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
    """Test that async_setup_entry adds a DMPArea entity."""
    listener, panel = mock_listener_panel
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
    entities = []
    def async_add(ents, update_before_add=True):
        entities.extend(ents)
    await async_setup_entry(hass, mock_config_entry, async_add)
    assert len(entities) == 1
    assert isinstance(entities[0], DMPArea)
    assert entities[0].name == "Test Panel Arming Control"


"""Test DMPArea initialization and basic properties."""
def test_dmparea_initialization(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
    listener, panel = mock_listener_panel
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
    area = DMPArea(listener, mock_config_entry.data)
    assert area._name == "Test Panel Arming Control"
    assert area._home_zone == "01"
    assert area._away_zone == "02"
    assert area._account_number == "12345"
    panel.updateArea.assert_called_once_with({
        "areaName": area.name,
        "areaState": STATE_ALARM_DISARMED
    })

@pytest.fixture
def area_with_sender(self, mock_config_entry, mock_listener_panel):
    listener, panel = mock_listener_panel
    sender = Mock()
    sender.disarm = AsyncMock()
    sender.arm = AsyncMock()
    panel._dmpSender = sender
    return DMPArea(listener, mock_config_entry.data), sender

@pytest.mark.asyncio
async def test_async_alarm_disarm(self, area_with_sender):
    area, sender = area_with_sender
    await area.async_alarm_disarm()
    sender.disarm.assert_awaited_once()

@pytest.mark.asyncio
async def test_async_alarm_arm_away(self, area_with_sender):
    area, sender = area_with_sender
    await area.async_alarm_arm_away()
    sender.arm.assert_awaited_once()

@pytest.mark.asyncio
async def test_async_alarm_arm_home_and_night(self, area_with_sender):
    area, sender = area_with_sender
    await area.async_alarm_arm_home()
    sender.arm.assert_any_await(area._home_zone, False)
    await area.async_alarm_arm_night()
    sender.arm.assert_any_await(area._home_zone, True)

@pytest.fixture
def setup_area(self, mock_config_entry, mock_listener_panel):
    listener, panel = mock_listener_panel
    config = mock_config_entry.data
    area = DMPArea(listener, config)
    return area, panel

@pytest.mark.parametrize(
    "prop,expected",
    [
        ("should_poll", False),
        ("code_arm_required", False),
        ("name", "Test Panel Arming Control"),
    ],
)
def test_properties(self, setup_area, prop, expected):
    area, panel = setup_area
    assert getattr(area, prop) == expected
