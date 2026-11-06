"""Diagnostics support for the DMP integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import DMPConfigEntry
from .const import CONF_PANEL_ACCOUNT_NUMBER, CONF_PANEL_REMOTE_KEY

# The entry's unique_id is the panel account number.
TO_REDACT = {CONF_PANEL_REMOTE_KEY, CONF_PANEL_ACCOUNT_NUMBER, "unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: DMPConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = entry.runtime_data
    last_contact = data.panel.getContactTime()
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "connected": data.pydmp_panel.is_connected,
        "area": data.panel.getArea(),
        "last_contact": last_contact.isoformat() if last_contact else None,
        "status_attributes": data.listener.getStatusAttributes(),
    }
