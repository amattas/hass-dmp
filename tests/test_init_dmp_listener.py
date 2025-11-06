"""Complete tests for DMPListener class."""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from custom_components.dmp import DMPListener
from custom_components.dmp.const import CONF_HOME_AREA, CONF_AWAY_AREA, CONF_PANEL_LISTEN_PORT
from homeassistant.components.alarm_control_panel import AlarmControlPanelState


@pytest.fixture
def listener_default():
    """Return a listener instance with default configuration."""
    return DMPListener(
        Mock(),
        {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02", CONF_PANEL_LISTEN_PORT: 40001},
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

    listener = DMPListener(hass_mock, config)

    assert listener._hass == hass_mock
    assert listener._domain == config
    assert listener._home_area == "01"
    assert listener._away_area == "02"
    assert listener._port == 40001
    assert listener._server is None
    assert listener._panels == {}
    assert listener.statusAttributes == {}
    assert len(listener._callbacks) == 0


def test_event_type_and_event_lookups():
    """Test event type and event code lookups."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})

    assert listener._event_types("UNKNOWN") == "Unknown Type UNKNOWN"
    assert listener._events("ZZ") == "Unknown Event ZZ"


def test_getS3Segment_with_backslash():
    """Test S3 segment extraction with backslash terminator."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})

    result = listener._getS3Segment("\\z", "prefix\\z001 Front Door\\next")
    assert result == "001 Front Door"

    result = listener._getS3Segment("\\a", "prefix\\a  01 Main Area  \\next")
    assert result == "01 Main Area"


def test_searchS3Segment_edge_cases():
    """Test S3 segment search edge cases."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})

    number, name = listener._searchS3Segment('001"')
    assert number == "001"
    assert name == ""

    number, name = listener._searchS3Segment('002"Zone-2 (Main)"')
    assert number == "002"
    assert name == 'Zone-2 (Main)"'


@pytest.mark.asyncio
async def test_listener_updateStatus_with_short_status():
    """Test updateStatus handles 'Short' status for open/close zones."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})

    panel = Mock()
    sender = Mock()
    sender.status = AsyncMock(
        return_value=(
            {"01": {"name": "Main", "status": "Disarmed"}},
            {
                "001": {"name": "Front Door", "status": "Short"},
                "002": {"name": "Window", "status": "Normal"},
            },
        )
    )
    panel._dmpSender = sender
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

    panel.updateOpenCloseZone.assert_any_call("001", {"zoneNumber": "001", "zoneState": True})
    panel.updateOpenCloseZone.assert_any_call("002", {"zoneNumber": "002", "zoneState": False})


@pytest.mark.asyncio
async def test_listener_updateStatus_all_zones():
    """Handle status updates for all zone types."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel = Mock()
    sender = Mock()

    sender.status = AsyncMock(return_value=(
        {"01": {"name": "Main", "status": "Armed"}},
        {
            "001": {"name": "Front", "status": "Bypassed"},
            "002": {"name": "Back", "status": "Missing"},
            "003": {"name": "Batt", "status": "Low Battery"},
            "004": {"name": "Door", "status": "Normal"},
        }
    ))

    panel._dmpSender = sender
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

    panel.updateBypassZone.assert_called_with("001", {"zoneNumber": "001", "zoneState": True})
    panel.updateTroubleZone.assert_called_with("002", {"zoneNumber": "002", "zoneState": True})
    panel.updateBatteryZone.assert_called_with("003", {"zoneNumber": "003", "zoneState": True})
    panel.updateOpenCloseZone.assert_called_with("004", {"zoneNumber": "004", "zoneState": False})
    listener.setStatusAttributes.assert_called_once()
    listener.updateHASS.assert_called_once()

@pytest.mark.asyncio  
async def test_listener_start_and_listen():
    """Test listener start creates server and calls listen."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02", CONF_PANEL_LISTEN_PORT: 40001})

    with patch("asyncio.start_server") as mock_start_server:
        mock_server = Mock()
        mock_socket = Mock()
        mock_socket.getsockname.return_value = ("0.0.0.0", 40001)
        mock_server.sockets = [mock_socket]
        mock_server.serve_forever = Mock()
        mock_start_server.return_value = mock_server

        await listener.listen()

        mock_start_server.assert_called_once_with(listener.handle_connection, "0.0.0.0", 40001)
        mock_server.serve_forever.assert_called_once()
        assert listener._listener == mock_server.serve_forever.return_value


