import pytest
pytest.skip("Consolidated into test_switch.py", allow_module_level=True)
"""Complete tests for DMPZoneBypassSwitch entity."""
import pytest
from unittest.mock import Mock, AsyncMock
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmp.switch import DMPZoneBypassSwitch
from custom_components.dmp.const import (
    DOMAIN, LISTENER, CONF_PANEL_ACCOUNT_NUMBER,
    CONF_ZONE_NAME, CONF_ZONE_NUMBER, CONF_ZONE_CLASS
)


class TestDMPZoneBypassSwitchComplete:
    """Complete tests for DMPZoneBypassSwitch entity."""

    @pytest.fixture
    def mock_setup(self, hass: HomeAssistant):
        """Set up complete test environment."""
        listener = Mock()
        panel = Mock()
        panel.getAccountNumber.return_value = "12345"
        panel.getBypassZone.return_value = {"zoneState": False}
        panel.updateBypassZone = Mock()
        panel.getContactTime = Mock(return_value="2023-01-01T00:00:00")
        
        # Mock DMPSender
        dmp_sender = Mock()
        dmp_sender.setBypass = AsyncMock(return_value=None)
        panel._dmpSender = dmp_sender
        
        listener.getPanels.return_value = {"12345": panel}
        listener.register_callback = Mock()
        listener.remove_callback = Mock()
        
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][LISTENER] = listener
        
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "panel_name": "Test Panel",
                CONF_PANEL_ACCOUNT_NUMBER: "12345"
            },
            entry_id="test_entry_id"
        )
        
        hass.data[DOMAIN][config_entry.entry_id] = config_entry.data
        
        return hass, config_entry, listener, panel

    def test_is_on_property(self, mock_setup):
        """Test is_on property returns current state."""
        hass, config_entry, listener, panel = mock_setup
        
        zone_config = {
            CONF_ZONE_NAME: "Test Zone",
            CONF_ZONE_NUMBER: "001",
            CONF_ZONE_CLASS: "wired_door"
        }
        
        switch = DMPZoneBypassSwitch(hass, config_entry, zone_config)
        
        # Initial state
        assert switch.is_on is False
        
        # Change state
        switch._state = True
        assert switch.is_on is True

    def test_device_name_property(self, mock_setup):
        """Test device_name property."""
        hass, config_entry, listener, panel = mock_setup
        
        zone_config = {
            CONF_ZONE_NAME: "Test Zone",
            CONF_ZONE_NUMBER: "001",
            CONF_ZONE_CLASS: "wired_door"
        }
        
        switch = DMPZoneBypassSwitch(hass, config_entry, zone_config)
        assert switch.device_name == "Test Zone"

    def test_should_poll_default(self, mock_setup):
        """Test should_poll defaults to True (parent class default)."""
        hass, config_entry, listener, panel = mock_setup
        
        zone_config = {
            CONF_ZONE_NAME: "Test Zone",
            CONF_ZONE_NUMBER: "001",
            CONF_ZONE_CLASS: "wired_door"
        }
        
        switch = DMPZoneBypassSwitch(hass, config_entry, zone_config)
        # SwitchEntity default is True
        assert switch.should_poll is True

    def test_device_info_missing_name(self, mock_setup):
        """Test device_info without name attribute."""
        hass, config_entry, listener, panel = mock_setup
        
        zone_config = {
            CONF_ZONE_NAME: "Test Zone",
            CONF_ZONE_NUMBER: "001",
            CONF_ZONE_CLASS: "wired_door"
        }
        
        switch = DMPZoneBypassSwitch(hass, config_entry, zone_config)
        device_info = switch.device_info
        
        # Should have identifiers and via_device
        assert "identifiers" in device_info
        assert "via_device" in device_info
        # Should not have name (not set in switch.py device_info)
        assert "name" not in device_info

    @pytest.mark.asyncio
    async def test_process_zone_callback_zone_not_found(self, mock_setup):
        """Test process_zone_callback when zone is not found."""
        hass, config_entry, listener, panel = mock_setup
        
        zone_config = {
            CONF_ZONE_NAME: "Test Zone",
            CONF_ZONE_NUMBER: "999",  # Non-existent zone
            CONF_ZONE_CLASS: "wired_door"
        }
        
        switch = DMPZoneBypassSwitch(hass, config_entry, zone_config)
        switch.async_write_ha_state = Mock()
        
        # Return None for non-existent zone
        panel.getBypassZone.return_value = None
        
        # This will raise an error when trying to access ["zoneState"] on None
        with pytest.raises(TypeError):
            await switch.process_zone_callback()