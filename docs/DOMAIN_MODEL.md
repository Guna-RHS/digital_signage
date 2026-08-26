# Domain Model

All 13 DocTypes below live in the `Digital Signage` module. They were
generated programmatically (11 from `digital_signage/setup/bootstrap.py` in
Milestone 1, 2 more — Device Pairing Code, Device Credential — from
`digital_signage/setup/bootstrap_device.py` in Milestone 2, both run once via
`bench --site rhs.local execute digital_signage.setup.<module>.run`) rather
than hand-built through the desk, so those files are the definitive record of
field choices — this doc explains the *why*, the `.json` files are the *what*.

Standard Frappe metadata fields (`name`, `creation`, `modified`, `owner`,
`modified_by`) are not repeated per doctype below — every doctype gets them
for free, so the spec's suggested `created_on`/`modified_on` fields were
deliberately not duplicated.

## Media

`title, media_type (Image/Video), file (Attach), mime_type, file_size, sha256,
asset_version, is_active, lifecycle_status`

- Autoname: `format:MEDIA-{#####}`.
- `media_service.py` computes `sha256`/`file_size`/`mime_type` from the
  attached file's actual bytes on every save, and bumps `asset_version` when
  the hash changes on an existing record — content, not filename, is the
  identity.
- Lifecycle: `Uploaded → Validated → Active → Retired`, enforced as a strict
  forward-only state machine (Retired is reachable from anywhere, never left).
  Only `Active` media is served by `resolve_effective_state`.
- Deletion is blocked unless `lifecycle_status = Retired` **and** no
  `Playlist Item` still references it (`media_service.guard_deletion`,
  called from `on_trash`) — matches "do not physically delete media
  immediately when active client states may still reference it."

## Display

`display_name, device_identifier (unique), is_active, registration_status
(Pending/Registered/Revoked), client_version, last_seen, last_heartbeat,
last_sync_at, last_sync_version, current_campaign, current_playlist,
current_media, last_error`

- Autoname: `field:device_identifier` — the human-legible primary key is the
  identifier a real device would present, since it must be unique anyway.
- Connectivity (Online/Offline/Unknown) is *never* a stored field — it's
  always computed from `last_heartbeat` recency. In Milestone 1 nothing
  writes `last_heartbeat` yet (no heartbeat endpoint exists), so it always
  reads Unknown; the field and the "compute, don't store" rule are both in
  place ready for Milestone 2.
- Saving a Display fires its own version bump (`Display.on_update` →
  `state_service.record_change`) — a display's own `is_active`/
  `registration_status` are themselves inputs to its effective state.

## Display Group / Display Group Member

`Display Group`: `group_name (unique), is_active, members (Table)`
`Display Group Member` (child, no fields beyond): `display (Link)`

- Autoname: `field:group_name`.
- Membership lives only in the child table — nothing else duplicates it.
  `state_service._group_member_displays` is the one place that reads it.

## Playlist / Playlist Item

`Playlist`: `title, description, is_active, revision, items (Table)`
`Playlist Item` (child): `media (Link), sort_order, image_duration_seconds, enabled`

