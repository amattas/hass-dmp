"""Base entities shared by the DMP platforms."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from pydmp.exceptions import DMPError

from .const import (
    CONF_PANEL_NAME,
    CONF_ZONE_CLASS,
    CONF_ZONE_NAME,
    CONF_ZONE_NUMBER,
    DOMAIN,
)

if TYPE_CHECKING:
    from pydmp import Zone

    from . import DMPListener, DMPPanel

MANUFACTURER = "Digital Monitoring Products"
PANEL_MODEL = "XR series"

# Device model shown for a zone, by its configured zone class.
ZONE_CLASS_MODELS = {
    "battery_door": "Battery door",
    "battery_glassbreak": "Battery glass break",
    "battery_motion": "Battery motion",
    "battery_siren": "Battery siren",
    "battery_smoke": "Battery smoke",
    "battery_window": "Battery window",
    "wired_door": "Wired door",
    "wired_glassbreak": "Wired glass break",
    "wired_motion": "Wired motion",
    "wired_siren": "Wired siren",
    "wired_smoke": "Wired smoke",
    "wired_window": "Wired window",
}


def panel_identifier(account: str) -> tuple[str, str]:
    """Return the device registry identifier of a panel."""
    return (DOMAIN, f"dmp-{account}-panel")


def zone_identifier(account: str, number: str) -> tuple[str, str]:
    """Return the device registry identifier of a panel zone."""
    return (DOMAIN, f"dmp-{account}-zone-{number}")


class DMPEntity(Entity):
    """An entity whose state is pushed by the DMP listener."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        listener: DMPListener,
        panel: DMPPanel,
        account: str,
        config: dict[str, Any],
    ) -> None:
        self._listener = listener
        self._panel = panel
        self._account = account
        self._config = config

    async def async_added_to_hass(self) -> None:
        """Start from the panel's current state and follow its updates."""
        await super().async_added_to_hass()
        self._update_from_panel()
        self._listener.register_callback(self._async_listener_update)

    async def async_will_remove_from_hass(self) -> None:
        """Stop following listener updates."""
        await super().async_will_remove_from_hass()
        self._listener.remove_callback(self._async_listener_update)

    @callback
    def _update_from_panel(self) -> None:
        """Refresh cached entity state from the panel (override as needed)."""

    async def _async_listener_update(self) -> None:
        self._update_from_panel()
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return whether the panel connection is up."""
        return self._listener.connected

    async def _async_command(self, command: Callable[[], Awaitable[None]]) -> None:
        """Run a panel command, raising translated errors when it cannot run."""
        if not self._listener.connected:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="not_connected"
            )
        try:
            await command()
        except (DMPError, OSError, TimeoutError) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"error": str(err)},
            ) from err

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return when the panel last sent an event."""
        return {"last_contact": self._panel.getContactTime()}


class DMPPanelEntity(DMPEntity):
    """An entity belonging to the panel device."""

    def __init__(
        self,
        listener: DMPListener,
        panel: DMPPanel,
        account: str,
        config: dict[str, Any],
    ) -> None:
        super().__init__(listener, panel, account, config)
        self._attr_device_info = DeviceInfo(
            identifiers={panel_identifier(account)},
            name=config.get(CONF_PANEL_NAME),
            manufacturer=MANUFACTURER,
            model=PANEL_MODEL,
            serial_number=account,
        )


class DMPZoneEntity(DMPEntity):
    """An entity belonging to a zone device (config is the zone's config)."""

    def __init__(
        self,
        listener: DMPListener,
        panel: DMPPanel,
        account: str,
        config: dict[str, Any],
    ) -> None:
        super().__init__(listener, panel, account, config)
        self._number: str = config[CONF_ZONE_NUMBER]
        self._zone: Zone | None = panel.ensure_zone(self._number)
        self._attr_device_info = DeviceInfo(
            identifiers={zone_identifier(account, self._number)},
            name=config.get(CONF_ZONE_NAME),
            manufacturer=MANUFACTURER,
            model=ZONE_CLASS_MODELS.get(config.get(CONF_ZONE_CLASS, "")),
            # HA 2026.8 deprecated via_device for via_device_id (removal in 2027.8)
            via_device=panel_identifier(account),  # type: ignore[typeddict-unknown-key]
        )

    def _unique_id(self, suffix: str) -> str:
        return f"dmp-{self._account}-zone-{self._number}-{suffix}"
