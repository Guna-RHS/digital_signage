// Copyright (c) 2026, RHS Group and contributors
// For license information, please see license.txt

frappe.ui.form.on("Display", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		frm.add_custom_button(__("Generate Pairing Code"), () => {
			frappe.call({
				method: "digital_signage.api.internal.generate_pairing_code",
				args: { display: frm.doc.name },
				callback: (r) => {
					if (!r.message) {
						return;
					}
					frappe.msgprint({
						title: __("Pairing Code"),
						message: __(
							"Code: <b>{0}</b><br>Valid for 15 minutes, single use. Enter this along with the device identifier ({1}) on the display to register it.",
							[r.message, frm.doc.device_identifier]
						),
						indicator: "green",
					});
				},
			});
		});

		if (frm.doc.registration_status === "Registered") {
			frm.add_custom_button(__("Force Sync"), () => {
				frappe.call({
					method: "digital_signage.api.internal.request_force_sync",
					args: { display: frm.doc.name },
					callback: () => {
						frappe.show_alert({
							message: __("Sync requested — the device will pick it up within ~15 seconds."),
							indicator: "green",
						});
						frm.reload_doc();
					},
				});
			});
		}

		frm.add_custom_button(
			__("Campaign Assignment"),
			() => {
				frappe.model.with_doctype("Campaign Assignment", () => {
					const new_doc = frappe.model.get_new_doc("Campaign Assignment");
					new_doc.target_type = "Display";
					new_doc.display = frm.doc.name;
					new_doc.is_active = 1;
					frappe.set_route("Form", "Campaign Assignment", new_doc.name);
				});
			},
			__("Create")
		);

		if (frm.doc.registration_status !== "Revoked") {
			frm.add_custom_button(__("Revoke Device"), () => {
				frappe.confirm(
					__("This immediately blocks the device from syncing or sending heartbeats. Continue?"),
					() => {
						frappe.call({
							method: "digital_signage.api.internal.revoke_device",
							args: { display: frm.doc.name },
							callback: () => frm.reload_doc(),
						});
					}
				);
			});
		}
	},
});
