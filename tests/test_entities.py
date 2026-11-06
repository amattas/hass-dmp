"""Entity-layer tests for every DMP platform, run through the real setup path."""

from __future__ import annotations

from collections.abc import Generator
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, PropertyMock, patch

import pytest
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_component import DATA_INSTANCES
from pydmp.exceptions import DMPConnectionError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmp.const import (
    CONF_ZONE_CLASS,
    CONF_ZONE_NAME,
    CONF_ZONE_NUMBER,
    CONF_ZONES,
    DOMAIN,
)

from .common import entry_devices
from .conftest import make_entry_data, setup_entry

STATUS_OPTIONS = ["ready", "open", "trouble", "bypass", "low_battery", "alarm"]


def _zone(name: str, number: str, zone_class: str) -> dict[str, str]:
    return {CONF_ZONE_NAME: name, CONF_ZONE_NUMBER: number, CONF_ZONE_CLASS: zone_class}


async def _setup_zones(hass: HomeAssistant, *zones: dict[str, str]) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=make_entry_data(**{CONF_ZONES: list(zones)}),
        unique_id="12345",
        entry_id="test_entry_id",
    )
    return await setup_entry(hass, entry)


@pytest.fixture
def enable_all_entities() -> Generator[None]:
    """Create disabled-by-default entities enabled, so they have states."""
    with patch(
        "homeassistant.helpers.entity.Entity.entity_registry_enabled_default",
        new_callable=PropertyMock,
        return_value=True,
    ):
        yield


@pytest.mark.parametrize(
    "domain,unique_id,entity_id,translation_key,category,device_class,enabled",
    [
        (
            "alarm_control_panel",
            "dmp-12345-panel-arming",
            "alarm_control_panel.test_panel_arming_control",
            "arming",
            None,
            None,
            True,
        ),
        (
            "button",
            "dmp-12345-panel-refresh-status",
            "button.test_panel_refresh_status",
            "refresh_status",
            EntityCategory.CONFIG,
            None,
            True,
        ),
        (
            "binary_sensor",
            "dmp-12345-zone-001-openclose",
            "binary_sensor.front_door",
            "door",
            None,
            "door",
            True,
        ),
        (
            "binary_sensor",
            "dmp-12345-zone-001-trouble",
            "binary_sensor.front_door_trouble",
            "trouble",
            EntityCategory.DIAGNOSTIC,
            "problem",
            False,
        ),
        (
            "binary_sensor",
            "dmp-12345-zone-001-alarm",
            "binary_sensor.front_door_alarm",
            "alarm",
            None,
            "safety",
            True,
        ),
        (
            "sensor",
            "dmp-12345-zone-001-status",
            "sensor.front_door_status",
            "status",
            EntityCategory.DIAGNOSTIC,
            "enum",
            False,
        ),
        (
            "switch",
            "dmp-12345-zone-001-bypass-switch",
            "switch.front_door_bypass",
            "bypass",
            EntityCategory.CONFIG,
            "switch",
            True,
        ),
        (
            "binary_sensor",
            "dmp-12345-zone-002-battery",
            "binary_sensor.back_window_battery",
            "battery",
            EntityCategory.DIAGNOSTIC,
            "battery",
            True,
        ),
    ],
)
async def test_entity_registry_entries(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_pydmp: SimpleNamespace,
    domain: str,
    unique_id: str,
    entity_id: str,
    translation_key: str,
    category: EntityCategory | None,
    device_class: str | None,
    enabled: bool,
) -> None:
    """Unique IDs are stable and each entity carries its quality-scale metadata."""
    await _setup_zones(
        hass,
        _zone("Front Door", "001", "wired_door"),
        _zone("Back Window", "002", "battery_window"),
    )

    entry = entity_registry.async_get(entity_id)
    assert entry is not None
    assert entry.entity_id == entity_registry.async_get_entity_id(
        domain, DOMAIN, unique_id
    )
    assert entry.has_entity_name is True
    assert entry.translation_key == translation_key
    assert entry.entity_category == category
    assert entry.original_device_class == device_class
    assert entry.disabled == (not enabled)
    if translation_key == "status":
        assert entry.capabilities == {"options": STATUS_OPTIONS}


