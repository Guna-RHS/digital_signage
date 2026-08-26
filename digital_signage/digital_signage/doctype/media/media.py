# Copyright (c) 2026, RHS Group and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from digital_signage.services import media_service, state_service


class Media(Document):
	def validate(self):
		media_service.validate(self)

	def on_update(self):
		state_service.record_change(self)

	def on_trash(self):
		media_service.guard_deletion(self)
