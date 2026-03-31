"""Complete tests for DMPPanel class."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from homeassistant.components.alarm_control_panel import AlarmControlPanelState

from custom_components.dmp import DMPPanel
from custom_components.dmp.const import (
    CONF_PANEL_IP,
    CONF_PANEL_ACCOUNT_NUMBER,
)


def _make_panel(pydmp_panel=None):
    config = {CONF_PANEL_ACCOUNT_NUMBER: "12345", CONF_PANEL_IP: "192.168.1.100"}
    return DMPPanel(Mock(), config, pydmp_panel=pydmp_panel)


def test_panel_initialization_with_defaults():
    """Test panel initialization with missing optional fields."""
    config = {CONF_PANEL_ACCOUNT_NUMBER: "12345", CONF_PANEL_IP: "192.168.1.100"}

    panel = DMPPanel(Mock(), config)

    assert panel._accountNumber == "12345"
    assert panel._ipAddress == "192.168.1.100"
    assert panel._panel_last_contact is None
    assert panel._area == AlarmControlPanelState.DISARMED


def test_panel_initialization_with_all_fields():
    """Test panel initialization with all config fields provided."""
    config = {
        CONF_PANEL_ACCOUNT_NUMBER: "12345",
        CONF_PANEL_IP: "192.168.1.100",
    }

    panel = DMPPanel(Mock(), config)

    assert panel._accountNumber == "12345"
    assert panel._ipAddress == "192.168.1.100"


def test_panel_str_representation():
    """Test string representation of panel."""
    config = {CONF_PANEL_ACCOUNT_NUMBER: "12345", CONF_PANEL_IP: "192.168.1.100"}

    panel = DMPPanel(Mock(), config)

    assert str(panel) == "DMP Panel with account number 12345 at addr 192.168.1.100"


def test_panel_contact_time_methods():
    """Test contact time update and retrieval."""
    panel = _make_panel()

    test_time = datetime.now()
    panel.updateContactTime(test_time)
    assert panel.getContactTime() == test_time


def test_panel_area_methods():
    """Test area update and retrieval."""
    panel = _make_panel()

    area_obj = {"areaName": "Main", "areaState": AlarmControlPanelState.ARMED_AWAY}
    panel.updateArea(area_obj)
    assert panel.getArea() == area_obj


def test_panel_alarm_zone_methods():
    """Test alarm zone set/get/clear methods."""
    panel = _make_panel()

    assert panel.get_alarm("001") is False

    panel.set_alarm("001")
    assert panel.get_alarm("001") is True

    panel.clear_alarm("001")
    assert panel.get_alarm("001") is False


def test_panel_initialization_with_pydmp_panel():
    """Test panel initialization with pyDMP panel reference."""
    config = {CONF_PANEL_ACCOUNT_NUMBER: "12345", CONF_PANEL_IP: "192.168.1.100"}
    mock_pydmp = Mock()

    panel = DMPPanel(Mock(), config, pydmp_panel=mock_pydmp)

    assert panel.getAccountNumber() == "12345"
    assert panel._pydmp_panel == mock_pydmp


def test_panel_ensure_zone_creates_new():
    """Test ensure_zone creates a new pyDMP Zone when not present."""
    mock_pydmp = Mock()
    mock_pydmp._zones = {}

    panel = _make_panel(pydmp_panel=mock_pydmp)
    zone = panel.ensure_zone("001")

    assert 1 in mock_pydmp._zones
    assert zone is not None


def test_panel_ensure_zone_returns_existing():
    """Test ensure_zone returns existing pyDMP Zone."""
    mock_pydmp = Mock()
    mock_zone = Mock()
    mock_pydmp._zones = {1: mock_zone}

    panel = _make_panel(pydmp_panel=mock_pydmp)
    zone = panel.ensure_zone("001")

    assert zone is mock_zone


def test_panel_ensure_zone_no_pydmp():
    """Test ensure_zone returns None when no pyDMP panel."""
    panel = _make_panel()
    zone = panel.ensure_zone("001")
    assert zone is None


@pytest.mark.asyncio
async def test_bypass_zone_existing():
    """Test bypass_zone calls bypass on existing pyDMP zone."""
    mock_pydmp = Mock()
    mock_zone = Mock()
    mock_zone.bypass = AsyncMock()
    mock_pydmp._zones = {1: mock_zone}

    panel = DMPPanel(
        Mock(),
        {CONF_PANEL_ACCOUNT_NUMBER: "12345", CONF_PANEL_IP: "1.1.1.1"},
        pydmp_panel=mock_pydmp,
    )

    await panel.bypass_zone("001")
    mock_zone.bypass.assert_awaited_once()


@pytest.mark.asyncio
async def test_bypass_zone_not_cached():
    """Test bypass_zone creates temporary Zone when not in cache."""
    mock_pydmp = Mock()
    mock_pydmp._zones = {}

    panel = DMPPanel(
        Mock(),
        {CONF_PANEL_ACCOUNT_NUMBER: "12345", CONF_PANEL_IP: "1.1.1.1"},
        pydmp_panel=mock_pydmp,
    )

    with pytest.raises(Exception):
        # Zone.bypass will try to send a command, which will fail on Mock panel
        await panel.bypass_zone("001")


@pytest.mark.asyncio
async def test_restore_zone_existing():
    """Test restore_zone calls restore on existing pyDMP zone."""
    mock_pydmp = Mock()
    mock_zone = Mock()
    mock_zone.restore = AsyncMock()
    mock_pydmp._zones = {1: mock_zone}

    panel = DMPPanel(
        Mock(),
        {CONF_PANEL_ACCOUNT_NUMBER: "12345", CONF_PANEL_IP: "1.1.1.1"},
        pydmp_panel=mock_pydmp,
    )

    await panel.restore_zone("001")
    mock_zone.restore.assert_awaited_once()
