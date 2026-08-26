# Copyright (c) 2026, RHS Group and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from digital_signage.services import schedule_service, state_service


class Schedule(Document):
	def validate(self):
		schedule_service.validate(self)

	def on_update(self):
		state_service.record_change(self)

	def on_trash(self):
		state_service.record_change(self)
