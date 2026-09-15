"""White-label the desk navbar.

Frappe ships a handful of standard items in the profile / help dropdown
(About, Frappe Support, ...) that link out to frappe.io. This deployment is
white-labelled, so we hide the ones that expose upstream Frappe branding.

Hooked into ``after_migrate`` (see hooks.py) so it re-applies on every deploy.
Idempotent -- it only touches rows that are not already hidden, and no-ops
once they are. Can also be run directly:

    bench --site <site> execute digital_signage.setup.navbar.hide_frappe_navbar_items
"""

import frappe

# ``item_label`` of each standard Navbar Item to hide from the desk header.
HIDDEN_NAVBAR_ITEMS = ("About", "Frappe Support")


def hide_frappe_navbar_items():
	if not frappe.db.exists("DocType", "Navbar Settings"):
		return

	settings = frappe.get_single("Navbar Settings")
	changed = False

	for item in settings.help_dropdown + settings.settings_dropdown:
		if item.item_label in HIDDEN_NAVBAR_ITEMS and not item.hidden:
			item.hidden = 1
			changed = True

	if not changed:
		return

	settings.flags.ignore_permissions = True
	settings.save()
	frappe.db.commit()
