"""Desk sidebar Workspace for the Digital Signage module — without this the
app has no landing page/sidebar entry in the desk, which is what "looks like
a real production app" actually means in Frappe terms (every other installed
app here — CRM, Tools, Build — has one).

Run once via:
    bench --site rhs.local execute digital_signage.setup.workspace.run

With developer_mode=1 this exports to
digital_signage/digital_signage/workspace/digital_signage/digital_signage.json
same as the DocTypes in bootstrap.py.
"""

import frappe

WORKSPACE_NAME = "Digital Signage"

# (label, doctype) — the handful of doctypes worth a one-click shortcut.
SHORTCUTS = [
	("Media", "Media"),
	("Displays", "Display"),
	("Campaigns", "Campaign"),
	("Playlists", "Playlist"),
	("Generated Content", "Generated Content"),
]

# (card title, [(label, doctype), ...]) — every doctype, grouped the way an
# operator actually thinks about them: what plays, when/who it plays for,
# what it plays on, and admin-only configuration.
CARDS = [
	("Content", [("Media", "Media"), ("Playlists", "Playlist")]),
	(
		"Templated Content",
		[("Content Templates", "Content Template"), ("Generated Content", "Generated Content")],
	),
	(
		"Campaigns & Scheduling",
		[("Campaigns", "Campaign"), ("Schedules", "Schedule"), ("Campaign Assignments", "Campaign Assignment")],
	),
	("Devices", [("Displays", "Display"), ("Display Groups", "Display Group")]),
	(
		"Configuration",
		[("Signage State Versions", "Signage State Version"), ("Digital Signage Settings", "Digital Signage Settings")],
	),
]


def run():
	# Re-runnable, not just idempotent-once: delete-and-recreate rather than
	# silently no-op'ing when it already exists, so this script stays the
	# one source of truth for the workspace layout — adding a doctype to
	# SHORTCUTS/CARDS above and re-running actually takes effect instead of
	# needing a manual desk edit every time (which is how Generated Content
	# and Content Template ended up missing from here in the first place).
	if frappe.db.exists("Workspace", WORKSPACE_NAME):
		frappe.delete_doc("Workspace", WORKSPACE_NAME, force=True, ignore_permissions=True)

	shortcuts = [
		{
			"label": label,
			"type": "DocType",
			"link_to": doctype,
			"doc_view": "List",
			"color": "Grey",
			"stats_filter": "[]",
		}
		for label, doctype in SHORTCUTS
	]

	links = []
	for card_title, items in CARDS:
		links.append({"type": "Card Break", "label": card_title})
		for label, doctype in items:
			links.append({"type": "Link", "label": label, "link_type": "DocType", "link_to": doctype})

	content = [_header("Your Shortcuts")]
	content += [_shortcut(label) for label, _doctype in SHORTCUTS]
	content.append(_spacer())
	content.append(_header("Documents"))
	content += [_card(card_title) for card_title, _items in CARDS]

	doc = frappe.get_doc(
		{
			"doctype": "Workspace",
			"name": WORKSPACE_NAME,
			"label": WORKSPACE_NAME,
			"title": WORKSPACE_NAME,
			"module": "Digital Signage",
			"icon": "image-view",
			"indicator_color": "blue",
			"public": 1,
			"is_hidden": 0,
			"sequence_id": 1.0,
			"content": frappe.as_json(content),
			"shortcuts": shortcuts,
			"links": links,
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	print("digital_signage workspace created")


def _block_id():
	return frappe.generate_hash(length=10)


def _header(text):
	return {"id": _block_id(), "type": "header", "data": {"text": f"<span class=\"h4\"><b>{text}</b></span>", "col": 12}}


def _shortcut(shortcut_name):
	return {"id": _block_id(), "type": "shortcut", "data": {"shortcut_name": shortcut_name, "col": 3}}


def _card(card_name):
	return {"id": _block_id(), "type": "card", "data": {"card_name": card_name, "col": 4}}


def _spacer():
	return {"id": _block_id(), "type": "spacer", "data": {"col": 12}}
