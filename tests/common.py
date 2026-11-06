"""Shared test helpers for the DMP integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import Mock

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from custom_components.dmp import DMPRuntimeData
from custom_components.dmp.const import DOMAIN


@dataclass
class FakeArea:
    """Minimal stand-in for pydmp.Area as returned by get_areas()."""

    number: int
    name: str
    state: str = "D"


@dataclass
class FakeZone:
    """Minimal stand-in for pydmp.Zone as returned by get_zones()."""

    number: int
    name: str
    state: str = "N"


def attach_runtime_data(
    entry: ConfigEntry, listener: Any, config: dict[str, Any] | None = None
) -> DMPRuntimeData:
    """Give an entry runtime_data around a (mock) listener, as setup would."""
    runtime_data = DMPRuntimeData(
        pydmp_panel=Mock(),
        status_server=Mock(),
        listener=listener,
        panel=Mock(),
        config=dict(entry.data) if config is None else config,
    )
    entry.runtime_data = runtime_data
    return runtime_data


def entry_devices(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, dr.DeviceEntry]:
    """Return the entry's devices keyed by their DMP identifier."""
    registry = dr.async_get(hass)
    return {
        ident: device
        for device in dr.async_entries_for_config_entry(registry, entry.entry_id)
        for domain, ident in device.identifiers
        if domain == DOMAIN
    }
