"""Test DMPRefreshStatusButton entity and async_setup_entry."""
import pytest
from unittest.mock import Mock, AsyncMock
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmp.button import async_setup_entry, DMPRefreshStatusButton
from custom_components.dmp.const import DOMAIN, LISTENER, CONF_PANEL_NAME, CONF_PANEL_ACCOUNT_NUMBER

@pytest.fixture
def mock_config_entry():
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
    listener = Mock()
    listener.updateStatus = AsyncMock()
    listener.register_callback = Mock()
    listener.remove_callback = Mock()
    listener.getStatusAttributes = Mock(return_value={"foo": "bar"})
    return listener

@pytest.mark.asyncio
async def test_async_setup_entry(hass: HomeAssistant, mock_config_entry, mock_listener):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = mock_listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data
    entities = []
    async_add = lambda new_entities, update_before_add=False: entities.extend(new_entities)

    await async_setup_entry(hass, mock_config_entry, async_add)
    assert len(entities) == 1
    assert isinstance(entities[0], DMPRefreshStatusButton)

def test_button_properties(hass: HomeAssistant, mock_config_entry, mock_listener):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = mock_listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data

    btn = DMPRefreshStatusButton(hass, mock_config_entry)
    assert btn.name == "Refresh Status"
    assert btn.unique_id == "dmp-12345-panel-refresh-status"
    device_info = btn.device_info
    assert device_info["identifiers"] == {(DOMAIN, "dmp-12345-panel")}
    assert device_info["name"] == "Test Panel"
    assert btn.extra_state_attributes == {"foo": "bar"}

@pytest.mark.asyncio
async def test_async_press_and_callbacks(hass: HomeAssistant, mock_config_entry, mock_listener):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = mock_listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = mock_config_entry.data

    btn = DMPRefreshStatusButton(hass, mock_config_entry)
    await btn.async_added_to_hass()
    mock_listener.register_callback.assert_called_once_with(btn.process_zone_callback)

    await btn.async_will_remove_from_hass()
    mock_listener.remove_callback.assert_called_once_with(btn.process_zone_callback)

    await btn.async_press()
    mock_listener.updateStatus.assert_awaited_once()
