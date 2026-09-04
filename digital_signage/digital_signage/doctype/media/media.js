// Copyright (c) 2026, RHS Group and contributors
// For license information, please see license.txt

// lifecycle_status is deliberately read_only on this form (so it can't be
// free-typed to an invalid value) -- these buttons are the only way to
// actually move it forward, via api.internal.advance_media_lifecycle,
// which still goes through the normal save()-enforced state machine
// (media_service._validate_lifecycle_transition), just from a button
// instead of the disabled field.
const MEDIA_LIFECYCLE_NEXT_STATUS = {
	Uploaded: "Validated",
	Validated: "Active",
};

frappe.ui.form.on("Media", {
	refresh(frm) {
		if (frm.is_new() || frm.is_dirty()) return;

		const next = MEDIA_LIFECYCLE_NEXT_STATUS[frm.doc.lifecycle_status];
		if (next) {
			frm.add_custom_button(__("Mark {0}", [next]), () => advance(frm, next)).addClass("btn-primary");
		}

		if (frm.doc.lifecycle_status !== "Retired") {
			frm.add_custom_button(__("Retire"), () => {
				frappe.confirm(
					__("Retire this Media? It stops appearing in any Playlist and can't be un-retired."),
					() => advance(frm, "Retired")
				);
			});
		}
	},
});

function advance(frm, status) {
	frappe.call({
		method: "digital_signage.api.internal.advance_media_lifecycle",
		args: { media: frm.doc.name, status },
		freeze: true,
		freeze_message: __("Updating..."),
		callback: () => frm.reload_doc(),
	});
}
