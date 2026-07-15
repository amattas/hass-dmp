# DMP for Home Assistant

Integrate your DMP XR-series alarm panel with Home Assistant: arming control,
zone monitoring with per-zone entities, and real-time status via the panel's
Serial 3 push protocol (powered by [pydmp](https://amattas.github.io/pydmp/)).

!!! warning

    This integration is not designed to replace monitoring by a UL-certified
    monitoring center; it exists to make the panel's supervised sensors easy to
    integrate with other platforms.

## Guides

- [Installation](guide/installation.md) — install the custom component and set
  it up via the config flow.
- [Panel configuration](guide/panel-configuration.md) — where each config-flow
  value lives in panel programming.
- [Features](guide/features.md) — the arming model, zone entities, and status
  sensors.

## Requirements

- A DMP XR-series panel reachable over TCP/IP
- "Zone Real-Time Status" enabled per zone (your dealer can enable this) for
  live sensor updates

## Credit

Thank you to
[baddienatalie](https://community.home-assistant.io/u/baddienatalie/summary) in
the Home Assistant community, whose
[first pass at this integration](https://git.natnat.xyz/hass-dmp-integration/dmp)
was the base this integration was forked from.
