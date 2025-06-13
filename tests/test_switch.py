"""Test switch module for DMP integration.

This module imports all test classes from their separate files.
"""
from .test_switch_dmp_zone_bypass_switch import TestDMPZoneBypassSwitch
from .test_switch_dmp_zone_bypass_switch_complete import TestDMPZoneBypassSwitchComplete
from .test_switch_async_setup_entry import TestSwitchAsyncSetupEntry

__all__ = [
    "TestDMPZoneBypassSwitch",
    "TestDMPZoneBypassSwitchComplete",
    "TestSwitchAsyncSetupEntry",
]