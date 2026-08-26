# Architecture

## The big picture

```text
                 ┌───────────────────────────┐
                 │     Frappe Custom App     │
                 │                           │
                 │ Media                     │
                 │ Displays                  │
                 │ Groups                    │
                 │ Playlists                 │
                 │ Campaigns                 │
                 │ Schedules                 │
                 │ Assignments               │
                 │ Device Lifecycle          │
                 │ Versioning                │
                 │ Monitoring         [M3]   │
                 └─────────────┬─────────────┘
                               │
                  Versioned API + Asset Manifest
                               │
                       Realtime Notification       [M3]
                               │
                 ┌─────────────▼─────────────┐
                 │    Tauri/Rust Client      │
                 │         (separate repo)    │
                 └───────────────────────────┘
```

`[M3]` = not built yet, targeted for Milestone 3+. Frappe is the source of
truth; the client is meant to be an autonomous, offline-capable runtime that
syncs against a versioned API — none of that changes as milestones are added,
only how much of the right-hand side of the diagram exists.

## Layering

```text
Frappe DocTypes
    ↓
Service layer
    ↓
Versioned signage API (digital_signage/api/v1/*.py)
    ↓
Tauri client
```

Business logic lives in `services/*.py`, not in DocType controllers — a
controller's `validate()`/`on_update()` is a one-line delegate to a service
function. This is deliberate: services are plain Python functions that take a
`doc` and don't require a live desk session to unit test, and it keeps the
DocTypes free to evolve without forcing a client rewrite once there is a
client talking to a stable API surface — which, as of Milestone 2, there
actually is.

## Module layout

```text
digital_signage/
├── digital_signage/
│   ├── api/
│   │   ├── internal.py          # desk-only (preview/generate/revoke)
│   │   └── v1/                  # device-facing (Milestone 2)
│   │       ├── __init__.py          # device_api error-handling decorator
│   │       ├── device.py            # register
│   │       ├── session.py           # session.create
│   │       ├── sync.py              # sync.get
│   │       ├── heartbeat.py         # heartbeat.post
│   │       └── assets.py            # assets.download
│   ├── core/
│   │   ├── constants.py         # shared enums/strings
│   │   ├── exceptions.py        # SignageError and subclasses (desk-side)
│   │   ├── device_errors.py     # DeviceApiError and subclasses (device-side)
│   │   ├── device_auth.py       # credential -> Display authentication
│   │   ├── permissions.py       # placeholder — no row-level perms yet
│   │   └── versioning.py        # Signage State Version bump primitive
│   ├── services/
│   │   ├── media_service.py         # hashing, lifecycle, deletion guard
│   │   ├── playlist_service.py      # explicit ordering, image durations
│   │   ├── campaign_service.py      # playlist/priority validation, revision
│   │   ├── schedule_service.py      # date/time/recurrence validation
│   │   ├── assignment_service.py    # exactly-one-target validation
│   │   ├── state_service.py         # Phase C: the effective-state engine
│   │   ├── device_service.py        # pairing, registration, revocation
│   │   ├── heartbeat_service.py     # device playback-status reporting
│   │   ├── asset_service.py         # manifest + authorized download
│   │   └── sync_service.py          # state_service + assets, sync bookkeeping
│   ├── digital_signage/doctype/     # the 13 DocTypes (see DOMAIN_MODEL.md)
│   └── tests/                       # cross-cutting tests + factories
└── docs/
```

## What actually exists today (through Milestone 2)

- The full domain model, including device identity (see `DOMAIN_MODEL.md`).
- The effective-state engine (Milestone 1, unchanged since): given a display
  and a point in time, computes exactly one deterministic answer for "what
  should this display be showing" (`SCHEDULING_AND_PRIORITY.md`), tracking a
  per-display `server_version` that increments whenever something relevant
  changes.
- Device pairing, credentials, and revocation (`DEVICE_LIFECYCLE.md`) — a
  device is never a Frappe `User`; auth is entirely custom
  (`core/device_auth.py`), separate from the desk's role-based permissions.
- The full `digital_signage.api.v1.*` device-facing API — `register`,
  `session.create`, `sync.get`, `heartbeat.post`, `assets.download`
  (`API_V1.md`) — verified working end-to-end over real HTTP, not just unit
  tests.
- Asset manifest + authorized, hash-verifiable download (`ASSET_MANAGEMENT.md`).
- `digital_signage.api.internal.*` desk-only methods:
  `preview_effective_state` (Milestone 1), `generate_pairing_code`,
  `revoke_device` (Milestone 2) — all gated to `System Manager`/`Signage
  Administrator`.

## What's explicitly deferred (Milestone 3+)

- Realtime change notifications (`signage.state_changed` etc.) — the version
  counter this would be built on already exists and is exercised by tests,
  but nothing publishes a realtime event from it yet; clients poll for now
  (`SYNC_PROTOCOL.md`).
- Online/offline connectivity as a computed property from `last_heartbeat`
  (the field is written now, by `heartbeat_service.py` — nothing reads it
  back into a status yet).
- Background lifecycle/cleanup jobs (stale heartbeats, deferred invalidation,
  temp file cleanup, retired-media cleanup).
- Delta sync (full sync only today — deliberate, see `SYNC_PROTOCOL.md`).
- The security hardening items listed at the end of `SECURITY.md`.

Nothing above was stubbed out ahead of time — no empty `notification_service.py`.
It gets created when the milestone that needs it actually builds it, so an
empty file never silently drifts out of sync with what the spec says it
should contain.