@pytest.mark.asyncio
async def test_listener_stop():
    """Test listener stop."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02", CONF_PANEL_LISTEN_PORT: 40001})

    with pytest.raises(AttributeError):
        await listener.stop()

    mock_server = Mock()
    mock_server.close = Mock()
    mock_server.wait_closed = AsyncMock()
    listener._server = mock_server

    result = await listener.stop()
    assert result is True
    mock_server.close.assert_called_once()
    mock_server.wait_closed.assert_called_once()


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


def test_getS3Segment_not_found():
    """Return empty string when segment is missing."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    result = listener._getS3Segment("\\z", "no segment here")
    assert result == ""


class DummyReader:
    def __init__(self, messages):
        self._messages = [m.encode() for m in messages]
    async def read(self, _):
        return self._messages.pop(0) if self._messages else b""

class DummyWriter:
    def __init__(self):
        self.writes = []
    def get_extra_info(self, name):
        return ("1.1.1.1", 1234)
    def write(self, data):
        self.writes.append(data)


@pytest.mark.asyncio
async def test_handle_connection_parses_events():
    """Parse incoming connection events and update zones."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel = Mock()
    panel.getAccountNumber.return_value = "12345"
    panel.updateBatteryZone = Mock()
    panel.updateContactTime = Mock()
    listener._panels = {"12345": panel}
    listener.updateHASS = AsyncMock()

    msg = "AAAAAAA123450000000ZdXXX\\z001\"Zone1\\"
    reader = DummyReader([msg, ""])
    writer = DummyWriter()

    await listener.handle_connection(reader, writer)

    panel.updateBatteryZone.assert_called_once_with("001", {"zoneNumber": "001", "zoneState": True})
    assert writer.writes[-1] == ("\x02" + "12345" + "\x06\x0d").encode()
    listener.updateHASS.assert_awaited()


@pytest.mark.asyncio
async def test_handle_connection_bypass_event():
    """Process bypass zone event message."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel = Mock()
    panel.getAccountNumber.return_value = "12345"
    panel.updateBypassZone = Mock()
    panel.updateContactTime = Mock()
    listener._panels = {"12345": panel}
    listener.updateHASS = AsyncMock()

    msg = 'AAAAAAA123450000000ZxYYY\\z002"Zone2\\'

    reader = DummyReader([msg, ""])
    writer = DummyWriter()

    await listener.handle_connection(reader, writer)

    panel.updateBypassZone.assert_called_once_with("002", {"zoneNumber": "002", "zoneState": True})
    assert writer.writes[-1] == ("\x02" + "12345" + "\x06\x0d").encode()
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
async def test_handle_connection_checkin_and_pass_events(caplog):
    """Handle checkin and pass events from panel."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel = Mock()
    panel.getAccountNumber.return_value = "12345"
    panel.updateContactTime = Mock()
    listener._panels = {"12345": panel}
    listener.updateHASS = AsyncMock()

    messages = [
        "AAAAAAA12345 s0700240",
        "AAAAAAA123450000000Zs",
        "AAAAAAA123450000000Zj",
        "AAAAAAA123450000000 S71",
    ]
    reader = DummyReader(messages + [""])
    writer = DummyWriter()

    await listener.handle_connection(reader, writer)

    assert writer.writes[-1] == ("\x02" + "12345" + "\x06\x0d").encode()
    assert panel.updateContactTime.called
    listener.updateHASS.assert_awaited()


@pytest.mark.asyncio
async def test_handle_connection_trouble_and_restore_events():
    """Process trouble and restore events for zones."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel = Mock()
    panel.getAccountNumber.return_value = "12345"
    panel.updateBypassZone = Mock()
    panel.updateTroubleZone = Mock()
    panel.updateBatteryZone = Mock()
    panel.updateAlarmZone = Mock()
    panel.updateContactTime = Mock()
    listener._panels = {"12345": panel}
    listener.updateHASS = AsyncMock()

    msgs = ['AAAAAAA123450000000ZfYYY\\z003"Zone3\\', 'AAAAAAA123450000000ZyYYY\\z004"Zone4\\', ""]
    reader = DummyReader(msgs)
    writer = DummyWriter()

    await listener.handle_connection(reader, writer)

    panel.updateBypassZone.assert_any_call("003", {"zoneNumber": "003", "zoneState": True})
    panel.updateBypassZone.assert_any_call("004", {"zoneNumber": "004", "zoneState": False})
    panel.updateTroubleZone.assert_called_with("004", {"zoneNumber": "004", "zoneState": False})
    panel.updateBatteryZone.assert_called_with("004", {"zoneNumber": "004", "zoneState": False})
    panel.updateAlarmZone.assert_called_with("004", {"zoneNumber": "004", "zoneState": False})
    assert writer.writes[-1] == ("\x02" + "12345" + "\x06\x0d").encode()
    listener.updateHASS.assert_awaited()


