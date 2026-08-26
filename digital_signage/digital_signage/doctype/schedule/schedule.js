// Copyright (c) 2026, RHS Group and contributors
// For license information, please see license.txt

// A Schedule alone never shows anything on a screen -- it also needs at
// least one active Campaign Assignment pointing a Display (or Display
// Group) at the same campaign. That's easy to forget (it happened in this
// app's own testing), so after saving, check for one and say so plainly
// instead of leaving it to be discovered as "why isn't this showing up."
frappe.ui.form.on("Schedule", {
	after_save(frm) {
		if (!frm.doc.campaign) {
			return;
		}
		frappe.call({
			method: "frappe.client.get_count",
			args: { doctype: "Campaign Assignment", filters: { campaign: frm.doc.campaign, is_active: 1 } },
			callback: (r) => {
				if (r.message > 0) {
					return;
				}
				frappe.msgprint({
					title: __("This won't show on any screen yet"),
					indicator: "orange",
					message: __(
						"Campaign {0} has a Schedule now, but no active Campaign Assignment — nothing tells a Display to play it. Create one to assign it to a Display or Display Group.",
						[`<a href="/app/campaign/${frm.doc.campaign}">${frm.doc.campaign}</a>`]
					),
					primary_action: {
						label: __("Create Campaign Assignment"),
						action: () => {
							frappe.model.with_doctype("Campaign Assignment", () => {
								const new_doc = frappe.model.get_new_doc("Campaign Assignment");
								new_doc.campaign = frm.doc.campaign;
								new_doc.target_type = "Display";
								new_doc.is_active = 1;
								frappe.set_route("Form", "Campaign Assignment", new_doc.name);
							});
						},
					},
				});
			},
		});
	},
});
