// Copyright (c) 2026, RHS Group and contributors
// For license information, please see license.txt

// Same "Create" chain convention as Campaign's form (see campaign.js) --
// Playlist -> Campaign is the first hop in Media -> Playlist -> Campaign ->
// Schedule/Assignment -> Display.
frappe.ui.form.on("Playlist", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		frm.add_custom_button(
			__("Campaign"),
			() => {
				frappe.model.with_doctype("Campaign", () => {
					const new_doc = frappe.model.get_new_doc("Campaign");
					new_doc.playlist = frm.doc.name;
					frappe.set_route("Form", "Campaign", new_doc.name);
				});
			},
			__("Create")
		);
	},
});
