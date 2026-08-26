"""Desk/admin-only API surface.

Not the device-facing `signage.api.v1.*` namespace (digital_signage/api/v1/)
— these are human/desk-session calls, gated by System Manager/Signage
Administrator, not device credentials.
"""

import frappe
from frappe.utils import now_datetime

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


@frappe.whitelist()
def request_force_sync(display):
	"""Marks a one-shot flag the device's own short heartbeat poll checks and
	clears on pickup (see heartbeat_service.record_heartbeat) — this is a
	convenience nudge to shorten the wait, not a replacement for the existing
	periodic sync; the device still owns when it actually syncs."""
	frappe.only_for(["System Manager", ROLE_ADMINISTRATOR])
	if not frappe.db.exists("Display", display):
		frappe.throw(f"No Display '{display}'.")
	frappe.db.set_value("Display", display, "force_sync_requested_at", now_datetime())
