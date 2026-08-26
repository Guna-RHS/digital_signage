// Copyright (c) 2026, RHS Group and contributors
// For license information, please see license.txt

frappe.ui.form.on("Generated Content", {
	refresh(frm) {
		if (frm.is_new() || frm.is_dirty()) {
			return;
		}

		frm.add_custom_button(__("Generate"), () => {
			frappe.call({
				method: "generate",
				doc: frm.doc,
				freeze: true,
				freeze_message: __("Rendering content..."),
				callback: () => frm.reload_doc(),
			});
		}).addClass(frm.doc.status === "Generated" ? "" : "btn-primary");
	},
});
