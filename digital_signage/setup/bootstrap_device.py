"""Milestone 2 DocType creation — Device Pairing Code + Device Credential.
Same scripted approach as setup/bootstrap.py (see that file's docstring for
why); run once via:
    bench --site rhs.local execute digital_signage.setup.bootstrap_device.run
"""

import frappe

from digital_signage.setup.bootstrap import create_doctype, f, perms_admin_managed


def run():
	create_device_pairing_code()
	create_device_credential()
	frappe.db.commit()
	print("digital_signage device bootstrap complete")


def create_device_pairing_code():
	create_doctype(
		"Device Pairing Code",
		fields=[
			f("display", "Link", options="Display", reqd=1, in_list_view=1),
			f("code_hash", "Data", read_only=1),
			f("expires_at", "Datetime", read_only=1, in_list_view=1),
			f("used_at", "Datetime", read_only=1, in_list_view=1),
			f("is_active", "Check", default="1"),
		],
		permissions=perms_admin_managed(),
		autoname="format:PAIR-{#####}",
	)


def create_device_credential():
	create_doctype(
		"Device Credential",
		fields=[
			f("display", "Link", options="Display", reqd=1, in_list_view=1),
			f("credential_identifier", "Data", reqd=1, unique=1, in_list_view=1),
			f("credential_secret_hash", "Data", read_only=1),
			f("issued_at", "Datetime", read_only=1),
			f("expires_at", "Datetime", read_only=1),
			f("revoked_at", "Datetime", read_only=1),
			f("last_used_at", "Datetime", read_only=1, in_list_view=1),
			f("is_active", "Check", default="1", in_list_view=1),
		],
		permissions=perms_admin_managed(),
		autoname="field:credential_identifier",
	)
