import frappe
from frappe.tests.utils import FrappeTestCase

from digital_signage.core import device_auth
from digital_signage.core.versioning import get_server_version
from digital_signage.services.heartbeat_service import record_heartbeat
from digital_signage.tests.factories import register_test_device


class TestHeartbeat(FrappeTestCase):
	def test_heartbeat_updates_display_fields(self):
		display, credential_identifier, secret = register_test_device()
		authenticated = device_auth.authenticate(credential_identifier, secret)

		record_heartbeat(authenticated, {"client_version": "1.2.3", "current_campaign": "CAMP-00001"})

		refreshed = frappe.get_doc("Display", display.name)
		self.assertEqual(refreshed.client_version, "1.2.3")
		self.assertEqual(refreshed.current_campaign, "CAMP-00001")
		self.assertIsNotNone(refreshed.last_heartbeat)
		self.assertIsNotNone(refreshed.last_seen)

	def test_malformed_payload_does_not_raise(self):
		display, credential_identifier, secret = register_test_device()
		authenticated = device_auth.authenticate(credential_identifier, secret)
		record_heartbeat(authenticated, None)
		record_heartbeat(authenticated, {"unexpected_key": "whatever"})

	def test_heartbeat_does_not_bump_state_version(self):
		display, credential_identifier, secret = register_test_device()
		authenticated = device_auth.authenticate(credential_identifier, secret)
		version_before = get_server_version(display.name)

		record_heartbeat(authenticated, {"client_version": "9.9.9"})

		self.assertEqual(get_server_version(display.name), version_before)
