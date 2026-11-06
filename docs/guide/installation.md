# Installation

The integration installs through [HACS](https://hacs.xyz/) and is set up from
the Home Assistant UI with a configuration flow.

## Before you start

You need:

- A DMP XR-series panel reachable from Home Assistant over TCP/IP.
- The panel's **account number** and **remote key**, and a few panel
  programming options set (Remote Options, PC Log Reports, per-zone real-time
  status) for live updates. See [Panel configuration](panel-configuration.md)
  for exactly where each value lives in panel programming.
- [HACS](https://hacs.xyz/docs/use/download/download/) installed in Home
  Assistant (for the recommended install path).

## Install with HACS (recommended)

1. In Home Assistant open **HACS**, then the **⋮** menu (top right) →
   **Custom repositories**.
2. Add `https://github.com/amattas/hass-dmp` with category **Integration**.
3. Search HACS for **DMP** and choose **Download**.
4. Restart Home Assistant when HACS prompts you.
5. Go to **Settings → Devices & Services → Add integration**, search for
   **DMP**, and follow the config flow below.

HACS will offer updates to the integration whenever a new release is published.

## Install manually

1. Download the latest release from the
   [releases page](https://github.com/amattas/hass-dmp/releases) and copy
   `custom_components/dmp` into your Home Assistant configuration directory:

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

Zone status and the armed state of each area are queried when the integration
starts and whenever you press the **Refresh status** button; after that the
panel pushes changes in real time.

## Removal

1. Go to **Settings → Devices & Services → DMP**, open the **⋮** menu on the
   panel entry and choose **Delete**. This disconnects from the panel and
   removes the panel and zone devices and all their entities.
2. If you installed with HACS: open **HACS**, find **DMP**, and choose
   **Remove**. If you installed manually, delete
   `<HASS CONFIG>/custom_components/dmp`.
3. Restart Home Assistant.

Removing the integration does not change anything on the panel itself. If you
no longer want the panel to send events to Home Assistant, clear the PC Log
Reports network settings described in
[Panel configuration](panel-configuration.md).
