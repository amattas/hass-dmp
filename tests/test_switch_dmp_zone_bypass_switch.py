"""Test DMPZoneBypassSwitch entity."""
import pytest
from unittest.mock import Mock, AsyncMock
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmp.switch import DMPZoneBypassSwitch
from custom_components.dmp.const import (
    DOMAIN, LISTENER, CONF_PANEL_ACCOUNT_NUMBER,
    CONF_ZONE_NAME, CONF_ZONE_NUMBER, CONF_ZONE_CLASS
)


@pytest.fixture
def mock_listener_panel(self):
    """Create mock listener with panel."""
    listener = Mock()
    panel = Mock()
    panel.getAccountNumber.return_value = "12345"
    panel.getBypassZone.return_value = {"zoneState": False}
    panel.updateBypassZone = Mock()
    
    # Mock DMPSender
    dmp_sender = Mock()
    dmp_sender.setBypass = AsyncMock(return_value=None)
    panel._dmpSender = dmp_sender
    
    listener.getPanels.return_value = {"12345": panel}
    listener.register_callback = Mock()
    listener.remove_callback = Mock()
    return listener, panel

@pytest.fixture
def mock_config_entry(self):
    """Create mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "panel_name": "Test Panel",
            CONF_PANEL_ACCOUNT_NUMBER: "12345"
        },
        entry_id="test_entry_id"
    )

@pytest.mark.parametrize(
    "zone_name,zone_number,zone_class,expected_name,expected_unique", [
        ("Front Door", "001", "wired_door",
            "Front Door Bypass", "dmp-12345-zone-001-bypass-switch"),
        ("Back Window", "002", "battery_window",
            "Back Window Bypass", "dmp-12345-zone-002-bypass-switch"),
    ]
)
def test_basic_properties(self, hass: HomeAssistant, mock_config_entry,
                            mock_listener_panel,
                            zone_name, zone_number, zone_class,
                            expected_name, expected_unique):
    listener, panel = mock_listener_panel
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
    zone_config = {
        CONF_ZONE_NAME: zone_name,
        CONF_ZONE_NUMBER: zone_number,
        CONF_ZONE_CLASS: zone_class,
    }
    switch = DMPZoneBypassSwitch(hass, mock_config_entry, zone_config)
    # Check initialization defaults
    assert switch._name == expected_name
    assert switch._number == zone_number
    assert switch._state is False
    # Check name, unique_id and device_class properties
    assert switch.name == expected_name
    assert switch.unique_id == expected_unique
    assert switch.device_class == "switch"

@pytest.mark.asyncio
async def test_async_turn_on(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
    """Test turning on bypass via async_turn_on calls setBypass with True."""
    listener, panel = mock_listener_panel
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
    zone_config = {
        CONF_ZONE_NAME: "Front Door",
        CONF_ZONE_NUMBER: "001",
        CONF_ZONE_CLASS: "wired_door",
    }
    switch = DMPZoneBypassSwitch(hass, mock_config_entry, zone_config)
    await switch.async_turn_on()
    panel._dmpSender.setBypass.assert_called_once_with("001", True)

@pytest.mark.asyncio
async def test_async_turn_off(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
    """Test turning off bypass via async_turn_off calls setBypass with False."""
    listener, panel = mock_listener_panel
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
    zone_config = {
        CONF_ZONE_NAME: "Front Door",
        CONF_ZONE_NUMBER: "001",
        CONF_ZONE_CLASS: "wired_door",
    }
    switch = DMPZoneBypassSwitch(hass, mock_config_entry, zone_config)
    await switch.async_turn_off()
    panel._dmpSender.setBypass.assert_called_once_with("001", False)

@pytest.mark.parametrize(
    "zone_name,zone_number,zone_class", [
        ("Front Door", "001", "wired_door"),
        ("Back Window", "002", "battery_window"),
    ]
)
def test_initial_update_calls_panel_update(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel,
                                            zone_name, zone_number, zone_class):
    """Init should call panel.updateBypassZone with initial state."""
    listener, panel = mock_listener_panel
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
    zone_config = {
        CONF_ZONE_NAME: zone_name,
        CONF_ZONE_NUMBER: zone_number,
        CONF_ZONE_CLASS: zone_class,
    }
    switch = DMPZoneBypassSwitch(hass, mock_config_entry, zone_config)
    # Should have been called once on init
    panel.updateBypassZone.assert_called_once()
    args = panel.updateBypassZone.call_args[0]
    assert args[0] == zone_number
    init_obj = args[1]
    assert init_obj["zoneName"] == zone_name
    assert init_obj["zoneNumber"] == zone_number
    assert init_obj["zoneState"] is False

def test_device_info_and_poll(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
    """Test device_info identifiers and default should_poll property."""
    listener, panel = mock_listener_panel
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
    zone_config = {CONF_ZONE_NAME: "Front Door", CONF_ZONE_NUMBER: "001", CONF_ZONE_CLASS: "wired_door"}
    switch = DMPZoneBypassSwitch(hass, mock_config_entry, zone_config)
    # should_poll default as implemented
    assert switch.should_poll is True
    # device_info identifiers
    device_info = switch.device_info
    expected_id = (DOMAIN, f"dmp-12345-zone-001")
    assert expected_id in device_info["identifiers"]
    # via_device set to panel
    assert device_info["via_device"] == (DOMAIN, "dmp-12345-panel")

@pytest.mark.asyncio
async def test_process_zone_callback_and_callbacks(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
    """Test process_zone_callback updates state and register/unregister callbacks."""
    listener, panel = mock_listener_panel
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
    zone_config = {CONF_ZONE_NAME: "Front Door", CONF_ZONE_NUMBER: "001", CONF_ZONE_CLASS: "wired_door"}
    switch = DMPZoneBypassSwitch(hass, mock_config_entry, zone_config)
    switch.async_write_ha_state = Mock()
    panel.getBypassZone.return_value = {"zoneState": True}
    await switch.process_zone_callback()
    assert switch._state is True
    switch.async_write_ha_state.assert_called_once()
    await switch.async_added_to_hass()
    listener.register_callback.assert_called_once_with(switch.process_zone_callback)
    await switch.async_will_remove_from_hass()
    listener.remove_callback.assert_called_once_with(switch.process_zone_callback)
def test_is_on_property(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
    """Test is_on property returns current state."""
    listener, panel = mock_listener_panel
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
    zone_config = {CONF_ZONE_NAME: "Front Door", CONF_ZONE_NUMBER: "001", CONF_ZONE_CLASS: "wired_door"}
    switch = DMPZoneBypassSwitch(hass, mock_config_entry, zone_config)
    assert switch.is_on is False
    switch._state = True
    assert switch.is_on is True
def test_device_name_property(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
    """Test device_name property."""
    listener, panel = mock_listener_panel
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
    zone_config = {CONF_ZONE_NAME: "Front Door", CONF_ZONE_NUMBER: "001", CONF_ZONE_CLASS: "wired_door"}
    switch = DMPZoneBypassSwitch(hass, mock_config_entry, zone_config)
    assert switch.device_name == "Front Door"
def test_device_info_missing_name(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
    """Test device_info does not include a name attribute."""
    listener, panel = mock_listener_panel
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
    zone_config = {CONF_ZONE_NAME: "Front Door", CONF_ZONE_NUMBER: "001", CONF_ZONE_CLASS: "wired_door"}
    switch = DMPZoneBypassSwitch(hass, mock_config_entry, zone_config)
    device_info = switch.device_info
    assert "name" not in device_info
@pytest.mark.asyncio
async def test_process_zone_callback_zone_not_found(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
    """Test process_zone_callback when zone is not found."""
    listener, panel = mock_listener_panel
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
    zone_config = {CONF_ZONE_NAME: "Front Door", CONF_ZONE_NUMBER: "999", CONF_ZONE_CLASS: "wired_door"}
    panel.getBypassZone.return_value = None
    switch = DMPZoneBypassSwitch(hass, mock_config_entry, zone_config)
    with pytest.raises(TypeError):
        await switch.process_zone_callback()