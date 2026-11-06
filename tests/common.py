"""Shared test helpers for the DMP integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import Mock

from homeassistant.config_entries import ConfigEntry

from custom_components.dmp import DMPRuntimeData


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
