---
sidebar_position: 1
---

# Installation

The integration implements a Home Assistant configuration flow, so setup is a
copy plus a few clicks.

1. Check out the repository and copy `custom_components/dmp` into your Home
   Assistant configuration directory:

   ```bash
   cp -r <REPO>/custom_components/dmp <HASS CONFIG>/custom_components/dmp
   ```

2. Restart Home Assistant.
3. Add the integration from **Settings → Devices & Services** by searching for
   **DMP**, and follow the config flow.

## Zone status prerequisites

For zone sensors to update in real time, **"Zone Real-Time Status"** must be
enabled in the zone information menu for each zone — your dealer can enable
this for you.

Zone status is queried when the integration starts (restart Home Assistant
after adding new zones). The armed state is not queried at startup — it is
assumed disarmed.