- Autoname: `format:PL-{#####}`.
- `playlist_service.py` requires every item to have an explicit, unique
  `sort_order` within the playlist (never relies on child-table row order —
  the spec is explicit about this), and requires a positive
  `image_duration_seconds` for any item whose media is an Image (Video items
  don't need one — natural duration is used, per spec).
- `revision` increments on every save. It exists specifically to feed the
  Campaign tie-break chain (see `SCHEDULING_AND_PRIORITY.md`) — a Campaign
  also has its own `revision` for the same reason, incremented independently.

## Campaign

`title, playlist (Link), priority, is_active, interrupt_policy
(Normal/Immediate Override), revision`

- Autoname: `format:CAMP-{#####}`.
- `campaign_service.py` requires the linked Playlist to be active and
  `priority >= 0`.
- `interrupt_policy` is stored and exposed in the envelope but Milestone 1's
  `resolve_effective_state` doesn't yet act on `Immediate Override`
  differently from `Normal` — there's no live playback session to interrupt
  without a device connected. It'll matter once Milestone 2's client exists.

## Schedule

`campaign (Link), recurrence_type (Always/Date Range/Daily/Selected Days),
all_day, start_date, end_date, start_time, end_time, monday..sunday, is_active,
timezone_policy (Display Local/Business Timezone)`

- Autoname: `format:SCH-{#####}`.
- **`all_day` exists because of a real Frappe framework quirk**: an empty
  `Time` field is *always* defaulted to the current time-of-day on insert
  (`frappe/model/create_new.py::set_dynamic_default_values`), so
  `start_time`/`end_time` being blank can never mean "no time restriction" —
  they'll silently contain near-current-time garbage instead. `all_day`
  (default checked) is the actual source of truth; `start_time`/`end_time`
  are only read when it's unchecked. This was caught by
  `test_schedule_evaluation.py` failing during Milestone 1, not discovered
  later — see `SCHEDULING_AND_PRIORITY.md` for the evaluation-side detail.
- `schedule_service.py` validates `end_date >= start_date`, `end_time >=
  start_time` (only when `all_day` is off), Date Range recurrence requiring
  both dates, and Selected Days recurrence requiring at least one day
  checked. Evaluating *whether* a schedule is currently active is a runtime
  concern, not a save-time one — that's `state_service.evaluate_schedule`.
- No overnight/wraparound windows (e.g. 22:00–02:00) in Milestone 1 — out of
  scope, `end_time < start_time` is rejected outright.

## Campaign Assignment

`campaign (Link), target_type (Display/Display Group), display (Link),
display_group (Link), assignment_priority, is_active`

- Autoname: `format:ASG-{#####}`.
- `assignment_service.py` enforces exactly one of `display`/`display_group`
  populated, matching `target_type`.

## Signage State Version

`display (Link, unique), server_version, generated_at, last_change_reason`

- Autoname: `field:display` — one row per display.
- The spec's "Sync Version" domain object. Written exclusively through
  `core/versioning.bump_display_versions` — every `on_update`/`on_trash`
  hook that can affect a display's state calls
  `state_service.record_change`, which resolves affected displays and bumps
  through that single function. No other code path writes this doctype.
- Read by `api/v1/sync.py`/`session.py` as of Milestone 2 (`server_version`
  in every sync/session response) — the version-bump behavior this doctype
  captures was built and tested in Milestone 1 ahead of Milestone 2 actually
  needing it, and that paid off directly here.

## Device Pairing Code

`display (Link), code_hash, expires_at, used_at, is_active`

- Autoname: `format:PAIR-{#####}`.
- Milestone 2. One-time, short-lived (15 minutes,
  `core/constants.PAIRING_CODE_EXPIRY_MINUTES`) codes an admin generates per
  Display to let a specific physical device register. `code_hash` is
  `sha256(code)` — the plaintext code is returned once, at generation time,
  and never stored. Usable iff `is_active`, `used_at` is unset, and
  `now < expires_at`; becomes permanently unusable the instant
  `device_service.register_device` succeeds. See `DEVICE_LIFECYCLE.md`.

## Device Credential

`display (Link), credential_identifier (unique), credential_secret_hash,
issued_at, expires_at, revoked_at, last_used_at, is_active`

- Autoname: `field:credential_identifier`.
- Milestone 2. The spec's "Device Session/Credential" domain object —
  deliberately one doctype, not a separate credential-plus-session-token
  pair (see `DEVICE_LIFECYCLE.md` for why). Issued by
  `device_service.register_device` on successful pairing;
  `credential_secret_hash` is `sha256(secret)`, the plaintext secret shown
  exactly once. `core/device_auth.authenticate` is the only code path that
  reads this doctype for auth purposes, and the only one that writes
  `last_used_at`. At most one row per display is ever active at a time —
  registering revokes whatever was active before.

## Digital Signage Settings (Single)

`default_playlist (Link → Playlist)`

- The spec's one explicit fallback: a configurable default playlist. Blank
  screen (empty `playlists`/`media` in the envelope) is what happens when
  this is unset, or when the configured playlist itself isn't active — never
  an undefined "no active campaign" state.
- Only `Signage Administrator`/`System Manager` can write it; every other
  role (including `Signage Manager`) is read-only, per the spec's "Manager =
  CRUD except Settings/Roles."

## Roles

`Signage Administrator, Signage Manager, Signage Operator, Signage Viewer` —
plain Frappe roles, created once by `bootstrap.py`. Permission shape (see
each doctype's `permissions` block):

- **Administrator** / **System Manager**: full CRUD everywhere.
- **Manager**: full CRUD everywhere except `Digital Signage Settings`
  (read-only there).
- **Operator**: read + create/update (no delete) on Media, Playlist,
  Campaign, Schedule, Campaign Assignment; read-only on Display, Display
  Group, Signage State Version, Settings.
- **Viewer**: read-only everywhere.
- `Device Pairing Code`/`Device Credential` (Milestone 2) use the same
  admin-managed shape as Display/Display Group — a human can see
  pairing/credential state for troubleshooting, never hand-edit a secret
  hash.

Device authentication is intentionally a separate concern from these human
roles — a device never holds one of these roles, is never a Frappe `User` at
all (`core/device_auth.py`, `SECURITY.md`).
