"""Desk/admin-only API surface.

Not the device-facing `signage.api.v1.*` namespace (digital_signage/api/v1/)
— these are human/desk-session calls, gated by System Manager/Signage
Administrator, not device credentials.
"""

import frappe

from digital_signage.core.constants import ROLE_ADMINISTRATOR
from digital_signage.services import device_service, state_service


@frappe.whitelist()
def preview_effective_state(display):
	frappe.only_for(["System Manager", ROLE_ADMINISTRATOR])
	return state_service.resolve_effective_state(display)


@frappe.whitelist()
def generate_pairing_code(display):
	frappe.only_for(["System Manager", ROLE_ADMINISTRATOR])
	return device_service.generate_pairing_code(display)


@frappe.whitelist()
def revoke_device(display):
	frappe.only_for(["System Manager", ROLE_ADMINISTRATOR])
	device_service.revoke_device(display)
