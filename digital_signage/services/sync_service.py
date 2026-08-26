"""Full sync response: the full-candidate-set envelope (state_service.resolve_sync_state
— NOT resolve_effective_state's single-winner preview, see that module's
docstring for why) + the asset manifest."""

import frappe
from frappe.utils import now_datetime

from digital_signage.services import asset_service, state_service


def build_sync_response(display):
	state = state_service.resolve_sync_state(display.name)
	state["assets"] = asset_service.build_manifest(state["media"])

	# Raw write, not display.save() — same reasoning as heartbeat_service:
	# the device completing a sync is not an admin content change.
	frappe.db.set_value(
		"Display",
		display.name,
		{"last_sync_at": now_datetime(), "last_sync_version": state["server_version"]},
	)
	return state
