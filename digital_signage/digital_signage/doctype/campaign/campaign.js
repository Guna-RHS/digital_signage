// Copyright (c) 2026, RHS Group and contributors
// For license information, please see license.txt

// Schedule and Campaign Assignment both link back to Campaign but have no
// field of their own on this form, so setting up a campaign otherwise means
// leaving this screen twice (once per doctype) just to create a linked row
// and come back. These two sections do both in place, no navigation away.
frappe.ui.form.on("Campaign", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		render_linked_list(frm, {
			doctype: "Schedule",
			section_label: __("Schedules"),
			button_label: __("Add Schedule"),
			list_fields: ["name", "recurrence_type", "all_day", "start_time", "end_time", "is_active"],
			row_text: (r) =>
				`${r.name}: ${r.recurrence_type}${r.all_day ? " · " + __("all day") : ` · ${r.start_time || ""}-${r.end_time || ""}`}${r.is_active ? "" : " · " + __("inactive")}`,
			dialog_fields: [
				{
					fieldname: "recurrence_type",
					fieldtype: "Select",
					label: __("Recurrence Type"),
					options: "Always\nDate Range\nDaily\nSelected Days",
					default: "Always",
					reqd: 1,
				},
				{ fieldname: "start_date", fieldtype: "Date", label: __("Start Date") },
				{ fieldname: "end_date", fieldtype: "Date", label: __("End Date") },
				{ fieldname: "col_break_1", fieldtype: "Column Break" },
				{ fieldname: "all_day", fieldtype: "Check", label: __("All Day"), default: 1 },
				{ fieldname: "start_time", fieldtype: "Time", label: __("Start Time"), depends_on: "eval:!doc.all_day" },
				{ fieldname: "end_time", fieldtype: "Time", label: __("End Time"), depends_on: "eval:!doc.all_day" },
				{ fieldname: "sec_break_1", fieldtype: "Section Break", label: __("Selected Days") },
				{ fieldname: "monday", fieldtype: "Check", label: __("Monday") },
				{ fieldname: "tuesday", fieldtype: "Check", label: __("Tuesday") },
				{ fieldname: "wednesday", fieldtype: "Check", label: __("Wednesday") },
				{ fieldname: "thursday", fieldtype: "Check", label: __("Thursday") },
				{ fieldname: "friday", fieldtype: "Check", label: __("Friday") },
				{ fieldname: "saturday", fieldtype: "Check", label: __("Saturday") },
				{ fieldname: "sunday", fieldtype: "Check", label: __("Sunday") },
			],
			defaults: { timezone_policy: "Display Local", is_active: 1 },
		});

		render_linked_list(frm, {
			doctype: "Campaign Assignment",
			section_label: __("Assignments"),
			button_label: __("Add Assignment"),
			list_fields: ["name", "target_type", "display", "display_group", "assignment_priority", "is_active"],
			row_text: (r) =>
				`${r.name}: ${r.target_type} → ${r.display || r.display_group || "?"} · ${__("priority")} ${r.assignment_priority}${r.is_active ? "" : " · " + __("inactive")}`,
			dialog_fields: [
				{
					fieldname: "target_type",
					fieldtype: "Select",
					label: __("Target Type"),
					options: "Display\nDisplay Group",
					default: "Display",
					reqd: 1,
				},
				{
					fieldname: "display",
					fieldtype: "Link",
					label: __("Display"),
					options: "Display",
					depends_on: "eval:doc.target_type=='Display'",
					mandatory_depends_on: "eval:doc.target_type=='Display'",
				},
				{
					fieldname: "display_group",
					fieldtype: "Link",
					label: __("Display Group"),
					options: "Display Group",
					depends_on: "eval:doc.target_type=='Display Group'",
					mandatory_depends_on: "eval:doc.target_type=='Display Group'",
				},
				{ fieldname: "assignment_priority", fieldtype: "Int", label: __("Assignment Priority"), default: 500 },
			],
			defaults: { is_active: 1 },
		});
	},
});

function render_linked_list(frm, opts) {
	const wrapper_name = `linked_${frappe.scrub(opts.doctype)}_wrapper`;
	if (!frm[wrapper_name]) {
		frm[wrapper_name] = $(`<div style="margin-top: 12px;"></div>`).insertAfter(frm.$wrapper.find(".form-layout"));
	}
	const $wrapper = frm[wrapper_name];
	$wrapper.empty();

	const $title = $(`<h6 style="margin-bottom: 6px;">${opts.section_label}</h6>`).appendTo($wrapper);
	const $list = $(`<div class="text-muted" style="font-size: 12px; margin-bottom: 6px;"></div>`).appendTo($wrapper);

	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: opts.doctype,
			filters: { campaign: frm.doc.name },
			fields: opts.list_fields,
			limit_page_length: 0,
		},
		callback: (r) => {
			const rows = r.message || [];
			if (!rows.length) {
				$list.text(__("None yet."));
			} else {
				$list.empty();
				rows.forEach((row) => {
					$(`<div>`)
						.text(opts.row_text(row))
						.css("cursor", "pointer")
						.on("click", () => frappe.set_route("Form", opts.doctype, row.name))
						.appendTo($list);
				});
			}
		},
	});

	$(`<button class="btn btn-xs btn-default">${opts.button_label}</button>`)
		.on("click", () => open_add_dialog(frm, opts))
		.appendTo($title);
	$title.css("display", "flex").css("justify-content", "space-between").css("align-items", "center");
}

function open_add_dialog(frm, opts) {
	const dialog = new frappe.ui.Dialog({
		title: opts.button_label,
		fields: opts.dialog_fields,
		primary_action_label: __("Save"),
		primary_action(values) {
			frappe.call({
				method: "frappe.client.insert",
				args: {
					doc: {
						doctype: opts.doctype,
						campaign: frm.doc.name,
						...opts.defaults,
						...values,
					},
				},
				freeze: true,
				callback: () => {
					dialog.hide();
					frappe.show_alert({ message: __("Added."), indicator: "green" });
					render_linked_list(frm, opts);
				},
			});
		},
	});
	dialog.show();
}
