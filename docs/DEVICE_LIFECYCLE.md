# Device Lifecycle

## The three independent state axes (recap from DOMAIN_MODEL.md)

A `Display` has three separate states that never drive each other
automatically:

- **Active / Inactive** (`is_active`) — admin-controlled, gates whether the
  display is considered for content at all (`state_service.resolve_effective_state`).
- **Pending / Registered / Revoked** (`registration_status`) — this doc.
  Gates whether the display *can authenticate* at all.
- **Online / Offline / Unknown** (computed from `last_heartbeat`) — not
  stored, not built yet as a computed property (Milestone 3).

`revoke_device` only ever touches `registration_status` and the display's
credentials — never `is_active`. If you also want a revoked display to stop
being schedulable, that's a separate, deliberate admin action.

## Pairing → credential → revoke

```text
Administrator creates Display (device_identifier set, e.g. a serial number)
        ↓
Administrator clicks "Generate Pairing Code" (Display form button, or
  digital_signage.api.internal.generate_pairing_code) — desk-only,
  System Manager / Signage Administrator
        ↓
Admin gives the device: server URL, device_identifier, pairing code
        ↓
Device calls POST api/v1/device.register with
  {device_identifier, pairing_code}
        ↓
Server validates the code (exists for that display, unused, unexpired),
  revokes any prior active credential for the display, issues a new
  Device Credential, marks the pairing code used, sets
  registration_status = Registered
        ↓
Device receives {credential_identifier, credential_secret} — the secret is
  shown exactly once, never recoverable again
        ↓
Device stores the credential locally, uses it on every subsequent
  session/sync/heartbeat/asset call
```

`Device Pairing Code` fields: `display, code_hash, expires_at, used_at,
is_active`. Codes are 8-character random strings, hashed the same way as
credential secrets (`core/device_auth.hash_secret` — sha256, never
plaintext), expire after 15 minutes
(`core/constants.PAIRING_CODE_EXPIRY_MINUTES`), and become permanently
unusable the moment `register` succeeds.

## Re-pairing

Generating a new pairing code and registering again (e.g. after a factory
reset) works with no separate "unpair" step: `register_device` revokes
whatever credential was previously active for that display *before* issuing
the new one — there is never more than one active `Device Credential` per
display. The admin doesn't need to manually revoke anything first.

## Revocation

`digital_signage.api.internal.revoke_device` (desk-only): sets
`registration_status = Revoked` and revokes every currently-active credential
for that display. Every subsequent `session`/`sync`/`heartbeat`/`assets.download`
call for that device immediately fails with `DEVICE_REVOKED` (403) — verified
end-to-end (see the manual verification pass this milestone did via `curl`).
There's no "un-revoke" — the recovery path is generating a fresh pairing code
and having the device register again, which also clears `Revoked` back to
`Registered`.

## Why there's no separate "session" doctype

The spec's Domain Model has one object — "Device Session/Credential" — not
two. `POST api/v1/session.create` doesn't mint a new token; it validates the
existing credential and touches `last_used_at`, mainly useful for a client to
confirm its stored credential still works right after a restart, before
attempting a real sync. See `core/device_auth.py`.
