"""Unit tests for DMPListener in __init__.py."""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock

from custom_components.dmp.__init__ import DMPListener
from custom_components.dmp.const import CONF_HOME_AREA, CONF_AWAY_AREA, CONF_PANEL_LISTEN_PORT


@pytest.fixture
def listener_fixture():
    """Create a DMPListener with dummy config."""
    config = {
        CONF_HOME_AREA: '01',
        CONF_AWAY_AREA: '02',
        CONF_PANEL_LISTEN_PORT: 9999,
    }
    listener = DMPListener(Mock(), config)
    return listener, config

def test_str(listener_fixture):
    listener, config = listener_fixture
    expected = f"DMP Listener on port {config[CONF_PANEL_LISTEN_PORT]}"
    assert str(listener) == expected

def test_event_types_and_events(listener_fixture):
    listener, _ = listener_fixture
    # Known event type
    from custom_components.dmp.dmp_codes import DMP_TYPES, DMP_EVENTS
    key_t = next(iter(DMP_TYPES))
    assert listener._event_types(key_t) == DMP_TYPES[key_t]
    unknown_t = 'ZZ'
    assert listener._event_types(unknown_t) == f"Unknown Type {unknown_t}"
    # Known event
    key_e = next(iter(DMP_EVENTS))
    assert listener._events(key_e) == DMP_EVENTS[key_e]
    unknown_e = 'XX'
    assert listener._events(unknown_e) == f"Unknown Event {unknown_e}"

@pytest.mark.asyncio
async def test_updateHASS_calls_callbacks(listener_fixture):
    listener, _ = listener_fixture
    calls = []
    async def cb1(): calls.append('cb1')
    async def cb2(): calls.append('cb2')
    listener.register_callback(cb1)
    listener.register_callback(cb2)
    await listener.updateHASS()
    assert 'cb1' in calls and 'cb2' in calls

@pytest.mark.asyncio
async def test_listen_and_start(monkeypatch, listener_fixture):
    listener, config = listener_fixture
    recorded = {}
    # Fake server class
    class FakeServer:
        def __init__(self):
            self.sockets = [MockSocket()]
        def serve_forever(self):
            recorded['serve'] = True
    class MockSocket:
        def getsockname(self):
            return ('0.0.0.0', config[CONF_PANEL_LISTEN_PORT])
    async def fake_start_server(handler, host, port):
        recorded['start_server'] = (handler, host, port)
        return FakeServer()
    monkeypatch.setattr(asyncio, 'start_server', fake_start_server)
    await listener.listen()
    assert 'start_server' in recorded
    assert recorded.get('serve', False)
    # Test start delegates to listen
    recorded.clear()
    async def fake_listen(self): recorded['listen'] = True
    monkeypatch.setattr(DMPListener, 'listen', fake_listen)
    await listener.start()
    assert recorded.get('listen', False)