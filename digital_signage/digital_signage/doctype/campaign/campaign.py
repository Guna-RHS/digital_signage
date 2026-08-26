# Copyright (c) 2026, RHS Group and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from digital_signage.services import campaign_service, state_service


class Campaign(Document):
	def validate(self):
		campaign_service.validate(self)

	def on_update(self):
		state_service.record_change(self)
