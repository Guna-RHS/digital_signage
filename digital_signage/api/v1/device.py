import frappe

from digital_signage.api.v1 import device_api
from digital_signage.services import device_service


@frappe.whitelist(allow_guest=True, methods=["POST"])
@device_api
def register(device_identifier, pairing_code, client_version=None):
	credential_identifier, credential_secret = device_service.register_device(
		device_identifier, pairing_code, client_version
	)
	return {"credential_identifier": credential_identifier, "credential_secret": credential_secret}
