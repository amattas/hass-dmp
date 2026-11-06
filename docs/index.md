# DMP for Home Assistant

Integrate your DMP XR-series alarm panel with Home Assistant: arming control,
zone monitoring with per-zone entities, and real-time status via the panel's
Serial 3 push protocol (powered by [pydmp](https://amattas.github.io/pydmp/)).

!!! warning

    This integration is not designed to replace monitoring by a UL-certified
    monitoring center; it exists to make the panel's supervised sensors easy to
    integrate with other platforms.

## Guides

- [Installation](guide/installation.md) — install through HACS (or manually),
  set it up via the config flow, and remove it again.
- [Panel configuration](guide/panel-configuration.md) — where each config-flow
  value lives in panel programming.
- [Features](guide/features.md) — the arming model, zone entities, status
  sensors, and how data is updated.
- [Use cases and automations](guide/automations.md) — what you can do with
  the integration, with ready-to-paste automation examples.
- [Supported devices and limitations](guide/limitations.md) — which panels
  work and what the integration does not do yet.
- [Troubleshooting](guide/troubleshooting.md) — common problems, diagnostics,
  and debug logging.

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
