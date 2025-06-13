"""Test binary sensor module for DMP integration."""
import pytest
from unittest.mock import Mock
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmp.binary_sensor import (
    DMPZoneOpenClose,
    DMPZoneBattery,
    DMPZoneTrouble,
    DMPZoneAlarm,
    DMPZoneBypass,
)
from custom_components.dmp.const import (
    DOMAIN, LISTENER, CONF_ZONE_NAME, CONF_ZONE_NUMBER,
    CONF_ZONE_CLASS, CONF_PANEL_ACCOUNT_NUMBER
)


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "panel_name": "Test Panel",
            "ip": "192.168.1.1",
            "listen_port": 40002,
            "remote_port": 40001,
            "account_number": "12345"
        },
        entry_id="test_entry_id"
    )


@pytest.fixture
def mock_listener():
    """Create a mock listener with panel."""
    listener = Mock()
    panel = Mock()
    panel.updateOpenCloseZone = Mock()
    panel.getOpenCloseZone = Mock(return_value={"zoneState": False})
    listener.getPanels = Mock(return_value={"12345": panel})
    listener.register_callback = Mock()
    listener.remove_callback = Mock()
    return listener


@pytest.fixture
def mock_zone_config():
    """Create mock zone configuration."""
    return [
        {
            CONF_ZONE_NAME: "Front Door",
            CONF_ZONE_NUMBER: "001",
            CONF_ZONE_CLASS: "wired_door"
        },
        {
            CONF_ZONE_NAME: "Living Room Window",
            CONF_ZONE_NUMBER: "002",
            CONF_ZONE_CLASS: "battery_window"
        },
        {
            CONF_ZONE_NAME: "Motion Sensor",
            CONF_ZONE_NUMBER: "003",
            CONF_ZONE_CLASS: "wired_motion"
        },
        {
            CONF_ZONE_NAME: "Smoke Detector",
            CONF_ZONE_NUMBER: "004",
            CONF_ZONE_CLASS: "wired_smoke"
        }
    ]



