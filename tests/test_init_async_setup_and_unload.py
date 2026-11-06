"""Test async_setup_entry and async_unload_entry."""

from unittest.mock import patch

import pytest
from homeassistant.components.alarm_control_panel import AlarmControlPanelState
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.core import HomeAssistant
from pydmp import DMPAuthenticationError
from pydmp.exceptions import DMPConnectionError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmp import DMPListener, DMPPanel, options_update_listener
from custom_components.dmp.const import DOMAIN

from .common import FakeArea
from .conftest import make_entry_data, setup_entry


@pytest.mark.parametrize("unique_id", ["12345", None], ids=["current", "pre_unique_id"])
async def test_async_setup_entry_success(hass: HomeAssistant, mock_pydmp, unique_id):
    """Setup connects, starts the status server and stores per-entry runtime_data.

    Entries created before unique IDs were set get the account number as theirs.
    """
    mock_pydmp.areas = [FakeArea(1, "Perimeter", "A"), FakeArea(2, "Interior", "D")]

    entry = await setup_entry(
        hass,
        MockConfigEntry(domain=DOMAIN, data=make_entry_data(), unique_id=unique_id),
    )

    assert entry.state is ConfigEntryState.LOADED
    assert entry.unique_id == "12345"
    (pydmp_panel,) = mock_pydmp.panels
    (status_server,) = mock_pydmp.servers
    assert pydmp_panel.init_kwargs == {"port": 2001}
    pydmp_panel.connect.assert_awaited_once_with("192.168.1.100", "12345", "testkey")
    pydmp_panel.start_keepalive.assert_awaited_once_with(
        on_disconnect=entry.runtime_data.listener.handle_disconnect
    )
    assert (status_server.host, status_server.port) == ("0.0.0.0", 40001)
    status_server.start.assert_awaited_once()

    data = entry.runtime_data
    assert data.pydmp_panel is pydmp_panel
    assert data.status_server is status_server
    assert isinstance(data.listener, DMPListener)
    assert data.listener.connected is True
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


@pytest.mark.parametrize(
    ("fail", "error", "state", "translation_key"),
    [
        (
            "connect",
            DMPAuthenticationError("rejected"),
            ConfigEntryState.SETUP_ERROR,
            "invalid_auth",
        ),
        (
            "connect",
            DMPConnectionError("refused"),
            ConfigEntryState.SETUP_RETRY,
            "cannot_connect",
        ),
        (
            "connect",
            OSError("unreachable"),
            ConfigEntryState.SETUP_RETRY,
            "cannot_connect",
        ),
        ("connect", TimeoutError(), ConfigEntryState.SETUP_RETRY, "cannot_connect"),
        (
            "start",
            OSError("address in use"),
            ConfigEntryState.SETUP_RETRY,
            "listen_port_unavailable",
        ),
    ],
    ids=["invalid_auth", "cannot_connect", "os_error", "timeout", "listen_port_in_use"],
)
async def test_async_setup_entry_failure(
    hass: HomeAssistant,
    mock_config_entry,
    mock_pydmp,
    fail,
    error,
    state,
    translation_key,
):
    """A rejected key starts reauth; an unreachable panel or busy listener port
    retries later. Either way the panel connection is released."""
    setattr(mock_pydmp, f"{fail}_side_effect", error)
    mock_config_entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is state
    assert mock_config_entry.error_reason_translation_key == translation_key
    mock_pydmp.panels[0].disconnect.assert_awaited_once()
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [f["context"]["source"] for f in flows] == (
        [SOURCE_REAUTH] if translation_key == "invalid_auth" else []
    )


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
