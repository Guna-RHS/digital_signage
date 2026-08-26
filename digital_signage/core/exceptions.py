"""Service-layer exceptions.

Services raise these instead of bare frappe.ValidationError so callers (tests,
the Milestone 2 API layer) can distinguish failure kinds without string
matching messages. Doctype controllers let these propagate as-is; Frappe
renders any Exception subclass with a message as a user-facing error.
"""

import frappe


class SignageError(frappe.ValidationError):
	"""Base class for all digital_signage service-layer errors."""


class SignageValidationError(SignageError):
	"""A document failed a Phase B business-rule check (see Validation section
	of the spec: media, playlist, campaign, schedule, assignment rules)."""


class SignageNotFoundError(SignageError):
	"""A referenced record (display, campaign, ...) does not exist or is not
	in a state the caller expected (e.g. inactive)."""


class SignageConflictError(SignageError):
	"""An operation would violate an invariant that isn't a simple field
	validation, e.g. deleting media that's still referenced/active."""
