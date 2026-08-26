"""Seeds the 'Welcome' Content Templates (Image and Video background
variants) — a worked example of the Content Template feature, ported from
the RHS branding used in the earlier rhs-signage prototype, extended to
support any number of people (the original only ever supported one name).

    bench --site <site> execute digital_signage.setup.seed_welcome_template.run

Every static brand element (logo, "RHS Logistics LLC", tagline, "Welcome"
heading, divider line) is its own positioned HTML element here — not one
flat baked-in photo — mirroring how the rhs-signage prototype's own
`layout.html` actually composes a display (separate text/image/shape
layers with their own x/y/w/h/opacity), not a single background image.
Position/size/font values are ported directly from that prototype's own
saved layer definitions (its `layouts` SQLite table), converted from cqw to
vw (numerically identical for a fixed-width render target). Doing it this
way — rather than one composite photo — is what lets the Video background
variant show the video cleanly behind crisp text, with nothing competing
for the same pixels: swap the background behind these layers (a solid
color, or a video) without needing a second baked photo, and there's
nothing left to make opaque or transparent to control how much of it
shows through.

Fonts and the logo are embedded as base64 data (not relying on anything
being installed/reachable on whatever server runs this) because the
"Welcome" / "RHS Logistics LLC" brand type turned out to be Poppins
Bold/SemiBold, not the sans-serif default a browser would otherwise fall
back to.
"""

import os

import frappe

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

# Every static element's position/size/font is ported from the rhs-signage
# prototype's own saved layout definition (displays.current_template =
# 'layout:3' in its signage.db) -- not arbitrary numbers. Only the
# person-overlay block (position/sizing per person-count) is new, since the
# prototype only ever supported a single name.
HTML_BODY_TEMPLATE = """<div style="position:relative;width:100%;height:100%;font-family:'Poppins',sans-serif;">
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

  {% set n = people|length %}
  <div style="position:absolute;left:56.9%;top:{{ 46.9 if n == 1 else (43 if n == 2 else 39) }}%;width:30.7%;
  height:{{ 38 if n == 1 else (42 if n == 2 else 48) }}%;
  display:flex;flex-direction:column;align-items:center;justify-content:flex-start;
  gap:{{ 2.2 if n == 1 else (1.5 if n == 2 else 0.9) }}vw;text-align:center;color:#325083;">
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
	with open(os.path.join(_ASSETS_DIR, "rhs_logo_b64.txt")) as fh:
		logo_b64 = fh.read().strip()
	return (
		HTML_BODY_TEMPLATE.replace("__BOLD__", bold_b64)
		.replace("__SEMIBOLD__", semibold_b64)
		.replace("__LOGO__", logo_b64)
	)


def run():
	html_body = _html_body()

	if not frappe.db.exists("Content Template", "Welcome"):
		frappe.get_doc(
			{
				"doctype": "Content Template",
				"template_name": "Welcome",
				"html_body": html_body,
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
				"background_type": "Video",
				"width": 1920,
				"height": 1080,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)
		print("created Content Template 'Welcome (Video)' (attach a Background Video before generating)")

	frappe.db.commit()
