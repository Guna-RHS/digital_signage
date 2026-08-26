import frappe
from frappe.tests.utils import FrappeTestCase

from digital_signage.core import device_auth
from digital_signage.core.device_errors import DeviceValidationError
from digital_signage.services.device_service import register_device
from digital_signage.services.heartbeat_service import record_heartbeat
from digital_signage.services.sync_service import build_sync_response
from digital_signage.tests.factories import make_pairing_code, register_test_device


class TestDeviceIdempotency(FrappeTestCase):
	def test_repeated_heartbeat_creates_no_duplicate_records(self):
		display, credential_identifier, secret = register_test_device()
		authenticated = device_auth.authenticate(credential_identifier, secret)
		record_heartbeat(authenticated, {"client_version": "1.0.0"})
		record_heartbeat(authenticated, {"client_version": "1.0.1"})
		self.assertEqual(frappe.db.count("Display", {"name": display.name}), 1)

	def test_repeated_sync_creates_no_duplicate_version_rows(self):
		display, credential_identifier, secret = register_test_device()
		authenticated = device_auth.authenticate(credential_identifier, secret)
		build_sync_response(authenticated)
		build_sync_response(authenticated)
		self.assertEqual(frappe.db.count("Signage State Version", {"display": display.name}), 1)

	def test_reusing_an_already_used_pairing_code_fails_cleanly(self):
		display, _credential_identifier, _secret = register_test_device()
		code = make_pairing_code(display.name)
		register_device(display.device_identifier, code)
		with self.assertRaises(DeviceValidationError):
			register_device(display.device_identifier, code)
		self.assertEqual(frappe.db.count("Device Credential", {"display": display.name, "is_active": 1}), 1)
