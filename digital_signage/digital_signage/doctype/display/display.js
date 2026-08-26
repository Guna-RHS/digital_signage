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