@pytest.mark.parametrize(
    "zone_class,suffixes,open_close,model",
    [
        (
            "wired_door",
            {"openclose", "trouble", "alarm", "status", "bypass-switch"},
            ("door", "door"),
            "Wired door",
        ),
        (
            "battery_door",
            {"openclose", "battery", "trouble", "alarm", "status", "bypass-switch"},
            ("door", "door"),
            "Battery door",
        ),
        (
            "battery_window",
            {"openclose", "battery", "trouble", "alarm", "status", "bypass-switch"},
            ("window", "window"),
            "Battery window",
        ),
        (
            "wired_motion",
            {"openclose", "trouble", "alarm", "status", "bypass-switch"},
            ("motion", "motion"),
            "Wired motion",
        ),
        (
            "default",
            {"openclose", "trouble", "status", "bypass-switch"},
            ("open_close", None),
            None,
        ),
        (
            "wired_glassbreak",
            {"trouble", "alarm", "status", "bypass-switch"},
            None,
            "Wired glass break",
        ),
        ("wired_smoke", {"trouble", "status", "bypass-switch"}, None, "Wired smoke"),
        (
            "battery_smoke",
            {"battery", "trouble", "status", "bypass-switch"},
            None,
            "Battery smoke",
        ),
        ("wired_siren", {"trouble", "status", "bypass-switch"}, None, "Wired siren"),
    ],
)
async def test_zone_class_entities_and_device(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_pydmp: SimpleNamespace,
    zone_class: str,
    suffixes: set[str],
    open_close: tuple[str, str | None] | None,
    model: str | None,
) -> None:
    """A zone's class decides its entities and its device's model."""
    entry = await _setup_zones(hass, _zone("Zone", "007", zone_class))

    prefix = "dmp-12345-zone-007-"
    zone_entries = {
        e.unique_id.removeprefix(prefix): e
        for e in er.async_entries_for_config_entry(entity_registry, entry.entry_id)
        if e.unique_id.startswith(prefix)
    }
    assert zone_entries.keys() == suffixes
    if open_close is not None:
        oc = zone_entries["openclose"]
        assert (oc.translation_key, oc.original_device_class) == open_close
        assert oc.original_name is None  # takes the zone (device) name

    devices = entry_devices(hass, entry)
    panel_device = devices["dmp-12345-panel"]
    zone_device = devices["dmp-12345-zone-007"]
    assert (
        panel_device.name,
        panel_device.manufacturer,
        panel_device.model,
        panel_device.serial_number,
    ) == ("Test Panel", "Digital Monitoring Products", "XR series", "12345")
    assert (zone_device.name, zone_device.manufacturer, zone_device.model) == (
        "Zone",
        "Digital Monitoring Products",
        model,
    )
    assert zone_device.via_device_id == panel_device.id
    assert {e.device_id for e in zone_entries.values()} == {zone_device.id}


@pytest.mark.usefixtures("enable_all_entities")
@pytest.mark.parametrize(
    "entity_id,friendly_name",
    [
        ("alarm_control_panel.test_panel_arming_control", "Test Panel Arming control"),
        ("button.test_panel_refresh_status", "Test Panel Refresh status"),
        ("binary_sensor.front_door", "Front Door"),
        ("binary_sensor.front_door_battery", "Front Door Battery"),
        ("binary_sensor.front_door_trouble", "Front Door Trouble"),
        ("binary_sensor.front_door_alarm", "Front Door Alarm"),
        ("sensor.front_door_status", "Front Door Status"),
        ("switch.front_door_bypass", "Front Door Bypass"),
    ],
)
async def test_entity_names(
    hass: HomeAssistant,
    mock_pydmp: SimpleNamespace,
    entity_id: str,
    friendly_name: str,
) -> None:
    """Names come from the device name plus the translated entity name."""
    await _setup_zones(hass, _zone("Front Door", "001", "battery_door"))

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.attributes["friendly_name"] == friendly_name


ZONE_ENTITIES = (
    "binary_sensor.front_door",
    "binary_sensor.front_door_battery",
    "binary_sensor.front_door_trouble",
    "binary_sensor.front_door_alarm",
    "switch.front_door_bypass",
    "sensor.front_door_status",
)


@pytest.mark.usefixtures("enable_all_entities")
@pytest.mark.parametrize(
    "zone_state,alarm,expected",
    [
        ("N", False, (STATE_OFF, STATE_OFF, STATE_OFF, STATE_OFF, STATE_OFF, "ready")),
        ("O", False, (STATE_ON, STATE_OFF, STATE_OFF, STATE_OFF, STATE_OFF, "open")),
        ("S", False, (STATE_OFF, STATE_OFF, STATE_ON, STATE_OFF, STATE_OFF, "trouble")),
        ("M", False, (STATE_OFF, STATE_OFF, STATE_ON, STATE_OFF, STATE_OFF, "trouble")),
        (
            "L",
            False,
            (STATE_OFF, STATE_ON, STATE_ON, STATE_OFF, STATE_OFF, "low_battery"),
        ),
        ("X", False, (STATE_OFF, STATE_OFF, STATE_OFF, STATE_OFF, STATE_ON, "bypass")),
        ("N", True, (STATE_OFF, STATE_OFF, STATE_OFF, STATE_ON, STATE_OFF, "alarm")),
    ],
)
async def test_zone_states_follow_listener_updates(
    hass: HomeAssistant,
    mock_pydmp: SimpleNamespace,
    zone_state: str,
    alarm: bool,
    expected: tuple[str, ...],
) -> None:
    """Zone entities re-read the panel whenever the listener pushes an update."""
    entry = await _setup_zones(hass, _zone("Front Door", "001", "battery_door"))
    data = entry.runtime_data
    zone = data.panel.ensure_zone("001")
    assert zone is not None
    zone.update_state(zone_state)
    if alarm:
        data.panel.set_alarm("001")

    await data.listener.updateHASS()
    await hass.async_block_till_done()

    states = {eid: hass.states.get(eid) for eid in ZONE_ENTITIES}
    assert tuple(s.state for s in states.values() if s) == expected
    assert all("last_contact" in s.attributes for s in states.values() if s)


