import frappe

from digital_signage.api.v1 import device_api
from digital_signage.core import device_auth
from digital_signage.core.versioning import get_server_version


@frappe.whitelist(allow_guest=True, methods=["POST"])
@device_api
def create(credential_identifier, credential_secret):
	"""Validates a credential is still good and touches last_used_at — a
	lightweight liveness check (e.g. after a client restart), not a second
	token type. See core/device_auth.py."""
	display = device_auth.authenticate(credential_identifier, credential_secret)
	return {
		"device_id": display.device_identifier,
		"registration_status": display.registration_status,
		"server_version": get_server_version(display.name),
	}
