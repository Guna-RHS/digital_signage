"""Shared test-data builders. Every doctype's automated tests (both the
per-doctype test_x.py files and the cross-cutting tests/ package) go through
these instead of hand-rolling frappe.get_doc(...) calls, so a field-shape
change only needs updating in one place."""

import frappe
from frappe.utils import add_to_date, now_datetime, random_string
from frappe.utils.file_manager import save_file

from digital_signage.core.constants import (
	MEDIA_LIFECYCLE_ACTIVE,
	MEDIA_LIFECYCLE_RETIRED,
	MEDIA_LIFECYCLE_UPLOADED,
	MEDIA_LIFECYCLE_VALIDATED,
	TARGET_TYPE_DISPLAY,
	TARGET_TYPE_DISPLAY_GROUP,
)
from digital_signage.core.device_auth import hash_secret

LIFECYCLE_ORDER = [
	MEDIA_LIFECYCLE_UPLOADED,
	MEDIA_LIFECYCLE_VALIDATED,
	MEDIA_LIFECYCLE_ACTIVE,
	MEDIA_LIFECYCLE_RETIRED,
]


def make_media(media_type="Image", content=b"fake-image-bytes", lifecycle_status=None, title=None):
	file_doc = save_file(f"test-{random_string(6)}.png", content, None, None, is_private=1)
	media = frappe.get_doc(
		{
			"doctype": "Media",
			"title": title or f"Test Media {random_string(6)}",
			"media_type": media_type,
			"file": file_doc.file_url,
		}
	)
	media.insert(ignore_permissions=True)
	if lifecycle_status:
		advance_media_lifecycle(media, lifecycle_status)
	return media


def advance_media_lifecycle(media, target_status):
	current_idx = LIFECYCLE_ORDER.index(media.lifecycle_status)
	target_idx = LIFECYCLE_ORDER.index(target_status)
	for status in LIFECYCLE_ORDER[current_idx + 1 : target_idx + 1]:
		media.lifecycle_status = status
		media.save(ignore_permissions=True)
	return media


def replace_media_file(media, content=b"different-bytes"):
	file_doc = save_file(f"test-{random_string(6)}.png", content, None, None, is_private=1)
	media.file = file_doc.file_url
	media.save(ignore_permissions=True)
	return media


def make_playlist(items=None, title=None, is_active=1):
	"""items: list of dicts with keys media, sort_order, image_duration_seconds, enabled."""
	playlist = frappe.get_doc(
		{
			"doctype": "Playlist",
			"title": title or f"Test Playlist {random_string(6)}",
			"is_active": is_active,
			"items": items or [],
		}
	)
	playlist.insert(ignore_permissions=True)
	return playlist


def make_campaign(playlist_name, priority=0, is_active=1, interrupt_policy="Normal", title=None):
	campaign = frappe.get_doc(
		{
			"doctype": "Campaign",
			"title": title or f"Test Campaign {random_string(6)}",
			"playlist": playlist_name,
			"priority": priority,
			"is_active": is_active,
			"interrupt_policy": interrupt_policy,
		}
	)
	campaign.insert(ignore_permissions=True)
	return campaign


def make_schedule(campaign_name, **kwargs):
	# Defaults all_day=0 automatically when a time window is given — passing
	# start_time/end_time without meaning to restrict by time would be a
	# footgun otherwise.
	all_day_default = 0 if ("start_time" in kwargs or "end_time" in kwargs) else 1
	doc = {
		"doctype": "Schedule",
		"campaign": campaign_name,
		"recurrence_type": kwargs.get("recurrence_type", "Always"),
		"is_active": kwargs.get("is_active", 1),
		"all_day": kwargs.get("all_day", all_day_default),
		"timezone_policy": kwargs.get("timezone_policy", "Display Local"),
	}
	for key in (
		"start_date",
		"end_date",
		"start_time",
		"end_time",
		"monday",
		"tuesday",
		"wednesday",
		"thursday",
		"friday",
		"saturday",
		"sunday",
	):
		if key in kwargs:
			doc[key] = kwargs[key]
	schedule = frappe.get_doc(doc)
	schedule.insert(ignore_permissions=True)
	return schedule


def make_display(is_active=1, device_identifier=None, display_name=None):
	device_id = device_identifier or f"DEV-{random_string(8)}"
	display = frappe.get_doc(
		{
			"doctype": "Display",
			"display_name": display_name or f"Test Display {device_id}",
			"device_identifier": device_id,
			"is_active": is_active,
		}
	)
	display.insert(ignore_permissions=True)
	return display


def make_display_group(display_names, is_active=1, group_name=None):
	group = frappe.get_doc(
		{
			"doctype": "Display Group",
			"group_name": group_name or f"Test Group {random_string(6)}",
			"is_active": is_active,
			"members": [{"display": d} for d in display_names],
		}
	)
	group.insert(ignore_permissions=True)
	return group


def make_assignment(campaign_name, display=None, display_group=None, priority=0, is_active=1):
	target_type = TARGET_TYPE_DISPLAY if display else TARGET_TYPE_DISPLAY_GROUP
	assignment = frappe.get_doc(
		{
			"doctype": "Campaign Assignment",
			"campaign": campaign_name,
			"target_type": target_type,
			"display": display,
			"display_group": display_group,
			"assignment_priority": priority,
			"is_active": is_active,
		}
	)
	assignment.insert(ignore_permissions=True)
	return assignment


def make_pairing_code(display_name, expires_at=None, used_at=None, is_active=1):
	"""Bypasses device_service.generate_pairing_code so tests can construct a
	pairing code in a specific state (expired, already-used) directly."""
	code = f"TEST{random_string(4).upper()}"
	frappe.get_doc(
		{
			"doctype": "Device Pairing Code",
			"display": display_name,
			"code_hash": hash_secret(code),
			"expires_at": expires_at or add_to_date(now_datetime(), minutes=15),
			"used_at": used_at,
			"is_active": is_active,
		}
	).insert(ignore_permissions=True)
	return code


def register_test_device(display_name=None):
	"""End-to-end: create a Display (unless given one), pair it, register it.
	Returns (display, credential_identifier, credential_secret)."""
	from digital_signage.services.device_service import register_device

	display = frappe.get_doc("Display", display_name) if display_name else make_display()
	code = make_pairing_code(display.name)
	credential_identifier, credential_secret = register_device(display.device_identifier, code)
	return display, credential_identifier, credential_secret
