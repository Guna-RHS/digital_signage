# Security

## Device credentials are not Frappe users

The spec is explicit on this twice: "Devices must not store administrator
credentials," and "do not build a duplicate human authentication system." A
paired device never gets a Frappe `User` record, never holds a Signage role,
and never touches Frappe's session/cookie/login system. All five
`api/v1/*` endpoints are `allow_guest=True` and do their own auth entirely
inside `core/device_auth.py`, against the `Device Credential` doctype.
Frappe's doctype permission tables (Administrator/Manager/Operator/Viewer,
Milestone 1) govern **desk access by humans only** — they have no bearing on
what a device can do.

## Secrets are hashed, never stored plaintext

Both the pairing code and the credential secret are stored only as
`sha256(value)` (`core/device_auth.hash_secret`). The plaintext value exists
only:
- in the HTTP response at the moment it's issued (pairing code: the admin's
  `generate_pairing_code` call; credential secret: the device's `register`
  response), and
- transiently in the device's own memory/storage after that.

Neither can be recovered from the database afterward — only revoked and
reissued (a new pairing code, or a full re-registration). This matches
common API-key UX (e.g. a GitHub PAT): shown once, gone after that.

## What's deliberately *not* hardened in this milestone

Documented explicitly rather than silently assumed:

- **No TLS enforcement at the application layer.** Whatever the deployment's
  reverse proxy/ingress does is what protects credentials/secrets in
  transit. `bench` dev mode serves plain HTTP.
- **No rate-limiting** on `register`, `session.create`, or any other
  endpoint. A brute-force attempt against a pairing code (8 random
  characters, 15-minute window) or a credential secret is not throttled by
  this app.
- **Credentials are passed as plain request parameters**, not a header
  (e.g. `Authorization: Bearer ...`). Simpler to implement and test
  directly as this milestone did, but means secrets can end up in access
  logs / URL history for the `GET` endpoints (`sync.get`,
  `assets.download`) unless the deployment strips query strings from logs.
  Moving to a header is a reasonable Milestone 3+ hardening step.
- **No credential rotation policy** beyond the 365-day expiry
  (`core/constants.CREDENTIAL_EXPIRY_DAYS`) and manual admin revoke — no
  automatic short-lived-token-plus-refresh scheme (see `DEVICE_LIFECYCLE.md`
  for why this milestone deliberately kept credential and session as one
  concept, not two).

None of these block the milestone's actual goal — a backend a device can
correctly register against, authenticate to, and sync from — but a
production rollout should treat this list as the next security work, not as
already handled.

## Error responses never leak internals

`api/v1/__init__.py`'s `device_api` decorator catches every exception a
device-facing endpoint can raise and returns only the spec's fixed
`{"code", "message", "retryable"}` shape — confirmed by deliberately
triggering a bad-secret error, a validation error, and an entirely
malformed/param-missing request over real HTTP during this milestone's
verification pass, and checking none of the response bodies contained a
traceback, file path, or SQL fragment. Unexpected exceptions are logged
server-side (`frappe.log_error`) and returned to the device as a generic
`TEMPORARY_SERVER_ERROR`.
