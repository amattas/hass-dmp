# DMP Integration for Home Assistant

Integrate your DMP XR series alarn panel with Home Assistant. This integration provides arming control along with zone monitoring for doors and windows. 

## Important Info
This integration is currently is in BETA. This means things may break or become unreliable. **Please Note: This integration is not designed to replace monitoring of your DMP panel by a UL certified monitoring center, and is solely designed to increase the ease of integrating the supervised sensors with other platforms**

## Currently Supported Features

### Arming and Disarming
This integration implements a simplified arming/disarming model from the panel's area model to a simple Arm Home/Arm Away model. This aligns better to how these panels are typically deployed in residential settings and also helps integrate better with Home Assistants model. It also facilitiates surfacing the alarm panel to other integrations like HomeKit. There are future plans to support arming with custom bypass.

### Zone Monitoring
This integration provides multiple binary sensors for each zone provided by the panel. These sensors include:

* Window Open/Close
* Door Open/Close
* Alarm
* Trouble
* Low Battery 
* Bypass

It's important to note that in order for these sensor to be updated you must have "Zone Real-Time Status" enabled in the zone information menu for each zone you want real-time status for. Your dealer should be able to easily enable this for you. 

Additionally the integration provides a consolidated status sensor that provides a high level overview of each zone. One point to note is all of these sensors are assumed in a good state when enabling the integration, this is due to the fact that we are unaware of a way to request the status of each zone at initialization time.

## Setup Instructions
This integration implements a Home Assistant configuration flow to simplify setup. To install, simply checkout this repo and copy `<REPO>/custom_components/dmp` to `<HASS INSTALL>/config/custom_components/dmp` and restart Home Assistant. Once installed the integration can be added from the control panel by searching for DMP.

## Planned Updates
* Additional zone type support
* Custom bypass arming
* Bypassing individual zones
* Validate configuration inputs
* Simplification of platform code
* Separation of panel specific code
* Unit testing

## Credit
Thank you to [baddienatalie](https://community.home-assistant.io/u/baddienatalie/summary) in the Home Assistant community. They made the first [pass at this integration](https://git.natnat.xyz/hass-dmp-integration/dmp), which was forked and used as the base for this integration. This was my first Home Assistant integration and I have learned a lot along the way. There was a lot of trial and error as I worked through the documentation, and as suchthere is a lot to cleanup and optimize now. 