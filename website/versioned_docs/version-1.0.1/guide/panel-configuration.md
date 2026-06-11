---
sidebar_position: 2
---

# Panel configuration

The config flow asks for a few values that live in the panel's programming.
All section and option names below come from the **XR Series Programming Guide
(LT-1232)**; these settings are changed in panel programming via a keypad or
Remote Link — if you don't program your own panel, your dealer can set them
in a few minutes.

## Account number

Found in **Communication → Account Number** (LT-1232 p. 7). It's a 1–5 digit
number (valid range 1–65535, factory default `12345`) that identifies which
panel is sending a message — the integration uses it when talking to the
panel. On the panel side, accounts of four digits or less are entered
*without* leading zeros.

Enter the same account number in the config flow.

## Remote key

Found in **Remote Options → Remote Key** (LT-1232 p. 25). This is a code of up
to 16 characters that the panel requires before allowing any remote function —
it's effectively the API credential for the integration. Panels ship from the
factory with the key **blank**; the current key displays as asterisks at the
keypad.

- If your panel has a remote key set, enter it in the config flow.
- If it's blank, leave the config-flow field empty (or set a key on the panel
  first — recommended).

While you're in **Remote Options**, also confirm:

| Option | Setting | Why |
|---|---|---|
| **Remote Disarm** | `YES` (factory default) | Required for Home Assistant to disarm the panel |
| **Allow Network Remote** | `YES` (factory default) | Allows remote commands over the network at all |
| **Network Programming Port** | match the integration's **remote port** | Panel factory default is `2001`; the integration defaults to `8011` — set them to the same value |

## Real-time status (PC Log Reports)

Live zone/arming updates arrive because the panel *pushes* events to Home
Assistant over Ethernet. Two pieces of programming make that happen:

### 1. PC Log Reports (LT-1232 p. 49–50)

The panel-wide push configuration, in **PC Log Reports**:

| Option | Setting |
|---|---|
| Communication Type | `NET` |
| **Net IP Address** | your Home Assistant host's IP — entered as all 12 digits without periods (e.g. `192.168.1.50` → `192168001050`) |
| **Net Port** | the integration's **listen port** (default `8001`) |
| Arm and Disarm Reports | `YES` |
| Zone Reports | `YES` |
| PC Log Real-Time Status | `YES` |

Notes from the guide: the PC Log address must not be the same as the address
in Communication; PC Log Reports have the lowest priority of panel reports,
and if the network connection drops, the panel keeps retrying and sends the
reports once it's reestablished.

### 2. Zone Real-Time Status, per zone (LT-1232 p. 64)

Each zone you want live updates from needs **Zone Information → Zone
Real-Time Status** set to `YES` (factory default is `NO`). This is what allows
reports like *Door Open / Door Closed with zone number* to be sent through PC
Log reporting — without it, that zone's sensors only update on a manual
refresh.

## Quick reference: config flow ↔ panel

| Config-flow field | Panel programming location |
|---|---|
| Panel IP | the panel's network address (Network Options) |
| Remote port (default `8011`) | Remote Options → Network Programming Port |
| Listen port (default `8001`) | PC Log Reports → Net Port (panel pushes here) |
| Account number | Communication → Account Number |
| Remote key | Remote Options → Remote Key |
