import frappe

from digital_signage.api.v1 import device_api
from digital_signage.core import device_auth
from digital_signage.services import sync_service


@frappe.whitelist(allow_guest=True, methods=["GET"])
@device_api
def get(credential_identifier, credential_secret):
	display = device_auth.authenticate(credential_identifier, credential_secret)
	return sync_service.build_sync_response(display)
