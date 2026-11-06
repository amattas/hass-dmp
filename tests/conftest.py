"""Shared fixtures for the DMP integration tests."""

from __future__ import annotations

from collections.abc import Generator
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmp.const import (
    CONF_AWAY_AREA,
    CONF_HOME_AREA,
    CONF_PANEL_ACCOUNT_NUMBER,
    CONF_PANEL_IP,
    CONF_PANEL_LISTEN_PORT,
    CONF_PANEL_NAME,
    CONF_PANEL_REMOTE_KEY,
    CONF_PANEL_REMOTE_PORT,
    CONF_ZONE_CLASS,
    CONF_ZONE_NAME,
    CONF_ZONE_NUMBER,
    CONF_ZONES,
    DOMAIN,
)

from .common import FakeArea, FakeZone, attach_runtime_data


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let Home Assistant load custom_components/dmp in every test."""


def make_entry_data(
    account: str = "12345", listen_port: int = 40001, **overrides: Any
) -> dict[str, Any]:
    """Return config entry data for a panel."""
    data: dict[str, Any] = {
        CONF_PANEL_NAME: "Test Panel",
        CONF_PANEL_IP: "192.168.1.100",
        CONF_PANEL_LISTEN_PORT: listen_port,
        CONF_PANEL_REMOTE_PORT: 2001,
        CONF_PANEL_ACCOUNT_NUMBER: account,
        CONF_PANEL_REMOTE_KEY: "testkey",
        CONF_HOME_AREA: "01",
        CONF_AWAY_AREA: "02",
        CONF_ZONES: [
            {
                CONF_ZONE_NAME: "Front Door",
                CONF_ZONE_NUMBER: "001",
                CONF_ZONE_CLASS: "wired_door",
            }
        ],
    }
    data.update(overrides)
    return data


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a DMP config entry (not yet added to hass)."""
    return MockConfigEntry(
        domain=DOMAIN,
        data=make_entry_data(),
        unique_id="12345",
        entry_id="test_entry_id",
    )


@pytest.fixture
def mock_pydmp() -> Generator[SimpleNamespace]:
    """Patch PyDMPPanel and DMPStatusServer with AsyncMock-based fakes.

    Each construction yields a fresh fake, recorded in ``panels``/``servers`` so
    tests with several config entries can tell them apart; the config flow's
    connection test builds its panels from the same factory. ``areas`` and
    ``zones`` are what every fake panel's get_areas()/get_zones() return, and
    ``connect_side_effect`` and ``start_side_effect`` become the side effects of
    each new panel's connect() and each new server's start().
    """
    state = SimpleNamespace(
        panels=[],
        servers=[],
        areas=[FakeArea(1, "Perimeter"), FakeArea(2, "Interior")],
        zones=[FakeZone(1, "Front Door")],
        connect_side_effect=None,
        start_side_effect=None,
    )

    def make_panel(*args: Any, **kwargs: Any) -> MagicMock:
        panel = MagicMock(name=f"PyDMPPanel{len(state.panels)}")
        for method in (
            "connect",
            "disconnect",
            "start_keepalive",
            "stop_keepalive",
            "update_status",
        ):
            setattr(panel, method, AsyncMock())
        panel.connect.side_effect = state.connect_side_effect
        panel.get_areas = AsyncMock(side_effect=lambda: list(state.areas))
        panel.get_zones = AsyncMock(side_effect=lambda: list(state.zones))
        panel._zones = {}
        panel.init_kwargs = kwargs
        state.panels.append(panel)
        return panel

    def make_server(host: str, port: int) -> Mock:
        server = Mock(name=f"DMPStatusServer{len(state.servers)}")
        server.host, server.port = host, port
        server.start = AsyncMock(side_effect=state.start_side_effect)
        server.stop = AsyncMock()
        state.servers.append(server)
        return server

    with (
        patch("custom_components.dmp.PyDMPPanel", side_effect=make_panel),
        patch("custom_components.dmp.config_flow.PyDMPPanel", side_effect=make_panel),
        patch("custom_components.dmp.DMPStatusServer", side_effect=make_server),
    ):
        yield state


async def setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> MockConfigEntry:
    """Add the entry to hass and run the real setup path."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.fixture
async def init_integration(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_pydmp: SimpleNamespace
) -> MockConfigEntry:
    """Set up mock_config_entry through Home Assistant with faked pydmp."""
    return await setup_entry(hass, mock_config_entry)


@pytest.fixture
def entry_with_listener(
    request: pytest.FixtureRequest, mock_config_entry: MockConfigEntry
) -> MockConfigEntry:
    """Attach runtime_data built around the test module's listener fixture.

    For entity unit tests that construct entities directly with a mocked
    listener, without running the integration setup.
    """
    if "mock_listener" in request.fixturenames:
        listener = request.getfixturevalue("mock_listener")
    else:
        # mock_listener_panel returns (listener, panel)
        listener = request.getfixturevalue("mock_listener_panel")[0]
    attach_runtime_data(mock_config_entry, listener)
    return mock_config_entry
