"""Media lifecycle: hashing, versioning, safe deletion.

Doctype controller (media.py) delegates here; this module holds all the
business logic so it's directly unit-testable without going through the
desk/API layer.
"""

import hashlib
import mimetypes

import frappe

from digital_signage.core.constants import (
	MEDIA_LIFECYCLE_ACTIVE,
	MEDIA_LIFECYCLE_RETIRED,
	MEDIA_LIFECYCLE_UPLOADED,
	MEDIA_LIFECYCLE_VALIDATED,
)
from digital_signage.core.exceptions import SignageConflictError, SignageValidationError

# Retired is a terminal state reachable from anywhere (a bad upload can be
# retired without ever going Active) but never left once reached.
ALLOWED_LIFECYCLE_TRANSITIONS = {
	None: {MEDIA_LIFECYCLE_UPLOADED},
	MEDIA_LIFECYCLE_UPLOADED: {MEDIA_LIFECYCLE_UPLOADED, MEDIA_LIFECYCLE_VALIDATED, MEDIA_LIFECYCLE_RETIRED},
	MEDIA_LIFECYCLE_VALIDATED: {MEDIA_LIFECYCLE_VALIDATED, MEDIA_LIFECYCLE_ACTIVE, MEDIA_LIFECYCLE_RETIRED},
	MEDIA_LIFECYCLE_ACTIVE: {MEDIA_LIFECYCLE_ACTIVE, MEDIA_LIFECYCLE_RETIRED},
	MEDIA_LIFECYCLE_RETIRED: {MEDIA_LIFECYCLE_RETIRED},
}


def validate(doc):
	_validate_lifecycle_transition(doc)
	if doc.file:
		_hash_and_stamp(doc)


def create_from_bytes(*, title, media_type, filename, content: bytes, is_private=1):
	"""Creates a File + a fully Active Media doc from raw bytes in one call —
	the exact Uploaded → Validated → Active dance (each transition its own
	save so _validate_lifecycle_transition's state machine is honored, not
	bypassed), used by anything that produces media programmatically rather
	than through a human's upload (e.g. template_service's generated
	images). sha256/file_size/mime_type are computed by validate()'s own
	_hash_and_stamp — never set directly here."""
	import base64

	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": filename,
			"content": base64.b64encode(content).decode(),
			"decode": True,
			"is_private": is_private,
		}
	)
	file_doc.insert(ignore_permissions=True)

	media = frappe.get_doc(
		{
			"doctype": "Media",
			"title": title,
			"media_type": media_type,
			"file": file_doc.file_url,
			"lifecycle_status": MEDIA_LIFECYCLE_UPLOADED,
			"is_active": 1,
		}
	)
	media.insert(ignore_permissions=True)
	media.lifecycle_status = MEDIA_LIFECYCLE_VALIDATED
	media.save(ignore_permissions=True)
	media.lifecycle_status = MEDIA_LIFECYCLE_ACTIVE
	media.save(ignore_permissions=True)
	return media


def guard_deletion(doc):
	"""Called from on_trash. Media must be Retired, and unreferenced, before
	it can actually be deleted — matches the spec's "Do not physically delete
	media immediately when active client states may still reference it."""
	if doc.lifecycle_status != MEDIA_LIFECYCLE_RETIRED:
		raise SignageConflictError("Retire this Media (lifecycle status = Retired) before deleting it.")
	if frappe.db.exists("Playlist Item", {"media": doc.name}):
		raise SignageConflictError("Cannot delete Media that is still referenced by a Playlist Item.")


def _validate_lifecycle_transition(doc):
	previous = None if doc.is_new() else frappe.db.get_value("Media", doc.name, "lifecycle_status")
	allowed = ALLOWED_LIFECYCLE_TRANSITIONS.get(previous, set())
	if doc.lifecycle_status not in allowed:
		raise SignageValidationError(
			f"Media cannot move from lifecycle status '{previous}' to '{doc.lifecycle_status}'."
		)
	if doc.lifecycle_status == MEDIA_LIFECYCLE_RETIRED:
		doc.is_active = 0


def _hash_and_stamp(doc):
	file_doc = frappe.get_doc("File", {"file_url": doc.file})
	content = file_doc.get_content()
	if isinstance(content, str):
		content = content.encode("utf-8")

	digest = hashlib.sha256(content).hexdigest()
	previous_hash = None if doc.is_new() else frappe.db.get_value("Media", doc.name, "sha256")
	if previous_hash and digest != previous_hash:
		doc.asset_version = (doc.asset_version or 1) + 1
	doc.sha256 = digest
	doc.file_size = len(content)
	doc.mime_type = mimetypes.guess_type(file_doc.file_name or doc.file)[0] or doc.mime_type
