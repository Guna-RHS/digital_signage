import frappe

from digital_signage.api.v1 import device_api
from digital_signage.core import device_auth
from digital_signage.services import heartbeat_service


@frappe.whitelist(allow_guest=True, methods=["POST"])
@device_api
def post(credential_identifier, credential_secret, **payload):
	display = device_auth.authenticate(credential_identifier, credential_secret)
	force_sync = heartbeat_service.record_heartbeat(display, payload)
	return {"ok": True, "force_sync": force_sync}
