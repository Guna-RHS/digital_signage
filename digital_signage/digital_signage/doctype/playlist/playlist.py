# Copyright (c) 2026, RHS Group and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from digital_signage.services import playlist_service, state_service


class Playlist(Document):
	def validate(self):
		playlist_service.validate(self)

	def on_update(self):
		state_service.record_change(self)
