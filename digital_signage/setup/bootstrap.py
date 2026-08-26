"""One-time scripted creation of Milestone 1 roles + DocTypes.

Run once via:
    bench --site rhs.local execute digital_signage.setup.bootstrap.run

With developer_mode=1 (already set on rhs.local) each DocType.insert() below
exports its json/py/js straight to
digital_signage/digital_signage/doctype/<name>/ on disk, which is what then
gets committed to the app. Idempotent (checks frappe.db.exists first) so it's
safe to re-run, but in practice this is a bootstrap script, not something
hooked into app install.

DocTypes are created in Link-dependency order — Frappe's DocType validation
rejects a Link field whose `options` doctype doesn't exist yet — not in the
Domain Model section order of the spec.
"""

import frappe

from digital_signage.core.constants import (
	ALL_ROLES,
	INTERRUPT_POLICIES,
	MEDIA_LIFECYCLE_STATUSES,
	MEDIA_TYPES,
	RECURRENCE_TYPES,
	REGISTRATION_STATUSES,
	ROLE_ADMINISTRATOR,
	ROLE_MANAGER,
	ROLE_OPERATOR,
	ROLE_VIEWER,
	TARGET_TYPES,
	TIMEZONE_POLICIES,
	WEEKDAY_FIELDS,
)

MODULE = "Digital Signage"


def run():
	create_roles()
	create_media()
	create_playlist_item()
	create_playlist()
	create_campaign()
	create_display()
	create_display_group_member()
	create_display_group()
	create_schedule()
	create_campaign_assignment()
	create_signage_state_version()
	create_digital_signage_settings()
	frappe.db.commit()
	print("digital_signage bootstrap complete")


def create_roles():
	for role in ALL_ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
				ignore_permissions=True
			)


# --- field/permission helpers -------------------------------------------------


def f(fieldname, fieldtype, **kw):
	label = kw.pop("label", fieldname.replace("_", " ").title())
	return {"fieldname": fieldname, "fieldtype": fieldtype, "label": label, **kw}


def perm(role, read=1, write=0, create=0, delete=0):
	return {"role": role, "read": read, "write": write, "create": create, "delete": delete}


def perms_operator_editable():
	"""Media, Playlist, Campaign, Schedule, Campaign Assignment: Operator can
	read/create/update but not delete; Viewer is read-only."""
	return [
		perm(ROLE_ADMINISTRATOR, 1, 1, 1, 1),
		perm("System Manager", 1, 1, 1, 1),
		perm(ROLE_MANAGER, 1, 1, 1, 1),
		perm(ROLE_OPERATOR, 1, 1, 1, 0),
		perm(ROLE_VIEWER, 1, 0, 0, 0),
	]


def perms_admin_managed():
	"""Display, Display Group, Signage State Version: Operator/Viewer are
	read-only, Manager gets full CRUD."""
	return [
		perm(ROLE_ADMINISTRATOR, 1, 1, 1, 1),
		perm("System Manager", 1, 1, 1, 1),
		perm(ROLE_MANAGER, 1, 1, 1, 1),
		perm(ROLE_OPERATOR, 1, 0, 0, 0),
		perm(ROLE_VIEWER, 1, 0, 0, 0),
	]


def perms_settings():
	"""Digital Signage Settings: only Administrator may change the fallback;
	everyone else (including Manager, per spec's 'CRUD except Settings') is
	read-only."""
	return [
		perm(ROLE_ADMINISTRATOR, 1, 1, 1, 0),
		perm("System Manager", 1, 1, 1, 0),
		perm(ROLE_MANAGER, 1, 0, 0, 0),
		perm(ROLE_OPERATOR, 1, 0, 0, 0),
		perm(ROLE_VIEWER, 1, 0, 0, 0),
	]


def create_doctype(name, fields, permissions=None, **kwargs):
	if frappe.db.exists("DocType", name):
		return
	doc = frappe.get_doc(
		{
			"doctype": "DocType",
			"name": name,
			"module": MODULE,
			"custom": 0,
			"istable": kwargs.get("istable", 0),
			"issingle": kwargs.get("issingle", 0),
			"editable_grid": 1 if kwargs.get("istable") else 0,
			"track_changes": kwargs.get("track_changes", 0 if kwargs.get("istable") else 1),
			"autoname": kwargs.get("autoname"),
			"fields": fields,
			"permissions": permissions or [],
		}
	)
	doc.insert(ignore_permissions=True)


# --- doctypes -------------------------------------------------------------


def create_media():
	create_doctype(
		"Media",
		fields=[
			f("title", "Data", reqd=1, in_list_view=1),
			f("media_type", "Select", options="\n".join(MEDIA_TYPES), reqd=1, in_list_view=1),
			f("file", "Attach", reqd=1),
			f("mime_type", "Data", read_only=1),
			f("file_size", "Int", read_only=1),
			f("sha256", "Data", read_only=1),
			f("asset_version", "Int", read_only=1, default="1"),
			f("is_active", "Check", default="1"),
			f(
				"lifecycle_status",
				"Select",
				options="\n".join(MEDIA_LIFECYCLE_STATUSES),
				default="Uploaded",
				read_only=1,
				in_list_view=1,
			),
		],
		permissions=perms_operator_editable(),
		autoname="format:MEDIA-{#####}",
	)


