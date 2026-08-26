"""Schedule doctype-level validation (not evaluation — see state_service.evaluate_schedule
for whether a schedule is currently active, which is a runtime concern, not a save-time one)."""

from digital_signage.core.constants import RECURRENCE_DATE_RANGE, RECURRENCE_SELECTED_DAYS, WEEKDAY_FIELDS
from digital_signage.core.exceptions import SignageValidationError


def validate(doc):
	_validate_date_range(doc)
	_validate_time_range(doc)
	_validate_recurrence_data(doc)


def _validate_date_range(doc):
	if doc.start_date and doc.end_date and doc.end_date < doc.start_date:
		raise SignageValidationError("Schedule end_date cannot precede start_date.")


def _validate_time_range(doc):
	if doc.all_day:
		return
	# Frappe defaults an empty Time field to the current time-of-day on
	# insert (see all_day's field description) — so "both set" isn't
	# meaningfully checkable, but the ordering still is once all_day is off.
	if doc.start_time is not None and doc.end_time is not None and doc.end_time < doc.start_time:
		raise SignageValidationError("Schedule end_time cannot be before start_time.")


def _validate_recurrence_data(doc):
	if doc.recurrence_type == RECURRENCE_DATE_RANGE and not (doc.start_date and doc.end_date):
		raise SignageValidationError("Date Range recurrence requires both start_date and end_date.")
	if doc.recurrence_type == RECURRENCE_SELECTED_DAYS and not any(doc.get(day) for day in WEEKDAY_FIELDS):
		raise SignageValidationError("Selected Days recurrence requires at least one day selected.")
