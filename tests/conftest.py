import pytest
from custom_components.dmp.const import DOMAIN, LISTENER

@pytest.fixture
def init_integration(hass, request):
    """
    Initialize hass.data for DMP integration based on provided fixtures.
    Sets up DOMAIN entry with listener and config entry data.
    """
    # Only initialize if a mock_config_entry fixture is used
    if "mock_config_entry" not in request.fixturenames:
        return
    cfg = request.getfixturevalue("mock_config_entry")
    # Determine listener fixture
    listener = None
    if "mock_listener" in request.fixturenames:
        listener = request.getfixturevalue("mock_listener")
    elif "mock_listener_panel" in request.fixturenames:
        # mock_listener_panel returns (listener, panel)
        listener = request.getfixturevalue("mock_listener_panel")[0]
    # Populate hass.data
    hass.data.setdefault(DOMAIN, {})
    if listener is not None:
        hass.data[DOMAIN][LISTENER] = listener
    hass.data[DOMAIN][cfg.entry_id] = cfg.data