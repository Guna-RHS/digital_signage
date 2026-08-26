"""Device-API exceptions — one class per ERROR_* code in core/constants.py.

api/v1/__init__.py's `device_api` decorator is the only place that turns
these into the spec's `{"error": {code, message, retryable}}` response shape
and HTTP status code; everything else just raises the right subclass.
"""

from digital_signage.core.constants import (
	ERROR_AUTHENTICATION_FAILED,
	ERROR_DEVICE_DISABLED,
	ERROR_DEVICE_NOT_FOUND,
	ERROR_DEVICE_REVOKED,
	ERROR_TEMPORARY_SERVER_ERROR,
	ERROR_VALIDATION_ERROR,
)


class DeviceApiError(Exception):
	code = ERROR_TEMPORARY_SERVER_ERROR
	http_status = 500
	retryable = True

	def __init__(self, message=None):
		self.message = message or self.code
		super().__init__(self.message)


class AuthenticationFailed(DeviceApiError):
	code = ERROR_AUTHENTICATION_FAILED
	http_status = 401
	retryable = False


class DeviceNotFound(DeviceApiError):
	code = ERROR_DEVICE_NOT_FOUND
	http_status = 404
	retryable = False


class DeviceRevoked(DeviceApiError):
	code = ERROR_DEVICE_REVOKED
	http_status = 403
	retryable = False


class DeviceDisabled(DeviceApiError):
	code = ERROR_DEVICE_DISABLED
	http_status = 403
	retryable = False


class DeviceValidationError(DeviceApiError):
	code = ERROR_VALIDATION_ERROR
	http_status = 400
	retryable = False
