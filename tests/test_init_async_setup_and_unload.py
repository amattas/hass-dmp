"""Test async_setup_entry and async_unload_entry."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.dmp as dmp_module
from custom_components.dmp import (
    async_setup_entry,
    async_unload_entry,
    options_update_listener,
)
from custom_components.dmp.const import (
    DOMAIN,
    LISTENER,
    PYDMP_PANEL,
    STATUS_SERVER,
    CONF_PANEL_NAME,
    CONF_PANEL_IP,
    CONF_PANEL_LISTEN_PORT,
    CONF_PANEL_REMOTE_PORT,
    CONF_PANEL_ACCOUNT_NUMBER,
    CONF_PANEL_REMOTE_KEY,
    CONF_HOME_AREA,
    CONF_AWAY_AREA,
)


@pytest.fixture(autouse=True)
def clean_hass_data(hass):
    """Ensure hass.data starts clean for DOMAIN."""
    hass.data.pop(DOMAIN, None)
    return hass


@pytest.mark.asyncio
async def test_async_setup_entry_success(monkeypatch, hass):
    """Test successful setup of integration."""
    calls = []

    mock_pydmp_panel = AsyncMock()
    mock_pydmp_panel.connect = AsyncMock()
    mock_pydmp_panel.start_keepalive = AsyncMock()
    mock_pydmp_panel._zones = {}
    mock_pydmp_panel._areas = {}

    mock_status_server = AsyncMock()
    mock_status_server.start = AsyncMock()
    mock_status_server.stop = AsyncMock()
    mock_status_server.register_callback = Mock()

    def fake_pydmp_panel(port=2001):
        calls.append(("pydmp_panel_init", port))
        return mock_pydmp_panel

    def fake_status_server(host, port):
        calls.append(("status_server_init", host, port))
        return mock_status_server

    class FakePanel:
        def __init__(self, hass_arg, config, pydmp_panel=None):
            calls.append(("panel_init", config))
            self._pydmp_panel = pydmp_panel

        def getAccountNumber(self):
            return "12345"

    class FakeListener:
        def __init__(self, hass_arg, config, pydmp_panel=None, status_server=None):
            calls.append(("listener_init", config))

        def addPanel(self, panel):
            calls.append(("addPanel", panel))

        def getPanels(self):
            return {}

        async def updateStatus(self):
            calls.append(("updateStatus",))

    monkeypatch.setattr(dmp_module, "PyDMPPanel", fake_pydmp_panel)
    monkeypatch.setattr(dmp_module, "DMPStatusServer", fake_status_server)
    monkeypatch.setattr(dmp_module, "DMPPanel", FakePanel)
    monkeypatch.setattr(dmp_module, "DMPListener", FakeListener)

    fwd = AsyncMock()
    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", fwd)

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
            CONF_AWAY_AREA: "02",
        },
        entry_id="test_entry",
    )

    entry.add_update_listener = Mock()

    result = await async_setup_entry(hass, entry)

    assert result is True
    assert ("pydmp_panel_init", 2001) in calls
    assert ("status_server_init", "0.0.0.0", 40001) in calls
    assert ("panel_init", entry.data) in calls
    assert ("listener_init", entry.data) in calls
    assert any(c[0] == "addPanel" for c in calls)

    mock_pydmp_panel.connect.assert_awaited_once_with(
        "192.168.1.100", "12345", "testkey"
    )
    mock_pydmp_panel.start_keepalive.assert_awaited_once()
    mock_status_server.start.assert_awaited_once()

    entry.add_update_listener.assert_called_once_with(options_update_listener)
    fwd.assert_called_once()

    assert LISTENER in hass.data[DOMAIN]
    assert PYDMP_PANEL in hass.data[DOMAIN]
    assert STATUS_SERVER in hass.data[DOMAIN]
    assert entry.entry_id in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_async_unload_entry_success(hass):
    """Test successful unload of integration."""
    mock_pydmp_panel = AsyncMock()
    mock_pydmp_panel.stop_keepalive = AsyncMock()
    mock_pydmp_panel.disconnect = AsyncMock()

    mock_status_server = AsyncMock()
    mock_status_server.stop = AsyncMock()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][PYDMP_PANEL] = mock_pydmp_panel
    hass.data[DOMAIN][STATUS_SERVER] = mock_status_server
    hass.data[DOMAIN]["test_entry"] = {"test": "data"}

    entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")

    with patch.object(
        hass.config_entries, "async_unload_platforms", return_value=True
    ) as mock_unload:
        result = await async_unload_entry(hass, entry)

    assert result is True
    mock_status_server.stop.assert_awaited_once()
    mock_pydmp_panel.stop_keepalive.assert_awaited_once()
    mock_pydmp_panel.disconnect.assert_awaited_once()
    mock_unload.assert_called_once()
    assert "test_entry" not in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_async_unload_entry_platform_failure(hass):
    """Test unload fails when platforms fail to unload."""
    mock_pydmp_panel = AsyncMock()
    mock_pydmp_panel.stop_keepalive = AsyncMock()
    mock_pydmp_panel.disconnect = AsyncMock()

    mock_status_server = AsyncMock()
    mock_status_server.stop = AsyncMock()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][PYDMP_PANEL] = mock_pydmp_panel
    hass.data[DOMAIN][STATUS_SERVER] = mock_status_server
    hass.data[DOMAIN]["test_entry"] = {"test": "data"}

    entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")

    with patch.object(
        hass.config_entries, "async_unload_platforms", return_value=False
    ):
        result = await async_unload_entry(hass, entry)

    assert result is False
    assert "test_entry" in hass.data[DOMAIN]
