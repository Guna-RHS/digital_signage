"""state_service.resolve_sync_state — the full-candidate-set envelope a
device actually syncs, as opposed to resolve_effective_state's single-winner
desk preview (see test_priority_resolution.py for that one). Added when the
client-player work surfaced that the original single-winner sync contract
didn't match either spec's own requirement that the client resolve
schedule/priority locally — see state_service.py's module docstring."""

import datetime

import frappe
from frappe.tests.utils import FrappeTestCase

from digital_signage.services.state_service import resolve_sync_state
from digital_signage.tests.factories import (
	make_assignment,
	make_campaign,
	make_display,
	make_display_group,
	make_media,
	make_playlist,
	make_schedule,
)


def _campaign_with_schedule(priority=0, **schedule_kwargs):
	media = make_media(media_type="Video", lifecycle_status="Active")
	playlist = make_playlist(items=[{"media": media.name, "sort_order": 1, "enabled": 1}])
	campaign = make_campaign(playlist.name, priority=priority)
	schedule_kwargs.setdefault("recurrence_type", "Always")
	make_schedule(campaign.name, **schedule_kwargs)
	return campaign, playlist, media


class TestResolveSyncState(FrappeTestCase):
	def setUp(self):
		# Digital Signage Settings.default_playlist is cached at the Python
		# process level (frappe.db.value_cache) independent of the DB
		# transaction rollback FrappeTestCase otherwise relies on for
		# isolation — a prior test setting a real playlist here bleeds into
		# later tests unless every test starts from a known state. Same
		# defensive pattern test_fallback.py already uses.
		frappe.db.set_single_value("Digital Signage Settings", "default_playlist", None)

	def test_all_eligible_campaigns_are_included_not_just_the_winner(self):
		display = make_display()
		low, low_playlist, low_media = _campaign_with_schedule(priority=1)
		high, high_playlist, high_media = _campaign_with_schedule(priority=100)
		make_assignment(low.name, display=display.name, priority=5)
		make_assignment(high.name, display=display.name, priority=50)

		state = resolve_sync_state(display.name)

		campaign_names = {c["name"] for c in state["campaigns"]}
		self.assertEqual(campaign_names, {low.name, high.name})
		playlist_names = {p["name"] for p in state["playlists"]}
		self.assertEqual(playlist_names, {low_playlist.name, high_playlist.name})
		media_names = {m["name"] for m in state["media"]}
		self.assertEqual(media_names, {low_media.name, high_media.name})

	def test_assignment_summary_includes_campaign(self):
		display = make_display()
		campaign, _playlist, _media = _campaign_with_schedule()
		make_assignment(campaign.name, display=display.name)

		state = resolve_sync_state(display.name)

		self.assertEqual(state["assignments"][0]["campaign"], campaign.name)

	def test_schedule_summary_includes_full_recurrence_fields(self):
		display = make_display()
		campaign, _playlist, _media = _campaign_with_schedule(
			recurrence_type="Date Range",
			all_day=0,
			start_date=datetime.date(2026, 1, 1),
			end_date=datetime.date(2026, 12, 31),
			start_time=datetime.time(9, 0),
			end_time=datetime.time(17, 0),
		)
		make_assignment(campaign.name, display=display.name)

		state = resolve_sync_state(display.name)

		schedule = state["schedules"][0]
		self.assertEqual(schedule["recurrence_type"], "Date Range")
		self.assertEqual(str(schedule["start_date"]), "2026-01-01")
		self.assertEqual(str(schedule["end_date"]), "2026-12-31")
		self.assertFalse(schedule["all_day"])
		self.assertIsNotNone(schedule["start_time"])
		self.assertIsNotNone(schedule["end_time"])

	def test_schedule_not_currently_in_window_is_still_included(self):
		"""The whole point: the client needs schedules it can't act on *yet*
		so it can switch locally at the boundary without re-syncing."""
		display = make_display()
		campaign, _playlist, _media = _campaign_with_schedule(
			recurrence_type="Date Range",
			start_date=datetime.date(2020, 1, 1),
			end_date=datetime.date(2020, 1, 31),
		)
		make_assignment(campaign.name, display=display.name)

		state = resolve_sync_state(display.name)

		self.assertEqual(state["campaigns"][0]["name"], campaign.name)
		self.assertEqual(state["schedules"][0]["campaign"], campaign.name)

	def test_direct_and_group_assignments_both_included(self):
		display = make_display()
		other_display = make_display()
		group = make_display_group([display.name, other_display.name])
		direct_campaign, _p1, _m1 = _campaign_with_schedule()
		group_campaign, _p2, _m2 = _campaign_with_schedule()
		make_assignment(direct_campaign.name, display=display.name)
		make_assignment(group_campaign.name, display_group=group.name)

		state = resolve_sync_state(display.name)

		campaign_names = {c["name"] for c in state["campaigns"]}
		self.assertEqual(campaign_names, {direct_campaign.name, group_campaign.name})

	def test_inactive_campaign_excluded(self):
		display = make_display()
		campaign, _playlist, _media = _campaign_with_schedule()
		make_assignment(campaign.name, display=display.name)
		frappe.db.set_value("Campaign", campaign.name, "is_active", 0)

		state = resolve_sync_state(display.name)

		self.assertEqual(state["campaigns"], [])

	def test_inactive_display_returns_no_campaigns_but_still_reports_fallback(self):
		display = make_display(is_active=0)
		media = make_media(media_type="Video", lifecycle_status="Active")
		fallback_playlist = make_playlist(items=[{"media": media.name, "sort_order": 1, "enabled": 1}])
		frappe.db.set_single_value("Digital Signage Settings", "default_playlist", fallback_playlist.name)

		state = resolve_sync_state(display.name)

		self.assertEqual(state["campaigns"], [])
		self.assertEqual(len(state["playlists"]), 1)
		self.assertEqual(state["playlists"][0]["name"], fallback_playlist.name)

	def test_fallback_playlist_included_alongside_eligible_campaigns(self):
		"""Fallback media must be locally available offline even when a
		campaign currently would win — the client needs it cached for the
		moment nothing else applies."""
		display = make_display()
		campaign, campaign_playlist, _media = _campaign_with_schedule()
		make_assignment(campaign.name, display=display.name)

		fallback_media = make_media(media_type="Video", lifecycle_status="Active")
		fallback_playlist = make_playlist(items=[{"media": fallback_media.name, "sort_order": 1, "enabled": 1}])
		frappe.db.set_single_value("Digital Signage Settings", "default_playlist", fallback_playlist.name)

		state = resolve_sync_state(display.name)

		playlist_names = {p["name"] for p in state["playlists"]}
		self.assertEqual(playlist_names, {campaign_playlist.name, fallback_playlist.name})

	def test_no_eligible_campaigns_and_no_fallback_is_fully_blank(self):
		display = make_display()

		state = resolve_sync_state(display.name)

		self.assertEqual(state["campaigns"], [])
		self.assertEqual(state["playlists"], [])
		self.assertEqual(state["media"], [])
