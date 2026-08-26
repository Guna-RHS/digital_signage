import frappe
from frappe.tests.utils import FrappeTestCase

from digital_signage.core.device_errors import DeviceValidationError
from digital_signage.services import asset_service
from digital_signage.tests.factories import (
	make_assignment,
	make_campaign,
	make_media,
	make_playlist,
	make_schedule,
	register_test_device,
)


class TestAssetDownload(FrappeTestCase):
	def _display_with_active_media(self, content=b"asset-bytes"):
		display, _credential_identifier, _secret = register_test_device()
		media = make_media(media_type="Video", lifecycle_status="Active", content=content)
		playlist = make_playlist(items=[{"media": media.name, "sort_order": 1, "enabled": 1}])
		campaign = make_campaign(playlist.name)
		make_schedule(campaign.name, recurrence_type="Always")
		make_assignment(campaign.name, display=display.name)
		return display, media

	def test_authorized_download_streams_correct_bytes(self):
		display, media = self._display_with_active_media(content=b"exact-bytes-here")
		media_doc = asset_service.authorize_download(display, media.name)
		asset_service.stream(media_doc)
		self.assertEqual(frappe.response["filecontent"], b"exact-bytes-here")
		self.assertEqual(frappe.response["type"], "download")

	def test_media_outside_current_state_is_rejected(self):
		display, _media = self._display_with_active_media()
		orphan_media = make_media(media_type="Video", lifecycle_status="Active")
		with self.assertRaises(DeviceValidationError):
			asset_service.authorize_download(display, orphan_media.name)

	def test_unknown_media_is_rejected(self):
		display, _media = self._display_with_active_media()
		with self.assertRaises(DeviceValidationError):
			asset_service.authorize_download(display, "MEDIA-does-not-exist")
