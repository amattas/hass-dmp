"""Test entity properties for various DMP entities."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmp.alarm_control_panel import DMPArea
from custom_components.dmp.const import (
    DOMAIN, LISTENER, CONF_PANEL_ACCOUNT_NUMBER,
    CONF_ZONE_NAME, CONF_ZONE_NUMBER, CONF_ZONE_CLASS,
    CONF_HOME_AREA, CONF_AWAY_AREA
)

class TestDMPAreaEntity:
    """Test DMPArea alarm control panel entity."""

    @pytest.fixture
    def mock_listener_panel(self):
        """Create mock listener with panel."""
        listener = Mock()
        panel = Mock()
        panel.getAccountNumber.return_value = "12345"
        panel._area_name = "Main Floor"
        panel.disarm = Mock()
        panel.arm = Mock()
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
                CONF_PANEL_ACCOUNT_NUMBER: "12345",
                CONF_HOME_AREA: "01",
                CONF_AWAY_AREA: "02"
            },
            entry_id="test_entry_id"
        )

    def test_dmparea_initialization(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
        """Test DMPArea initialization."""
        hass.data.setdefault(DOMAIN, {})
        listener, panel = mock_listener_panel
        hass.data[DOMAIN][LISTENER] = listener
        hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
        
        area = DMPArea(listener, mock_config_entry.data)
        
        assert area._name == "Test Panel Arming Control"
        assert area._home_zone == "01"
        assert area._away_zone == "02"
        assert area._account_number == "12345"

    def test_dmparea_unique_id(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
        """Test unique_id generation."""
        hass.data.setdefault(DOMAIN, {})
        listener, panel = mock_listener_panel
        hass.data[DOMAIN][LISTENER] = listener
        hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
        
        area = DMPArea(listener, mock_config_entry.data)
        
        assert area.unique_id == "dmp-12345-panel-arming"

    def test_dmparea_device_info(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
        """Test device_info generation."""
        hass.data.setdefault(DOMAIN, {})
        listener, panel = mock_listener_panel
        hass.data[DOMAIN][LISTENER] = listener
        hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
        
        area = DMPArea(listener, mock_config_entry.data)
        device_info = area.device_info
        
        assert device_info["identifiers"] == {(DOMAIN, "dmp-12345-panel")}
        assert device_info["name"] == "Test Panel"
        assert device_info["manufacturer"] == "Digital Monitoring Products"

    def test_dmparea_state_property(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
        """Test state property retrieval from panel."""
        hass.data.setdefault(DOMAIN, {})
        listener, panel = mock_listener_panel
        hass.data[DOMAIN][LISTENER] = listener
        hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
        
        # Mock panel area state - getArea returns the entire area object
        panel.getArea.return_value = {"areaState": "armed_away"}
        
        area = DMPArea(listener, mock_config_entry.data)
        
        assert area.state == "armed_away"
        panel.getArea.assert_called()

    def test_dmparea_supported_features(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
        """Test supported features calculation."""
        hass.data.setdefault(DOMAIN, {})
        listener, panel = mock_listener_panel
        hass.data[DOMAIN][LISTENER] = listener
        hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
        
        area = DMPArea(listener, mock_config_entry.data)
        features = area.supported_features
        
        # Should support arm_home, arm_away and arm_night
        assert features == 7  # ARM_HOME | ARM_AWAY | ARM_NIGHT

    def test_dmparea_extra_state_attributes(self, hass: HomeAssistant, mock_config_entry, mock_listener_panel):
        """Test extra state attributes."""
        hass.data.setdefault(DOMAIN, {})
        listener, panel = mock_listener_panel
        hass.data[DOMAIN][LISTENER] = listener
        hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
        
        # Mock contact time
        panel.getContactTime.return_value = "2023-01-01 12:00:00"
        
        area = DMPArea(listener, mock_config_entry.data)
        attrs = area.extra_state_attributes
        
        assert "last_contact" in attrs
        assert attrs["last_contact"] == "2023-01-01 12:00:00"