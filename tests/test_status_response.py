from custom_components.dmp.dmp_sender import StatusResponse

class TestStatusResponse:
    """Test StatusResponse class."""

    def test_parse_reply_zone_data(self):
        """Test parsing zone status data."""
        response = StatusResponse()
        response.parseReply('z001=00"Entry"')
        
        assert "001" in response.Zones
        assert response.Zones["001"]["Status"] == "00"
        assert response.Zones["001"]["Name"] == "Entry"

    def test_parse_reply_area_data(self):
        """Test parsing area status data."""
        response = StatusResponse()
        response.parseReply('a02="Office"')
        
        assert "02" in response.Areas
        assert response.Areas["02"] == "Office"

    def test_parse_reply_invalid_format(self):
        """Test parsing invalid data format."""
        response = StatusResponse()
        response.parseReply("invalid data")
        
        assert len(response.Zones) == 0
        assert len(response.Areas) == 0

    def test_parse_reply_missing_quotes(self):
        """Test parsing data with missing quotes."""
        response = StatusResponse()
        response.parseReply('z001=00Entry')
        
        assert len(response.Zones) == 0  # Should not parse without quotes