def create_playlist_item():
	create_doctype(
		"Playlist Item",
		fields=[
			f("media", "Link", options="Media", reqd=1, in_list_view=1),
			f("sort_order", "Int", reqd=1, in_list_view=1),
			f("image_duration_seconds", "Int", in_list_view=1),
			f("enabled", "Check", default="1", in_list_view=1),
		],
		istable=1,
	)


def create_playlist():
	create_doctype(
		"Playlist",
		fields=[
			f("title", "Data", reqd=1, in_list_view=1),
			f("description", "Small Text"),
			f("is_active", "Check", default="1"),
			f("revision", "Int", read_only=1, default="1"),
			f("items", "Table", options="Playlist Item"),
		],
		permissions=perms_operator_editable(),
		autoname="format:PL-{#####}",
	)


def create_campaign():
	create_doctype(
		"Campaign",
		fields=[
			f("title", "Data", reqd=1, in_list_view=1),
			f("playlist", "Link", options="Playlist", reqd=1, in_list_view=1),
			f("priority", "Int", default="0", in_list_view=1),
			f("is_active", "Check", default="1"),
			f("interrupt_policy", "Select", options="\n".join(INTERRUPT_POLICIES), default="Normal"),
			f("revision", "Int", read_only=1, default="1"),
		],
		permissions=perms_operator_editable(),
		autoname="format:CAMP-{#####}",
	)


def create_display():
	create_doctype(
		"Display",
		fields=[
			f("display_name", "Data", reqd=1, in_list_view=1),
			f("device_identifier", "Data", reqd=1, unique=1, in_list_view=1),
			f("is_active", "Check", default="1"),
			f(
				"registration_status",
				"Select",
				options="\n".join(REGISTRATION_STATUSES),
				default="Pending",
				in_list_view=1,
			),
			f("client_version", "Data", read_only=1),
			f("last_seen", "Datetime", read_only=1),
			f("last_heartbeat", "Datetime", read_only=1),
			f("last_sync_at", "Datetime", read_only=1),
			f("last_sync_version", "Int", read_only=1),
			f("current_campaign", "Link", options="Campaign", read_only=1),
			f("current_playlist", "Link", options="Playlist", read_only=1),
			f("current_media", "Link", options="Media", read_only=1),
			f("last_error", "Small Text", read_only=1),
		],
		permissions=perms_admin_managed(),
		autoname="field:device_identifier",
	)


def create_display_group_member():
	create_doctype(
		"Display Group Member",
		fields=[
			f("display", "Link", options="Display", reqd=1, in_list_view=1),
		],
		istable=1,
	)


def create_display_group():
	create_doctype(
		"Display Group",
		fields=[
			f("group_name", "Data", reqd=1, unique=1, in_list_view=1),
			f("is_active", "Check", default="1"),
			f("members", "Table", options="Display Group Member"),
		],
		permissions=perms_admin_managed(),
		autoname="field:group_name",
	)


def create_schedule():
	weekday_fields = [f(day, "Check", default="0", in_list_view=(day in ("monday", "friday"))) for day in WEEKDAY_FIELDS]
	create_doctype(
		"Schedule",
		fields=[
			f("campaign", "Link", options="Campaign", reqd=1, in_list_view=1),
			f("recurrence_type", "Select", options="\n".join(RECURRENCE_TYPES), default="Always", reqd=1, in_list_view=1),
			f("start_date", "Date"),
			f("end_date", "Date"),
			f("start_time", "Time"),
			f("end_time", "Time"),
			*weekday_fields,
			f("is_active", "Check", default="1"),
			f("timezone_policy", "Select", options="\n".join(TIMEZONE_POLICIES), default="Display Local", reqd=1),
		],
		permissions=perms_operator_editable(),
		autoname="format:SCH-{#####}",
	)


def create_campaign_assignment():
	create_doctype(
		"Campaign Assignment",
		fields=[
			f("campaign", "Link", options="Campaign", reqd=1, in_list_view=1),
			f("target_type", "Select", options="\n".join(TARGET_TYPES), reqd=1, in_list_view=1),
			f("display", "Link", options="Display", in_list_view=1),
			f("display_group", "Link", options="Display Group", in_list_view=1),
			f("assignment_priority", "Int", default="0", in_list_view=1),
			f("is_active", "Check", default="1"),
		],
		permissions=perms_operator_editable(),
		autoname="format:ASG-{#####}",
	)


def create_signage_state_version():
	create_doctype(
		"Signage State Version",
		fields=[
			f("display", "Link", options="Display", reqd=1, unique=1, in_list_view=1),
			f("server_version", "Int", default="0", in_list_view=1),
			f("generated_at", "Datetime", read_only=1),
			f("last_change_reason", "Data", read_only=1),
		],
		permissions=perms_admin_managed(),
		autoname="field:display",
	)


def create_digital_signage_settings():
	create_doctype(
		"Digital Signage Settings",
		fields=[
			f("default_playlist", "Link", options="Playlist"),
		],
		permissions=perms_settings(),
		issingle=1,
	)
