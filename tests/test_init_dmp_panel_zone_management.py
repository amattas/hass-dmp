"""Test zone getter/setter methods in DMPPanel."""
import pytest
from unittest.mock import Mock, patch
from custom_components.dmp import DMPPanel


class TestDMPPanelZoneManagement:
    """Test zone getter/setter methods."""

    @pytest.fixture
    def mock_panel(self):
        """Create a mock panel."""
        with patch('custom_components.dmp.DMPListener'), \
             patch('custom_components.dmp.DMPSender'):
            panel_config = {
                "ip": "192.168.1.1",
                "listen_port": 40002,
                "remote_port": 40001,
                "account_number": "12345",
                "panel_name": "Test Panel"
            }
            return DMPPanel(panel_config, Mock())

    def test_updateArea_and_getArea(self, mock_panel):
        """Test area update and retrieval."""
        area_data = {"areaState": "Armed", "name": "Main Floor"}
        
        mock_panel.updateArea(area_data)
        result = mock_panel.getArea()
        
        assert result == area_data

    @pytest.mark.parametrize(
        "zone_type,update_method,get_method", [
            ("open_close", "updateOpenCloseZone", "getOpenCloseZone"),
            ("battery", "updateBatteryZone", "getBatteryZone"),
            ("trouble", "updateTroubleZone", "getTroubleZone"),
            ("bypass", "updateBypassZone", "getBypassZone"),
            ("alarm", "updateAlarmZone", "getAlarmZone"),
        ]
    )
    def test_zone_update_and_get(self, mock_panel, zone_type, update_method, get_method):
        """Test zone update and retrieval for various zone types."""
        zone_num = "001"
        zone_data = {"zoneState": True, "zoneName": "Test Zone"}
        
        # Mock updateStatusZone since it will be called
        mock_panel.updateStatusZone = Mock()
        
        # Call the update method
        getattr(mock_panel, update_method)(zone_num, zone_data)
        
        # Get the result
        result = getattr(mock_panel, get_method)(zone_num)
        
        assert result["zoneState"] == zone_data["zoneState"]
        # Should call updateStatusZone
        mock_panel.updateStatusZone.assert_called_once_with(zone_num, zone_data)

    @pytest.mark.parametrize(
        "get_method", [
            "getOpenCloseZone",
            "getBatteryZone",
            "getTroubleZone",
            "getBypassZone",
            "getAlarmZone",
        ]
    )
    def test_getZone_returns_none_for_missing_zone(self, mock_panel, get_method):
        """Test that getters return None for non-existent zones."""
        assert getattr(mock_panel, get_method)("999") is None