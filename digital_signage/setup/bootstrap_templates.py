"""Templated content generation — Content Template + Generated Content
DocTypes. Reuses bootstrap.py's create_doctype/f/perm pattern (not imported
— bootstrap.py's run() is a standalone Milestone 1 entrypoint; this is a
separate, later addition run on its own):

    bench --site rhs.local execute digital_signage.setup.bootstrap_templates.run

Idempotent, same as bootstrap.py — checks frappe.db.exists first.
"""

import frappe

MODULE = "Digital Signage"


def f(fieldname, fieldtype, **kw):
	label = kw.pop("label", fieldname.replace("_", " ").title())
	return {"fieldname": fieldname, "fieldtype": fieldtype, "label": label, **kw}


def perm(role, read=1, write=0, create=0, delete=0):
	return {"role": role, "read": read, "write": write, "create": create, "delete": delete}


def perms_operator_editable():
	return [
		perm("Administrator", 1, 1, 1, 1),
		perm("System Manager", 1, 1, 1, 1),
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


def run():
	create_content_template()
	create_generated_content_person()
	create_generated_content()
	frappe.db.commit()
	print("digital_signage templates bootstrap complete")


def create_content_template():
	create_doctype(
		"Content Template",
		fields=[
			f("template_name", "Data", reqd=1, in_list_view=1, unique=1),
			f(
				"html_body",
				"Code",
				options="HTML",
				reqd=1,
				description=(
					"Jinja2 body rendered via frappe.render_template. Available in "
					"context: title, subtitle, people (list of {person_name, "
					"person_title, logo_url}), background_url."
				),
			),
			f("background_image", "Attach Image"),
			f("width", "Int", default="1920", reqd=1),
			f("height", "Int", default="1080", reqd=1),
			f("is_active", "Check", default="1"),
		],
		permissions=perms_operator_editable(),
		autoname="field:template_name",
	)


def create_generated_content_person():
	create_doctype(
		"Generated Content Person",
		fields=[
			f("person_name", "Data", reqd=1, in_list_view=1),
			f("person_title", "Data", in_list_view=1),
			f("logo", "Attach Image"),
		],
		istable=1,
	)


def create_generated_content():
	create_doctype(
		"Generated Content",
		fields=[
			f("title", "Data", reqd=1, in_list_view=1, description="Also passed into the template as `title`."),
			f("content_template", "Link", options="Content Template", reqd=1, in_list_view=1),
			f("subtitle", "Data"),
			f("people", "Table", options="Generated Content Person"),
			f(
				"status",
				"Select",
				options="Draft\nGenerated\nFailed",
				default="Draft",
				read_only=1,
				in_list_view=1,
			),
			f("generated_media", "Link", options="Media", read_only=1, in_list_view=1),
			f("last_error", "Small Text", read_only=1),
		],
		permissions=perms_operator_editable(),
		autoname="format:GEN-{#####}",
	)
