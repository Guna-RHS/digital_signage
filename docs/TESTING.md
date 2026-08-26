# Testing

## Running the suite

```bash
cd ~/rhs-bench
bench --site rhs.local set-config allow_tests true   # one-time; rhs.local defaults to false
bench --site rhs.local run-tests --app digital_signage
```

Each test runs inside a DB transaction that's rolled back afterward
(`FrappeTestCase`), so running the suite against the shared `rhs.local` site
(also used by `crm`/`rhs_leadgen`) never leaves data behind. 77 tests as of
Milestone 2 (50 from Milestone 1 + 27 new).

## Layout

- `digital_signage/tests/factories.py` — shared test-data builders
  (`make_media`, `make_playlist`, `make_campaign`, `make_schedule`,
  `make_display`, `make_display_group`, `make_assignment`, plus Milestone 2's
  `make_pairing_code`, `register_test_device`). Every test goes through these
  instead of hand-rolling `frappe.get_doc(...)` calls.
- `digital_signage/tests/test_*.py` — cross-cutting tests that don't belong to
  a single doctype:
  - Milestone 1 (Phase C): `test_schedule_evaluation.py`,
    `test_priority_resolution.py`, `test_affected_display_resolution.py`,
    `test_state_versioning.py`, `test_fallback.py`, `test_integration.py`.
  - Milestone 2 (Phase D/E): `test_device_registration.py`,
    `test_device_auth.py`, `test_heartbeat.py`, `test_sync.py`,
    `test_asset_download.py`, `test_device_idempotency.py`.
- `digital_signage/digital_signage/doctype/<name>/test_<name>.py` — Phase B
  validation tests co-located with the doctype they test (`test_media.py`,
  `test_playlist.py`, `test_campaign_assignment.py`). Standard Frappe
  convention, and where `bench new-app` already scaffolds an (empty) stub per
  doctype.

## What's covered

Every bullet from the spec's "Unit tests" list for Milestone 1: date windows,
time windows, day-of-week recurrence, overlapping schedules, priority, direct
vs. group, deterministic ties, inactive/expired campaigns, fallback,
affected-display resolution, state version changes.

Milestone 2 adds registration (success + every failure mode: unknown device,
wrong/expired/already-used/wrong-display pairing code, re-registration
revoking the prior credential), device auth (valid + every failure mode:
wrong secret, unknown credential, revoked credential, expired credential,
revoked display, disabled display, `last_used_at` bumping), heartbeat
(field updates, malformed-payload tolerance, no spurious version bumps),
sync (envelope correctness, asset manifest correctness, `last_sync_at`/
`last_sync_version` updates, repeat-safety), asset download (authorized
success with hash-verified bytes, unauthorized media rejected, unknown media
rejected), and idempotency (repeated heartbeat/sync create no duplicate
records, a reused pairing code fails cleanly on the second attempt).

**Not covered by the automated suite, but manually verified with real HTTP
`curl` calls during Milestone 2** (documented in `API_V1.md`/`SECURITY.md`):
the actual `{"message": ...}` response-wrapping behavior, real HTTP status
codes, that error responses never contain a traceback, and that a revoked
device is actually blocked end-to-end. Doing this as a manual pass rather
than HTTP-level automated tests was a deliberate scope choice for this
milestone (`bench run-tests` doesn't spin up a real web server) — a
Milestone 3+ candidate would be adding `pytest`+`requests`-based HTTP
integration tests, or Frappe's own API test-client pattern, so this pass
doesn't have to be repeated by hand each time.

**Still not covered** (Milestone 3+, no code exists to test): realtime
notification delivery, background job behavior (stale-heartbeat marking,
cleanup), delta sync.
