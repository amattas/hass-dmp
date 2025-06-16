"""Test constants module."""
import pytest
import custom_components.dmp.const as const


@pytest.mark.parametrize("const_name,expected", [
    ("DOMAIN", "dmp"),
    ("LISTENER", "dmp_listener"),
])
def test_component_constants(const_name, expected):
    """Component constants have expected values."""
    assert getattr(const, const_name) == expected


@pytest.mark.parametrize("const_name,expected", [
    ("CONF_PANEL", "panel"),
    ("CONF_PANEL_NAME", "panel_name"),
    ("CONF_PANEL_IP", "ip"),
    ("CONF_PANEL_LISTEN_PORT", "listen_port"),
    ("CONF_PANEL_REMOTE_PORT", "remote_port"),
    ("CONF_PANEL_ACCOUNT_NUMBER", "account_number"),
    ("CONF_PANEL_REMOTE_KEY", "remote_key"),
    ("CONF_HOME_AREA", "home_zone"),
    ("CONF_AWAY_AREA", "away_zone"),
    ("CONF_LOCK_NAME", "door_name"),
    ("CONF_LOCK_NUMBER", "door_number"),
    ("CONF_LOCK_ACCOUNT_NUMBER", "account_number"),
    ("CONF_ZONE_NAME", "zone_name"),
    ("CONF_ZONE_NUMBER", "zone_number"),
    ("CONF_ZONE_CLASS", "zone_class"),
    ("CONFIG_FLOW_PANEL", "panel"),
    ("CONF_AREAS", "areas"),
    ("CONF_ZONES", "zones"),
    ("CONF_ADD_ANOTHER", "add_another"),
])
def test_configuration_constants(const_name, expected):
    """Configuration constants have expected values."""
    assert getattr(const, const_name) == expected

@pytest.mark.parametrize("const_name,expected", [
    ("DEV_TYPE_BATTERY_DOOR", "battery_door"),
    ("DEV_TYPE_BATTERY_GLASSBREAK", "battery_glassbreak"),
    ("DEV_TYPE_BATTERY_MOTION", "battery_motion"),
    ("DEV_TYPE_BATTERY_SIREN", "battery_siren"),
    ("DEV_TYPE_BATTERY_SMOKE", "battery_smoke"),
    ("DEV_TYPE_BATTERY_WINDOW", "battery_window"),
    ("DEV_TYPE_WIRED_DOOR", "wired_door"),
    ("DEV_TYPE_WIRED_GLASSBREAK", "wired_glassbreak"),
    ("DEV_TYPE_WIRED_MOTION", "wired_motion"),
    ("DEV_TYPE_WIRED_SIREN", "wired_siren"),
    ("DEV_TYPE_WIRED_SMOKE", "wired_smoke"),
    ("DEV_TYPE_WIRED_WINDOW", "wired_window"),
])
def test_device_type_constants(const_name, expected):
    """Device type constants have expected values."""
    assert getattr(const, const_name) == expected


@pytest.mark.parametrize("const_name,expected", [
    ("BATTERY_LEVEL", "BatteryLevel"),
])
def test_attribute_constants(const_name, expected):
    """Attribute constants have expected values."""
    assert getattr(const, const_name) == expected


@pytest.mark.parametrize("const_name,expected", [
    ("PANEL_AREA_COUNT", 3),
    ("PANEL_ALL_AREAS", "010203"),
])
def test_other_constants(const_name, expected):
    """Other constants have expected values."""
    assert getattr(const, const_name) == expected