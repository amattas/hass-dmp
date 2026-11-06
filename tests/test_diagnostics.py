"""Test DMP config entry diagnostics."""

from datetime import UTC, datetime

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.dmp.const import CONF_PANEL_ACCOUNT_NUMBER, CONF_PANEL_REMOTE_KEY


async def test_entry_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    init_integration: MockConfigEntry,
) -> None:
    """Diagnostics report connection and panel state with secrets redacted."""
    data = init_integration.runtime_data
    data.pydmp_panel.is_connected = True
    data.panel.updateContactTime(datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC))

    diag = await get_diagnostics_for_config_entry(hass, hass_client, init_integration)

    entry = diag["entry"]
    assert entry["data"][CONF_PANEL_REMOTE_KEY] == "**REDACTED**"
    assert entry["data"][CONF_PANEL_ACCOUNT_NUMBER] == "**REDACTED**"
    assert entry["unique_id"] == "**REDACTED**"
    assert entry["data"]["zones"][0]["zone_name"] == "Front Door"
    assert diag["connected"] is True
    assert diag["area"] == {"areaName": "Perimeter", "areaState": "disarmed"}
    assert diag["last_contact"] == "2026-01-02T03:04:05+00:00"
    assert diag["status_attributes"] == data.listener.getStatusAttributes()
    assert diag["status_attributes"]["Zone: 001 - Front Door"] == "Normal"
