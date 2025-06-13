"""Test async_setup_entry and async_unload_entry."""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP

import custom_components.dmp as dmp_module
from custom_components.dmp import async_setup_entry, async_unload_entry, options_update_listener
from custom_components.dmp.const import (
    DOMAIN, LISTENER, CONF_PANEL_NAME, CONF_PANEL_IP, CONF_PANEL_LISTEN_PORT,
    CONF_PANEL_REMOTE_PORT, CONF_PANEL_ACCOUNT_NUMBER, CONF_PANEL_REMOTE_KEY,
    CONF_HOME_AREA, CONF_AWAY_AREA
)

@pytest.fixture(autouse=True)
def clean_hass_data(self, hass):
    """Ensure hass.data starts clean for DOMAIN."""
    hass.data.pop(DOMAIN, None)
    return hass

@pytest.mark.asyncio
async def test_async_setup_entry_success(self, monkeypatch, hass):
    """Test successful setup of integration."""
    calls = []

    # Fake DMPListener
    class FakeListener:
        def __init__(self, hass_arg, config):
            calls.append(('listener_init', config))
            self.hass = hass_arg
        async def start(self):
            calls.append(('listener_start',))
        async def stop(self, *args):
            calls.append(('listener_stop',))
            return True
        def addPanel(self, panel):
            calls.append(('addPanel', panel))
        def getPanels(self):
            return {}
        async def updateStatus(self):
            calls.append(('updateStatus',))

    # Fake DMPPanel
    class FakePanel:
        def __init__(self, hass_arg, config):
            calls.append(('panel_init', config))
        def getAccountNumber(self):
            return "12345"

    # Patch classes
    monkeypatch.setattr(dmp_module, 'DMPListener', FakeListener)
    monkeypatch.setattr(dmp_module, 'DMPPanel', FakePanel)

    # Mock async methods
    fwd = AsyncMock()
    monkeypatch.setattr(hass.config_entries, 'async_forward_entry_setups', fwd)

    # Create config entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PANEL_NAME: "Test Panel",
            CONF_PANEL_IP: "192.168.1.100",
            CONF_PANEL_LISTEN_PORT: 40001,
            CONF_PANEL_REMOTE_PORT: 2001,
            CONF_PANEL_ACCOUNT_NUMBER: "12345",
            CONF_PANEL_REMOTE_KEY: "testkey",
            CONF_HOME_AREA: "01",
            CONF_AWAY_AREA: "02"
        },
        entry_id="test_entry"
    )

    # Mock entry methods
    entry.add_update_listener = Mock()

    # Call setup
    result = await async_setup_entry(hass, entry)
    
    assert result is True
    assert ('listener_init', entry.data) in calls
    assert ('listener_start',) in calls
    assert ('panel_init', entry.data) in calls
    assert any(c[0] == 'addPanel' for c in calls)
    
    # Verify update listener registered
    entry.add_update_listener.assert_called_once_with(options_update_listener)
    
    # Verify platforms forwarded
    fwd.assert_called_once()
    
    # Verify data stored
    assert LISTENER in hass.data[DOMAIN]
    assert entry.entry_id in hass.data[DOMAIN]

@pytest.mark.asyncio
async def test_async_unload_entry_success(self, hass):
    """Test successful unload of integration."""
    # Setup mock listener
    mock_listener = Mock()
    mock_listener.stop = AsyncMock(return_value=True)
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = mock_listener
    hass.data[DOMAIN]["test_entry"] = {"test": "data"}
    
    entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")
    
    # Mock unload platforms
    with patch.object(hass.config_entries, 'async_unload_platforms', return_value=True) as mock_unload:
        result = await async_unload_entry(hass, entry)
        
    assert result is True
    mock_listener.stop.assert_called_once()
    mock_unload.assert_called_once()
    # Data should be removed on success
    assert "test_entry" not in hass.data[DOMAIN]

@pytest.mark.asyncio
async def test_async_unload_entry_platform_failure(self, hass):
    """Test unload fails when platforms fail to unload."""
    # Setup mock listener
    mock_listener = Mock()
    mock_listener.stop = AsyncMock(return_value=True)
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = mock_listener
    hass.data[DOMAIN]["test_entry"] = {"test": "data"}
    
    entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")
    
    # Mock unload platforms to fail
    with patch.object(hass.config_entries, 'async_unload_platforms', return_value=False):
        result = await async_unload_entry(hass, entry)
        
    assert result is False
    # Data should not be removed on failure
    assert "test_entry" in hass.data[DOMAIN]

@pytest.mark.asyncio
async def test_async_unload_entry_listener_failure(self, hass):
    """Test unload fails when listener fails to stop."""
    # Setup mock listener that fails to stop
    mock_listener = Mock()
    mock_listener.stop = AsyncMock(return_value=False)
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = mock_listener
    hass.data[DOMAIN]["test_entry"] = {"test": "data"}
    
    entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")
    
    # Mock unload platforms to succeed
    with patch.object(hass.config_entries, 'async_unload_platforms', return_value=True):
        result = await async_unload_entry(hass, entry)
        
    assert result is False
    # Data should not be removed on failure
    assert "test_entry" in hass.data[DOMAIN]