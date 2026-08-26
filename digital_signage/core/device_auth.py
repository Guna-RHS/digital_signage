"""Device credential authentication — the one place that turns
(credential_identifier, credential_secret) into a verified Display, used by
every api/v1 endpoint. Not Frappe's user/session system: a device is never a
Frappe User (spec: "Device authentication is separate from human roles" /
"do not build a duplicate human authentication system")."""

import hashlib

import frappe
from frappe.utils import now_datetime

from digital_signage.core.constants import REGISTRATION_REVOKED
from digital_signage.core.device_errors import AuthenticationFailed, DeviceDisabled, DeviceRevoked


def hash_secret(secret):
	return hashlib.sha256((secret or "").encode()).hexdigest()


def authenticate(credential_identifier, credential_secret):
	if not credential_identifier or not credential_secret:
		raise AuthenticationFailed("Missing credentials.")

	credential = frappe.db.get_value(
		"Device Credential",
		credential_identifier,
		["name", "display", "credential_secret_hash", "expires_at", "revoked_at", "is_active"],
		as_dict=True,
	)
	if not credential:
		raise AuthenticationFailed("Unknown credential.")
	if not credential.is_active or credential.revoked_at:
		raise DeviceRevoked("Credential has been revoked.")
	if credential.expires_at and now_datetime() > credential.expires_at:
		raise AuthenticationFailed("Credential has expired.")
	if hash_secret(credential_secret) != credential.credential_secret_hash:
		raise AuthenticationFailed("Invalid credential secret.")

	display = frappe.get_doc("Display", credential.display)
	if display.registration_status == REGISTRATION_REVOKED:
		raise DeviceRevoked("Display has been revoked.")
	if not display.is_active:
		raise DeviceDisabled("Display is disabled.")

	# Deliberately a raw write, not display.save() — this is the device
	# proving liveness, not an admin content change, so it must never run
	# through state_service.record_change and bump the version counter.
	frappe.db.set_value("Device Credential", credential.name, "last_used_at", now_datetime())

	return display
