"""Seeds the 'Welcome' Content Templates — a worked example of the Content
Template feature, ported from the RHS branding used in the earlier
rhs-signage prototype, extended to support any number of people (the
original only ever supported one name).

    bench --site <site> execute digital_signage.setup.seed_welcome_template.run

Two different bodies, not one shared between both templates:

- 'Welcome' (Image background): the branding is the actual photo
  (welcome_background.png — the real building/logo/tagline composite) with
  just the person-overlay positioned on top, matching the original
  reference design as closely as reasonably possible.
- 'Welcome (Video)': logo/text as separate positioned HTML layers instead
  of that same baked-in photo, with no photo at all — this is the one
  that matters for the video, since an opaque photo on top of the video
  would just hide it regardless of any opacity tuning (see
  template_service.render_to_video's own docstring/comments). The photo
  version was never meant as this template's look; only the video variant
  needed to drop it.

Fonts (and, for the Video variant, the logo) are embedded as base64 data
(not relying on anything being installed/reachable on whatever server
runs this) because the "Welcome" / "RHS Logistics LLC" brand type turned
out to be Poppins Bold/SemiBold, not the sans-serif default a browser
would otherwise fall back to.
"""

import base64
import os

import frappe

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

# Shared across both variants: the person-overlay block. Position/sizing
# per person-count is the result of fitting a real 1/2/3-person case
# inside the background's available space without overlapping the logo,
# tagline, or "Welcome" heading -- not arbitrary numbers.
_PERSON_OVERLAY = """  {% set n = people|length %}
  <div style="position:absolute;left:56.9%;top:{{ 46.9 if n == 1 else (43 if n == 2 else 39) }}%;width:30.7%;
  height:{{ 38 if n == 1 else (42 if n == 2 else 48) }}%;
  display:flex;flex-direction:column;align-items:center;justify-content:flex-start;
  gap:{{ 2.2 if n == 1 else (1.5 if n == 2 else 0.9) }}vw;text-align:center;color:#325083;font-family:'Poppins',sans-serif;">
    {% for person in people %}
    <div style="display:flex;flex-direction:column;align-items:center;">
      {% if person.logo_url %}
      <img src="{{ person.logo_url }}" style="height:{{ 4.5 if n == 1 else (3.8 if n == 2 else 2.9) }}vw;max-width:26vw;object-fit:contain;margin-bottom:0.3vw;">
      {% endif %}
      <div style="font-weight:700;font-size:{{ 3.4 if n == 1 else (2.5 if n == 2 else 1.9) }}vw;line-height:1.1;text-shadow:0 0 10px rgba(255,255,255,0.95),0 0 18px rgba(255,255,255,0.85),0 2px 4px rgba(0,0,0,0.35);">{{ person.person_name }}</div>
      {% if person.person_title %}
      <div style="font-weight:600;font-size:{{ 1.7 if n == 1 else (1.35 if n == 2 else 1.0) }}vw;margin-top:0.2vw;text-shadow:0 0 8px rgba(255,255,255,0.95),0 0 14px rgba(255,255,255,0.8),0 2px 3px rgba(0,0,0,0.3);">{{ person.person_title }}</div>
      {% endif %}
    </div>
    {% endfor %}
  </div>"""

# Image variant: the actual photo as the root div's own background --
# background_url is supplied by template_service.build_context from this
# template's Background Image field, same as any other Image-type template.
_IMAGE_HTML_BODY = (
	"""<div style="position:relative;width:100%;height:100%;
background-image:url('{{ background_url }}');background-size:cover;background-position:center;
background-repeat:no-repeat;">
  <style>
    @font-face { font-family: 'Poppins'; font-weight: 700; src: url(data:font/ttf;base64,__BOLD__) format('truetype'); }
    @font-face { font-family: 'Poppins'; font-weight: 600; src: url(data:font/ttf;base64,__SEMIBOLD__) format('truetype'); }
  </style>
"""
	+ _PERSON_OVERLAY
	+ "\n</div>"
)

