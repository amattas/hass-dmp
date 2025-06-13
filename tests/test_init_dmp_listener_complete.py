"""Complete tests for DMPListener class."""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from homeassistant.const import STATE_ALARM_DISARMED, STATE_ALARM_ARMED_AWAY, STATE_ALARM_ARMED_HOME, STATE_ALARM_TRIGGERED

from custom_components.dmp import DMPListener
from custom_components.dmp.const import CONF_HOME_AREA, CONF_AWAY_AREA, CONF_PANEL_LISTEN_PORT


class TestDMPListenerComplete:
    """Complete tests for DMPListener class."""

    def test_listener_str_representation(self):
        """Test string representation of listener."""
        config = {
            CONF_HOME_AREA: "01",
            CONF_AWAY_AREA: "02", 
            CONF_PANEL_LISTEN_PORT: 40001
        }
        
        listener = DMPListener(Mock(), config)
        assert str(listener) == "DMP Listener on port 40001"

    def test_listener_initialization(self):
        """Test listener initialization."""
        hass_mock = Mock()
        config = {
            CONF_HOME_AREA: "01",
            CONF_AWAY_AREA: "02",
            CONF_PANEL_LISTEN_PORT: 40001
        }
        
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

    def test_event_type_and_event_lookups(self):
        """Test event type and event code lookups."""
        listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
        
        # Test unknown codes return proper format
        assert listener._event_types("UNKNOWN") == "Unknown Type UNKNOWN"
        assert listener._events("ZZ") == "Unknown Event ZZ"

    def test_getS3Segment_with_backslash(self):
        """Test S3 segment extraction with backslash terminator."""
        listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
        
        # Test extraction up to backslash
        result = listener._getS3Segment("\\z", "prefix\\z001 Front Door\\next")
        assert result == "001 Front Door"
        
        # Test with spaces
        result = listener._getS3Segment("\\a", "prefix\\a  01 Main Area  \\next")
        assert result == "01 Main Area"

    def test_searchS3Segment_edge_cases(self):
        """Test S3 segment search edge cases."""
        listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
        
        # Test with empty zone name
        number, name = listener._searchS3Segment('001"')
        assert number == "001"
        assert name == ""
        
        # Test with special characters in name
        number, name = listener._searchS3Segment('002"Zone-2 (Main)"')
        assert number == "002"
        assert name == "Zone-2 (Main)\""

    @pytest.mark.asyncio
    async def test_listener_handle_connection_checkin(self):
        """Test handling checkin message."""
        listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02", CONF_PANEL_LISTEN_PORT: 40001})
        
        # Create mock panel
        panel = Mock()
        panel.getAccountNumber.return_value = "12345"
        panel.updateContactTime = Mock()
        listener._panels = {"12345": panel}
        
        # Mock reader and writer
        reader = Mock()
        reader.read = AsyncMock(side_effect=[
            b'\x0212345 s0700240\x03',  # Checkin message
            b''  # End connection
        ])
        writer = Mock()
        writer.get_extra_info = Mock(return_value="192.168.1.100")
        writer.write = Mock()
        
        # Mock updateHASS
        listener.updateHASS = AsyncMock()
        
        await listener.handle_connection(reader, writer)
        
        # Verify ACK sent
        writer.write.assert_called_with(b'\x0212345\x06\x0d')
        # Verify contact time updated
        panel.updateContactTime.assert_called_once()

    @pytest.mark.asyncio
    async def test_listener_handle_connection_zone_events(self):
        """Test handling various zone events."""
        listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02", CONF_PANEL_LISTEN_PORT: 40001})
        
        # Create mock panel
        panel = Mock()
        panel.getAccountNumber.return_value = "12345"
        panel.updateContactTime = Mock()
        panel.updateBatteryZone = Mock()
        panel.updateBypassZone = Mock()
        panel.updateTroubleZone = Mock()
        panel.updateAlarmZone = Mock()
        panel.updateOpenCloseZone = Mock()
        panel.updateArea = Mock()
        panel.getArea = Mock(return_value={"areaState": STATE_ALARM_DISARMED})
        listener._panels = {"12345": panel}
        
        # Mock reader with multiple events
        reader = Mock()
        reader.read = AsyncMock(side_effect=[
            b'\x0212345      Zd\\z001"Front Door\\t\x03',  # Battery event
            b'\x0212345      Zx\\z002"Window\\t\x03',     # Bypass event
            b'\x0212345      Zf\\z003"Motion\\t\x03',     # Trouble event
            b'\x0212345      Za\\z004"Smoke\\a01"Main\\tFA\x03',  # Alarm event
            b'\x0212345      Zc\\z005"Door\\tDO\x03',     # Door open event
            b'\x0212345      Zc\\z005"Door\\tDC\x03',     # Door close event
            b''  # End connection
        ])
        writer = Mock()
        writer.get_extra_info = Mock(return_value="192.168.1.100")
        writer.write = Mock()
        
        # Mock updateHASS
        listener.updateHASS = AsyncMock()
        
        await listener.handle_connection(reader, writer)
        
        # Verify zone updates called
        panel.updateBatteryZone.assert_called_with("001", {"zoneNumber": "001", "zoneState": True})
        panel.updateBypassZone.assert_any_call("002", {"zoneNumber": "002", "zoneState": True})
        panel.updateBypassZone.assert_any_call("003", {"zoneNumber": "003", "zoneState": True})  # Trouble uses bypass
        panel.updateAlarmZone.assert_not_called()  # Alarm events update area, not alarm zone
        panel.updateArea.assert_called_with({"areaName": "Main", "areaState": STATE_ALARM_TRIGGERED})
        panel.updateOpenCloseZone.assert_any_call("005", {"zoneNumber": "005", "zoneState": True})
        panel.updateOpenCloseZone.assert_any_call("005", {"zoneNumber": "005", "zoneState": False})

    @pytest.mark.asyncio
    async def test_listener_handle_connection_arming_events(self):
        """Test handling arming status events."""
        listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02", CONF_PANEL_LISTEN_PORT: 40001})
        
        # Create mock panel
        panel = Mock()
        panel.getAccountNumber.return_value = "12345"
        panel.updateContactTime = Mock()
        panel.updateArea = Mock()
        panel.getArea = Mock(return_value={"areaState": STATE_ALARM_DISARMED})
        listener._panels = {"12345": panel}
        listener.updateStatus = AsyncMock()
        
        # Mock reader with arming events
        reader = Mock()
        reader.read = AsyncMock(side_effect=[
            b'\x0212345      Zq\\a001"Main\\tOP\x03',     # Disarm
            b'\x0212345      Zq\\a001"Main\\tCL\x03',     # Arm home area
            b'\x0212345      Zq\\a002"Away\\tCL\x03',     # Arm away area
            b''  # End connection
        ])
        writer = Mock()
        writer.get_extra_info = Mock(return_value="192.168.1.100")
        writer.write = Mock()
        
        # Mock updateHASS
        listener.updateHASS = AsyncMock()
        
        await listener.handle_connection(reader, writer)
        
        # Verify area updates
        calls = panel.updateArea.call_args_list
        assert calls[0][0][0] == {"areaName": "Main", "areaState": STATE_ALARM_DISARMED}
        assert calls[1][0][0] == {"areaName": "Main", "areaState": STATE_ALARM_ARMED_HOME}
        assert calls[2][0][0] == {"areaName": "Away", "areaState": STATE_ALARM_ARMED_AWAY}
        
        # Verify status update triggered on disarm
        listener.updateStatus.assert_called()

    @pytest.mark.asyncio
    async def test_listener_handle_connection_reset_events(self):
        """Test handling zone reset events."""
        listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02", CONF_PANEL_LISTEN_PORT: 40001})
        
        # Create mock panel
        panel = Mock()
        panel.getAccountNumber.return_value = "12345"
        panel.updateContactTime = Mock()
        panel.updateBypassZone = Mock()
        panel.updateTroubleZone = Mock()
        panel.updateBatteryZone = Mock()
        panel.updateAlarmZone = Mock()
        listener._panels = {"12345": panel}
        
        # Mock reader with reset events
        reader = Mock()
        reader.read = AsyncMock(side_effect=[
            b'\x0212345      Zy\\z001"Zone\\t\x03',     # Reset event
            b'\x0212345      Zr\\z002"Zone\\t\x03',     # Restore event
            b''  # End connection
        ])
        writer = Mock()
        writer.get_extra_info = Mock(return_value="192.168.1.100")
        writer.write = Mock()
        
        # Mock updateHASS
        listener.updateHASS = AsyncMock()
        
        await listener.handle_connection(reader, writer)
        
        # Verify all zones cleared for both events
        clear_obj = {"zoneNumber": "001", "zoneState": False}
        panel.updateBypassZone.assert_any_call("001", clear_obj)
        panel.updateTroubleZone.assert_any_call("001", clear_obj)
        panel.updateBatteryZone.assert_any_call("001", clear_obj)
        panel.updateAlarmZone.assert_any_call("001", clear_obj)
        
        clear_obj2 = {"zoneNumber": "002", "zoneState": False}
        panel.updateBypassZone.assert_any_call("002", clear_obj2)
        panel.updateTroubleZone.assert_any_call("002", clear_obj2)
        panel.updateBatteryZone.assert_any_call("002", clear_obj2)
        panel.updateAlarmZone.assert_any_call("002", clear_obj2)

    @pytest.mark.asyncio
    async def test_listener_handle_connection_unknown_account(self):
        """Test handling message from unknown account number."""
        listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02", CONF_PANEL_LISTEN_PORT: 40001})
        listener._panels = {}  # No panels registered
        
        # Mock reader
        reader = Mock()
        reader.read = AsyncMock(return_value=b'\x0299999      Zd\\z001"Zone\\t\x03')
        writer = Mock()
        writer.get_extra_info = Mock(return_value="192.168.1.100")
        
        # Should handle gracefully without error
        await listener.handle_connection(reader, writer)

    @pytest.mark.asyncio
    async def test_listener_handle_connection_ignored_events(self):
        """Test that certain events are ignored."""
        listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02", CONF_PANEL_LISTEN_PORT: 40001})
        
        # Create mock panel
        panel = Mock()
        panel.getAccountNumber.return_value = "12345"
        panel.updateContactTime = Mock()
        listener._panels = {"12345": panel}
        
        # Mock reader with ignored events
        reader = Mock()
        reader.read = AsyncMock(side_effect=[
            b'\x0212345      S71\\t\x03',        # Time update (ignored)
            b'\x0212345      Zs\\t\x03',         # System message (ignored)
            b'\x0212345      Zj\\t\x03',         # Door/Panel access (ignored)
            b'\x0212345      Zl\\t\x03',         # Schedule change (ignored)
            b''  # End connection
        ])
        writer = Mock()
        writer.get_extra_info = Mock(return_value="192.168.1.100")
        writer.write = Mock()
        
        # Mock updateHASS
        listener.updateHASS = AsyncMock()
        
        await listener.handle_connection(reader, writer)
        
        # Should send ACKs but not process events
        assert writer.write.call_count == 4  # One ACK per event

    @pytest.mark.asyncio
    async def test_listener_updateStatus_with_short_status(self):
        """Test updateStatus handles 'Short' status for open/close zones."""
        listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
        
        # Create mock panel with sender
        panel = Mock()
        sender = Mock()
        sender.status = AsyncMock(return_value=(
            {"01": {"name": "Main", "status": "Disarmed"}},
            {
                "001": {"name": "Front Door", "status": "Short"},  # Short = Open
                "002": {"name": "Window", "status": "Normal"}
            }
        ))
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
        
        # Verify 'Short' treated as open
        panel.updateOpenCloseZone.assert_any_call("001", {"zoneNumber": "001", "zoneState": True})
        panel.updateOpenCloseZone.assert_any_call("002", {"zoneNumber": "002", "zoneState": False})

    @pytest.mark.asyncio  
    async def test_listener_start_and_listen(self):
        """Test listener start creates server and calls listen."""
        listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02", CONF_PANEL_LISTEN_PORT: 40001})
        
        with patch('asyncio.start_server') as mock_start_server:
            mock_server = Mock()
            mock_socket = Mock()
            mock_socket.getsockname.return_value = ("0.0.0.0", 40001)
            mock_server.sockets = [mock_socket]
            mock_server.serve_forever = Mock()
            mock_start_server.return_value = mock_server
            
            await listener.start()
            
            mock_start_server.assert_called_once_with(
                listener.handle_connection, "0.0.0.0", 40001
            )
            mock_server.serve_forever.assert_called_once()
            assert listener._server == mock_server

    @pytest.mark.asyncio
    async def test_listener_stop(self):
        """Test listener stop."""
        listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02", CONF_PANEL_LISTEN_PORT: 40001})
        
        # Test stop when no server
        result = await listener.stop()
        assert result is True
        
        # Test stop with server
        mock_server = Mock()
        mock_server.close = Mock()
        mock_server.wait_closed = AsyncMock()
        listener._server = mock_server
        
        result = await listener.stop()
        assert result is True
        mock_server.close.assert_called_once()
        mock_server.wait_closed.assert_called_once()

    @pytest.mark.asyncio
    async def test_listener_updateHASS(self):
        """Test updateHASS method with callbacks."""
        listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
        
        # Add callbacks
        callback1 = AsyncMock()
        callback2 = AsyncMock()
        listener.register_callback(callback1)
        listener.register_callback(callback2)
        
        await listener.updateHASS()
        
        # Both callbacks should be called
        callback1.assert_called_once()
        callback2.assert_called_once()

    def test_listener_panel_management(self):
        """Test panel add/remove/get operations."""
        listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
        
        # Create mock panels
        panel1 = Mock()
        panel1.getAccountNumber.return_value = "12345"
        panel2 = Mock()
        panel2.getAccountNumber.return_value = "67890"
        
        # Add panels
        listener.addPanel(panel1)
        listener.addPanel(panel2)
        
        # Verify panels stored correctly
        panels = listener.getPanels()
        assert len(panels) == 2
        assert panels["12345"] == panel1
        assert panels["67890"] == panel2