@pytest.mark.asyncio
async def test_handle_connection_alarm_and_arming_events():
    """Handle alarm and arming related events."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel = Mock()
    panel.getAccountNumber.return_value = "12345"
    panel.updateArea = Mock()
    panel.getArea = Mock(return_value={"areaState": AlarmControlPanelState.DISARMED})
    panel.updateContactTime = Mock()
    listener._panels = {"12345": panel}
    listener.updateHASS = AsyncMock()
    listener._hass.async_create_task = AsyncMock()
    listener.updateStatus = Mock()

    msgs = [
        'AAAAAAA123450000000ZaXXX\\z005"Zone5\\\\a001"Main\\\\tSAA\\',
        'AAAAAAA123450000000ZqXXX\\a001"Main\\\\tSOP\\',
        'AAAAAAA123450000000ZqXXX\\a001"Main\\\\tSCL\\',
        "",
    ]
    reader = DummyReader(msgs)
    writer = DummyWriter()

    await listener.handle_connection(reader, writer)

    panel.updateArea.assert_any_call({"areaName": "Main", "areaState": AlarmControlPanelState.TRIGGERED})
    panel.updateArea.assert_any_call({"areaName": "Main", "areaState": AlarmControlPanelState.DISARMED})
    panel.updateArea.assert_any_call({"areaName": "Main", "areaState": AlarmControlPanelState.ARMED_HOME})
    listener._hass.async_create_task.assert_called_once()
    assert writer.writes[-1] == ("\x02" + "12345" + "\x06\x0d").encode()


@pytest.mark.asyncio
async def test_handle_connection_device_events_and_unknown():
    """Handle device events and ignore unknown ones."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel = Mock()
    panel.getAccountNumber.return_value = "12345"
    panel.updateOpenCloseZone = Mock()
    panel.updateContactTime = Mock()
    listener._panels = {"12345": panel}
    listener.updateHASS = AsyncMock()

    msgs = [
        "AAAAAAA123450000000ZcXXX\\z006\\tADO\\",
        "AAAAAAA123450000000ZcXXX\\z006\\tADC\\",
        "AAAAAAA123450000000ZZ",
        "",
    ]
    reader = DummyReader(msgs)
    writer = DummyWriter()

    await listener.handle_connection(reader, writer)

    panel.updateOpenCloseZone.assert_any_call("006", {"zoneNumber": "006", "zoneState": True})
    panel.updateOpenCloseZone.assert_any_call("006", {"zoneNumber": "006", "zoneState": False})
    assert writer.writes[-1] == ("\x02" + "12345" + "\x06\x0d").encode()
    listener.updateHASS.assert_awaited()


@pytest.mark.asyncio
async def test_listener_updateStatus_clearing():
    """Clear zones when status reports all normal."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel = Mock()
    sender = Mock()
    sender.status = AsyncMock(
        return_value=(
            {"01": {"name": "Main", "status": "Armed"}},
            {
                "001": {"name": "Front", "status": "Normal"},
                "002": {"name": "Back", "status": "Normal"},
                "003": {"name": "Batt", "status": "Normal"},
            },
        )
    )
    panel._dmpSender = sender
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

    panel.updateBypassZone.assert_called_with("001", {"zoneNumber": "001", "zoneState": False})
    panel.updateTroubleZone.assert_called_with("002", {"zoneNumber": "002", "zoneState": False})
    panel.updateBatteryZone.assert_called_with("003", {"zoneNumber": "003", "zoneState": False})
    listener.setStatusAttributes.assert_called_once()
    listener.updateHASS.assert_called_once()
