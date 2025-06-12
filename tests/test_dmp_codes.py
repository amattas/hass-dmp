"""Test dmp_codes module."""
import pytest

from custom_components.dmp.dmp_codes import DMP_EVENTS, DMP_TYPES

def test_dmp_events_not_empty():
    """DMP_EVENTS should be a non-empty dict with string keys and values."""
    assert isinstance(DMP_EVENTS, dict)
    assert DMP_EVENTS
    for key, value in DMP_EVENTS.items():
        assert isinstance(key, str)
        assert isinstance(value, str)

def test_dmp_types_not_empty():
    """DMP_TYPES should be a non-empty dict with string keys and values."""
    assert isinstance(DMP_TYPES, dict)
    assert DMP_TYPES
    for key, value in DMP_TYPES.items():
        assert isinstance(key, str)
        assert isinstance(value, str)

@pytest.mark.parametrize("event_code, expected", [
    ("Za", "Zone Alarm"),
    ("Zb", "Zone Force Alarm"),
    ("Zc", "Device Status"),
])
def test_known_dmp_events(event_code, expected):
    """Specific DMP_EVENTS mappings should match expected values."""
    assert DMP_EVENTS.get(event_code) == expected

@pytest.mark.parametrize("type_code, expected", [
    ("BL", "Blank"),
    ("FI", "Fire"),
    ("DA", "Door Access Granted"),
])
def test_known_dmp_types(type_code, expected):
    """Specific DMP_TYPES mappings should match expected values."""
    assert DMP_TYPES.get(type_code) == expected

def test_unknown_codes_return_none():
    """Lookup for unknown codes should return None."""
    assert DMP_EVENTS.get("UNKNOWN_CODE") is None
    assert DMP_TYPES.get("UNKNOWN_CODE") is None
