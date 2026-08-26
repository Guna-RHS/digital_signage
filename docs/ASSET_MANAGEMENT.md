# Asset Management

## Manifest shape

Every entry in a `sync.get` response's `assets` array
(`services/asset_service.build_manifest`):

```json
{
  "asset_id": "MEDIA-00001",
  "version": 1,
  "sha256": "2bb3bbc5...",
  "size": 15,
  "mime_type": "image/png",
  "download_url": "/api/method/digital_signage.api.v1.assets.download?media=MEDIA-00001"
}
```

Matches the spec exactly. `version` is `Media.asset_version` (Milestone 1 —
bumped when the file content's hash changes, not on every save). A changed
`server_version` on the envelope does **not** imply every asset changed — a
client should diff each manifest entry's `sha256`/`version` against what it
already has cached and only re-download what actually changed (the spec's
"A changed server version alone must not force redownloading unchanged
assets" — the manifest is what makes that diffing possible; this backend
doesn't decide what's "changed" for the client, it just always reports the
current truth).

## Authorization: scoped to current state, not "any Media"

`asset_service.authorize_download(display, media_name)` calls
`state_service.resolve_sync_state(display)` (the same full candidate set
`sync.get` sends — see `SCHEDULING_AND_PRIORITY.md`, not the single-winner
`resolve_effective_state`) and only allows a download if `media_name`
appears in that response's `media` list — i.e. it's actually part of *some*
eligible campaign's playlist or the fallback playlist. A device needs every
eligible campaign's assets cached to switch between them offline, not just
whichever would currently win. A device cannot use a valid credential to
fetch arbitrary Media records
by guessing/enumerating names — verified in `test_asset_download.py` with a
real, valid, Active Media record that just isn't assigned to the requesting
display, and confirmed rejected with `VALIDATION_ERROR` (400) over real HTTP.

This also means a device must be able to reach `sync.get` (or have recently)
for asset downloads for genuinely current content to succeed — that's
intentional, not an oversight; there's no route to fetch media that isn't
part of what was actually synced.

## How assets are actually served

`GET assets.download` sets three keys on `frappe.response` — the same
pattern Frappe's own `frappe/core/api/file.py` uses:

```python
frappe.response["filename"] = file_doc.file_name
frappe.response["filecontent"] = content   # bytes
frappe.response["type"] = "download"
```

Frappe's response builder turns that into a real
`Content-Disposition: attachment` / correct `Content-Type` HTTP response —
confirmed with `curl -D -` during this milestone's manual verification pass
(headers, byte-for-byte content, and the sha256 all checked out against the
source Media record).

## Known limitation: in-memory streaming

`File.get_content()` reads the entire file into memory before
`asset_service.stream()` hands it to `frappe.response`. Fine for images and
modest video files; a real limitation for large video assets — no
range-request support, no chunked/streamed transfer, and a large file briefly
occupies memory equal to its own size on every download. Not addressed in
this milestone. A future milestone should revisit this — options include
redirecting to a signed, time-limited URL for large files, or genuine
chunked streaming from disk.