async def test_refresh_button_exposes_status_attributes(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """The refresh button carries the consolidated panel status as attributes."""
    state = hass.states.get("button.test_panel_refresh_status")
    assert state is not None
    assert state.attributes["Zone: 001 - Front Door"] == "Normal"
    assert state.attributes["Area: 01 - Perimeter"] == "Disarmed"


ENTITY_COMMANDS = [
    (
        "alarm_control_panel",
        "alarm_disarm",
        "alarm_control_panel.test_panel_arming_control",
        "pydmp",
        "disarm_areas",
        ([1, 2, 3],),
        {},
    ),
    (
        "alarm_control_panel",
        "alarm_arm_away",
        "alarm_control_panel.test_panel_arming_control",
        "pydmp",
        "arm_areas",
        ([1, 2, 3],),
        {},
    ),
    (
        "alarm_control_panel",
        "alarm_arm_home",
        "alarm_control_panel.test_panel_arming_control",
        "pydmp",
        "arm_areas",
        ([1],),
        {},
    ),
    (
        "alarm_control_panel",
        "alarm_arm_night",
        "alarm_control_panel.test_panel_arming_control",
        "pydmp",
        "arm_areas",
        ([1],),
        {"instant": True},
    ),
    (
        "switch",
        "turn_on",
        "switch.front_door_bypass",
        "panel",
        "bypass_zone",
        ("001",),
        {},
    ),
    (
        "switch",
        "turn_off",
        "switch.front_door_bypass",
        "panel",
        "restore_zone",
        ("001",),
        {},
    ),
    (
        "button",
        "press",
        "button.test_panel_refresh_status",
        "listener",
        "updateStatus",
        (),
        {},
    ),
]


@pytest.mark.parametrize(
    "domain,service,entity_id,target,method,args,kwargs", ENTITY_COMMANDS
)
async def test_entity_commands(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    domain: str,
    service: str,
    entity_id: str,
    target: str,
    method: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> None:
    """Entity services drive the matching panel/listener call."""
    data = init_integration.runtime_data
    obj = {"pydmp": data.pydmp_panel, "panel": data.panel, "listener": data.listener}
    with patch.object(obj[target], method, new_callable=AsyncMock) as call:
        await hass.services.async_call(
            domain, service, {ATTR_ENTITY_ID: entity_id}, blocking=True
        )
    call.assert_awaited_once_with(*args, **kwargs)


@pytest.mark.parametrize(
    ("connected", "error", "translation_key", "placeholders"),
    [
        (
            True,
            DMPConnectionError("timed out"),
            "command_failed",
            {"error": "timed out"},
        ),
        (False, None, "not_connected", None),
    ],
    ids=["command_failed", "not_connected"],
)
@pytest.mark.parametrize(
    "domain,service,entity_id,target,method,args,kwargs", ENTITY_COMMANDS
)
async def test_entity_command_errors(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    domain: str,
    service: str,
    entity_id: str,
    target: str,
    method: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    connected: bool,
    error: Exception | None,
    translation_key: str,
    placeholders: dict[str, str] | None,
) -> None:
    """A failed panel command, or one sent while the panel is disconnected,
    raises a translated Home Assistant error."""
    data = init_integration.runtime_data
    obj = {"pydmp": data.pydmp_panel, "panel": data.panel, "listener": data.listener}
    # Unavailable entities never receive service calls, so call the entity itself.
    entity = hass.data[DATA_INSTANCES][domain].get_entity(entity_id)
    assert entity is not None
    data.listener.connected = connected
    with (
        patch.object(obj[target], method, new_callable=AsyncMock, side_effect=error),
        pytest.raises(HomeAssistantError) as exc_info,
    ):
        await getattr(entity, f"async_{service}")()

    assert exc_info.value.translation_domain == DOMAIN
    assert exc_info.value.translation_key == translation_key
    assert exc_info.value.translation_placeholders == placeholders
    assert exc_info.value.__cause__ is error


async def test_alarm_command_without_panel_connection(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Arming commands raise a Home Assistant error when the panel is not connected."""
    init_integration.runtime_data.panel._pydmp_panel = None
    with pytest.raises(HomeAssistantError, match="not connected"):
        await hass.services.async_call(
            "alarm_control_panel",
            "alarm_disarm",
            {ATTR_ENTITY_ID: "alarm_control_panel.test_panel_arming_control"},
            blocking=True,
        )


async def test_unload_removes_listener_callbacks(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Every entity deregisters from the listener when the entry unloads."""
    listener = init_integration.runtime_data.listener
    assert listener._callbacks

    assert await hass.config_entries.async_unload(init_integration.entry_id)

    assert listener._callbacks == set()
