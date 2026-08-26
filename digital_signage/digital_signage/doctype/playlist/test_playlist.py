# Copyright (c) 2026, RHS Group and Contributors
# See license.txt

from frappe.tests.utils import FrappeTestCase

from digital_signage.core.exceptions import SignageValidationError
from digital_signage.tests.factories import make_media, make_playlist


class TestPlaylist(FrappeTestCase):
	def test_requires_explicit_sort_order(self):
		media = make_media(media_type="Video")
		with self.assertRaises(SignageValidationError):
			make_playlist(items=[{"media": media.name, "sort_order": None, "enabled": 1}])

	def test_rejects_duplicate_sort_order(self):
		media_a = make_media(media_type="Video")
		media_b = make_media(media_type="Video")
		with self.assertRaises(SignageValidationError):
			make_playlist(
				items=[
					{"media": media_a.name, "sort_order": 1, "enabled": 1},
					{"media": media_b.name, "sort_order": 1, "enabled": 1},
				]
			)

	def test_image_item_requires_positive_duration(self):
		media = make_media(media_type="Image")
		with self.assertRaises(SignageValidationError):
			make_playlist(items=[{"media": media.name, "sort_order": 1, "enabled": 1}])

	def test_video_item_does_not_require_duration(self):
		media = make_media(media_type="Video")
		playlist = make_playlist(items=[{"media": media.name, "sort_order": 1, "enabled": 1}])
		self.assertEqual(len(playlist.items), 1)

	def test_revision_bumps_on_update(self):
		playlist = make_playlist(items=[])
		self.assertEqual(playlist.revision, 1)
		playlist.description = "updated"
		playlist.save(ignore_permissions=True)
		self.assertEqual(playlist.revision, 2)
