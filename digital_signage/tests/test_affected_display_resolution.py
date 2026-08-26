import frappe
from frappe.tests.utils import FrappeTestCase

from digital_signage.services.state_service import resolve_affected_displays
from digital_signage.tests.factories import (
	make_assignment,
	make_campaign,
	make_display,
	make_display_group,
	make_media,
	make_playlist,
	make_schedule,
)


class TestAffectedDisplayResolution(FrappeTestCase):
	def setUp(self):
		self.media = make_media(media_type="Video")
		self.playlist = make_playlist(items=[{"media": self.media.name, "sort_order": 1, "enabled": 1}])
		self.campaign = make_campaign(self.playlist.name)
		self.schedule = make_schedule(self.campaign.name, recurrence_type="Always")

	def test_direct_assignment_affects_only_that_display(self):
		display = make_display()
		unrelated = make_display()
		assignment = make_assignment(self.campaign.name, display=display.name)

		self.assertEqual(resolve_affected_displays(assignment), {display.name})
		self.assertNotIn(unrelated.name, resolve_affected_displays(assignment))

	def test_group_assignment_fans_out_to_members(self):
		d1, d2 = make_display(), make_display()
		unrelated = make_display()
		group = make_display_group([d1.name, d2.name])
		assignment = make_assignment(self.campaign.name, display_group=group.name)

		affected = resolve_affected_displays(assignment)
		self.assertEqual(affected, {d1.name, d2.name})
		self.assertNotIn(unrelated.name, affected)

	def test_campaign_change_resolves_through_its_assignments(self):
		display = make_display()
		make_assignment(self.campaign.name, display=display.name)
		self.assertEqual(resolve_affected_displays(self.campaign), {display.name})

	def test_playlist_change_resolves_through_campaigns_using_it(self):
		display = make_display()
		make_assignment(self.campaign.name, display=display.name)
		self.assertEqual(resolve_affected_displays(self.playlist), {display.name})

	def test_media_change_resolves_through_playlist_and_campaign(self):
		display = make_display()
		make_assignment(self.campaign.name, display=display.name)
		self.assertEqual(resolve_affected_displays(self.media), {display.name})

	def test_schedule_change_resolves_through_its_campaign(self):
		display = make_display()
		make_assignment(self.campaign.name, display=display.name)
		self.assertEqual(resolve_affected_displays(self.schedule), {display.name})

	def test_display_group_membership_change_affects_current_members(self):
		d1, d2 = make_display(), make_display()
		group = make_display_group([d1.name])
		group.append("members", {"display": d2.name})
		group.save(ignore_permissions=True)

		self.assertEqual(resolve_affected_displays(group), {d1.name, d2.name})

	def test_media_with_no_playlist_reference_affects_nothing(self):
		orphan_media = make_media(media_type="Video")
		self.assertEqual(resolve_affected_displays(orphan_media), set())
