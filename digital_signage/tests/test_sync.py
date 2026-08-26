import frappe
from frappe.tests.utils import FrappeTestCase

from digital_signage.core import device_auth
from digital_signage.services.sync_service import build_sync_response
from digital_signage.tests.factories import (
	make_assignment,
	make_campaign,
	make_media,
	make_playlist,
	make_schedule,
	register_test_device,
)


class TestSync(FrappeTestCase):
	def test_sync_returns_effective_state_plus_asset_manifest(self):
		display, credential_identifier, secret = register_test_device()
		media = make_media(media_type="Video", lifecycle_status="Active")
		playlist = make_playlist(items=[{"media": media.name, "sort_order": 1, "enabled": 1}])
		campaign = make_campaign(playlist.name)
		make_schedule(campaign.name, recurrence_type="Always")
		make_assignment(campaign.name, display=display.name)

		authenticated = device_auth.authenticate(credential_identifier, secret)
		state = build_sync_response(authenticated)

		self.assertEqual(state["campaigns"][0]["name"], campaign.name)
		self.assertEqual(len(state["assets"]), 1)
		asset = state["assets"][0]
		self.assertEqual(asset["asset_id"], media.name)
		self.assertEqual(asset["sha256"], media.sha256)
		self.assertEqual(
			asset["download_url"], f"/api/method/digital_signage.api.v1.assets.download?media={media.name}"
		)

	def test_sync_updates_last_sync_fields(self):
		display, credential_identifier, secret = register_test_device()
		authenticated = device_auth.authenticate(credential_identifier, secret)
		self.assertIsNone(frappe.db.get_value("Display", display.name, "last_sync_at"))

		state = build_sync_response(authenticated)

		self.assertIsNotNone(frappe.db.get_value("Display", display.name, "last_sync_at"))
		self.assertEqual(frappe.db.get_value("Display", display.name, "last_sync_version"), state["server_version"])

	def test_repeated_sync_is_safe(self):
		display, credential_identifier, secret = register_test_device()
		authenticated = device_auth.authenticate(credential_identifier, secret)
		build_sync_response(authenticated)
		state2 = build_sync_response(authenticated)
		self.assertIn("assets", state2)
