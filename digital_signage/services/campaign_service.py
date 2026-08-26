"""Campaign validation: playlist must be usable, priority must be sane."""

import frappe

from digital_signage.core.exceptions import SignageValidationError


def validate(doc):
	_validate_playlist(doc)
	_validate_priority(doc)
	_bump_revision(doc)


def _validate_playlist(doc):
	if not doc.playlist:
		return
	if not frappe.db.get_value("Playlist", doc.playlist, "is_active"):
		raise SignageValidationError(f"Campaign playlist '{doc.playlist}' must be active.")


def _validate_priority(doc):
	if doc.priority is None or doc.priority < 0:
		raise SignageValidationError("Campaign priority must be a non-negative integer.")


def _bump_revision(doc):
	if doc.is_new():
		doc.revision = doc.revision or 1
	else:
		previous = frappe.db.get_value("Campaign", doc.name, "revision") or 0
		doc.revision = previous + 1
