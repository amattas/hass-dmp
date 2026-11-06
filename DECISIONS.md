# Decisions

Project-specific decisions for hass-dmp. Fleet-wide standards live in
mattas-net/standards.

## 2026-11-05 — Quality-scale uplift (dev/quality-scale)

- **pydmp changes are in scope.** Platinum `strict-typing` needs pydmp to ship
  a `py.typed` marker, and the reauth flow needs `DMPAuthenticationError` raised
  from `connect()`. Both land in pydmp 1.2.0; hass-dmp pins `pydmp==1.2.0`.
- **One `DMPStatusServer` per config entry.** Each entry owns its own status
  server on its own listen port, held in `ConfigEntry.runtime_data`. The config
  flow rejects a listen port already used by another entry. A shared server
  keyed by account number was rejected as extra machinery for a rare setup.
- **Single PR.** The whole uplift ships as one PR with ordered commits and one
  release (hass-dmp 1.1.0), rather than phased PRs.
- **Out of scope for this PR** (handled with the #52 dynamic-device work):
  `discovery`, `discovery-update-info`, `dynamic-devices`, `stale-devices`,
  `repair-issues`. These stay `todo`, not `exempt`, so the manifest claims
  `silver` until that follow-up. #62 (fire alarm) is also deferred.
- **Exemptions and why:** `action-setup`/`docs-actions` (no service actions),
  `appropriate-polling` (push integration), `docs-conditions`/`docs-triggers`
  (none provided), `inject-websession` (raw TCP, no HTTP).
