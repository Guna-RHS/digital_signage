# Copyright (c) 2026, RHS Group and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from digital_signage.services import state_service


class Display(Document):
	def on_update(self):
		state_service.record_change(self)
