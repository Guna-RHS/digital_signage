# Sync Protocol

**`sync.get` sends the full eligible-campaign set, not a single resolved
winner** — see `SCHEDULING_AND_PRIORITY.md`'s "Who resolves this" section.
The client's local scheduler is what turns this into "what plays right now,"
including across schedule boundaries the client crosses while offline.

## The sequence, realized

```text
Client checks version                  -> session.create (or just calls sync;
                                            server_version is in both responses)
      ↓
Version differs                        -> client decides locally, comparing
                                            against its last-synced version
      ↓
Client requests applicable state       -> GET sync.get
      ↓
Receives state + asset manifest        -> the envelope's `assets` array
      ↓
Downloads missing/changed assets       -> GET assets.download per asset,
                                            comparing local cache against
                                            each asset's sha256/version
      ↓
Verifies SHA-256                       -> client's responsibility — the
                                            manifest gives it the value to
                                            check against
      ↓
Client atomically commits local state  -> client's responsibility (this
                                            backend has no visibility into
                                            or control over that step)
      ↓
Client activates state                 -> client's responsibility
```

**The backend never assumes activation succeeded just because it returned a
response.** `sync.get` updating `Display.last_sync_at`/`last_sync_version`
records only that the *server sent* a response — not that the client
persisted or activated it. The only signal the server gets back about actual
playback is whatever the next `heartbeat` reports (`current_campaign`/
`current_playlist`/`current_media`), which is inherently after the fact and
best-effort.

## Full sync only — no delta sync (yet)

Every `sync.get` call returns the *complete* applicable state, every time —
there is no "since version X" partial-update mode. This is deliberate, per
the spec ("Start with correct full synchronization. Only add delta sync when
full sync and versioning are reliable") — this milestone is what makes full
sync exist at all, so it isn't the milestone to also add delta sync on top.

## Recovery is just "call sync again"

There's no separate recovery endpoint. Internet loss, a Frappe restart, a
missed realtime notification (once Milestone 3 adds those), a client that
simply hasn't synced in a while — all of these are handled the same way: the
client calls `sync.get` again and gets the complete, current, correct state.
Idempotent by construction — `state_service.resolve_effective_state` is a
pure read of current data, calling it twice with nothing changed in between
returns the identical envelope (verified: `test_sync.py::test_repeated_sync_is_safe`,
`test_device_idempotency.py::test_repeated_sync_creates_no_duplicate_version_rows`).

## Version checking

`server_version` in the envelope comes from `Signage State Version` (Milestone
1) — a plain integer that increments whenever
`state_service.resolve_affected_displays` determines a change is relevant to
this display (see `SCHEDULING_AND_PRIORITY.md`). A client's job is simple:
remember the `server_version` it last synced, and if a later `session.create`
or heartbeat response reports a higher one, sync again. Nothing about *why*
it changed is exposed beyond `Signage State Version.last_change_reason`
(desk-visible, not part of the device-facing envelope).
