"""Test constants module."""
import pytest
from custom_components.dmp.const import (
    DOMAIN, LISTENER, CONF_PANEL, CONF_PANEL_NAME, CONF_PANEL_IP,
    CONF_PANEL_LISTEN_PORT, CONF_PANEL_REMOTE_PORT, CONF_PANEL_ACCOUNT_NUMBER,
    CONF_PANEL_REMOTE_KEY, CONF_HOME_AREA, CONF_AWAY_AREA, CONF_LOCK_NAME,
    CONF_LOCK_NUMBER, CONF_LOCK_ACCOUNT_NUMBER, CONF_ZONE_NAME, CONF_ZONE_NUMBER,
    CONF_ZONE_CLASS, CONFIG_FLOW_PANEL, CONF_AREAS, CONF_ZONES, CONF_ADD_ANOTHER,
    DEV_TYPE_BATTERY_DOOR, DEV_TYPE_BATTERY_GLASSBREAK, DEV_TYPE_BATTERY_MOTION,
    DEV_TYPE_BATTERY_SIREN, DEV_TYPE_BATTERY_SMOKE, DEV_TYPE_BATTERY_WINDOW,
    DEV_TYPE_WIRED_DOOR, DEV_TYPE_WIRED_GLASSBREAK, DEV_TYPE_WIRED_MOTION,
    DEV_TYPE_WIRED_SIREN, DEV_TYPE_WIRED_SMOKE, DEV_TYPE_WIRED_WINDOW,
    BATTERY_LEVEL, PANEL_AREA_COUNT, PANEL_ALL_AREAS
)


def test_component_constant():
    """Test that the component constants have the expected value."""
    assert DOMAIN == "dmp"
    assert LISTENER == "dmp_listener"


def test_configuration_constants():
    """Test that configuration constants have the expected value."""
    assert CONF_PANEL == "panel"
    assert CONF_PANEL_NAME == "panel_name"
    assert CONF_PANEL_IP == "ip"
    assert CONF_PANEL_LISTEN_PORT == "listen_port"
    assert CONF_PANEL_REMOTE_PORT == "remote_port"
    assert CONF_PANEL_ACCOUNT_NUMBER == "account_number"
    assert CONF_PANEL_REMOTE_KEY == "remote_key"
    assert CONF_HOME_AREA == "home_zone"
    assert CONF_AWAY_AREA == "away_zone"
    assert CONF_LOCK_NAME == "door_name"
    assert CONF_LOCK_NUMBER == "door_number"
    assert CONF_LOCK_ACCOUNT_NUMBER == "account_number"
    assert CONF_ZONE_NAME == "zone_name"
    assert CONF_ZONE_NUMBER == "zone_number"
    assert CONF_ZONE_CLASS == "zone_class"
    assert CONFIG_FLOW_PANEL == "panel"
    assert CONF_AREAS == "areas"
    assert CONF_ZONES == "zones"
    assert CONF_ADD_ANOTHER == "add_another"

def test_device_type_constants():
    """Test that device type constants have the expected value."""
    assert DEV_TYPE_BATTERY_DOOR == "battery_door"
    assert DEV_TYPE_BATTERY_GLASSBREAK == "battery_glassbreak"
    assert DEV_TYPE_BATTERY_MOTION == "battery_motion"
    assert DEV_TYPE_BATTERY_SIREN == "battery_siren"
    assert DEV_TYPE_BATTERY_SMOKE == "battery_smoke"
    assert DEV_TYPE_BATTERY_WINDOW == "battery_window"
    assert DEV_TYPE_WIRED_DOOR == "wired_door"
    assert DEV_TYPE_WIRED_GLASSBREAK == "wired_glassbreak"
    assert DEV_TYPE_WIRED_MOTION == "wired_motion"
    assert DEV_TYPE_WIRED_SIREN == "wired_siren"
    assert DEV_TYPE_WIRED_SMOKE == "wired_smoke"
    assert DEV_TYPE_WIRED_WINDOW == "wired_window"


def test_attribute_constants():
    """Test that atrribute name constants have the expected value."""
    assert BATTERY_LEVEL == "BatteryLevel"


def test_other_constants():
    """Test that other constants have the expected value."""
    assert PANEL_AREA_COUNT == 3
    assert PANEL_ALL_AREAS == "010203"