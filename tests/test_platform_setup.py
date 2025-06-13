"""Generic async_setup_entry smoke tests for DMP integration platforms."""
import importlib
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from unittest.mock import Mock
from custom_components.dmp.const import (
    DOMAIN, LISTENER,
    CONF_PANEL_ACCOUNT_NUMBER, CONF_ZONES,
    CONF_ZONE_NAME, CONF_ZONE_NUMBER, CONF_ZONE_CLASS,
    CONF_PANEL_NAME, CONF_HOME_AREA, CONF_AWAY_AREA,
)
from homeassistant.core import HomeAssistant


@pytest.mark.parametrize("module_name, platform_config, expected_count, expected_types", [
    (
        "binary_sensor",
        {
            CONF_PANEL_ACCOUNT_NUMBER: "12345",
            CONF_ZONES: [
                {CONF_ZONE_NAME: "Front Door", CONF_ZONE_NUMBER: "001", CONF_ZONE_CLASS: "wired_door"},
                {CONF_ZONE_NAME: "Living Room Window", CONF_ZONE_NUMBER: "002", CONF_ZONE_CLASS: "battery_window"},
                {CONF_ZONE_NAME: "Motion Sensor", CONF_ZONE_NUMBER: "003", CONF_ZONE_CLASS: "wired_motion"},
                {CONF_ZONE_NAME: "Smoke Detector", CONF_ZONE_NUMBER: "004", CONF_ZONE_CLASS: "wired_smoke"},
            ],
        },
        11,
        ("DMPZoneOpenClose", "DMPZoneBattery", "DMPZoneTrouble", "DMPZoneAlarm"),
    ),
    (
        "sensor",
        {
            CONF_PANEL_ACCOUNT_NUMBER: "12345",
            CONF_ZONES: [
                {CONF_ZONE_NAME: "Test Zone", CONF_ZONE_NUMBER: "001", CONF_ZONE_CLASS: "wired_door"},
            ],
        },
        1,
        ("DMPZoneStatus",),
    ),
    (
        "button",
        {
            CONF_PANEL_ACCOUNT_NUMBER: "12345",
            CONF_PANEL_NAME: "Test Panel",
        },
        1,
        ("DMPRefreshStatusButton",),
    ),
    (
        "switch",
        {
            CONF_PANEL_ACCOUNT_NUMBER: "12345",
            CONF_ZONES: [
                {CONF_ZONE_NAME: "Door Zone", CONF_ZONE_NUMBER: "001", CONF_ZONE_CLASS: "wired_door"},
                {CONF_ZONE_NAME: "Window Zone", CONF_ZONE_NUMBER: "002", CONF_ZONE_CLASS: "battery_window"},
                {CONF_ZONE_NAME: "Motion Zone", CONF_ZONE_NUMBER: "003", CONF_ZONE_CLASS: "wired_motion"},
                {CONF_ZONE_NAME: "Smoke Zone", CONF_ZONE_NUMBER: "004", CONF_ZONE_CLASS: "wired_smoke"},
                {CONF_ZONE_NAME: "Glass Break", CONF_ZONE_NUMBER: "005", CONF_ZONE_CLASS: "wired_glassbreak"},
            ],
        },
        5,
        ("DMPZoneBypassSwitch",),
    ),
    (
        "alarm_control_panel",
        {
            CONF_PANEL_ACCOUNT_NUMBER: "12345",
            CONF_PANEL_NAME: "Test Panel",
            CONF_HOME_AREA: "01",
            CONF_AWAY_AREA: "02",
        },
        1,
        ("DMPArea",),
    ),
])
async def test_platform_async_setup_entry(
    module_name, platform_config, expected_count, expected_types, hass: HomeAssistant
):
    """Test async_setup_entry for each DMP platform creates correct entities."""
    module = importlib.import_module(f"custom_components.dmp.{module_name}")
    async_setup_entry = getattr(module, "async_setup_entry")

    # Create dummy config entry; actual run-time config is in hass.data
    entry = MockConfigEntry(domain=DOMAIN, data={}, entry_id="test_entry")

    # Prepare listener and panel stub
    listener = Mock()
    panel = Mock()
    acct = platform_config.get(CONF_PANEL_ACCOUNT_NUMBER)
    panel.getAccountNumber.return_value = acct
    listener.getPanels.return_value = {acct: panel}

    # Populate hass data for the integration
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = listener
    hass.data[DOMAIN][entry.entry_id] = platform_config

    # Collect created entities
    entities = []
    async_add = lambda items, update_before_add=True: entities.extend(items)

    await async_setup_entry(hass, entry, async_add)
    assert len(entities) == expected_count
    # Verify each entity is instance of expected types
    for ent in entities:
        name = type(ent).__name__
        assert name in expected_types, f"Unexpected entity type {name}"