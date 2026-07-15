# Features

## Arming and disarming

The integration maps the panel's area model onto Home Assistant's simpler
Arm Home / Arm Away / Arm Night model — a better fit for residential
deployments, and it lets the panel surface cleanly to other integrations like
HomeKit.

| Arm type | Behavior |
|---|---|
| **Arm Home** | Arms the home area defined during configuration |
| **Arm Away** | Arms areas 01, 02, 03 (not currently configurable) |
| **Arm Night** | Arms the home area with the **instant** flag — delay doors are disabled, so any faulted zone triggers immediately. Reports as armed-home in status. |

## Zone monitoring

Each panel zone gets multiple entities.

Shown based on device type:

- Window open/close (binary sensor)
- Door open/close (binary sensor)
- Alarm (binary sensor)
- Trouble (binary sensor)
- Low battery (binary sensor)

Shown for every zone:

- Status (sensor — rollup of the binary sensors for faults)
- Bypass (switch — enable/disable bypass per zone)

The alarm panel device also exposes a **Refresh Status** button that manually
queries the panel for current zone status, and the integration provides a
consolidated status sensor with a high-level overview of every zone.
