# Copyright (c) 2026, RHS Group and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from digital_signage.core.exceptions import SignageConflictError, SignageValidationError
from digital_signage.tests.factories import advance_media_lifecycle, make_media, make_playlist, replace_media_file


class TestMedia(FrappeTestCase):
	def test_upload_computes_hash_and_metadata(self):
		media = make_media(content=b"hello-world")
		self.assertEqual(len(media.sha256), 64)
		self.assertEqual(media.file_size, len(b"hello-world"))
		self.assertEqual(media.asset_version, 1)
		self.assertEqual(media.lifecycle_status, "Uploaded")

	def test_allowed_lifecycle_transitions(self):
		media = make_media()
		advance_media_lifecycle(media, "Retired")
		self.assertEqual(media.lifecycle_status, "Retired")
		self.assertEqual(media.is_active, 0)

	def test_rejects_skipping_lifecycle_states(self):
		media = make_media()
		media.lifecycle_status = "Active"
		self.assertRaises(SignageValidationError, media.save, ignore_permissions=True)

	def test_asset_version_bumps_on_content_change(self):
		media = make_media(content=b"version-one")
		original_hash = media.sha256
		replace_media_file(media, content=b"version-two")
		self.assertNotEqual(media.sha256, original_hash)
		self.assertEqual(media.asset_version, 2)

	def test_deletion_blocked_unless_retired(self):
		media = make_media()
		self.assertRaises(SignageConflictError, media.delete)

	def test_deletion_blocked_if_referenced_by_playlist(self):
		media = make_media(lifecycle_status="Retired")
		make_playlist(items=[{"media": media.name, "sort_order": 1, "image_duration_seconds": 5, "enabled": 1}])
		self.assertRaises(SignageConflictError, media.delete)

	def test_deletion_allowed_when_retired_and_unreferenced(self):
		media = make_media(lifecycle_status="Retired")
		media.delete()
		self.assertFalse(frappe.db.exists("Media", media.name))
