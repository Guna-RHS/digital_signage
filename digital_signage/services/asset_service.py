"""Asset manifest + secure download. Layers on top of state_service (itself
unmodified in spirit — build_manifest() wraps whatever `media` list a caller
passes it) rather than owning the notion of "what media is this display
allowed" — see docs/ASSET_MANAGEMENT.md.
"""

import frappe

from digital_signage.core.device_errors import DeviceValidationError


def build_manifest(media_rows):
	return [
		{
			"asset_id": row["name"],
			"version": row["asset_version"],
			"sha256": row["sha256"],
			"size": row["file_size"],
			"mime_type": row["mime_type"],
			"download_url": f"/api/method/digital_signage.api.v1.assets.download?media={row['name']}",
		}
		for row in media_rows
	]


def authorize_download(display, media_name):
	"""Only media that's actually part of this display's *synced* candidate
	set (any eligible campaign's playlist, or the fallback playlist) can be
	downloaded — not any Media record the device happens to ask for. Uses
	resolve_sync_state (the full candidate set), not resolve_effective_state
	(the single-winner desk preview) — a device needs every eligible
	campaign's assets cached to switch between them offline, not just
	whichever one would currently win. See state_service's module docstring."""
	from digital_signage.services.state_service import resolve_sync_state

	state = resolve_sync_state(display.name)
	allowed = {row["name"] for row in state["media"]}
	if media_name not in allowed:
		raise DeviceValidationError("That media is not part of this display's current state.")
	return frappe.get_doc("Media", media_name)


def stream(media_doc):
	file_doc = frappe.get_doc("File", {"file_url": media_doc.file})
	content = file_doc.get_content()
	# File.get_content() decodes to str for text-detected content — media is
	# always binary from the device's point of view (matches
	# media_service._hash_and_stamp's same normalization for hashing).
	if isinstance(content, str):
		content = content.encode("utf-8")
	frappe.response["filename"] = file_doc.file_name or media_doc.title
	frappe.response["filecontent"] = content
	frappe.response["type"] = "download"
