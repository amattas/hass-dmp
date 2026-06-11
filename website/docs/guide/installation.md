---
sidebar_position: 1
---

# Installation

The integration implements a Home Assistant configuration flow, so setup is a
copy plus a few clicks.

## Before you start

The config flow asks for the panel's account number and remote key, and the
panel needs a few programming options set (PC Log Reports, per-zone real-time
status) for live updates. See [Panel configuration](panel-configuration.md)
for exactly where each value lives in panel programming.

## Install

1. Check out the repository and copy `custom_components/dmp` into your Home
   Assistant configuration directory:

   ```bash
   cp -r <REPO>/custom_components/dmp <HASS CONFIG>/custom_components/dmp
   ```

2. Restart Home Assistant.
3. Add the integration from **Settings → Devices & Services** by searching for
   **DMP**, and follow the config flow.

## Zone status prerequisites

For zone sensors to update in real time, **Zone Real-Time Status** must be
enabled in the zone information menu for each zone, and PC Log Reports must
point at Home Assistant — both covered in
[Panel configuration](panel-configuration.md).

Zone status is queried when the integration starts (restart Home Assistant
after adding new zones). The armed state is not queried at startup — it is
assumed disarmed.
