// Copyright (c) 2026, RHS Group and contributors
// For license information, please see license.txt

// Schedule and Campaign Assignment both link back to Campaign but have no
// field of their own on this form, so setting up a campaign otherwise meant
// leaving this screen twice (once per doctype) just to create a linked row
// and come back. Follows the same "Create" button convention as ERPNext's
// Quotation -> Sales Order -> Delivery Note/Sales Invoice chain: a grouped
// dropdown that creates the next document in the flow, pre-filled, and
// routes to its full form for review before saving -- not a modal with a
// reduced field set.
frappe.ui.form.on("Campaign", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		frm.add_custom_button(
			__("Schedule"),
			() => create_linked_doc(frm, "Schedule", { campaign: frm.doc.name, timezone_policy: "Display Local", is_active: 1 }),
			__("Create")
		);
		frm.add_custom_button(
			__("Campaign Assignment"),
			() => create_linked_doc(frm, "Campaign Assignment", { campaign: frm.doc.name, target_type: "Display", is_active: 1 }),
			__("Create")
		);

		render_linked_list(frm, "Schedule", __("Schedules"), ["name", "recurrence_type", "all_day", "start_time", "end_time", "is_active"], (r) =>
			`${r.name}: ${r.recurrence_type}${r.all_day ? " · " + __("all day") : ` · ${r.start_time || ""}-${r.end_time || ""}`}${r.is_active ? "" : " · " + __("inactive")}`
		);
		render_linked_list(
			frm,
			"Campaign Assignment",
			__("Assignments"),
			["name", "target_type", "display", "display_group", "assignment_priority", "is_active"],
			(r) => `${r.name}: ${r.target_type} → ${r.display || r.display_group || "?"} · ${__("priority")} ${r.assignment_priority}${r.is_active ? "" : " · " + __("inactive")}`
		);
	},
});

/// Shared by every "Create" button in this app (Playlist -> Campaign,
/// Campaign -> Schedule/Campaign Assignment, Display -> Campaign
/// Assignment): creates a new, unsaved document of `doctype`, pre-fills the
/// given field values, and routes to its full form -- the user reviews/
/// completes it and saves themselves, same as ERPNext's chained "Create".
function create_linked_doc(frm, doctype, values) {
	frappe.model.with_doctype(doctype, () => {
		const new_doc = frappe.model.get_new_doc(doctype);
		Object.assign(new_doc, values);
		frappe.set_route("Form", doctype, new_doc.name);
	});
}

function render_linked_list(frm, doctype, section_label, list_fields, row_text) {
	const wrapper_name = `linked_${frappe.scrub(doctype)}_wrapper`;
	if (!frm[wrapper_name]) {
		frm[wrapper_name] = $(`<div style="margin-top: 12px;"></div>`).insertAfter(frm.$wrapper.find(".form-layout"));
	}
	const $wrapper = frm[wrapper_name];
	$wrapper.empty();

	$(`<h6 style="margin-bottom: 6px;">${section_label}</h6>`).appendTo($wrapper);
	const $list = $(`<div class="text-muted" style="font-size: 12px; margin-bottom: 6px;"></div>`).appendTo($wrapper);

	frappe.call({
		method: "frappe.client.get_list",
		args: { doctype, filters: { campaign: frm.doc.name }, fields: list_fields, limit_page_length: 0 },
		callback: (r) => {
			const rows = r.message || [];
			if (!rows.length) {
				$list.text(__("None yet — use Create above."));
				return;
			}
			$list.empty();
			rows.forEach((row) => {
				$(`<div>`)
					.text(row_text(row))
					.css("cursor", "pointer")
					.on("click", () => frappe.set_route("Form", doctype, row.name))
					.appendTo($list);
			});
		},
	});
}
