"""Complete tests for DMPListener class."""

import pytest
from unittest.mock import Mock, AsyncMock

from pydmp import S3Message

from custom_components.dmp import DMPListener
from custom_components.dmp.const import (
    CONF_HOME_AREA,
    CONF_AWAY_AREA,
    CONF_PANEL_LISTEN_PORT,
)
from homeassistant.components.alarm_control_panel import AlarmControlPanelState


@pytest.fixture
def listener_default():
    """Return a listener instance with default configuration."""
    mock_status_server = Mock()
    mock_status_server.register_callback = Mock()
    return DMPListener(
        Mock(),
        {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02", CONF_PANEL_LISTEN_PORT: 40001},
        pydmp_panel=Mock(),
        status_server=mock_status_server,
    )


def test_listener_str_representation():
    """Test string representation of listener."""
    config = {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02", CONF_PANEL_LISTEN_PORT: 40001}

    listener = DMPListener(Mock(), config)
    assert str(listener) == "DMP Listener on port 40001"


def test_listener_initialization():
    """Test listener initialization."""
    hass_mock = Mock()
    config = {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02", CONF_PANEL_LISTEN_PORT: 40001}
    mock_pydmp = Mock()
    mock_server = Mock()
    mock_server.register_callback = Mock()

    listener = DMPListener(
        hass_mock, config, pydmp_panel=mock_pydmp, status_server=mock_server
    )

    assert listener._hass == hass_mock
    assert listener._domain == config
    assert listener._home_area == "01"
    assert listener._away_area == "02"
    assert listener._port == 40001
    assert listener._pydmp_panel == mock_pydmp
    assert listener._status_server == mock_server
    assert listener._panels == {}
    assert listener.statusAttributes == {}
    assert len(listener._callbacks) == 0
    mock_server.register_callback.assert_called_once_with(listener._handle_s3_event)


def _make_s3_msg(account, definition, type_code=None, fields=None, raw=""):
    """Helper to create S3Message objects for testing.

    Fields use pyDMP format: prefix letter + space + content.
    e.g. 'z 001"Front Door', 'a 001"Main', 't SOP'
    """
    return S3Message(
        account=account,
        definition=definition,
        type_code=type_code,
        fields=fields or [],
        raw=raw,
    )


@pytest.mark.asyncio
async def test_handle_s3_event_battery():
    """Parse battery event and update zone."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel = Mock()
    panel.getAccountNumber.return_value = "12345"
    panel.updateBatteryZone = Mock()
    panel.updateContactTime = Mock()
    listener._panels = {"12345": panel}
    listener.updateHASS = AsyncMock()

    msg = _make_s3_msg("12345", "Zd", fields=['z 001"Zone1'], raw="test")

    await listener._handle_s3_event(msg)

    panel.updateBatteryZone.assert_called_once_with(
        "001", {"zoneNumber": "001", "zoneState": True}
    )
    listener.updateHASS.assert_awaited()


@pytest.mark.asyncio
async def test_handle_s3_event_bypass():
    """Process bypass zone event message."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel = Mock()
    panel.getAccountNumber.return_value = "12345"
    panel.updateBypassZone = Mock()
    panel.updateContactTime = Mock()
    listener._panels = {"12345": panel}
    listener.updateHASS = AsyncMock()

    msg = _make_s3_msg("12345", "Zx", fields=['z 002"Zone2'], raw="test")

    await listener._handle_s3_event(msg)

    panel.updateBypassZone.assert_called_once_with(
        "002", {"zoneNumber": "002", "zoneState": True}
    )
    listener.updateHASS.assert_awaited()


@pytest.mark.asyncio
async def test_remove_callback():
    """Remove a registered callback and verify remaining execution."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    cb1 = AsyncMock()
    cb2 = AsyncMock()
    listener.register_callback(cb1)
    listener.register_callback(cb2)
    listener.remove_callback(cb1)
    assert cb1 not in listener._callbacks
    await listener.updateHASS()
    cb1.assert_not_called()
    cb2.assert_called_once()


def test_status_attributes_helpers():
    """Ensure helper functions build status attributes."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})

    areas = {"01": {"name": "Main", "status": "Armed"}}
    zones = {"001": {"name": "Door", "status": "Open"}}

    listener.setStatusAttributes(areas, zones)

    attr = listener.getStatusAttributes()
    assert attr["Areas:"] == ""
    assert attr["Zones:"] == ""
    assert attr["Area: 01 - Main"] == "Armed"
    assert attr["Zone: 001 - Door"] == "Open"


@pytest.mark.asyncio
async def test_handle_s3_event_trouble():
    """Process trouble events (Zf, Zh, Zt, Zw) update trouble zone."""
    for event_code in ["Zf", "Zh", "Zt", "Zw"]:
        listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
        panel = Mock()
        panel.getAccountNumber.return_value = "12345"
        panel.updateTroubleZone = Mock()
        panel.updateContactTime = Mock()
        listener._panels = {"12345": panel}
        listener.updateHASS = AsyncMock()

        msg = _make_s3_msg("12345", event_code, fields=['z 003"Zone3'], raw="test")

        await listener._handle_s3_event(msg)

        panel.updateTroubleZone.assert_called_once_with(
            "003", {"zoneNumber": "003", "zoneState": True}
        )


@pytest.mark.asyncio
async def test_handle_s3_event_restore():
    """Process restore/reset events clear all zone states."""
    for event_code in ["Zy", "Zr"]:
        listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
        panel = Mock()
        panel.getAccountNumber.return_value = "12345"
        panel.updateOpenCloseZone = Mock()
        panel.updateTroubleZone = Mock()
        panel.updateBatteryZone = Mock()
        panel.updateBypassZone = Mock()
        panel.updateAlarmZone = Mock()
        panel.updateContactTime = Mock()
        listener._panels = {"12345": panel}
        listener.updateHASS = AsyncMock()

        msg = _make_s3_msg("12345", event_code, fields=['z 004"Zone4'], raw="test")

        await listener._handle_s3_event(msg)

        clear_obj = {"zoneNumber": "004", "zoneState": False}
        panel.updateOpenCloseZone.assert_not_called()
        panel.updateTroubleZone.assert_called_with("004", clear_obj)
        panel.updateBatteryZone.assert_called_with("004", clear_obj)
        panel.updateBypassZone.assert_called_with("004", clear_obj)
        panel.updateAlarmZone.assert_called_with("004", clear_obj)


@pytest.mark.asyncio
async def test_handle_s3_event_alarm():
    """Handle alarm event updates alarm zone and area to TRIGGERED."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel = Mock()
    panel.getAccountNumber.return_value = "12345"
    panel.updateAlarmZone = Mock()
    panel.updateArea = Mock()
    panel.updateContactTime = Mock()
    listener._panels = {"12345": panel}
    listener.updateHASS = AsyncMock()

    msg = _make_s3_msg(
        "12345",
        "Za",
        type_code="AA",
        fields=['z 005"Zone5', 'a 001"Main', "t SAA"],
        raw="test",
    )

    await listener._handle_s3_event(msg)

    panel.updateAlarmZone.assert_called_once_with(
        "005", {"zoneNumber": "005", "zoneState": True}
    )
    panel.updateArea.assert_called_once_with(
        {"areaName": "Main", "areaState": AlarmControlPanelState.TRIGGERED}
    )


@pytest.mark.asyncio
async def test_handle_s3_event_arming_disarm():
    """Handle arming status disarm event."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel = Mock()
    panel.getAccountNumber.return_value = "12345"
    panel.updateArea = Mock()
    panel.getArea = Mock(return_value={"areaState": AlarmControlPanelState.DISARMED})
    panel.updateContactTime = Mock()
    listener._panels = {"12345": panel}
    listener.updateHASS = AsyncMock()
    listener._hass.async_create_task = Mock()
    listener.updateStatus = AsyncMock()

    msg = _make_s3_msg(
        "12345", "Zq", type_code="OP", fields=['a 001"Main', "t SOP"], raw="test"
    )

    await listener._handle_s3_event(msg)

    panel.updateArea.assert_called_once_with(
        {
            "areaName": "Main",
            "areaState": AlarmControlPanelState.DISARMED,
        }
    )
    listener._hass.async_create_task.assert_called_once()


@pytest.mark.asyncio
async def test_handle_s3_event_arming_arm_home():
    """Handle arming status CL event for home area."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel = Mock()
    panel.getAccountNumber.return_value = "12345"
    panel.updateArea = Mock()
    panel.getArea = Mock(return_value={"areaState": AlarmControlPanelState.DISARMED})
    panel.updateContactTime = Mock()
    listener._panels = {"12345": panel}
    listener.updateHASS = AsyncMock()

    msg = _make_s3_msg(
        "12345", "Zq", type_code="CL", fields=['a 001"Main', "t SCL"], raw="test"
    )

    await listener._handle_s3_event(msg)

    panel.updateArea.assert_called_once_with(
        {
            "areaName": "Main",
            "areaState": AlarmControlPanelState.ARMED_HOME,
        }
    )


@pytest.mark.asyncio
async def test_handle_s3_event_arming_arm_away():
    """Handle arming status CL event for away area."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel = Mock()
    panel.getAccountNumber.return_value = "12345"
    panel.updateArea = Mock()
    panel.getArea = Mock(return_value={"areaState": AlarmControlPanelState.DISARMED})
    panel.updateContactTime = Mock()
    listener._panels = {"12345": panel}
    listener.updateHASS = AsyncMock()

    msg = _make_s3_msg(
        "12345", "Zq", type_code="CL", fields=['a 002"Main', "t SCL"], raw="test"
    )

    await listener._handle_s3_event(msg)

    panel.updateArea.assert_called_once_with(
        {
            "areaName": "Main",
            "areaState": AlarmControlPanelState.ARMED_AWAY,
        }
    )


@pytest.mark.asyncio
async def test_handle_s3_event_arming_unknown_type_code():
    """Unknown arming type codes should not change area state."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel = Mock()
    panel.getAccountNumber.return_value = "12345"
    panel.updateArea = Mock()
    panel.updateContactTime = Mock()
    listener._panels = {"12345": panel}
    listener.updateHASS = AsyncMock()

    msg = _make_s3_msg(
        "12345", "Zq", type_code="LA", fields=['a 001"Main', "t SLA"], raw="test"
    )

    await listener._handle_s3_event(msg)

    panel.updateArea.assert_not_called()


@pytest.mark.asyncio
async def test_handle_s3_event_device_status():
    """Handle device status (Zc) events for open/close."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel = Mock()
    panel.getAccountNumber.return_value = "12345"
    panel.updateOpenCloseZone = Mock()
    panel.updateContactTime = Mock()
    listener._panels = {"12345": panel}
    listener.updateHASS = AsyncMock()

    # Door Open
    msg = _make_s3_msg(
        "12345", "Zc", type_code="DO", fields=["z 006", "t ADO"], raw="test"
    )
    await listener._handle_s3_event(msg)
    panel.updateOpenCloseZone.assert_called_with(
        "006", {"zoneNumber": "006", "zoneState": True}
    )

    panel.updateOpenCloseZone.reset_mock()

    # Door Closed
    msg = _make_s3_msg(
        "12345", "Zc", type_code="DC", fields=["z 006", "t ADC"], raw="test"
    )
    await listener._handle_s3_event(msg)
    panel.updateOpenCloseZone.assert_called_with(
        "006", {"zoneNumber": "006", "zoneState": False}
    )


@pytest.mark.asyncio
async def test_handle_s3_event_ignored_events():
    """Ignored events (Zs, Zj, Zl) should not update zones."""
    for event_code in ["Zs", "Zj", "Zl"]:
        listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
        panel = Mock()
        panel.getAccountNumber.return_value = "12345"
        panel.updateContactTime = Mock()
        listener._panels = {"12345": panel}
        listener.updateHASS = AsyncMock()

        msg = _make_s3_msg("12345", event_code, raw="test")

        await listener._handle_s3_event(msg)

        # Should still update contact time and call updateHASS
        panel.updateContactTime.assert_called_once()
        listener.updateHASS.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_s3_event_unknown_account():
    """Unknown account number should warn and return early."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    listener._panels = {}
    listener.updateHASS = AsyncMock()

    msg = _make_s3_msg("99999", "Zd", fields=['z 001"Zone1'], raw="test")

    await listener._handle_s3_event(msg)

    listener.updateHASS.assert_not_awaited()


@pytest.mark.asyncio
async def test_listener_updateHASS():
    """Test updateHASS method with callbacks."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})

    callback1 = AsyncMock()
    callback2 = AsyncMock()
    listener.register_callback(callback1)
    listener.register_callback(callback2)

    await listener.updateHASS()

    callback1.assert_called_once()
    callback2.assert_called_once()


def test_listener_panel_management():
    """Test panel add/remove/get operations."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})

    panel1 = Mock()
    panel1.getAccountNumber.return_value = "12345"
    panel2 = Mock()
    panel2.getAccountNumber.return_value = "67890"

    listener.addPanel(panel1)
    listener.addPanel(panel2)

    panels = listener.getPanels()
    assert len(panels) == 2
    assert panels["12345"] == panel1
    assert panels["67890"] == panel2


@pytest.mark.asyncio
async def test_listener_updateStatus_with_short_status():
    """Test updateStatus handles 'Short' status for open/close zones."""
    mock_pydmp = Mock()
    mock_pydmp.update_status = AsyncMock()

    mock_zone_001 = Mock()
    mock_zone_001.state = "S"  # Short
    mock_zone_001.name = "Front Door"
    mock_zone_001.number = 1

    mock_zone_002 = Mock()
    mock_zone_002.state = "N"  # Normal
    mock_zone_002.name = "Window"
    mock_zone_002.number = 2

    mock_pydmp._zones = {1: mock_zone_001, 2: mock_zone_002}
    mock_pydmp._areas = {}

    listener = DMPListener(
        Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"}, pydmp_panel=mock_pydmp
    )

    panel = Mock()
    panel.getAccountNumber.return_value = "12345"
    panel._open_close_zones = {"001": {}, "002": {}}
    panel._bypass_zones = {}
    panel._trouble_zones = {}
    panel._battery_zones = {}
    panel.updateOpenCloseZone = Mock()

    listener._panels = {"12345": panel}
    listener.setStatusAttributes = Mock()
    listener.updateHASS = AsyncMock()

    await listener.updateStatus()

    panel.updateOpenCloseZone.assert_any_call(
        "001", {"zoneNumber": "001", "zoneState": True}
    )
    panel.updateOpenCloseZone.assert_any_call(
        "002", {"zoneNumber": "002", "zoneState": False}
    )


@pytest.mark.asyncio
async def test_listener_updateStatus_all_zones():
    """Handle status updates for all zone types."""
    mock_pydmp = Mock()
    mock_pydmp.update_status = AsyncMock()

    mock_zones = {
        1: Mock(state="X", name="Front", number=1),  # Bypassed
        2: Mock(state="M", name="Back", number=2),  # Missing
        3: Mock(state="L", name="Batt", number=3),  # Low Battery
        4: Mock(state="N", name="Door", number=4),  # Normal
    }
    mock_pydmp._zones = mock_zones
    mock_pydmp._areas = {1: Mock(state="A", name="Main", number=1)}

    listener = DMPListener(
        Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"}, pydmp_panel=mock_pydmp
    )

    panel = Mock()
    panel.getAccountNumber.return_value = "12345"
    panel._open_close_zones = {"004": {}}
    panel._bypass_zones = {"001": {}}
    panel._trouble_zones = {"002": {}}
    panel._battery_zones = {"003": {}}
    panel.updateOpenCloseZone = Mock()
    panel.updateBypassZone = Mock()
    panel.updateTroubleZone = Mock()
    panel.updateBatteryZone = Mock()

    listener._panels = {"12345": panel}
    listener.setStatusAttributes = Mock()
    listener.updateHASS = AsyncMock()

    await listener.updateStatus()

    panel.updateBypassZone.assert_called_with(
        "001", {"zoneNumber": "001", "zoneState": True}
    )
    panel.updateTroubleZone.assert_called_with(
        "002", {"zoneNumber": "002", "zoneState": True}
    )
    panel.updateBatteryZone.assert_called_with(
        "003", {"zoneNumber": "003", "zoneState": True}
    )
    panel.updateOpenCloseZone.assert_called_with(
        "004", {"zoneNumber": "004", "zoneState": False}
    )
    listener.setStatusAttributes.assert_called_once()
    listener.updateHASS.assert_called_once()


@pytest.mark.asyncio
async def test_listener_updateStatus_clearing():
    """Clear zones when status reports all normal."""
    mock_pydmp = Mock()
    mock_pydmp.update_status = AsyncMock()

    mock_zones = {
        1: Mock(state="N", name="Front", number=1),
        2: Mock(state="N", name="Back", number=2),
        3: Mock(state="N", name="Batt", number=3),
    }
    mock_pydmp._zones = mock_zones
    mock_pydmp._areas = {1: Mock(state="A", name="Main", number=1)}

    listener = DMPListener(
        Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"}, pydmp_panel=mock_pydmp
    )

    panel = Mock()
    panel.getAccountNumber.return_value = "12345"
    panel._open_close_zones = {}
    panel._bypass_zones = {"001": {}}
    panel._trouble_zones = {"002": {}}
    panel._battery_zones = {"003": {}}
    panel.updateBypassZone = Mock()
    panel.updateTroubleZone = Mock()
    panel.updateBatteryZone = Mock()

    listener._panels = {"12345": panel}
    listener.setStatusAttributes = Mock()
    listener.updateHASS = AsyncMock()

    await listener.updateStatus()

    panel.updateBypassZone.assert_called_with(
        "001", {"zoneNumber": "001", "zoneState": False}
    )
    panel.updateTroubleZone.assert_called_with(
        "002", {"zoneNumber": "002", "zoneState": False}
    )
    panel.updateBatteryZone.assert_called_with(
        "003", {"zoneNumber": "003", "zoneState": False}
    )
    listener.setStatusAttributes.assert_called_once()
    listener.updateHASS.assert_called_once()


@pytest.mark.asyncio
async def test_handle_s3_event_held_open_and_forced_open():
    """Handle HO (held open) and FO (forced open) device status events."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel = Mock()
    panel.getAccountNumber.return_value = "12345"
    panel.updateOpenCloseZone = Mock()
    panel.updateContactTime = Mock()
    listener._panels = {"12345": panel}
    listener.updateHASS = AsyncMock()

    for type_code in ["HO", "FO"]:
        panel.updateOpenCloseZone.reset_mock()
        msg = _make_s3_msg(
            "12345",
            "Zc",
            type_code=type_code,
            fields=["z 007", f"t A{type_code}"],
            raw="test",
        )
        await listener._handle_s3_event(msg)
        panel.updateOpenCloseZone.assert_called_with(
            "007", {"zoneNumber": "007", "zoneState": True}
        )
