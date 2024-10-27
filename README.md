# DMP Integration for Home Assistant

Integrate your DMP XR series alarn panel with Home Assistant. This integration provides arming control along with zone monitoring. 

## Important Info
This integration is currently is in BETA. This means things may break or become unreliable. **Please Note: This integration is not designed to replace monitoring of your DMP panel by a UL certified monitoring center, and is solely designed to increase the ease of integrating the supervised sensors with other platforms**

## Currently Supported Features

### Arming and Disarming
This integration implements a simplified arming/disarming model from the panel's area model to a simple Arm Home/Arm Away/Arm Night model. This aligns better to how these panels are typically deployed in residential settings and also helps integrate better with Home Assistants model. It also facilitiates surfacing the alarm panel to other integrations like HomeKit.

#### Arm Types
* Arm Home - arms the home area defined during platform configuration
* Arm Away - arms areas 01, 02, 03 - not currently configurable 
* Arm Night - arms the home area with the **instant** flag. This disables delay doors for exit and entry - alarm will trigger immediately if any zone is faulted. Shows as armed home from a status POV (haven't found a way to differentiate)

### Zone Monitoring
This integration provides multiple entities for each zone provided by the panel. 

___Entities shown based on device type:___
* Window Open/Close (binary sensor)
* Door Open/Close (binary sensor)
* Alarm (binary sensor)
* Trouble (binary sensor)
* Low Battery (binary sensor)

___Entities shown regardless of device type:___
* Status (sensor - rollup of binary sensors for faults)
* Bypass (switch - allow for enable/disable of bypass for each zone)

The alarm panel itself has a *Refresh Status* button which will manually query the panel for current zone status. 

It's important to note that in order for these sensor to be updated you must have "Zone Real-Time Status" enabled in the zone information menu for each zone you want real-time status for. Your dealer should be able to easily enable this for you. 

Additionally the integration provides a consolidated status sensor that provides a high level overview of each zone. Zone status will be queried when the integration starts (may need to restart after adding new zones to query status). The current armed state is not queried - that is assumed to be disarmed on startup. 

## Setup Instructions
This integration implements a Home Assistant configuration flow to simplify setup. To install, simply checkout this repo and copy `<REPO>/custom_components/dmp` to `<HASS INSTALL>/config/custom_components/dmp` and restart Home Assistant. Once installed the integration can be added from the control panel by searching for DMP.

## Planned Updates
* Track status of each area individually, support more than areas 01, 02 and 03
* Validate configuration inputs
* Simplification of platform code
* Separation of panel specific listener code
* Unit testing
* Dynamic discovery of zones/areas

## Credit
Thank you to [baddienatalie](https://community.home-assistant.io/u/baddienatalie/summary) in the Home Assistant community. They made the first [pass at this integration](https://git.natnat.xyz/hass-dmp-integration/dmp), which was forked and used as the base for this integration. This was my first Home Assistant integration and I have learned a lot along the way. There was a lot of trial and error as I worked through the documentation, and as suchthere is a lot to cleanup and optimize now. 