@pytest.fixture
def setup_sensor(hass: HomeAssistant, mock_config_entry, mock_listener):
    """Set up sensor with mocked dependencies."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][LISTENER] = mock_listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = {
        CONF_PANEL_ACCOUNT_NUMBER: "12345"
    }
    return hass, mock_listener.getPanels()["12345"]

@pytest.mark.parametrize(
    "zone_class,expected_device_class", [
        ("wired_door", "door"),
        ("battery_window", "window"),
        ("wired_motion", "motion"),
        ("unknown_type", "sensors"),
    ]
)
def test_device_class_mapping(setup_sensor, mock_config_entry, zone_class, expected_device_class):
    hass, panel = setup_sensor
    zone_config = {
        CONF_ZONE_NAME: "Test Zone",
        CONF_ZONE_NUMBER: "001",
        CONF_ZONE_CLASS: zone_class
    }
    sensor = DMPZoneOpenClose(hass, mock_config_entry, zone_config)
    assert sensor._device_class == expected_device_class

@pytest.mark.parametrize(
    "zone_class,state,expected_icon", [
        ("wired_door", False, "mdi:door-closed"),
        ("wired_door", True, "mdi:door-open"),
        ("battery_window", False, "mdi:window-closed"),
        ("battery_window", True, "mdi:window-open"),
        ("wired_motion", False, "mdi:motion-sensor-off"),
        ("wired_motion", True, "mdi:motion-sensor"),
    ]
)
def test_icon_mapping(setup_sensor, mock_config_entry, zone_class, state, expected_icon):
    hass, panel = setup_sensor
    zone_config = {
        CONF_ZONE_NAME: "Test Zone",
        CONF_ZONE_NUMBER: "001",
        CONF_ZONE_CLASS: zone_class
    }
    sensor = DMPZoneOpenClose(hass, mock_config_entry, zone_config)
    sensor._state = state
    assert sensor.icon == expected_icon

@pytest.mark.asyncio
async def test_process_zone_callback(setup_sensor, mock_config_entry):
    """Test processing zone state callback."""
    hass, panel = setup_sensor
    zone_config = {
        CONF_ZONE_NAME: "Test Door",
        CONF_ZONE_NUMBER: "001",
        CONF_ZONE_CLASS: "wired_door"
    }
    sensor = DMPZoneOpenClose(hass, mock_config_entry, zone_config)
    sensor.async_write_ha_state = Mock()

    panel.getOpenCloseZone.return_value = {"zoneState": True}
    await sensor.process_zone_callback()

    assert sensor._state is True
    sensor.async_write_ha_state.assert_called_once()

@pytest.mark.asyncio
async def test_async_added_to_hass(setup_sensor, mock_config_entry, mock_listener):
    """Test registering callback when added to hass."""
    hass, panel = setup_sensor
    zone_config = {
        CONF_ZONE_NAME: "Test Door",
        CONF_ZONE_NUMBER: "001",
        CONF_ZONE_CLASS: "wired_door"
    }
    sensor = DMPZoneOpenClose(hass, mock_config_entry, zone_config)
    await sensor.async_added_to_hass()
    mock_listener.register_callback.assert_called_once_with(sensor.process_zone_callback)

@pytest.mark.asyncio
async def test_async_will_remove_from_hass(setup_sensor, mock_config_entry, mock_listener):
    """Test removing callback when removed from hass."""
    hass, panel = setup_sensor
    zone_config = {
        CONF_ZONE_NAME: "Test Door",
        CONF_ZONE_NUMBER: "001",
        CONF_ZONE_CLASS: "wired_door"
    }
    sensor = DMPZoneOpenClose(hass, mock_config_entry, zone_config)
    await sensor.async_will_remove_from_hass()
    mock_listener.remove_callback.assert_called_once_with(sensor.process_zone_callback)



@pytest.fixture
def setup_battery_sensor(hass: HomeAssistant, mock_config_entry, mock_listener):
    hass.data.setdefault(DOMAIN, {})
    panel = mock_listener.getPanels()["12345"]
    panel.updateBatteryZone = Mock()
    panel.getBatteryZone = Mock(return_value={"zoneState": False})
    panel.getContactTime = Mock(return_value="t0")
    hass.data[DOMAIN][LISTENER] = mock_listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = {CONF_PANEL_ACCOUNT_NUMBER: "12345"}
    return hass, panel

def test_battery_sensor_initialization(setup_battery_sensor, mock_config_entry):
    hass, panel = setup_battery_sensor
    zone_config = {CONF_ZONE_NAME: "Test Battery", CONF_ZONE_NUMBER: "010", CONF_ZONE_CLASS: "battery_window"}
    sensor = DMPZoneBattery(hass, mock_config_entry, zone_config)
    assert sensor._device_class == "battery"
    assert sensor.name == "Test Battery Battery"
    assert sensor.is_on is False
    panel.updateBatteryZone.assert_called_once()

@pytest.mark.parametrize("state,icon", [(False, 'mdi:battery'), (True, 'mdi:battery-alert-variant-outline')])
def test_battery_icon(setup_battery_sensor, mock_config_entry, state, icon):
    hass, panel = setup_battery_sensor
    zone_config = {CONF_ZONE_NAME: "Test Battery", CONF_ZONE_NUMBER: "010", CONF_ZONE_CLASS: "battery_window"}
    sensor = DMPZoneBattery(hass, mock_config_entry, zone_config)
    sensor._state = state
    assert sensor.icon == icon

@pytest.mark.asyncio
async def test_battery_callbacks(setup_battery_sensor, mock_config_entry, mock_listener):
    hass, panel = setup_battery_sensor
    zone_config = {CONF_ZONE_NAME: "Test Battery", CONF_ZONE_NUMBER: "010", CONF_ZONE_CLASS: "battery_window"}
    sensor = DMPZoneBattery(hass, mock_config_entry, zone_config)
    sensor.async_write_ha_state = Mock()
    panel.getBatteryZone.return_value = {"zoneState": True}
    await sensor.process_zone_callback()
    assert sensor._state is True
    sensor.async_write_ha_state.assert_called_once()
    await sensor.async_added_to_hass()
    mock_listener.register_callback.assert_called_with(sensor.process_zone_callback)
    await sensor.async_will_remove_from_hass()
    mock_listener.remove_callback.assert_called_with(sensor.process_zone_callback)



@pytest.fixture
def setup_trouble_sensor(hass: HomeAssistant, mock_config_entry, mock_listener):
    hass.data.setdefault(DOMAIN, {})
    panel = mock_listener.getPanels()["12345"]
    panel.updateTroubleZone = Mock()
    panel.getTroubleZone = Mock(return_value={"zoneState": False})
    panel.getContactTime = Mock(return_value="t1")
    hass.data[DOMAIN][LISTENER] = mock_listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = {CONF_PANEL_ACCOUNT_NUMBER: "12345"}
    return hass, panel

def test_trouble_sensor_initialization(setup_trouble_sensor, mock_config_entry):
    hass, panel = setup_trouble_sensor
    zone_config = {CONF_ZONE_NAME: "Test Trouble", CONF_ZONE_NUMBER: "011", CONF_ZONE_CLASS: "wired_motion"}
    sensor = DMPZoneTrouble(hass, mock_config_entry, zone_config)
    assert sensor._device_class == "problem"
    assert sensor.name == "Test Trouble Trouble"
    assert sensor.is_on is False
    panel.updateTroubleZone.assert_called_once()

@pytest.mark.parametrize("state,icon", [(False, 'mdi:check'), (True, 'mdi:alert-outline')])
def test_trouble_icon(setup_trouble_sensor, mock_config_entry, state, icon):
    hass, panel = setup_trouble_sensor
    zone_config = {CONF_ZONE_NAME: "Test Trouble", CONF_ZONE_NUMBER: "011", CONF_ZONE_CLASS: "wired_motion"}
    sensor = DMPZoneTrouble(hass, mock_config_entry, zone_config)
    sensor._state = state
    assert sensor.icon == icon

@pytest.mark.asyncio
async def test_trouble_callbacks(setup_trouble_sensor, mock_config_entry, mock_listener):
    hass, panel = setup_trouble_sensor
    zone_config = {CONF_ZONE_NAME: "Test Trouble", CONF_ZONE_NUMBER: "011", CONF_ZONE_CLASS: "wired_motion"}
    sensor = DMPZoneTrouble(hass, mock_config_entry, zone_config)
    sensor.async_write_ha_state = Mock()
    panel.getTroubleZone.return_value = {"zoneState": True}
    await sensor.process_zone_callback()
    assert sensor._state is True
    sensor.async_write_ha_state.assert_called_once()
    await sensor.async_added_to_hass()
    mock_listener.register_callback.assert_called_with(sensor.process_zone_callback)
    await sensor.async_will_remove_from_hass()
    mock_listener.remove_callback.assert_called_with(sensor.process_zone_callback)

@pytest.fixture
def setup_bypass_sensor(hass: HomeAssistant, mock_config_entry, mock_listener):
    hass.data.setdefault(DOMAIN, {})
    panel = mock_listener.getPanels()["12345"]
    panel.updateBypassZone = Mock()
    panel.getBypassZone = Mock(return_value={"zoneState": False})
    panel.getContactTime = Mock(return_value="t3")
    hass.data[DOMAIN][LISTENER] = mock_listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = {CONF_PANEL_ACCOUNT_NUMBER: "12345"}
    return hass, panel

def test_bypass_sensor_initialization(setup_bypass_sensor, mock_config_entry):
    hass, panel = setup_bypass_sensor
    zone_config = {CONF_ZONE_NAME: "Test Bypass", CONF_ZONE_NUMBER: "013", CONF_ZONE_CLASS: "wired_door"}
    sensor = DMPZoneBypass(hass, mock_config_entry, zone_config)
    assert sensor._device_class == "problem"
    assert sensor.name == "Test Bypass Bypass"
    assert sensor.is_on is False
    panel.updateBypassZone.assert_called_once()

@pytest.mark.parametrize("state,icon", [(False, "mdi:check"), (True, "mdi:alert-outline")])
def test_bypass_icon(setup_bypass_sensor, mock_config_entry, state, icon):
    hass, panel = setup_bypass_sensor
    zone_config = {CONF_ZONE_NAME: "Test Bypass", CONF_ZONE_NUMBER: "013", CONF_ZONE_CLASS: "wired_door"}
    sensor = DMPZoneBypass(hass, mock_config_entry, zone_config)
    sensor._state = state
    assert sensor.icon == icon

def test_bypass_properties(setup_bypass_sensor, mock_config_entry):
    hass, panel = setup_bypass_sensor
    zone_config = {CONF_ZONE_NAME: "Test Bypass", CONF_ZONE_NUMBER: "013", CONF_ZONE_CLASS: "wired_door"}
    sensor = DMPZoneBypass(hass, mock_config_entry, zone_config)
    assert sensor.device_name == "Test Bypass"
    assert sensor.should_poll is False
    assert sensor.unique_id == "dmp-12345-zone-013-bypass"
    assert sensor.device_class == "problem"
    assert sensor.extra_state_attributes == {"last_contact": "t3"}

@pytest.mark.asyncio
async def test_bypass_callbacks(setup_bypass_sensor, mock_config_entry, mock_listener):
    hass, panel = setup_bypass_sensor
    zone_config = {CONF_ZONE_NAME: "Test Bypass", CONF_ZONE_NUMBER: "013", CONF_ZONE_CLASS: "wired_door"}
    sensor = DMPZoneBypass(hass, mock_config_entry, zone_config)
    sensor.async_write_ha_state = Mock()
    panel.getBypassZone.return_value = {"zoneState": True}
    await sensor.process_zone_callback()
    assert sensor._state is True
    sensor.async_write_ha_state.assert_called_once()
    await sensor.async_added_to_hass()
    mock_listener.register_callback.assert_called_with(sensor.process_zone_callback)
    await sensor.async_will_remove_from_hass()
    mock_listener.remove_callback.assert_called_with(sensor.process_zone_callback)


@pytest.fixture
def setup_alarm_sensor(hass: HomeAssistant, mock_config_entry, mock_listener):
    hass.data.setdefault(DOMAIN, {})
    panel = mock_listener.getPanels()["12345"]
    panel.updateAlarmZone = Mock()
    panel.getAlarmZone = Mock(return_value={"zoneState": False})
    panel.getContactTime = Mock(return_value="t2")
    hass.data[DOMAIN][LISTENER] = mock_listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = {CONF_PANEL_ACCOUNT_NUMBER: "12345"}
    return hass, panel

def test_alarm_sensor_initialization(setup_alarm_sensor, mock_config_entry):
    hass, panel = setup_alarm_sensor
    zone_config = {CONF_ZONE_NAME: "Test Alarm", CONF_ZONE_NUMBER: "012", CONF_ZONE_CLASS: "wired_motion"}
    sensor = DMPZoneAlarm(hass, mock_config_entry, zone_config)
    assert sensor._device_class == "problem"
    assert sensor.name == "Test Alarm Alarm"
    assert sensor.is_on is False
    panel.updateAlarmZone.assert_called_once()

@pytest.mark.parametrize("state,icon", [(False, 'mdi:check'), (True, 'mdi:alarm-bell')])
def test_alarm_icon(setup_alarm_sensor, mock_config_entry, state, icon):
    hass, panel = setup_alarm_sensor
    zone_config = {CONF_ZONE_NAME: "Test Alarm", CONF_ZONE_NUMBER: "012", CONF_ZONE_CLASS: "wired_motion"}
    sensor = DMPZoneAlarm(hass, mock_config_entry, zone_config)
    sensor._state = state
    assert sensor.icon == icon

@pytest.mark.asyncio
async def test_alarm_callbacks(setup_alarm_sensor, mock_config_entry, mock_listener):
    hass, panel = setup_alarm_sensor
    zone_config = {CONF_ZONE_NAME: "Test Alarm", CONF_ZONE_NUMBER: "012", CONF_ZONE_CLASS: "wired_motion"}
    sensor = DMPZoneAlarm(hass, mock_config_entry, zone_config)
    sensor.async_write_ha_state = Mock()
    panel.getAlarmZone.return_value = {"zoneState": True}
    await sensor.process_zone_callback()
    assert sensor._state is True
    sensor.async_write_ha_state.assert_called_once()
    await sensor.async_added_to_hass()
    mock_listener.register_callback.assert_called_with(sensor.process_zone_callback)
    await sensor.async_will_remove_from_hass()
    mock_listener.remove_callback.assert_called_with(sensor.process_zone_callback)


__all__ = [
"TestBinarySensorSetup",
"TestDMPZoneOpenClose",
"TestDMPZoneBattery",
"TestDMPZoneTrouble",
"TestDMPZoneAlarm",
"TestDMPZoneBypass",
]