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
pytestmark = pytest.mark.usefixtures("init_integration")

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
def setup_sensor(hass, init_integration, mock_config_entry, mock_listener):
    """Set up sensor with mocked dependencies."""
    panel = mock_listener.getPanels()["12345"]
    return hass, panel

@pytest.mark.parametrize(
    "zone_class,expected_device_class", [
        ("wired_door", "door"),
        ("battery_window", "window"),
        ("wired_motion", "motion"),
        ("unknown_type", "sensors"),
    ]
)
def test_device_class_mapping(setup_sensor, mock_config_entry, zone_class, expected_device_class):
    """Verify zone class maps to the correct device class."""
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
    """Confirm icon selection based on device class and state."""
    hass, panel = setup_sensor
    zone_config = {
        CONF_ZONE_NAME: "Test Zone",
        CONF_ZONE_NUMBER: "001",
        CONF_ZONE_CLASS: zone_class
    }
    sensor = DMPZoneOpenClose(hass, mock_config_entry, zone_config)
    sensor._state = state
    assert sensor.icon == expected_icon




@pytest.fixture
def setup_battery_sensor(hass, init_integration, mock_config_entry, mock_listener):
    """Set up battery sensor with mocked dependencies."""
    panel = mock_listener.getPanels()["12345"]
    panel.updateBatteryZone = Mock()
    panel.getBatteryZone = Mock(return_value={"zoneState": False})
    panel.getContactTime = Mock(return_value="t0")
    return hass, panel

def test_battery_sensor_initialization(setup_battery_sensor, mock_config_entry):
    """Check battery sensor initialization and defaults."""
    hass, panel = setup_battery_sensor
    zone_config = {CONF_ZONE_NAME: "Test Battery", CONF_ZONE_NUMBER: "010", CONF_ZONE_CLASS: "battery_window"}
    sensor = DMPZoneBattery(hass, mock_config_entry, zone_config)
    assert sensor._device_class == "battery"
    assert sensor.name == "Test Battery Battery"
    assert sensor.is_on is False
    panel.updateBatteryZone.assert_called_once()

@pytest.mark.parametrize("state,icon", [(False, 'mdi:battery'), (True, 'mdi:battery-alert-variant-outline')])
def test_battery_icon(setup_battery_sensor, mock_config_entry, state, icon):
    """Ensure battery sensor icon reflects state."""
    hass, panel = setup_battery_sensor
    zone_config = {CONF_ZONE_NAME: "Test Battery", CONF_ZONE_NUMBER: "010", CONF_ZONE_CLASS: "battery_window"}
    sensor = DMPZoneBattery(hass, mock_config_entry, zone_config)
    sensor._state = state
    assert sensor.icon == icon




@pytest.fixture
def setup_trouble_sensor(hass: HomeAssistant, mock_config_entry, mock_listener):
    """Set up a trouble binary sensor with mocked dependencies."""
    hass.data.setdefault(DOMAIN, {})
    panel = mock_listener.getPanels()["12345"]
    panel.updateTroubleZone = Mock()
    panel.getTroubleZone = Mock(return_value={"zoneState": False})
    panel.getContactTime = Mock(return_value="t1")
    hass.data[DOMAIN][LISTENER] = mock_listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = {CONF_PANEL_ACCOUNT_NUMBER: "12345"}
    return hass, panel

def test_trouble_sensor_initialization(setup_trouble_sensor, mock_config_entry):
    """Validate trouble sensor initialization settings."""
    hass, panel = setup_trouble_sensor
    zone_config = {CONF_ZONE_NAME: "Test Trouble", CONF_ZONE_NUMBER: "011", CONF_ZONE_CLASS: "wired_motion"}
    sensor = DMPZoneTrouble(hass, mock_config_entry, zone_config)
    assert sensor._device_class == "problem"
    assert sensor.name == "Test Trouble Trouble"
    assert sensor.is_on is False
    panel.updateTroubleZone.assert_called_once()