# Video variant: logo + every static text element as its own positioned
# layer -- no photo at all, so the video shows fully behind them. Position/
# size/font values are ported directly from the rhs-signage prototype's own
# saved layer definitions (its `layouts` SQLite table, displays.
# current_template = 'layout:3'), converted from cqw to vw (numerically
# identical for a fixed-width render target).
_VIDEO_HTML_BODY = (
	"""<div style="position:relative;width:100%;height:100%;font-family:'Poppins',sans-serif;">
  <style>
    @font-face { font-family: 'Poppins'; font-weight: 700; src: url(data:font/ttf;base64,__BOLD__) format('truetype'); }
    @font-face { font-family: 'Poppins'; font-weight: 600; src: url(data:font/ttf;base64,__SEMIBOLD__) format('truetype'); }
  </style>

  <img src="data:image/png;base64,__LOGO__" style="position:absolute;left:5.9%;top:11.8%;width:34.4%;height:34.6%;object-fit:contain;">

  <div style="position:absolute;left:2.6%;top:46.9%;width:41.1%;height:13.5%;font-size:5.625vw;font-weight:700;color:#325083;text-align:left;">RHS Logistics LLC</div>

  <div style="position:absolute;left:9%;top:60.3%;width:34.6%;height:4.5%;font-size:1.425vw;font-style:italic;color:#325083;text-align:right;">Your preferred Logistics PARTNER for regional distribution</div>

  <div style="position:absolute;left:17%;top:66.8%;width:26.6%;height:9.4%;font-size:1.425vw;font-weight:700;font-style:italic;color:#325083;text-align:right;white-space:pre-line;">Rais Hassan Saadi  (RHS) Group
Established 1910</div>

  <div style="position:absolute;left:44.6%;top:7.3%;width:0.15%;height:85.4%;background-color:#325083;"></div>

  <div style="position:absolute;left:53.56%;top:21.57%;width:37.37%;height:16.16%;display:flex;align-items:center;justify-content:center;font-size:6.87vw;font-weight:700;color:#325083;text-align:center;">Welcome</div>

"""
	+ _PERSON_OVERLAY
	+ "\n</div>"
)


def _fonts():
	with open(os.path.join(_ASSETS_DIR, "poppins_bold_b64.txt")) as fh:
		bold_b64 = fh.read().strip()
	with open(os.path.join(_ASSETS_DIR, "poppins_semibold_b64.txt")) as fh:
		semibold_b64 = fh.read().strip()
	return bold_b64, semibold_b64


def _upload_background_image():
	existing = frappe.db.exists("File", {"file_name": "welcome_background.png"})
	if existing:
		return frappe.db.get_value("File", existing, "file_url")
	with open(os.path.join(_ASSETS_DIR, "welcome_background.png"), "rb") as fh:
		content = fh.read()
	f = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": "welcome_background.png",
			"content": base64.b64encode(content).decode(),
			"decode": True,
			"is_private": 1,
		}
	)
	f.insert(ignore_permissions=True)
	return f.file_url


def run():
	bold_b64, semibold_b64 = _fonts()

	if not frappe.db.exists("Content Template", "Welcome"):
		background_url = _upload_background_image()
		image_html_body = _IMAGE_HTML_BODY.replace("__BOLD__", bold_b64).replace("__SEMIBOLD__", semibold_b64)
		frappe.get_doc(
			{
				"doctype": "Content Template",
				"template_name": "Welcome",
				"html_body": image_html_body,
				"background_image": background_url,
				"background_type": "Image",
				"width": 1920,
				"height": 1080,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)
		print("created Content Template 'Welcome'")

	if not frappe.db.exists("Content Template", "Welcome (Video)"):
		with open(os.path.join(_ASSETS_DIR, "rhs_logo_b64.txt")) as fh:
			logo_b64 = fh.read().strip()
		video_html_body = (
			_VIDEO_HTML_BODY.replace("__BOLD__", bold_b64).replace("__SEMIBOLD__", semibold_b64).replace("__LOGO__", logo_b64)
		)
		frappe.get_doc(
			{
				"doctype": "Content Template",
				"template_name": "Welcome (Video)",
				"html_body": video_html_body,
				"background_type": "Video",
				"width": 1920,
				"height": 1080,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)
		print("created Content Template 'Welcome (Video)' (attach a Background Video before generating)")

	frappe.db.commit()
