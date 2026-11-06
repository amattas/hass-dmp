[![Checks](https://github.com/amattas/hass-dmp/actions/workflows/checks.yml/badge.svg)](https://github.com/amattas/hass-dmp/actions/workflows/checks.yml) [![Docs](https://github.com/amattas/hass-dmp/actions/workflows/docs.yml/badge.svg)](https://amattas.github.io/hass-dmp/)

# DMP Integration for Home Assistant

Integrate your DMP XR series alarn panel with Home Assistant. This integration provides arming control along with zone monitoring. 

## Important Info
**Please Note: This integration is not designed to replace monitoring of your DMP panel by a UL certified monitoring center, and is solely designed to increase the ease of integrating the supervised sensors with other platforms.**

## Currently Supported Features

### Arming and Disarming
This integration implements a simplified arming/disarming model from the panel's area model to a simple Arm Home/Arm Away/Arm Night model. This aligns better to how these panels are typically deployed in residential settings and also helps integrate better with Home Assistants model. It also facilitiates surfacing the alarm panel to other integrations like HomeKit.

#### Arm Types
* Arm Home - arms the home area defined during platform configuration
* Arm Away - arms areas 01, 02, 03 - not currently configurable 
* Arm Night - arms the home area with the **instant** flag. This disables delay doors for exit and entry - alarm will trigger immediately if any zone is faulted. Shows as armed home from a status POV (haven't found a way to differentiate)

### Zone Monitoring
Each configured zone becomes a device with these entities:

___Shown based on device type:___
* Open/close (binary sensor, named after the zone) for door, window and motion zones
* Alarm (binary sensor) for door, window, motion and glass-break zones
* Battery (binary sensor) for battery-powered zones

___Shown for every zone:___
* Trouble (binary sensor, diagnostic, disabled by default)
* Status (enum sensor, diagnostic, disabled by default): `ready`, `open`, `trouble`, `bypass`, `low_battery` or `alarm`
* Bypass (switch)

The panel device has the arming control and a *Refresh status* button that queries the panel for the current armed state and zone status.

Zone sensors update in real time from events the panel pushes, which requires "Zone Real-Time Status" to be enabled in the zone information menu for each zone (your dealer can enable this). The armed state and zone status are also queried at startup and whenever *Refresh status* is pressed.

## Installation

### HACS (recommended)
1. In HACS open **⋮ → Custom repositories** and add `https://github.com/amattas/hass-dmp` with category **Integration**.
2. Search HACS for **DMP** and choose **Download**, then restart Home Assistant when prompted.
3. Go to **Settings → Devices & Services → Add integration**, search for **DMP**, and follow the configuration flow.

HACS offers updates automatically whenever a new release is published.

### Manual
Download the latest [release](https://github.com/amattas/hass-dmp/releases), copy `custom_components/dmp` to `<HASS CONFIG>/custom_components/dmp`, restart Home Assistant, and add the integration from **Settings → Devices & Services**.

Full setup, panel programming, troubleshooting and removal instructions are in the [documentation](https://amattas.github.io/hass-dmp/).

## Planned Updates
* Track status of each area individually and make the Arm Away areas configurable (#34)
* Discover the panel and enumerate its zones and areas automatically (#52)
* Separate fire alarm handling (#62)

## Credit
Thank you to [baddienatalie](https://community.home-assistant.io/u/baddienatalie/summary) in the Home Assistant community. They made the first [pass at this integration](https://git.natnat.xyz/hass-dmp-integration/dmp), which was forked and used as the base for this integration. This was my first Home Assistant integration and I have learned a lot along the way. There was a lot of trial and error as I worked through the documentation, and as suchthere is a lot to cleanup and optimize now. 