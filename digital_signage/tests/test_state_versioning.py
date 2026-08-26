import frappe
from frappe.tests.utils import FrappeTestCase

from digital_signage.core.versioning import get_server_version
from digital_signage.tests.factories import make_assignment, make_campaign, make_display, make_media, make_playlist


class TestStateVersioning(FrappeTestCase):
	def setUp(self):
		media = make_media(media_type="Video")
		self.playlist = make_playlist(items=[{"media": media.name, "sort_order": 1, "enabled": 1}])
		self.campaign = make_campaign(self.playlist.name)

	def test_version_increments_when_assigned_campaign_changes(self):
		display = make_display()
		make_assignment(self.campaign.name, display=display.name)
		version_after_assignment = get_server_version(display.name)
		self.assertGreaterEqual(version_after_assignment, 1)

		campaign_doc = frappe.get_doc("Campaign", self.campaign.name)
		campaign_doc.title = "Renamed"
		campaign_doc.save(ignore_permissions=True)

		self.assertGreater(get_server_version(display.name), version_after_assignment)

	def test_version_unaffected_for_unrelated_display(self):
		display = make_display()
		unrelated = make_display()
		version_before = get_server_version(unrelated.name)
		make_assignment(self.campaign.name, display=display.name)

		campaign_doc = frappe.get_doc("Campaign", self.campaign.name)
		campaign_doc.title = "Renamed Again"
		campaign_doc.save(ignore_permissions=True)

		self.assertEqual(get_server_version(unrelated.name), version_before)

	def test_last_change_reason_is_recorded(self):
		display = make_display()
		make_assignment(self.campaign.name, display=display.name)

		version_doc = frappe.get_doc("Signage State Version", display.name)
		self.assertIn("Campaign Assignment", version_doc.last_change_reason)

	def test_creating_a_display_bumps_its_own_version(self):
		# Display.on_update -> record_change resolves to {self}, so the row a
		# display is created in is itself a version-relevant change (e.g. a
		# freshly-registered display's is_active/registration_status matter).
		display = make_display()
		self.assertEqual(get_server_version(display.name), 1)
