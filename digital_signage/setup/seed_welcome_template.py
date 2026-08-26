"""Seeds the 'Welcome' Content Templates (Image and Video background
variants) — a worked example of the Content Template feature, ported from
the RHS branding used in the earlier rhs-signage prototype, extended to
support any number of people (the original only ever supported one name).

    bench --site <site> execute digital_signage.setup.seed_welcome_template.run

Fonts are embedded as base64 @font-face data (not relying on the font
being installed system-wide) because the background image's baked-in
"Welcome" / "RHS Logistics LLC" text turned out to be set in Poppins
Bold/SemiBold, not the sans-serif default a browser would otherwise fall
back to. The person-overlay box's position/size and the tie-break sizing
per person-count are the result of fitting a real 1/2/3-person case inside
the background image's available space without overlapping the logo,
tagline, or "Welcome" heading — not arbitrary numbers.
"""

import base64
import os

import frappe

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

# The overlay content only -- no background of its own. The background
# (a still image, or a video with this template's Background Image
# layered on top as a low-opacity watermark) is composited by
# template_service.py's page wrapper, not baked in here; see that
# module's render_to_png/render_to_video.
HTML_BODY_TEMPLATE = """<div style="position:relative;width:100%;height:100%;">
  <style>
    @font-face { font-family: 'Poppins'; font-weight: 700; src: url(data:font/ttf;base64,__BOLD__) format('truetype'); }
    @font-face { font-family: 'Poppins'; font-weight: 600; src: url(data:font/ttf;base64,__SEMIBOLD__) format('truetype'); }
  </style>
  {% set n = people|length %}
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
  </div>
</div>"""


def _html_body():
	with open(os.path.join(_ASSETS_DIR, "poppins_bold_b64.txt")) as fh:
		bold_b64 = fh.read().strip()
	with open(os.path.join(_ASSETS_DIR, "poppins_semibold_b64.txt")) as fh:
		semibold_b64 = fh.read().strip()
	return HTML_BODY_TEMPLATE.replace("__BOLD__", bold_b64).replace("__SEMIBOLD__", semibold_b64)


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
	background_url = _upload_background_image()
	html_body = _html_body()

	if not frappe.db.exists("Content Template", "Welcome"):
		frappe.get_doc(
			{
				"doctype": "Content Template",
				"template_name": "Welcome",
				"html_body": html_body,
				"background_image": background_url,
				"background_type": "Image",
				"width": 1920,
				"height": 1080,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)
		print("created Content Template 'Welcome'")

	if not frappe.db.exists("Content Template", "Welcome (Video)"):
		frappe.get_doc(
			{
				"doctype": "Content Template",
				"template_name": "Welcome (Video)",
				"html_body": html_body,
				"background_image": background_url,
				"background_type": "Video",
				"background_overlay_opacity": 0.3,
				"width": 1920,
				"height": 1080,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)
		print("created Content Template 'Welcome (Video)' (attach a Background Video before generating)")

	frappe.db.commit()
