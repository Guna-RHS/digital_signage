"""Campaign Assignment validation: exactly one target, matching target_type."""

from digital_signage.core.constants import TARGET_TYPE_DISPLAY, TARGET_TYPE_DISPLAY_GROUP
from digital_signage.core.exceptions import SignageValidationError


def validate(doc):
	if doc.target_type == TARGET_TYPE_DISPLAY:
		if not doc.display or doc.display_group:
			raise SignageValidationError("target_type 'Display' requires 'display' set and 'display_group' empty.")
	elif doc.target_type == TARGET_TYPE_DISPLAY_GROUP:
		if not doc.display_group or doc.display:
			raise SignageValidationError(
				"target_type 'Display Group' requires 'display_group' set and 'display' empty."
			)
	else:
		raise SignageValidationError(f"Unknown target_type '{doc.target_type}'.")

	if doc.assignment_priority is None or doc.assignment_priority < 0:
		raise SignageValidationError("assignment_priority must be a non-negative integer.")
