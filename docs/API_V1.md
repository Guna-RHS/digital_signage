# API v1 (device-facing)

All endpoints live under `digital_signage.api.v1.*`, called as standard
Frappe whitelisted methods: `/api/method/digital_signage.api.v1.<module>.<fn>`.
All are `allow_guest=True` — **a device is never a Frappe User**; auth is
purely `credential_identifier`/`credential_secret` (see `SECURITY.md` and
`core/device_auth.py`), checked inside each endpoint, not via Frappe's
session/login system.

**Response envelope**: like every Frappe whitelisted method, a successful
call's return value is wrapped as `{"message": <value>}` — confirmed by
actually calling every endpoint over real HTTP during this milestone's
verification, not assumed. A client should always read `response.message`.

**Errors**: this app's own shape, still inside `message` (see `SECURITY.md`/
`core/device_errors.py`):

```json
{"message": {"error": {"code": "AUTHENTICATION_FAILED", "message": "...", "retryable": false}}}
```

with the matching HTTP status code also set (401/403/404/400/500 — see the
table below). Never a raw traceback — verified by deliberately breaking calls
(bad secret, garbage media, missing params) during this milestone's manual
pass.

## `POST device.register`

Params: `device_identifier`, `pairing_code`, `client_version` (optional).

```json
{"credential_identifier": "CRED-...", "credential_secret": "..."}
```

The secret is shown **exactly once** — see `DEVICE_LIFECYCLE.md`.

Errors: `DEVICE_NOT_FOUND` (404, unknown `device_identifier`),
`VALIDATION_ERROR` (400, wrong/expired/already-used pairing code, or a code
that belongs to a different display).

## `POST session.create`

Params: `credential_identifier`, `credential_secret`.

```json
{"device_id": "DEV-...", "registration_status": "Registered", "server_version": 3}
```

A liveness/validity check, not a new token — see `DEVICE_LIFECYCLE.md`.

Errors: `AUTHENTICATION_FAILED` (401, unknown credential / wrong secret /
expired), `DEVICE_REVOKED` (403, credential or display revoked),
`DEVICE_DISABLED` (403, display `is_active = 0`).

## `GET sync.get`

Params: `credential_identifier`, `credential_secret`.

Returns the full envelope from `state_service.resolve_sync_state` plus an
`assets` array — see `SYNC_PROTOCOL.md`/`ASSET_MANAGEMENT.md` for the shape.
Also updates `Display.last_sync_at`/`last_sync_version` as a side effect.

**Important**: this is *not* a single pre-resolved winner. It's every
currently-eligible campaign (active display/assignment/campaign, direct or
via an active group) with *all* of its schedules, regardless of whether
each schedule's date/time window currently matches. The client is
responsible for evaluating schedules and resolving priority locally, offline,
at every schedule boundary — see `SCHEDULING_AND_PRIORITY.md`'s "Who resolves
this" section. (`state_service.resolve_effective_state`, which *does*
resolve to one winner, still exists — it backs the desk-only
`preview_effective_state` admin method, not this endpoint.)

Errors: same auth errors as `session.create`.

## `POST heartbeat.post`

Params: `credential_identifier`, `credential_secret`, plus any of
`client_version`, `current_campaign`, `current_playlist`, `current_media`,
`last_error` (all optional — anything else in the payload is accepted and
silently ignored, never validated strictly; spec: "Heartbeat failure must
never stop playback").

```json
{"ok": true}
```

Errors: same auth errors. Never anything else — a malformed payload cannot
fail this call (`heartbeat_service.py`).

## `GET assets.download`

Params: `credential_identifier`, `credential_secret`, `media` (a Media
document name, e.g. `MEDIA-00001` — from a `sync` response's `assets[].asset_id`).

Not a JSON response — streams the file directly (`Content-Disposition:
attachment`, correct `Content-Type`/`Content-Length`). See
`ASSET_MANAGEMENT.md` for the authorization rule and the in-memory-streaming
limitation.

Errors: same auth errors, plus `VALIDATION_ERROR` (400) if `media` isn't part
of this display's *current* resolved state — verified with `curl` against a
media name that exists but isn't assigned to the display.

## Error code → HTTP status

| code | status | retryable |
|---|---|---|
| `AUTHENTICATION_FAILED` | 401 | false |
| `DEVICE_NOT_FOUND` | 404 | false |
| `DEVICE_REVOKED` | 403 | false |
| `DEVICE_DISABLED` | 403 | false |
| `VALIDATION_ERROR` | 400 | false |
| `TEMPORARY_SERVER_ERROR` | 500 | true |

`CONTRACT_VERSION_UNSUPPORTED`/`SYNC_VERSION_INVALID` are reserved
(`core/constants.py`) but unused until delta sync exists.
