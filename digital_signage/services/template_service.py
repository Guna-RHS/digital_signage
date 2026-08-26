"""Renders a Content Template's Jinja2 HTML body against a Generated
Content record's field values, and screenshots the result with a headless
Chromium (Playwright) into a real PNG — the file that then goes through
media_service.create_from_bytes exactly like any human-uploaded image.
Nothing downstream (sync, scheduling, playback) knows or cares that a given
Media was generated rather than uploaded; this module's only job is turning
a template + params into bytes.
"""

import base64
import mimetypes

import frappe

from digital_signage.core.exceptions import SignageValidationError


def _data_uri(file_url):
	"""Playwright's page.set_content() never authenticates as a desk user,
	so an <img src="/private/files/..."> reference would just 401 — every
	image goes in as an embedded data: URI instead, so the render never
	makes an HTTP request of its own."""
	if not file_url:
		return None
	content = frappe.get_doc("File", {"file_url": file_url}).get_content()
	if isinstance(content, str):
		content = content.encode("utf-8")
	mime = mimetypes.guess_type(file_url)[0] or "image/png"
	return f"data:{mime};base64,{base64.b64encode(content).decode()}"


def build_context(generated_content_doc):
	"""The Jinja2 context every Content Template body renders against."""
	template = frappe.get_doc("Content Template", generated_content_doc.content_template)
	return {
		"title": generated_content_doc.title,
		"subtitle": generated_content_doc.subtitle,
		"people": [
			{
				"person_name": p.person_name,
				"person_title": p.person_title,
				"logo_url": _data_uri(p.logo),
			}
			for p in generated_content_doc.people
		],
		"background_url": _data_uri(template.background_image),
	}


def render_to_png(template, context) -> bytes:
	"""`template` is a Content Template doc. Renders its html_body via
	frappe.render_template (server-side Jinja2 — same engine Frappe already
	uses for print formats/emails, nothing new to depend on), wraps it in a
	fixed-size page matching the template's declared width/height, and
	screenshots that exact viewport — so what admins see in the template
	editor's positioning (percentages, vw units) is pixel-for-pixel what
	gets captured, no separate re-implementation of the layout in Python."""
	try:
		from playwright.sync_api import sync_playwright
	except ImportError as e:
		raise SignageValidationError(
			"Playwright isn't installed on this server — template rendering needs it "
			"(pip install playwright && playwright install chromium)."
		) from e

	body_html = frappe.render_template(template.html_body, context)
	background_url = context.get("background_url")
	bg_image_tag = f'<img id="__bg_image" src="{background_url}">' if background_url else ""
	page_html = f"""<!doctype html>
<html><head><meta charset="utf-8">
<style>* {{ margin:0; padding:0; box-sizing:border-box; }}
html,body {{ width:{template.width}px; height:{template.height}px; overflow:hidden; position:relative; background:#fff; }}
#__bg_image {{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; z-index:0; }}
#__overlay {{ position:absolute; inset:0; width:100%; height:100%; z-index:1; }}
</style>
</head><body>
{bg_image_tag}
<div id="__overlay">{body_html}</div>
</body></html>"""

	with sync_playwright() as p:
		browser = p.chromium.launch()
		try:
			page = browser.new_page(viewport={"width": template.width, "height": template.height})
			page.set_content(page_html, wait_until="networkidle")
			return page.screenshot(type="png")
		finally:
			browser.close()


def render_to_video(template, context) -> bytes:
	"""Same idea as render_to_png, but the template's background is a video
	instead of a still image: the overlay HTML sits on top of an autoplaying
	<video>, and instead of a screenshot Playwright records the page for
	exactly the background video's own duration (read off the element's own
	`duration` once its metadata loads — never guessed or hardcoded) and
	returns that recording. Produces a .webm — the same format Playwright
	itself records in, playable directly by both Chromium-based renderers
	(desk preview) and the Tauri player's WebView2."""
	try:
		from playwright.sync_api import sync_playwright
	except ImportError as e:
		raise SignageValidationError(
			"Playwright isn't installed on this server — template rendering needs it "
			"(pip install playwright && playwright install chromium)."
		) from e

	if not template.background_video:
		raise SignageValidationError("This template's Background Type is Video, but no Background Video is attached.")

	body_html = frappe.render_template(template.html_body, context)
	video_uri = _data_uri(template.background_video)
	# Background Image is optional here — an extra watermark layered
	# between the video and the text, at this opacity (an *image* opacity:
	# CSS layering means an opaque layer fully blocks whatever's beneath it
	# regardless of that lower layer's own opacity, so putting the opacity
	# on the video instead did nothing visible — it was always fully
	# hidden either way). Most templates (e.g. Welcome) put logo/text
	# directly in html_body instead and leave Background Image unset, so
	# there's nothing to layer here at all.
	background_url = context.get("background_url")
	image_opacity = template.background_overlay_opacity or 0.85
	watermark_tag = (
		f'<img id="__bg_watermark" src="{background_url}" style="position:absolute; inset:0; '
		f'width:100%; height:100%; object-fit:cover; z-index:1; opacity:{image_opacity};">'
		if background_url
		else ""
	)
	# A sharp, unblurred video at any opacity still reads as "busy" behind
	# text — blurring it softens it into ambient motion/color rather than
	# competing detail, letting whatever's on top (the watermark, if any,
	# or the text/logo layers directly) read as dominant while the video
	# stays visibly alive underneath.
	page_html = f"""<!doctype html>
<html><head><meta charset="utf-8">
<style>* {{ margin:0; padding:0; box-sizing:border-box; }}
html,body {{ width:{template.width}px; height:{template.height}px; overflow:hidden; position:relative; }}
#__bg_video {{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; z-index:0; filter:blur(8px); transform:scale(1.05); }}
#__overlay {{ position:absolute; inset:0; width:100%; height:100%; z-index:2; }}
</style>
</head><body>
<video id="__bg_video" src="{video_uri}" autoplay muted playsinline></video>
{watermark_tag}
<div id="__overlay">{body_html}</div>
</body></html>"""

	import glob
	import os
	import tempfile

	with tempfile.TemporaryDirectory() as tmpdir:
		with sync_playwright() as p:
			browser = p.chromium.launch()
			try:
				ctx = browser.new_context(
					viewport={"width": template.width, "height": template.height},
					record_video_dir=tmpdir,
					record_video_size={"width": template.width, "height": template.height},
				)
				page = ctx.new_page()
				page.set_content(page_html, wait_until="load")
				duration_seconds = page.evaluate(
					"""() => new Promise(resolve => {
						const v = document.getElementById('__bg_video');
						if (v.readyState >= 1) resolve(v.duration);
						else v.onloadedmetadata = () => resolve(v.duration);
					})"""
				)
				page.wait_for_timeout(int(duration_seconds * 1000) + 300)
				page.close()
				ctx.close()
			finally:
				browser.close()

		webm_files = glob.glob(os.path.join(tmpdir, "*.webm"))
		if not webm_files:
			raise SignageValidationError("Video recording failed — no output was produced.")
		with open(webm_files[0], "rb") as fh:
			return fh.read()
