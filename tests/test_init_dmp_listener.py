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


def _make_panel_with_zone(zone_number="001"):
    """Helper to create a mock panel with ensure_zone returning a mock zone."""
    panel = Mock()
    panel.getAccountNumber.return_value = "12345"
    panel.updateContactTime = Mock()
    mock_zone = Mock()
    mock_zone.update_state = Mock()
    panel.ensure_zone = Mock(return_value=mock_zone)
    panel.set_alarm = Mock()
    panel.clear_alarm = Mock()
    panel.updateArea = Mock()
    panel.getArea = Mock(return_value={"areaState": AlarmControlPanelState.DISARMED})
    return panel, mock_zone


@pytest.mark.asyncio
async def test_handle_s3_event_battery():
    """Parse battery event and update zone via pyDMP."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel, mock_zone = _make_panel_with_zone()
    listener._panels = {"12345": panel}
    listener.updateHASS = AsyncMock()

    msg = _make_s3_msg("12345", "Zd", fields=['z 001"Zone1'], raw="test")

    await listener._handle_s3_event(msg)

    mock_zone.update_state.assert_called_once_with("L")
    listener.updateHASS.assert_awaited()


@pytest.mark.asyncio
async def test_handle_s3_event_bypass():
    """Process bypass zone event message."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel, mock_zone = _make_panel_with_zone()
    listener._panels = {"12345": panel}
    listener.updateHASS = AsyncMock()

    msg = _make_s3_msg("12345", "Zx", fields=['z 002"Zone2'], raw="test")

    await listener._handle_s3_event(msg)

    mock_zone.update_state.assert_called_once_with("X")
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
    """Process trouble events (Zf, Zh, Zt, Zw) update zone state."""
    for event_code, expected_state in [
        ("Zf", "S"),
        ("Zh", "M"),
        ("Zt", "S"),
        ("Zw", "S"),
    ]:
        listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
        panel, mock_zone = _make_panel_with_zone()
        listener._panels = {"12345": panel}
        listener.updateHASS = AsyncMock()

        msg = _make_s3_msg("12345", event_code, fields=['z 003"Zone3'], raw="test")

        await listener._handle_s3_event(msg)

        mock_zone.update_state.assert_called_once_with(expected_state)


@pytest.mark.asyncio
async def test_handle_s3_event_restore():
    """Process restore/reset events set zone to Normal and clear alarm."""
    for event_code in ["Zy", "Zr"]:
        listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
        panel, mock_zone = _make_panel_with_zone()
        listener._panels = {"12345": panel}
        listener.updateHASS = AsyncMock()

        msg = _make_s3_msg("12345", event_code, fields=['z 004"Zone4'], raw="test")

        await listener._handle_s3_event(msg)

        mock_zone.update_state.assert_called_once_with("N")
        panel.clear_alarm.assert_called_once_with("004")


@pytest.mark.asyncio
async def test_handle_s3_event_alarm():
    """Handle alarm event sets alarm flag and area to TRIGGERED."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel, mock_zone = _make_panel_with_zone()
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

    panel.set_alarm.assert_called_once_with("005")
    panel.updateArea.assert_called_once_with(
        {"areaName": "Main", "areaState": AlarmControlPanelState.TRIGGERED}
    )


@pytest.mark.asyncio
async def test_handle_s3_event_arming_disarm():
    """Handle arming status disarm event."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel, mock_zone = _make_panel_with_zone()
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
    panel, mock_zone = _make_panel_with_zone()
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
    panel, mock_zone = _make_panel_with_zone()
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
    panel, mock_zone = _make_panel_with_zone()
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
    panel, mock_zone = _make_panel_with_zone()
    listener._panels = {"12345": panel}
    listener.updateHASS = AsyncMock()

    # Door Open
    msg = _make_s3_msg(
        "12345", "Zc", type_code="DO", fields=["z 006", "t ADO"], raw="test"
    )
    await listener._handle_s3_event(msg)
    mock_zone.update_state.assert_called_with("O")

    mock_zone.update_state.reset_mock()

    # Door Closed
    msg = _make_s3_msg(
        "12345", "Zc", type_code="DC", fields=["z 006", "t ADC"], raw="test"
    )
    await listener._handle_s3_event(msg)
    mock_zone.update_state.assert_called_with("N")


@pytest.mark.asyncio
async def test_handle_s3_event_ignored_events():
    """Ignored events (Zs, Zj, Zl) should not update zones."""
    for event_code in ["Zs", "Zj", "Zl"]:
        listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
        panel, mock_zone = _make_panel_with_zone()
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
async def test_handle_s3_event_empty_account_fallback():
    """Empty account should fall back to single panel."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel, mock_zone = _make_panel_with_zone()
    listener._panels = {"12345": panel}
    listener.updateHASS = AsyncMock()

    msg = _make_s3_msg("     ", "Zd", fields=['z 001"Zone1'], raw="test")

    await listener._handle_s3_event(msg)

    mock_zone.update_state.assert_called_once_with("L")
    listener.updateHASS.assert_awaited()


@pytest.mark.asyncio
async def test_handle_s3_event_empty_account_no_fallback():
    """Empty account with multiple panels should warn and return."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel1, _ = _make_panel_with_zone()
    panel2, _ = _make_panel_with_zone()
    panel2.getAccountNumber.return_value = "67890"
    listener._panels = {"12345": panel1, "67890": panel2}
    listener.updateHASS = AsyncMock()

    msg = _make_s3_msg("     ", "Zd", fields=['z 001"Zone1'], raw="test")

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
async def test_listener_updateStatus():
    """Test updateStatus reads from pyDMP zones and areas."""
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

    listener._panels = {"12345": panel}
    listener.setStatusAttributes = Mock()
    listener.updateHASS = AsyncMock()

    await listener.updateStatus()

    mock_pydmp.update_status.assert_awaited_once()
    listener.setStatusAttributes.assert_called_once()
    listener.updateHASS.assert_called_once()


@pytest.mark.asyncio
async def test_handle_s3_event_held_open_and_forced_open():
    """Handle HO (held open) and FO (forced open) device status events."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    panel, mock_zone = _make_panel_with_zone()
    listener._panels = {"12345": panel}
    listener.updateHASS = AsyncMock()

    for type_code in ["HO", "FO"]:
        mock_zone.update_state.reset_mock()
        msg = _make_s3_msg(
            "12345",
            "Zc",
            type_code=type_code,
            fields=["z 007", f"t A{type_code}"],
            raw="test",
        )
        await listener._handle_s3_event(msg)
        mock_zone.update_state.assert_called_with("O")
