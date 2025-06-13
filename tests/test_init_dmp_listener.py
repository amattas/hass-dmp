"""Complete tests for DMPListener class."""
import pytest
from unittest.mock import Mock, patch, AsyncMock

from custom_components.dmp import DMPListener
from custom_components.dmp.const import CONF_HOME_AREA, CONF_AWAY_AREA, CONF_PANEL_LISTEN_PORT
@pytest.fixture
def listener_default():
    return DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02", CONF_PANEL_LISTEN_PORT: 40001})


def test_listener_str_representation():
    """Test string representation of listener."""
    config = {
        CONF_HOME_AREA: "01",
        CONF_AWAY_AREA: "02", 
        CONF_PANEL_LISTEN_PORT: 40001
    }
    
    listener = DMPListener(Mock(), config)
    assert str(listener) == "DMP Listener on port 40001"

def test_listener_initialization():
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

def test_event_type_and_event_lookups():
    """Test event type and event code lookups."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    
    # Test unknown codes return proper format
    assert listener._event_types("UNKNOWN") == "Unknown Type UNKNOWN"
    assert listener._events("ZZ") == "Unknown Event ZZ"

def test_getS3Segment_with_backslash():
    """Test S3 segment extraction with backslash terminator."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02"})
    
    # Test extraction up to backslash
    result = listener._getS3Segment("\\z", "prefix\\z001 Front Door\\next")
    assert result == "001 Front Door"
    
    # Test with spaces
    result = listener._getS3Segment("\\a", "prefix\\a  01 Main Area  \\next")
    assert result == "01 Main Area"

def test_searchS3Segment_edge_cases():
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
async def test_listener_updateStatus_with_short_status():
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
async def test_listener_start_and_listen():
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
async def test_listener_stop():
    """Test listener stop."""
    listener = DMPListener(Mock(), {CONF_HOME_AREA: "01", CONF_AWAY_AREA: "02", CONF_PANEL_LISTEN_PORT: 40001})
    
    # Test stop when no server should raise AttributeError due to no server
    with pytest.raises(AttributeError):
        await listener.stop()
    
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
async def test_listener_updateHASS():
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

def test_listener_panel_management():
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