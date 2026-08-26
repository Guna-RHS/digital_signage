# Copyright (c) 2026, RHS Group and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from digital_signage.core.exceptions import SignageValidationError
from digital_signage.tests.factories import make_campaign, make_display, make_display_group, make_media, make_playlist


class TestCampaignAssignment(FrappeTestCase):
	def setUp(self):
		media = make_media(media_type="Video")
		playlist = make_playlist(items=[{"media": media.name, "sort_order": 1, "enabled": 1}])
		self.campaign = make_campaign(playlist.name)

	def test_direct_target_requires_display_only(self):
		display = make_display()
		other_display = make_display()
		group = make_display_group([other_display.name])
		with self.assertRaises(SignageValidationError):
			frappe.get_doc(
				{
					"doctype": "Campaign Assignment",
					"campaign": self.campaign.name,
					"target_type": "Display",
					"display": display.name,
					"display_group": group.name,
				}
			).insert(ignore_permissions=True)

	def test_group_target_requires_group_only(self):
		display = make_display()
		with self.assertRaises(SignageValidationError):
			frappe.get_doc(
				{
					"doctype": "Campaign Assignment",
					"campaign": self.campaign.name,
					"target_type": "Display Group",
					"display": display.name,
				}
			).insert(ignore_permissions=True)

	def test_target_type_must_match_a_populated_field(self):
		with self.assertRaises(SignageValidationError):
			frappe.get_doc(
				{
					"doctype": "Campaign Assignment",
					"campaign": self.campaign.name,
					"target_type": "Display",
				}
			).insert(ignore_permissions=True)

	def test_valid_direct_assignment_succeeds(self):
		display = make_display()
		assignment = frappe.get_doc(
			{
				"doctype": "Campaign Assignment",
				"campaign": self.campaign.name,
				"target_type": "Display",
				"display": display.name,
			}
		).insert(ignore_permissions=True)
		self.assertEqual(assignment.display, display.name)

	def test_valid_group_assignment_succeeds(self):
		display = make_display()
		group = make_display_group([display.name])
		assignment = frappe.get_doc(
			{
				"doctype": "Campaign Assignment",
				"campaign": self.campaign.name,
				"target_type": "Display Group",
				"display_group": group.name,
			}
		).insert(ignore_permissions=True)
		self.assertEqual(assignment.display_group, group.name)
