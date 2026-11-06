"""Connection loss, reconnect with backoff, and reauth when the key is rejected."""

from __future__ import annotations

import logging
from datetime import timedelta
from types import SimpleNamespace

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from pydmp import DMPAuthenticationError
from pydmp.exceptions import DMPConnectionError
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.dmp.const import DOMAIN

from .conftest import setup_entry

ENTITIES = ("alarm_control_panel.test_panel_arming_control", "switch.front_door_bypass")
# Seconds before each reconnect attempt: doubling from 10, capped at 300.
BACKOFF = (10, 20, 40, 80, 160, 300, 300)
LOST = "Connection to DMP panel 192.168.1.100 lost: connection reset"
RESTORED = "Connection to DMP panel 192.168.1.100 restored"


@pytest.mark.parametrize(
    ("attempts", "restored", "reauth"),
    [
        ([DMPConnectionError("refused")] * len(BACKOFF), False, False),
        ([DMPConnectionError("refused"), OSError("unreachable"), None], True, False),
        (
            [DMPConnectionError("refused"), DMPAuthenticationError("rejected")],
            False,
            True,
        ),
    ],
    ids=["stays_down", "restored", "key_rejected"],
)
async def test_connection_loss_and_recovery(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_pydmp: SimpleNamespace,
    caplog: pytest.LogCaptureFixture,
    freezer: FrozenDateTimeFactory,
    attempts: list[Exception | None],
    restored: bool,
    reauth: bool,
) -> None:
    """Losing the panel makes entities unavailable and logs once; reconnects back
    off until one succeeds (logged once), or a rejected key starts reauth."""
    caplog.set_level(logging.INFO, logger="custom_components.dmp")
    entry = await setup_entry(hass, mock_config_entry)
    listener = entry.runtime_data.listener
    panel = entry.runtime_data.pydmp_panel
    panel.connect.reset_mock()
    panel.start_keepalive.reset_mock()
    panel.update_status.reset_mock()
    panel.connect.side_effect = attempts

    # pydmp reports the dropped keep-alive; a repeat report changes nothing.
    await listener.handle_disconnect(OSError("connection reset"))
    await listener.handle_disconnect(OSError("connection reset"))
    await hass.async_block_till_done()

    assert listener.connected is False
    assert all(hass.states.get(e).state == STATE_UNAVAILABLE for e in ENTITIES)

    for count, delay in enumerate(BACKOFF[: len(attempts)]):
        freezer.tick(timedelta(seconds=delay - 1))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        assert panel.connect.await_count == count  # not before the backoff
        freezer.tick(timedelta(seconds=1))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        assert panel.connect.await_count == count + 1

    assert listener.connected is restored
    assert all(
        (hass.states.get(e).state != STATE_UNAVAILABLE) is restored for e in ENTITIES
    )
    messages = [r.getMessage() for r in caplog.records]
    assert messages.count(LOST) == 1
    assert messages.count(RESTORED) == (1 if restored else 0)
    if restored:
        panel.start_keepalive.assert_awaited_once_with(
            on_disconnect=listener.handle_disconnect
        )
        panel.update_status.assert_awaited_once()
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [f["context"]["source"] for f in flows] == (
        [SOURCE_REAUTH] if reauth else []
    )

    # Unloading stops any pending reconnect.
    assert await hass.config_entries.async_unload(entry.entry_id)
    panel.connect.side_effect = None
    freezer.tick(timedelta(seconds=BACKOFF[-1]))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert panel.connect.await_count == len(attempts)
