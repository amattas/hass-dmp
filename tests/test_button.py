"""Test DMPRefreshStatusButton entity and async_setup_entry."""
import pytest
from unittest.mock import Mock, AsyncMock
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmp.button import async_setup_entry, DMPRefreshStatusButton
from custom_components.dmp.const import DOMAIN, CONF_PANEL_NAME, CONF_PANEL_ACCOUNT_NUMBER

pytestmark = pytest.mark.usefixtures("init_integration")

@pytest.fixture
def mock_config_entry():
    """Return a mock config entry for button tests."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PANEL_NAME: "Test Panel",
            CONF_PANEL_ACCOUNT_NUMBER: "12345"
        },
        entry_id="test_entry_id"
    )
    return entry

@pytest.fixture
def mock_listener():
    """Return a mock listener used by button entities."""
    listener = Mock()
    listener.updateStatus = AsyncMock()
    listener.register_callback = Mock()
    listener.remove_callback = Mock()
    listener.getStatusAttributes = Mock(return_value={"foo": "bar"})
    return listener

@pytest.mark.asyncio
async def test_async_setup_entry(hass: HomeAssistant, mock_config_entry, mock_listener):
    """Ensure async_setup_entry registers a refresh button entity."""
    entities = []
    
    def async_add(new_entities, update_before_add=False):
        """Async callback to append new entities to list."""
        entities.extend(new_entities)

    await async_setup_entry(hass, mock_config_entry, async_add)
    assert len(entities) == 1
    assert isinstance(entities[0], DMPRefreshStatusButton)

def test_button_properties(hass: HomeAssistant, mock_config_entry, mock_listener):
    """Verify DMPRefreshStatusButton exposes expected properties."""

    btn = DMPRefreshStatusButton(hass, mock_config_entry)
    assert btn.name == "Refresh Status"
    assert btn.unique_id == "dmp-12345-panel-refresh-status"
    device_info = btn.device_info
    assert device_info["identifiers"] == {(DOMAIN, "dmp-12345-panel")}
    assert device_info["name"] == "Test Panel"
    assert btn.extra_state_attributes == {"foo": "bar"}

@pytest.mark.asyncio
async def test_async_press_and_callbacks(hass: HomeAssistant, mock_config_entry, mock_listener):
    """Test button press triggers update and manages callbacks."""

    btn = DMPRefreshStatusButton(hass, mock_config_entry)
    await btn.async_added_to_hass()
    mock_listener.register_callback.assert_called_once_with(btn.process_zone_callback)

    await btn.async_will_remove_from_hass()
    mock_listener.remove_callback.assert_called_once_with(btn.process_zone_callback)

    await btn.async_press()
    mock_listener.updateStatus.assert_awaited_once()

@pytest.mark.asyncio
async def test_process_zone_callback(hass: HomeAssistant, mock_config_entry, mock_listener):
    """Confirm process_zone_callback writes state."""
    btn = DMPRefreshStatusButton(hass, mock_config_entry)
    btn.async_write_ha_state = Mock()
    await btn.process_zone_callback()
    btn.async_write_ha_state.assert_called_once()

