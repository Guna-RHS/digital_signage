"""device_api: the shared wrapper every api/v1/*.py endpoint uses. Turns a
DeviceApiError into the spec's exact error envelope
(`{"error": {code, message, retryable}}`) with the right HTTP status code,
and turns anything unexpected into a TEMPORARY_SERVER_ERROR after logging —
never a raw traceback to the device (spec: "Do not return stack traces to
signage devices").

Also the one place that explicitly commits on success. Frappe only
auto-commits after *unsafe* HTTP methods (POST/PUT/DELETE/PATCH) —
deliberately not after GET, since GET is supposed to be side-effect-free.
`sync.get` isn't (it bumps Display.last_sync_at/last_sync_version), and
core/device_auth.py's last_used_at bump runs on every authenticated call
including the GET ones — both were being silently discarded on every real
GET request until this was added. Caught by manual testing against the
running client, not by any test in this suite: every existing test calls
the service functions directly in Python, never through an actual HTTP GET,
so the missing commit was invisible to them."""

import functools

import frappe

from digital_signage.core.device_errors import DeviceApiError


def device_api(fn):
	@functools.wraps(fn)
	def wrapper(*args, **kwargs):
		try:
			result = fn(*args, **kwargs)
			frappe.db.commit()
			frappe.response["http_status_code"] = 200
			return result
		except DeviceApiError as e:
			frappe.response["http_status_code"] = e.http_status
			return {"error": {"code": e.code, "message": e.message, "retryable": e.retryable}}
		except TypeError:
			# A required param was never passed — Frappe's own kwarg binding
			# raises this before validation logic ever runs, so it needs its
			# own mapping rather than falling into the generic 500 below.
			frappe.response["http_status_code"] = 400
			return {
				"error": {
					"code": "VALIDATION_ERROR",
					"message": "Missing or invalid request parameters.",
					"retryable": False,
				}
			}
		except Exception:
			frappe.log_error(title=f"digital_signage.api.v1.{fn.__name__} failed")
			frappe.response["http_status_code"] = 500
			return {
				"error": {
					"code": "TEMPORARY_SERVER_ERROR",
					"message": "An unexpected error occurred.",
					"retryable": True,
				}
			}

	return wrapper
