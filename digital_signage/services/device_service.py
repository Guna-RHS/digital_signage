"""Pairing, registration, and revocation — Phase D of the spec.

Deliberately uses raw frappe.db.set_value for Display/Device Credential
bookkeeping fields throughout this module rather than doc.save(): these are
device-lifecycle facts (registered, revoked, credential issued), not admin
content changes, so none of them should run through
state_service.record_change and bump the per-display version counter — see
core/device_auth.py's authenticate() for the same reasoning applied to
last_used_at.
"""

import frappe
from frappe.utils import add_days, add_to_date, now_datetime, random_string

from digital_signage.core.constants import (
	CREDENTIAL_EXPIRY_DAYS,
	CREDENTIAL_SECRET_LENGTH,
	PAIRING_CODE_EXPIRY_MINUTES,
	PAIRING_CODE_LENGTH,
	REGISTRATION_REGISTERED,
	REGISTRATION_REVOKED,
)
from digital_signage.core.device_auth import hash_secret
from digital_signage.core.device_errors import DeviceNotFound, DeviceValidationError


def generate_pairing_code(display_name):
	"""Admin-only (called from api/internal.py). Returns the plaintext code —
	shown once, only the hash is persisted."""
	if not frappe.db.exists("Display", display_name):
		raise DeviceNotFound(f"No Display '{display_name}'.")

	code = random_string(PAIRING_CODE_LENGTH).upper()
	frappe.get_doc(
		{
			"doctype": "Device Pairing Code",
			"display": display_name,
			"code_hash": hash_secret(code),
			"expires_at": add_to_date(now_datetime(), minutes=PAIRING_CODE_EXPIRY_MINUTES),
			"is_active": 1,
		}
	).insert(ignore_permissions=True)
	return code


def register_device(device_identifier, pairing_code, client_version=None):
	"""The spec's pairing flow: validate the code, issue a credential, burn
	the code. Returns (credential_identifier, plaintext_secret) — the secret
	is returned exactly once and never recoverable again."""
	display_name = frappe.db.get_value("Display", {"device_identifier": device_identifier})
	if not display_name:
		raise DeviceNotFound("No display with that device_identifier.")

	pairing = frappe.db.get_value(
		"Device Pairing Code",
		{"display": display_name, "code_hash": hash_secret(pairing_code), "is_active": 1},
		["name", "expires_at", "used_at"],
		as_dict=True,
	)
	if not pairing:
		raise DeviceValidationError("Invalid pairing code.")
	if pairing.used_at:
		raise DeviceValidationError("Pairing code has already been used.")
	if now_datetime() > pairing.expires_at:
		raise DeviceValidationError("Pairing code has expired.")

	# At most one active credential per display — re-pairing (e.g. a factory
	# reset) supersedes whatever credential existed before.
	for existing in frappe.get_all(
		"Device Credential", filters={"display": display_name, "is_active": 1}, pluck="name"
	):
		frappe.db.set_value("Device Credential", existing, {"is_active": 0, "revoked_at": now_datetime()})

	secret = random_string(CREDENTIAL_SECRET_LENGTH)
	credential_identifier = f"CRED-{random_string(16)}"
	frappe.get_doc(
		{
			"doctype": "Device Credential",
			"display": display_name,
			"credential_identifier": credential_identifier,
			"credential_secret_hash": hash_secret(secret),
			"issued_at": now_datetime(),
			"expires_at": add_days(now_datetime(), CREDENTIAL_EXPIRY_DAYS),
			"is_active": 1,
		}
	).insert(ignore_permissions=True)

	frappe.db.set_value("Device Pairing Code", pairing.name, "used_at", now_datetime())
	display_updates = {"registration_status": REGISTRATION_REGISTERED}
	if client_version:
		display_updates["client_version"] = client_version
	frappe.db.set_value("Display", display_name, display_updates)

	return credential_identifier, secret


def revoke_device(display_name):
	"""Admin-only (called from api/internal.py). Blocks all future
	sync/heartbeat/asset auth for this display immediately — Definition of
	Done #20. Does not touch Display.is_active: registration and
	active/inactive are independent axes (see docs/DOMAIN_MODEL.md)."""
	if not frappe.db.exists("Display", display_name):
		raise DeviceNotFound(f"No Display '{display_name}'.")

	frappe.db.set_value("Display", display_name, "registration_status", REGISTRATION_REVOKED)
	for credential in frappe.get_all(
		"Device Credential", filters={"display": display_name, "is_active": 1}, pluck="name"
	):
		frappe.db.set_value("Device Credential", credential, {"is_active": 0, "revoked_at": now_datetime()})
