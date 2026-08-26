"""Heartbeat: the device reporting its own current playback status.

Spec: "Heartbeat failure must never stop playback" — so this is deliberately
lenient (no strict Link validation on the reported campaign/playlist/media,
malformed/partial payloads never raise) and deliberately uses raw
frappe.db.set_value rather than Display.save(), so a heartbeat never runs
through state_service.record_change and bumps the version counter — a
device reporting what it's already playing is not an admin content change.
"""

import frappe
from frappe.utils import now_datetime

REPORTED_FIELDS = ("client_version", "current_campaign", "current_playlist", "current_media", "last_error")


def record_heartbeat(display, payload):
	"""Returns whether an admin-requested force sync is pending, clearing the
	flag in the same write so it fires exactly once — see
	api/internal.request_force_sync."""
	payload = payload or {}
	force_sync = bool(display.get("force_sync_requested_at"))
	updates = {"last_heartbeat": now_datetime(), "last_seen": now_datetime()}
	if force_sync:
		updates["force_sync_requested_at"] = None
	for field in REPORTED_FIELDS:
		value = payload.get(field)
		if value:
			updates[field] = value
	frappe.db.set_value("Display", display.name, updates)
	return force_sync