@pytest.mark.parametrize("state,icon", [(False, 'mdi:check'), (True, 'mdi:alert-outline')])
def test_trouble_icon(setup_trouble_sensor, mock_config_entry, state, icon):
    """Ensure trouble sensor icon reflects state."""
    hass, panel = setup_trouble_sensor
    zone_config = {CONF_ZONE_NAME: "Test Trouble", CONF_ZONE_NUMBER: "011", CONF_ZONE_CLASS: "wired_motion"}
    sensor = DMPZoneTrouble(hass, mock_config_entry, zone_config)
    sensor._state = state
    assert sensor.icon == icon


@pytest.fixture
def setup_bypass_sensor(hass: HomeAssistant, mock_config_entry, mock_listener):
    """Set up a bypass binary sensor with mocked dependencies."""
    hass.data.setdefault(DOMAIN, {})
    panel = mock_listener.getPanels()["12345"]
    panel.updateBypassZone = Mock()
    panel.getBypassZone = Mock(return_value={"zoneState": False})
    panel.getContactTime = Mock(return_value="t3")
    hass.data[DOMAIN][LISTENER] = mock_listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = {CONF_PANEL_ACCOUNT_NUMBER: "12345"}
    return hass, panel

def test_bypass_sensor_initialization(setup_bypass_sensor, mock_config_entry):
    """Validate bypass sensor initialization settings."""
    hass, panel = setup_bypass_sensor
    zone_config = {CONF_ZONE_NAME: "Test Bypass", CONF_ZONE_NUMBER: "013", CONF_ZONE_CLASS: "wired_door"}
    sensor = DMPZoneBypass(hass, mock_config_entry, zone_config)
    assert sensor._device_class == "problem"
    assert sensor.name == "Test Bypass Bypass"
    assert sensor.is_on is False
    panel.updateBypassZone.assert_called_once()

@pytest.mark.parametrize("state,icon", [(False, "mdi:check"), (True, "mdi:alert-outline")])
def test_bypass_icon(setup_bypass_sensor, mock_config_entry, state, icon):
    """Ensure bypass sensor icon reflects state."""
    hass, panel = setup_bypass_sensor
    zone_config = {CONF_ZONE_NAME: "Test Bypass", CONF_ZONE_NUMBER: "013", CONF_ZONE_CLASS: "wired_door"}
    sensor = DMPZoneBypass(hass, mock_config_entry, zone_config)
    sensor._state = state
    assert sensor.icon == icon



@pytest.fixture
def setup_alarm_sensor(hass: HomeAssistant, mock_config_entry, mock_listener):
    """Set up an alarm binary sensor with mocked dependencies."""
    hass.data.setdefault(DOMAIN, {})
    panel = mock_listener.getPanels()["12345"]
    panel.updateAlarmZone = Mock()
    panel.getAlarmZone = Mock(return_value={"zoneState": False})
    panel.getContactTime = Mock(return_value="t2")
    hass.data[DOMAIN][LISTENER] = mock_listener
    hass.data[DOMAIN][mock_config_entry.entry_id] = {CONF_PANEL_ACCOUNT_NUMBER: "12345"}
    return hass, panel

def test_alarm_sensor_initialization(setup_alarm_sensor, mock_config_entry):
    """Validate alarm sensor initialization settings."""
    hass, panel = setup_alarm_sensor
    zone_config = {CONF_ZONE_NAME: "Test Alarm", CONF_ZONE_NUMBER: "012", CONF_ZONE_CLASS: "wired_motion"}
    sensor = DMPZoneAlarm(hass, mock_config_entry, zone_config)
    assert sensor._device_class == "problem"
    assert sensor.name == "Test Alarm Alarm"
    assert sensor.is_on is False
    panel.updateAlarmZone.assert_called_once()

