import frappe
from frappe.tests.utils import FrappeTestCase

from digital_signage.services.state_service import resolve_effective_state
from digital_signage.tests.factories import (
	make_assignment,
	make_campaign,
	make_display,
	make_media,
	make_playlist,
	make_schedule,
)


class TestFallback(FrappeTestCase):
	def test_default_playlist_used_when_no_campaign_applies(self):
		display = make_display()
		media = make_media(media_type="Video", lifecycle_status="Active")
		fallback_playlist = make_playlist(items=[{"media": media.name, "sort_order": 1, "enabled": 1}])
		frappe.db.set_single_value("Digital Signage Settings", "default_playlist", fallback_playlist.name)

		state = resolve_effective_state(display.name)

		self.assertEqual(state["campaigns"], [])
		self.assertEqual(len(state["playlists"]), 1)
		self.assertEqual(state["playlists"][0]["name"], fallback_playlist.name)

	def test_blank_when_no_fallback_configured(self):
		display = make_display()
		frappe.db.set_single_value("Digital Signage Settings", "default_playlist", None)

		state = resolve_effective_state(display.name)

		self.assertEqual(state["campaigns"], [])
		self.assertEqual(state["playlists"], [])
		self.assertEqual(state["media"], [])

	def test_inactive_fallback_playlist_treated_as_blank(self):
		display = make_display()
		media = make_media(media_type="Video", lifecycle_status="Active")
		fallback_playlist = make_playlist(items=[{"media": media.name, "sort_order": 1, "enabled": 1}])
		frappe.db.set_value("Playlist", fallback_playlist.name, "is_active", 0)
		frappe.db.set_single_value("Digital Signage Settings", "default_playlist", fallback_playlist.name)

		state = resolve_effective_state(display.name)

		self.assertEqual(state["playlists"], [])

	def test_fallback_key_reports_configured_default_even_when_a_campaign_wins(self):
		display = make_display()
		media = make_media(media_type="Video", lifecycle_status="Active")
		fallback_playlist = make_playlist(items=[{"media": media.name, "sort_order": 1, "enabled": 1}])
		frappe.db.set_single_value("Digital Signage Settings", "default_playlist", fallback_playlist.name)

		active_playlist = make_playlist(items=[{"media": media.name, "sort_order": 1, "enabled": 1}])
		campaign = make_campaign(active_playlist.name)
		make_schedule(campaign.name, recurrence_type="Always")
		make_assignment(campaign.name, display=display.name)

		state = resolve_effective_state(display.name)

		self.assertEqual(state["campaigns"][0]["name"], campaign.name)
		self.assertEqual(state["fallback"]["default_playlist"], fallback_playlist.name)
