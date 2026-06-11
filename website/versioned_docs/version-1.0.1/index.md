---
slug: /
sidebar_position: 1
sidebar_label: Overview
title: DMP for Home Assistant
---

import Link from '@docusaurus/Link';

Integrate your DMP XR-series alarm panel with Home Assistant: arming control,
zone monitoring with per-zone entities, and real-time status via the panel's
Serial 3 push protocol (powered by [pydmp](https://amattas.github.io/pydmp/)).

:::caution

This integration is in **beta** — things may break or become unreliable. It is
not designed to replace monitoring by a UL-certified monitoring center; it
exists to make the panel's supervised sensors easy to integrate with other
platforms.

:::

<div className="pd-cards">
  <Link className="pd-card" to="/guide/installation">
    <span className="pd-card-kicker">Guide</span>
    <span className="pd-card-title">Installation</span>
    <span className="pd-card-desc">Install the custom component and set it up via the config flow.</span>
  </Link>
  <Link className="pd-card" to="/guide/features">
    <span className="pd-card-kicker">Guide</span>
    <span className="pd-card-title">Features</span>
    <span className="pd-card-desc">The arming model, zone entities, and status sensors.</span>
  </Link>
</div>

## Requirements

- A DMP XR-series panel reachable over TCP/IP
- "Zone Real-Time Status" enabled per zone (your dealer can enable this) for
  live sensor updates

## Credit

Thank you to
[baddienatalie](https://community.home-assistant.io/u/baddienatalie/summary) in
the Home Assistant community, whose
[first pass at this integration](https://git.natnat.xyz/hass-dmp-integration/dmp)
was the base this integration was forked from.
