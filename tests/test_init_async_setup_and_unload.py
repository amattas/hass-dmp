"""Test async_setup_entry and async_unload_entry."""

from unittest.mock import patch

from homeassistant.components.alarm_control_panel import AlarmControlPanelState
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmp import DMPListener, DMPPanel, options_update_listener
from custom_components.dmp.const import DOMAIN

from .common import FakeArea
from .conftest import make_entry_data, setup_entry


async def test_async_setup_entry_success(
    hass: HomeAssistant, mock_config_entry, mock_pydmp
):
    """Setup connects, starts the status server and stores per-entry runtime_data."""
    mock_pydmp.areas = [FakeArea(1, "Perimeter", "A"), FakeArea(2, "Interior", "D")]

    entry = await setup_entry(hass, mock_config_entry)

    assert entry.state is ConfigEntryState.LOADED
    (pydmp_panel,) = mock_pydmp.panels
    (status_server,) = mock_pydmp.servers
    assert pydmp_panel.init_kwargs == {"port": 2001}
    pydmp_panel.connect.assert_awaited_once_with("192.168.1.100", "12345", "testkey")
    pydmp_panel.start_keepalive.assert_awaited_once()
    assert (status_server.host, status_server.port) == ("0.0.0.0", 40001)
    status_server.start.assert_awaited_once()

    data = entry.runtime_data
    assert data.pydmp_panel is pydmp_panel
    assert data.status_server is status_server
    assert isinstance(data.listener, DMPListener)
    assert isinstance(data.panel, DMPPanel)
    assert data.listener.getPanels() == {"12345": data.panel}
    assert data.config == dict(entry.data)
    assert options_update_listener in entry.update_listeners
    assert DOMAIN not in hass.data

    # The scheduled startup status query set the real armed state (#86).
    assert data.panel.getArea()["areaState"] is AlarmControlPanelState.ARMED_HOME
    state = hass.states.get("alarm_control_panel.test_panel_arming_control")
    assert state is not None
    assert state.state == AlarmControlPanelState.ARMED_HOME


async def test_async_unload_entry_success(
    hass: HomeAssistant, mock_config_entry, mock_pydmp
):
    """Unload stops the entry's status server and disconnects its panel."""
    entry = await setup_entry(hass, mock_config_entry)

    assert await hass.config_entries.async_unload(entry.entry_id)

    assert entry.state is ConfigEntryState.NOT_LOADED
    mock_pydmp.servers[0].stop.assert_awaited_once()
    mock_pydmp.panels[0].stop_keepalive.assert_awaited_once()
    mock_pydmp.panels[0].disconnect.assert_awaited_once()
    assert options_update_listener not in entry.update_listeners


async def test_async_unload_entry_platform_failure(
    hass: HomeAssistant, mock_config_entry, mock_pydmp
):
    """When platforms fail to unload, the connection is left running."""
    entry = await setup_entry(hass, mock_config_entry)

    with patch.object(
        hass.config_entries, "async_unload_platforms", return_value=False
    ):
        assert not await hass.config_entries.async_unload(entry.entry_id)

    mock_pydmp.servers[0].stop.assert_not_awaited()
    mock_pydmp.panels[0].disconnect.assert_not_awaited()


async def test_unload_one_of_two_entries_leaves_the_other(
    hass: HomeAssistant, mock_pydmp
):
    """Each entry owns its own panel and status server (#64)."""
    first = await setup_entry(
        hass,
        MockConfigEntry(
            domain=DOMAIN, data=make_entry_data("11111", 40001), unique_id="11111"
        ),
    )
    second = await setup_entry(
        hass,
        MockConfigEntry(
            domain=DOMAIN, data=make_entry_data("22222", 40002), unique_id="22222"
        ),
    )
    first_panel, second_panel = mock_pydmp.panels
    first_server, second_server = mock_pydmp.servers
    assert [s.port for s in mock_pydmp.servers] == [40001, 40002]

    assert await hass.config_entries.async_unload(first.entry_id)

    first_server.stop.assert_awaited_once()
    first_panel.disconnect.assert_awaited_once()
    second_server.stop.assert_not_awaited()
    second_panel.disconnect.assert_not_awaited()
    assert second.state is ConfigEntryState.LOADED
    assert second.runtime_data.pydmp_panel is second_panel
    assert second.runtime_data.listener.getPanels().keys() == {"22222"}
