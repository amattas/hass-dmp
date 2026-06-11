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
   **DMP**, and follow the config flow below.

## The config flow

### Step 1 — DMP Panel Configuration

| Field | Default | What to enter |
|---|---|---|
| Panel Name | `DMP XR150` | A friendly name for the device in Home Assistant |
| Panel Hostname/IP Address | `192.168.1.2` | The panel's network address |
| Panel Port | `8011` | The panel's **Network Programming Port** (Remote Options) — set them to match |
| Listener Port | `8001` | The port Home Assistant listens on for panel events — point the panel's **PC Log Reports → Net Port** here |
| Account Number | — | The panel's account number (Communication → Account Number) |
| Panel Key | — | The panel's **Remote Key** (Remote Options); leave empty if the panel's key is blank |

### Step 2 — DMP Arming Configuration

| Field | Default | What to enter |
|---|---|---|
| Home Zone | `01` | The area armed by **Arm Home** / **Arm Night** (digits only) |
| Away Zone | `02` | Shown for reference — **Arm Away** arms areas 01–03 |

On most panels area `01` is the perimeter (use it for home arming) and
`02`/`03` are interior areas. Arming home arms only the area you specify;
disarming and arming away affect all areas.

### Step 3 — DMP Zone Configuration

Add each panel zone you want entities for — the step repeats while
**"Add another zone?"** is checked:

| Field | What to enter |
|---|---|
| Zone Name | The entity name, e.g. `Front Door` |
| Zone Number | The zone number as programmed in the panel (digits only) |
| Zone Device Class | Pick the device type — Door, Window, Motion Detector, Glass Break Detector, Siren, or Smoke Detector (each in wired or battery-powered variants). This controls which entities the zone gets. |

### Adding or removing zones later

Open the integration's **Configure** option (Settings → Devices & Services →
DMP → Configure): the **Manage Zones** screen lets you uncheck existing zones
to remove them or add a new one — no reinstall needed.

## Zone status prerequisites

For zone sensors to update in real time, **Zone Real-Time Status** must be
enabled in the zone information menu for each zone, and PC Log Reports must
point at Home Assistant — both covered in
[Panel configuration](panel-configuration.md).

Zone status is queried when the integration starts (restart Home Assistant
after adding new zones). The armed state is not queried at startup — it is
assumed disarmed.
