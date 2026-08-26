# Client Integration

The flow a real (Tauri/Rust, or anything else) client should follow, using
only what this backend actually implements today. Every step below was
exercised over real HTTP during this milestone's verification pass, not just
unit-tested in isolation.

## 1. First run — pairing

The client doesn't do anything until a human gives it a server URL, a device
identifier, and a pairing code (out-of-band — typed in, scanned, however the
client's own onboarding UI works; that UI is out of scope for this backend).

```
POST {server}/api/method/digital_signage.api.v1.device.register
  device_identifier=<...>
  pairing_code=<...>
  client_version=<optional>

-> {"message": {"credential_identifier": "...", "credential_secret": "..."}}
```

Persist `credential_identifier`/`credential_secret` locally — securely, this
is effectively an API key — and never re-request it; it isn't recoverable
from the server after this call. See `DEVICE_LIFECYCLE.md`.

## 2. Every subsequent run — validate, then sync

```
POST {server}/api/method/digital_signage.api.v1.session.create
  credential_identifier=<stored>
  credential_secret=<stored>

-> {"message": {"device_id": "...", "registration_status": "Registered", "server_version": N}}
```

If this returns `DEVICE_REVOKED` or `AUTHENTICATION_FAILED`, the stored
credential is no longer valid — stop, surface that to whatever's monitoring
the device, and wait for re-pairing. This is the one case the client can't
route around by retrying.

```
GET {server}/api/method/digital_signage.api.v1.sync.get
  ?credential_identifier=<stored>&credential_secret=<stored>

-> {"message": {...full envelope, see SYNC_PROTOCOL.md...}}
```

## 3. Downloading/verifying assets

For each entry in the sync response's `assets` array: if the local cache
doesn't have that `asset_id` at that `sha256`/`version`, fetch it:

```
GET {server}{download_url}&credential_identifier=<stored>&credential_secret=<stored>
```

(`download_url` from the manifest already has `?media=...` — append the auth
params.) Verify the downloaded bytes hash to the manifest's `sha256` before
treating the asset as valid — this backend computes and reports the hash
(`Media.sha256`, Milestone 1) but doesn't re-verify what was actually
transferred; that's the client's job, per the spec.

Only *commit and activate* the new state once every asset it references has
been downloaded and verified — see `SYNC_PROTOCOL.md`'s note that this
backend has no visibility into whether that actually happened.

## 4. Ongoing: play locally, heartbeat periodically

Playback timing and evaluation is entirely the client's job (spec: "The
client owns playback timing and evaluates its synchronized schedule
locally" — nothing in this backend drives frame-by-frame or even
item-by-item playback). Periodically (on whatever interval the client
chooses):

```
POST {server}/api/method/digital_signage.api.v1.heartbeat.post
  credential_identifier=<stored>&credential_secret=<stored>
  client_version=<...>&current_campaign=<...>&current_playlist=<...>
  &current_media=<...>&last_error=<...>

-> {"message": {"ok": true}}
```

A failed heartbeat call (network down, server unreachable) must never affect
local playback — the client keeps playing its last-synced, already-verified
local state regardless. This is the offline-operation guarantee from the
spec; this backend cannot enforce it, only avoid getting in the way of it
(no endpoint here is on any critical path for continued local playback).

## 5. Re-syncing

Compare `server_version` (from `session.create` or the last `sync.get`)
against what was last synced. If it's higher, run step 2's `sync.get` again.
There's no push/notification yet (Milestone 3) — this is poll-based for now,
at whatever interval the client chooses.
