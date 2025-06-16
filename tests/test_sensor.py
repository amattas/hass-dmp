"""Test sensor module for DMP integration."""
import pytest
from unittest.mock import Mock
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmp.const import DOMAIN, CONF_PANEL_ACCOUNT_NUMBER, CONF_ZONES, CONF_ZONE_NAME, CONF_ZONE_NUMBER, CONF_ZONE_CLASS


@pytest.fixture
def mock_config_entry():
    """Return a mock config entry for sensor tests."""
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
    """Return a listener and panel pair for sensor tests."""
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


# async_setup_entry test consolidated in test_platform_setup.py

