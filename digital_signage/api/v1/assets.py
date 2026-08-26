import frappe

from digital_signage.api.v1 import device_api
from digital_signage.core import device_auth
from digital_signage.services import asset_service


@frappe.whitelist(allow_guest=True, methods=["GET"])
@device_api
def download(credential_identifier, credential_secret, media):
	display = device_auth.authenticate(credential_identifier, credential_secret)
	media_doc = asset_service.authorize_download(display, media)
	asset_service.stream(media_doc)
