"""Replicates the spec's Definition-of-Done sequence for what Milestone 1
covers: upload media -> playlist -> campaign -> schedule -> assign display ->
sync returns correct state; then change something -> affected version changes
-> sync returns updated state. (The spec's "notification published" step is
Phase F/Milestone 2 — the version bump here is the mechanism a realtime
notification would later be triggered from.)"""

from frappe.tests.utils import FrappeTestCase

from digital_signage.core.versioning import get_server_version
from digital_signage.services.state_service import resolve_effective_state
from digital_signage.tests.factories import make_assignment, make_campaign, make_display, make_media, make_playlist, make_schedule


class TestFullSyncSequence(FrappeTestCase):
	def test_upload_to_effective_state_end_to_end(self):
		media = make_media(media_type="Video", lifecycle_status="Active")
		playlist = make_playlist(items=[{"media": media.name, "sort_order": 1, "enabled": 1}])
		campaign = make_campaign(playlist.name, priority=10)
		make_schedule(campaign.name, recurrence_type="Always")
		display = make_display()
		make_assignment(campaign.name, display=display.name)

		state = resolve_effective_state(display.name)

		self.assertEqual(state["campaigns"][0]["name"], campaign.name)
		self.assertEqual(state["playlists"][0]["name"], playlist.name)
		self.assertEqual(state["media"][0]["name"], media.name)
		self.assertEqual(state["assignments"][0]["display"], display.name)

	def test_reassigning_to_a_higher_priority_campaign_bumps_version_and_updates_state(self):
		media = make_media(media_type="Video", lifecycle_status="Active")
		playlist_low = make_playlist(items=[{"media": media.name, "sort_order": 1, "enabled": 1}])
		playlist_high = make_playlist(items=[{"media": media.name, "sort_order": 1, "enabled": 1}])
		low_campaign = make_campaign(playlist_low.name)
		high_campaign = make_campaign(playlist_high.name)
		make_schedule(low_campaign.name, recurrence_type="Always")
		make_schedule(high_campaign.name, recurrence_type="Always")

		display = make_display()
		make_assignment(low_campaign.name, display=display.name, priority=5)

		state = resolve_effective_state(display.name)
		self.assertEqual(state["campaigns"][0]["name"], low_campaign.name)
		version_before = get_server_version(display.name)

		make_assignment(high_campaign.name, display=display.name, priority=50)

		self.assertGreater(get_server_version(display.name), version_before)
		state_after = resolve_effective_state(display.name)
		self.assertEqual(state_after["campaigns"][0]["name"], high_campaign.name)
