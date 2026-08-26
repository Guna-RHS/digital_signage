"""The Signage State Version bump primitive.

state_service.resolve_affected_displays() decides *which* displays a change
affects; this module is the one place that actually writes the version
counter, so there's exactly one code path that can increment it.
"""

import frappe
from frappe.utils import now_datetime


def bump_display_versions(display_names, reason):
	"""Increment (or create) the Signage State Version row for each display,
	and flag each for pickup on its next short heartbeat check-in (see
	heartbeat_service.record_heartbeat) -- so any content change that
	actually affects a display reaches it within ~15s on its own, the same
	as clicking Force Sync in Desk, without requiring that manual step.
	Force Sync still exists for "I want this immediately, don't even wait
	for the next heartbeat tick" — this just makes it the common case
	instead of the only case.

	display_names: iterable of Display document names. Silently no-ops for an
	empty iterable — callers don't need to guard against "no affected
	displays" themselves.
	"""
	generated_at = now_datetime()
	for display_name in set(display_names):
		if frappe.db.exists("Signage State Version", display_name):
			version_doc = frappe.get_doc("Signage State Version", display_name)
			version_doc.server_version = (version_doc.server_version or 0) + 1
		else:
			version_doc = frappe.get_doc(
				{
					"doctype": "Signage State Version",
					"display": display_name,
					"server_version": 1,
				}
			)
		version_doc.generated_at = generated_at
		version_doc.last_change_reason = reason
		version_doc.save(ignore_permissions=True)

		if frappe.db.exists("Display", display_name):
			_flag_for_sync(display_name, generated_at)


def _flag_for_sync(display_name, generated_at):
	"""Writes inline, inside whatever transaction is already open (the same
	one bump_display_versions/version_doc.save() is part of) — it must
	commit alongside the real change, not separately (an after_commit-deferred
	write here was tried and doesn't work: that phase runs *after* the
	surrounding commit() has already fired, so the write only lands in a
	fresh transaction nothing then commits, and is silently lost the moment
	the connection resets for the next request).

	The Display row is also written concurrently by that device's own
	heartbeat (~every 15s, independent of any content change) — a savepoint
	around just this one write means a lock conflict from that race only
	undoes this flag, never the real content change alongside it.
	"""
	frappe.db.sql("SAVEPOINT force_sync_flag")
	try:
		frappe.db.set_value("Display", display_name, "force_sync_requested_at", generated_at, update_modified=False)
	except frappe.QueryDeadlockError:
		frappe.db.rollback(save_point="force_sync_flag")


def get_server_version(display_name):
	"""Current server_version for a display, or 0 if it has never changed."""
	return frappe.db.get_value("Signage State Version", display_name, "server_version") or 0
