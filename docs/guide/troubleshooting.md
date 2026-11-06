# Troubleshooting

## Setup fails with "Failed to connect"

Home Assistant could not open the panel's remote programming port.

- Check the **Panel Hostname/IP Address** and **Panel Port** (default `8011`).
  The port must match **Remote Options → Network Programming Port** on the
  panel.
- Confirm Home Assistant can reach the panel: from the Home Assistant host,
  `nc -vz <panel-ip> 8011` should connect.
- DMP panels allow only one remote-programming session at a time. Close Dealer
  Admin, Remote Link, or another Home Assistant instance that is still
  connected, then try again.

## Setup fails with "Invalid authentication"

The panel rejected the **Remote Key**. Re-enter it exactly as programmed in
**Remote Options → Remote Key**; leave the field empty if the panel's key is
blank. If the key was changed on the panel after setup, Home Assistant will
ask you to re-authenticate from **Settings → Devices & Services**.

## Entities are "Unavailable"

The integration lost its connection to the panel. It logs one warning when the
connection drops and one when it is back, and reconnects automatically. If the
entities stay unavailable:

- Check the panel is powered and on the network.
- Check nothing else has taken the panel's single remote session (see above).
- Reload the integration from **Settings → Devices & Services → DMP → ⋮ →
  Reload**.

## Arming works but zone sensors never change

Zone sensors update from events the panel pushes to Home Assistant, so the
panel must be programmed to send them:

- **PC Log Reports → Net IP / Net Port** must point at the Home Assistant host
  and the integration's **Listener Port** (default `8001`).
- **PC Log Real-Time Status** must be `YES`, and **Zone Real-Time Status** must
  be enabled on each zone you want live updates for. Your dealer can enable
  these. See [Panel configuration](panel-configuration.md).
- The listener binds every interface on the Home Assistant host, so a
  multi-homed host works; make sure a firewall is not blocking the listener
  port.
- Press **Refresh Status** on the panel device to pull the current state on
  demand; if that updates the sensors, the push path is what is broken.

## "Unknown account number sending data" in the log

The panel is reporting with an account number different from the one entered
during setup. Compare **Communication → Account Number** on the panel with the
value in the integration (reconfigure the entry from **Settings → Devices &
Services → DMP → ⋮ → Reconfigure**).

## The alarm panel stays "Triggered"

After a burglary alarm the panel returns to its armed or disarmed state when
the panel reports the zone restored or the system is disarmed. Fire alarms
currently do not clear the triggered state until the integration is reloaded
or the panel is disarmed; this is tracked in
[issue #62](https://github.com/amattas/hass-dmp/issues/62).

## Collecting diagnostics

Open **Settings → Devices & Services → DMP → ⋮ → Download diagnostics**. The
file contains the entry configuration (with the remote key redacted), the
connection state, and the last status the panel reported. Attach it to a
[GitHub issue](https://github.com/amattas/hass-dmp/issues).

To get debug logs, add this to `configuration.yaml` and restart:

```yaml
logger:
  logs:
    custom_components.dmp: debug
    pydmp: debug
```
