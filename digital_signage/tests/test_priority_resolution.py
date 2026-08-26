import datetime

import frappe
from frappe.tests.utils import FrappeTestCase

from digital_signage.services.state_service import resolve_effective_state
from digital_signage.tests.factories import (
	make_assignment,
	make_campaign,
	make_display,
	make_display_group,
	make_media,
	make_playlist,
	make_schedule,
)

NOW = datetime.datetime(2026, 6, 15, 12, 0)


def _campaign_with_always_schedule(priority=0):
	media = make_media(media_type="Video")
	playlist = make_playlist(items=[{"media": media.name, "sort_order": 1, "enabled": 1}])
	campaign = make_campaign(playlist.name, priority=priority)
	make_schedule(campaign.name, recurrence_type="Always")
	return campaign


class TestPriorityResolution(FrappeTestCase):
	def test_direct_beats_group_regardless_of_priority(self):
		display = make_display()
		group = make_display_group([display.name])
		direct_campaign = _campaign_with_always_schedule()
		group_campaign = _campaign_with_always_schedule()
		make_assignment(direct_campaign.name, display=display.name, priority=1)
		make_assignment(group_campaign.name, display_group=group.name, priority=100)

		state = resolve_effective_state(display.name, at_datetime=NOW)
		self.assertEqual(state["campaigns"][0]["name"], direct_campaign.name)

	def test_higher_assignment_priority_wins_within_same_specificity(self):
		display = make_display()
		low = _campaign_with_always_schedule()
		high = _campaign_with_always_schedule()
		make_assignment(low.name, display=display.name, priority=1)
		make_assignment(high.name, display=display.name, priority=10)

		state = resolve_effective_state(display.name, at_datetime=NOW)
		self.assertEqual(state["campaigns"][0]["name"], high.name)

	def test_tie_break_prefers_newer_revision(self):
		display = make_display()
		campaign_a = _campaign_with_always_schedule()
		campaign_b = _campaign_with_always_schedule()
		make_assignment(campaign_a.name, display=display.name, priority=5)
		make_assignment(campaign_b.name, display=display.name, priority=5)

		# Bump campaign_a's revision past campaign_b's without changing anything meaningful.
		doc = frappe.get_doc("Campaign", campaign_a.name)
		doc.save(ignore_permissions=True)
		self.assertGreater(doc.revision, frappe.db.get_value("Campaign", campaign_b.name, "revision"))

		state = resolve_effective_state(display.name, at_datetime=NOW)
		self.assertEqual(state["campaigns"][0]["name"], campaign_a.name)

	def test_tie_break_falls_back_to_stable_campaign_name(self):
		display = make_display()
		campaign_a = _campaign_with_always_schedule()
		campaign_b = _campaign_with_always_schedule()
		make_assignment(campaign_a.name, display=display.name, priority=5)
		make_assignment(campaign_b.name, display=display.name, priority=5)

		state = resolve_effective_state(display.name, at_datetime=NOW)
		self.assertEqual(state["campaigns"][0]["name"], min(campaign_a.name, campaign_b.name))

	def test_inactive_campaign_is_excluded(self):
		display = make_display()
		campaign = _campaign_with_always_schedule()
		make_assignment(campaign.name, display=display.name)
		frappe.db.set_value("Campaign", campaign.name, "is_active", 0)

		state = resolve_effective_state(display.name, at_datetime=NOW)
		self.assertEqual(state["campaigns"], [])

	def test_inactive_assignment_is_excluded(self):
		display = make_display()
		campaign = _campaign_with_always_schedule()
		make_assignment(campaign.name, display=display.name, is_active=0)

		state = resolve_effective_state(display.name, at_datetime=NOW)
		self.assertEqual(state["campaigns"], [])

	def test_expired_schedule_is_excluded(self):
		display = make_display()
		media = make_media(media_type="Video")
		playlist = make_playlist(items=[{"media": media.name, "sort_order": 1, "enabled": 1}])
		campaign = make_campaign(playlist.name)
		make_schedule(
			campaign.name,
			recurrence_type="Date Range",
			start_date=datetime.date(2020, 1, 1),
			end_date=datetime.date(2020, 1, 31),
		)
		make_assignment(campaign.name, display=display.name)

		state = resolve_effective_state(display.name, at_datetime=NOW)
		self.assertEqual(state["campaigns"], [])

	def test_inactive_display_group_is_excluded(self):
		display = make_display()
		group = make_display_group([display.name], is_active=0)
		campaign = _campaign_with_always_schedule()
		make_assignment(campaign.name, display_group=group.name)

		state = resolve_effective_state(display.name, at_datetime=NOW)
		self.assertEqual(state["campaigns"], [])
