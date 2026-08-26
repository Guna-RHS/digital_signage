# Copyright (c) 2026, RHS Group and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from digital_signage.services import media_service, template_service


class GeneratedContent(Document):
	@frappe.whitelist()
	def generate(self):
		"""Renders this record's Content Template with its own field values
		(title/subtitle/people -- one Person row per name+logo, any count)
		via a headless browser, then creates a real Media record from the
		result through the same Uploaded->Validated->Active lifecycle every
		other Media goes through -- nothing downstream treats generated
		media any differently from an uploaded one. Branches on the
		template's own Background Type: Image produces a screenshot PNG,
		Video records the overlay over the background video for exactly
		that video's own duration and produces a webm."""
		try:
			template = frappe.get_doc("Content Template", self.content_template)
			context = template_service.build_context(self)

			if template.background_type == "Video":
				content_bytes = template_service.render_to_video(template, context)
				media_type = "Video"
				filename = f"{frappe.scrub(self.title)}.webm"
			else:
				content_bytes = template_service.render_to_png(template, context)
				media_type = "Image"
				filename = f"{frappe.scrub(self.title)}.png"

			media = media_service.create_from_bytes(
				title=self.title,
				media_type=media_type,
				filename=filename,
				content=content_bytes,
			)

			self.generated_media = media.name
			self.status = "Generated"
			self.last_error = None
		except Exception as e:
			self.status = "Failed"
			self.last_error = str(e)
			self.save(ignore_permissions=True)
			raise

		self.save(ignore_permissions=True)
		return self.generated_media
