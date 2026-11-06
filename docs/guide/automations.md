# Use cases and automation examples

## What people use this integration for

- **One place for the whole house.** Arm and disarm the panel from the Home
  Assistant dashboard, the companion app, or HomeKit alongside locks, lights,
  and cameras.
- **Reuse the panel's supervised sensors.** Door, window, motion, glass-break,
  and smoke zones become ordinary Home Assistant binary sensors, so they can
  drive lighting, climate, and presence automations without extra hardware.
- **Arm on leaving, disarm on arrival** with Home Assistant presence detection.
- **Get notified** when a zone goes into alarm, trouble, or low battery, or
  when the panel is left disarmed at night.
- **Bypass a zone** from Home Assistant (for example a sensor on a door that
  is propped open while you work outside).

## Examples

Replace the entity IDs with your own.

### Notify when the panel is armed or disarmed

```yaml
automation:
  - alias: "Alarm state notification"
    triggers:
      - trigger: state
        entity_id: alarm_control_panel.dmp_xr150_arming
    actions:
      - action: notify.mobile_app_phone
        data:
          message: >
            Alarm is now {{ states('alarm_control_panel.dmp_xr150_arming') }}
```

### Arm away when everyone leaves

```yaml
automation:
  - alias: "Arm away when the house is empty"
    triggers:
      - trigger: state
        entity_id: zone.home
        to: "0"
    conditions:
      - condition: state
        entity_id: alarm_control_panel.dmp_xr150_arming
        state: disarmed
    actions:
      - action: alarm_control_panel.alarm_arm_away
        target:
          entity_id: alarm_control_panel.dmp_xr150_arming
```

### Turn on the hall light when the front door opens at night

```yaml
automation:
  - alias: "Front door light"
    triggers:
      - trigger: state
        entity_id: binary_sensor.front_door_open_close
        to: "on"
    conditions:
      - condition: sun
        after: sunset
    actions:
      - action: light.turn_on
        target:
          entity_id: light.hallway
```

### Alert on a zone alarm or trouble

```yaml
automation:
  - alias: "Zone alarm or trouble"
    triggers:
      - trigger: state
        entity_id:
          - binary_sensor.front_door_alarm
          - binary_sensor.front_door_trouble
        to: "on"
    actions:
      - action: notify.mobile_app_phone
        data:
          title: "DMP panel"
          message: "{{ trigger.to_state.name }} is on"
```

### Bypass a zone while the garage is in use

```yaml
automation:
  - alias: "Bypass garage door while the workbench light is on"
    triggers:
      - trigger: state
        entity_id: light.workbench
    actions:
      - action: >
          {{ 'switch.turn_on' if trigger.to_state.state == 'on' else 'switch.turn_off' }}
        target:
          entity_id: switch.garage_door_bypass
```

### Refresh the panel status every hour

The panel pushes changes in real time, so this is only useful as a safety net
on panels where real-time status is not enabled for every zone.

```yaml
automation:
  - alias: "Hourly DMP status refresh"
    triggers:
      - trigger: time_pattern
        minutes: 0
    actions:
      - action: button.press
        target:
          entity_id: button.dmp_xr150_refresh_status
```
