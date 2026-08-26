// Copyright (c) 2026, RHS Group and contributors
// For license information, please see license.txt

// The mirror image of schedule.js's reminder: an Assignment alone doesn't
// show anything either without an active Schedule on the same campaign
// telling it *when* to play.
frappe.ui.form.on("Campaign Assignment", {
	after_save(frm) {
		if (!frm.doc.campaign) {
			return;
		}
		frappe.call({
			method: "frappe.client.get_count",
			args: { doctype: "Schedule", filters: { campaign: frm.doc.campaign, is_active: 1 } },
			callback: (r) => {
				if (r.message > 0) {
					return;
				}
				frappe.msgprint({
					title: __("This won't show on any screen yet"),
					indicator: "orange",
					message: __(
						"Campaign {0} is now assigned to a Display, but has no active Schedule — nothing tells it when to play. Create one so it actually becomes eligible.",
						[`<a href="/app/campaign/${frm.doc.campaign}">${frm.doc.campaign}</a>`]
					),
					primary_action: {
						label: __("Create Schedule"),
						action: () => {
							frappe.model.with_doctype("Schedule", () => {
								const new_doc = frappe.model.get_new_doc("Schedule");
								new_doc.campaign = frm.doc.campaign;
								new_doc.recurrence_type = "Always";
								new_doc.all_day = 1;
								new_doc.timezone_policy = "Display Local";
								new_doc.is_active = 1;
								frappe.set_route("Form", "Schedule", new_doc.name);
							});
						},
					},
				});
			},
		});
	},
});
