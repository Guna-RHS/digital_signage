import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from digital_signage.core.device_errors import DeviceNotFound, DeviceValidationError
from digital_signage.services.device_service import register_device
from digital_signage.tests.factories import make_display, make_pairing_code


class TestDeviceRegistration(FrappeTestCase):
	def test_successful_registration_returns_credential(self):
		display = make_display()
		code = make_pairing_code(display.name)

		credential_identifier, secret = register_device(display.device_identifier, code)

		self.assertTrue(credential_identifier.startswith("CRED-"))
		self.assertTrue(secret)
		self.assertEqual(frappe.db.get_value("Display", display.name, "registration_status"), "Registered")
		self.assertTrue(frappe.db.exists("Device Credential", credential_identifier))

	def test_unknown_device_identifier_raises(self):
		with self.assertRaises(DeviceNotFound):
			register_device("NO-SUCH-DEVICE", "WHATEVER1")

	def test_wrong_code_raises(self):
		display = make_display()
		make_pairing_code(display.name)
		with self.assertRaises(DeviceValidationError):
			register_device(display.device_identifier, "WRONGCODE")

	def test_expired_code_raises(self):
		display = make_display()
		code = make_pairing_code(display.name, expires_at=add_to_date(now_datetime(), minutes=-1))
		with self.assertRaises(DeviceValidationError):
			register_device(display.device_identifier, code)

	def test_already_used_code_raises(self):
		display = make_display()
		code = make_pairing_code(display.name, used_at=now_datetime())
		with self.assertRaises(DeviceValidationError):
			register_device(display.device_identifier, code)

	def test_code_scoped_to_its_own_display(self):
		display_a = make_display()
		display_b = make_display()
		code_for_a = make_pairing_code(display_a.name)
		with self.assertRaises(DeviceValidationError):
			register_device(display_b.device_identifier, code_for_a)

	def test_reregistration_revokes_prior_credential(self):
		display = make_display()
		first_id, _ = register_device(display.device_identifier, make_pairing_code(display.name))
		second_id, _ = register_device(display.device_identifier, make_pairing_code(display.name))

		self.assertNotEqual(first_id, second_id)
		self.assertFalse(frappe.db.get_value("Device Credential", first_id, "is_active"))
		self.assertTrue(frappe.db.get_value("Device Credential", second_id, "is_active"))
