import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from digital_signage.core.device_auth import authenticate
from digital_signage.core.device_errors import AuthenticationFailed, DeviceDisabled, DeviceRevoked
from digital_signage.services.device_service import revoke_device
from digital_signage.tests.factories import register_test_device


class TestDeviceAuth(FrappeTestCase):
	def test_valid_credential_succeeds(self):
		display, credential_identifier, secret = register_test_device()
		self.assertEqual(authenticate(credential_identifier, secret).name, display.name)

	def test_wrong_secret_fails(self):
		_, credential_identifier, _ = register_test_device()
		with self.assertRaises(AuthenticationFailed):
			authenticate(credential_identifier, "totally-wrong")

	def test_unknown_credential_fails(self):
		with self.assertRaises(AuthenticationFailed):
			authenticate("CRED-does-not-exist", "whatever")

	def test_revoked_credential_fails(self):
		_, credential_identifier, secret = register_test_device()
		frappe.db.set_value(
			"Device Credential", credential_identifier, {"is_active": 0, "revoked_at": now_datetime()}
		)
		with self.assertRaises(DeviceRevoked):
			authenticate(credential_identifier, secret)

	def test_expired_credential_fails(self):
		_, credential_identifier, secret = register_test_device()
		frappe.db.set_value(
			"Device Credential", credential_identifier, "expires_at", add_to_date(now_datetime(), days=-1)
		)
		with self.assertRaises(AuthenticationFailed):
			authenticate(credential_identifier, secret)

	def test_revoked_display_fails(self):
		display, credential_identifier, secret = register_test_device()
		revoke_device(display.name)
		with self.assertRaises(DeviceRevoked):
			authenticate(credential_identifier, secret)

	def test_inactive_display_fails(self):
		display, credential_identifier, secret = register_test_device()
		frappe.db.set_value("Display", display.name, "is_active", 0)
		with self.assertRaises(DeviceDisabled):
			authenticate(credential_identifier, secret)

	def test_authenticate_bumps_last_used_at(self):
		_, credential_identifier, secret = register_test_device()
		self.assertIsNone(frappe.db.get_value("Device Credential", credential_identifier, "last_used_at"))
		authenticate(credential_identifier, secret)
		self.assertIsNotNone(frappe.db.get_value("Device Credential", credential_identifier, "last_used_at"))