@pytest.mark.parametrize("state,icon", [(False, 'mdi:check'), (True, 'mdi:alarm-bell')])
def test_alarm_icon(setup_alarm_sensor, mock_config_entry, state, icon):
    """Ensure alarm sensor icon reflects state."""
    hass, panel = setup_alarm_sensor
    zone_config = {CONF_ZONE_NAME: "Test Alarm", CONF_ZONE_NUMBER: "012", CONF_ZONE_CLASS: "wired_motion"}
    sensor = DMPZoneAlarm(hass, mock_config_entry, zone_config)
    sensor._state = state
    assert sensor.icon == icon


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "setup_fixture,sensor_cls,getter,zone_name,zone_number,zone_class",
    [
        ("setup_sensor", DMPZoneOpenClose, "getOpenCloseZone", "Test Door", "001", "wired_door"),
        ("setup_battery_sensor", DMPZoneBattery, "getBatteryZone", "Test Battery", "010", "battery_window"),
        ("setup_trouble_sensor", DMPZoneTrouble, "getTroubleZone", "Test Trouble", "011", "wired_motion"),
        ("setup_bypass_sensor", DMPZoneBypass, "getBypassZone", "Test Bypass", "013", "wired_door"),
        ("setup_alarm_sensor", DMPZoneAlarm, "getAlarmZone", "Test Alarm", "012", "wired_motion"),
    ],
)
async def test_sensor_callbacks_general(request, setup_fixture, sensor_cls, getter, zone_name, zone_number,
                                        zone_class, mock_config_entry, mock_listener):
    """Verify callbacks registration and process_zone_callback for all sensors."""
    hass, panel = request.getfixturevalue(setup_fixture)
    zone_config = {
        CONF_ZONE_NAME: zone_name,
        CONF_ZONE_NUMBER: zone_number,
        CONF_ZONE_CLASS: zone_class,
    }
    sensor = sensor_cls(hass, mock_config_entry, zone_config)
    sensor.async_write_ha_state = Mock()
    getattr(panel, getter).return_value = {"zoneState": True}
    await sensor.process_zone_callback()
    assert sensor._state is True
    sensor.async_write_ha_state.assert_called_once()
    await sensor.async_added_to_hass()
    mock_listener.register_callback.assert_called_with(sensor.process_zone_callback)
    await sensor.async_will_remove_from_hass()
    mock_listener.remove_callback.assert_called_with(sensor.process_zone_callback)


@pytest.mark.parametrize(
    "setup_fixture,sensor_cls,zone_name,zone_number,zone_class,attr_time,device_class,name_suffix,unique_suffix,info_name",
    [
        ("setup_sensor", DMPZoneOpenClose, "Front Door", "001", "wired_door", "time", "door", "", "openclose", "Front Door"),
        ("setup_battery_sensor", DMPZoneBattery, "Test Battery", "010", "battery_window", "t0", "battery", " Battery", "battery", "Test Battery Battery"),
        ("setup_trouble_sensor", DMPZoneTrouble, "Test Trouble", "011", "wired_motion", "t1", "problem", " Trouble", "trouble", "Test Trouble Trouble"),
        ("setup_alarm_sensor", DMPZoneAlarm, "Test Alarm", "012", "wired_motion", "t2", "problem", " Alarm", "alarm", "Test Alarm"),
        ("setup_bypass_sensor", DMPZoneBypass, "Test Bypass", "013", "wired_door", "t3", "problem", " Bypass", "bypass", "Test Bypass Bypass"),
    ],
)
def test_sensor_properties_general(request, setup_fixture, sensor_cls, zone_name, zone_number, zone_class,
                                   attr_time, device_class, name_suffix, unique_suffix, info_name,
                                   mock_config_entry, mock_listener):
    """Check common entity properties across all binary sensor variants."""
    hass, panel = request.getfixturevalue(setup_fixture)
    panel.getContactTime = Mock(return_value=attr_time)
    zone_config = {
        CONF_ZONE_NAME: zone_name,
        CONF_ZONE_NUMBER: zone_number,
        CONF_ZONE_CLASS: zone_class,
    }
    sensor = sensor_cls(hass, mock_config_entry, zone_config)
    assert sensor.device_name == zone_name
    assert sensor.name == f"{zone_name}{name_suffix}"
    assert sensor.should_poll is False
    assert sensor.device_class == device_class
    assert sensor.extra_state_attributes == {"last_contact": attr_time}
    assert sensor.unique_id == f"dmp-12345-zone-{zone_number}-{unique_suffix}"
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, f"dmp-12345-zone-{zone_number}")}
    assert info["name"] == info_name







