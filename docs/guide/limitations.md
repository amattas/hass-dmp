# Supported devices and known limitations

## Supported panels

The integration talks to the panel through
[pydmp](https://amattas.github.io/pydmp/) over the panel's TCP/IP remote
programming port and receives events through the Serial 3 (PC Log Reports)
push protocol.

| Panel | Status |
|---|---|
| DMP XR150 | Tested; the panel the integration is developed against |
| DMP XR550 and other XR-series panels | Expected to work (same protocol); not extensively tested |
| DMP XT-series and older panels | Not supported |

The panel must be reachable over the local network. Cloud-only setups through
Virtual Keypad or SecureCom are not supported.

## Known limitations

- **Arm Away arms areas 01, 02, and 03.** The areas armed by Arm Away are not
  configurable yet
  ([issue #34](https://github.com/amattas/hass-dmp/issues/34)). Arm Home and
  Arm Night arm only the configured home area.
- **Arm Night reports as Armed Home.** The panel does not report an
  "instant" arming mode distinctly, so the entity shows `armed_home` after an
  Arm Night.
- **Fire alarms do not clear the triggered state**
  ([issue #62](https://github.com/amattas/hass-dmp/issues/62)). Burglary
  alarms clear when the zone restores or the panel is disarmed.
- **Zones are configured by hand.** The integration does not yet discover
  the panel or enumerate its zones and areas; add each zone in the config flow
  or the **Configure** options
  ([issue #52](https://github.com/amattas/hass-dmp/issues/52)).
- **Real-time zone updates need panel programming.** Without PC Log Real-Time
  Status and per-zone Zone Real-Time Status enabled, zone sensors only update
  at startup and on **Refresh status**.
- **One remote session per panel.** DMP panels allow a single remote
  programming connection. While Home Assistant is connected, Dealer Admin and
  Remote Link cannot connect, and vice versa.
- **No user codes.** Arming and disarming from Home Assistant do not require
  or send a user code; anyone with access to the entity can arm or disarm.
  Restrict the entity with Home Assistant users and dashboards accordingly.
- **Not a monitoring replacement.** The integration does not replace
  monitoring by a UL-certified monitoring center.
