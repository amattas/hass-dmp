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

Each configured zone becomes a device (linked to the panel device) with
several entities. Entity names are prefixed with the zone name.

Shown based on device type:

| Entity | Name | Shown for |
|---|---|---|
| Open/close (binary sensor) | *Zone name* | Door, window and motion zones, and zones with no device type |
| Battery (binary sensor, diagnostic) | *Zone name* Battery | Battery-powered zones |
| Alarm (binary sensor) | *Zone name* Alarm | Door, window, motion and glass break zones |

Shown for every zone:

| Entity | Name | Notes |
|---|---|---|
| Trouble (binary sensor, diagnostic) | *Zone name* Trouble | Disabled by default |
| Status (sensor, diagnostic) | *Zone name* Status | Disabled by default. One of `ready`, `open`, `trouble`, `bypass`, `low_battery`, `alarm` (shown translated in the UI) |
| Bypass (switch, configuration) | *Zone name* Bypass | Turn on to bypass the zone, off to restore it |

Enable the disabled entities from the zone's device page if you need them.

!!! warning "Status sensor values changed"
    The Status sensor is now an enum sensor whose state is a lowercase key
    (`ready`, `low_battery`, ...). Automations or templates that compared it
    with the old values (`Ready`, `Low Battery`, ...) must be updated.

The panel device exposes the **Arming control** alarm panel and a
**Refresh status** button that manually queries the panel for current zone
status and armed state; the button's attributes hold a consolidated overview
of every area and zone from the last query.

## How data is updated

- **Real-time events:** the panel pushes Serial 3 events (zone open/close,
  alarms, troubles, bypasses, arming and disarming) to the integration's
  listener port as they happen, so entities update without polling.
- **Full status:** the complete zone and armed state is queried from the
  panel at startup and whenever you press **Refresh status** (and after a
  disarm, since the panel does not report the zones it un-bypasses).
- **Keep-alive:** a keep-alive is sent to the panel every 10 seconds to hold
  the connection open.
