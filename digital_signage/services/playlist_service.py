"""Playlist validation: explicit, unambiguous ordering + valid image durations."""

import frappe

from digital_signage.core.constants import MEDIA_TYPE_IMAGE
from digital_signage.core.exceptions import SignageValidationError


def validate(doc):
	_validate_items(doc)
	_bump_revision(doc)


def _validate_items(doc):
	seen_orders = set()
	for item in doc.items or []:
		if item.sort_order is None:
			raise SignageValidationError(f"Playlist Item row {item.idx} is missing an explicit sort_order.")
		if item.sort_order in seen_orders:
			raise SignageValidationError(
				f"Duplicate sort_order {item.sort_order} in playlist '{doc.title}' — ordering must be unambiguous."
			)
		seen_orders.add(item.sort_order)

		if not item.media:
			continue
		media_type = frappe.db.get_value("Media", item.media, "media_type")
		if media_type == MEDIA_TYPE_IMAGE and not (item.image_duration_seconds and item.image_duration_seconds > 0):
			raise SignageValidationError(
				f"Playlist Item for image media '{item.media}' needs a positive image_duration_seconds."
			)


def _bump_revision(doc):
	if doc.is_new():
		doc.revision = doc.revision or 1
	else:
		previous = frappe.db.get_value("Playlist", doc.name, "revision") or 0
		doc.revision = previous + 1
