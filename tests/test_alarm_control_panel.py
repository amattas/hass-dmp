"""Test alarm control panel entity for DMP integration."""
import pytest
from unittest.mock import Mock, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.components.alarm_control_panel import AlarmControlPanelState
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
    panel.getArea = Mock(return_value={"areaState": AlarmControlPanelState.DISARMED})
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
async def test_async_setup_entry_creates_area_entity(hass: HomeAssistant, mock_config_entry, mock_listener_panel):
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


def test_dmparea_initialization(hass: HomeAssistant, mock_config_entry, mock_listener_panel):
    """Verify DMPArea initializes with expected values."""
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
        "areaState": AlarmControlPanelState.DISARMED
    })

@pytest.fixture
def area_with_sender(mock_config_entry, mock_listener_panel):
    """Provide a DMPArea with an attached DMPSender for action tests."""
    listener, panel = mock_listener_panel
    sender = Mock()
    sender.disarm = AsyncMock()
    sender.arm = AsyncMock()
    panel._dmpSender = sender
    return DMPArea(listener, mock_config_entry.data), sender

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,expected",
    [
        ("async_alarm_disarm", ("disarm", None)),
        ("async_alarm_arm_away", ("arm", None)),
        ("async_alarm_arm_home", ("arm", False)),
        ("async_alarm_arm_night", ("arm", True)),
    ],
)
async def test_alarm_actions(area_with_sender, method, expected):
    """Verify alarm actions call the DMPSender appropriately."""
    area, sender = area_with_sender
    await getattr(area, method)()

    attr, arg = expected
    if attr == "disarm":
        sender.disarm.assert_awaited_once()
    elif arg is None:
        getattr(sender, attr).assert_awaited_once()
    else:
        getattr(sender, attr).assert_any_await(area._home_zone, arg)

@pytest.fixture
def setup_area(mock_config_entry, mock_listener_panel):
    """Return a DMPArea instance along with its panel."""
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
def test_properties(setup_area, prop, expected):
    """Ensure DMPArea properties return configured values."""
    area, panel = setup_area
    assert getattr(area, prop) == expected


@pytest.mark.asyncio
async def test_callbacks_and_properties(setup_area, mock_listener_panel):
    """Test callback registration and attribute properties."""
    area, panel = setup_area
    listener, _ = mock_listener_panel
    panel.getArea.return_value = {"areaState": "armed"}
    panel.getContactTime.return_value = "now"

    await area.async_added_to_hass()
    listener.register_callback.assert_called_with(area.process_area_callback)

    area.async_write_ha_state = Mock()
    await area.process_area_callback()
    area.async_write_ha_state.assert_called_once()

    assert area.state == "armed"
    assert area.supported_features != 0
    assert area.extra_state_attributes == {"last_contact": "now"}
    assert area.unique_id == "dmp-12345-panel-arming"
    info = area.device_info
    assert info["identifiers"] == {(DOMAIN, "dmp-12345-panel")}
    assert info["name"] == "Test Panel"

    await area.async_will_remove_from_hass()
    listener.remove_callback.assert_called_with(area.process_area_callback)
